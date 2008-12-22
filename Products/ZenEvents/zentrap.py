###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """zentrap

Creates events from SNMP Traps.
Currently a wrapper around the Net-SNMP C library.
"""

import time
import sys
import socket
import cPickle

# Magical interfacing with C code
import ctypes as c

import Globals

from EventServer import EventServer

from pynetsnmp import netsnmp, twistedsnmp

from twisted.internet import defer, reactor
from Products.ZenUtils.Driver import drive


# This is what struct sockaddr_in {} looks like
family = [('family', c.c_ushort)]
if sys.platform == 'darwin':
    family = [('len', c.c_ubyte), ('family', c.c_ubyte)]

class sockaddr_in(c.Structure):
    _fields_ = family + [
        ('port', c.c_ubyte * 2),        # need to decode from net-byte-order
        ('addr', c.c_ubyte * 4)
        ];

# teach python that the return type of snmp_clone_pdu is a pdu pointer
netsnmp.lib.snmp_clone_pdu.restype = netsnmp.netsnmp_pdu_p

TRAP_PORT = 162
try:
    TRAP_PORT = socket.getservbyname('snmptrap', 'udp')
except socket.error:
    pass

def lp2oid(ptr, length):
    "Convert a pointer to an array of longs to an oid"
    return '.'.join([str(ptr[i]) for i in range(length)])

def bp2ip(ptr):
    "Convert a pointer to 4 bytes to a dotted-ip-address"
    return '.'.join([str(ptr[i]) for i in range(4)])

# Some vendors form their trap MIBs to insert a 0 before the
# specific part of the v1 trap, but the device doesn't actually
# send the 0. Unfortunately we have to make explicit exceptions
# for these to get the OIDs decoded properly.
expandableV1Prefixes = (
    '1.3.6.1.2.1.17',        # Spanning Tree Protocol
    '1.3.6.1.4.1.1916',      # Extreme Networks
    '1.3.6.1.4.1.6247',      # Comtech
    '1.3.6.1.4.1.8072',      # Net-SNMP
    '1.3.6.1.4.1.12394.1.2', # Rainbow
    )

class FakePacket(object):
    """
    A fake object to make packet replaying feasible.
    """
    def __init__(self):
        self.fake = True


class ZenTrap(EventServer):
    """
    Listen for SNMP traps and turn them into events
    Connects to the EventService service in zenhub.
    """

    name = 'zentrap'

    def __init__(self):
        EventServer.__init__(self)

        self.oidCache = {}

        # Command-line argument sanity checking
        if self.options.captureFilePrefix and len(self.options.replayFilePrefix) > 0:
            self.log.error( "Can't specify both --captureFilePrefix and -replayFilePrefix" \
                 " at the same time.  Exiting" )
            sys.exit(1)

        if self.options.captureFilePrefix and not self.options.captureAll and \
            self.optionscaptureIps == '':
            self.log.warn( "Must specify either --captureIps or --captureAll for" + \
                 " --capturePrefix to take effect.  Ignoring option --capturePrefix" )

        if len(self.options.replayFilePrefix) > 0:
            self.connected = self.replayAll
            return

        if not self.options.useFileDescriptor and self.options.trapport < 1024:
            self.openPrivilegedPort('--listen', '--proto=udp',
                '--port=%s:%d' % (self.options.listenip,
                self.options.trapport))
        self.session = netsnmp.Session()
        if self.options.useFileDescriptor is not None:
            fileno = int(self.options.useFileDescriptor)
            # open port 1162, but then dup fileno onto it
            self.session.awaitTraps('%s:1162' % self.options.listenip, fileno)
        else:
            self.session.awaitTraps('%s:%d' % (
                self.options.listenip, self.options.trapport))
        self.session.callback = self.receiveTrap

        self.captureSerialNum = 0
        self.captureIps = self.options.captureIps.split(',')

        twistedsnmp.updateReactor()


    def getEnterpriseString(self, pdu):
        """
        Get the enterprise string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: enterprise string
        @rtype: string
        """
        if hasattr(pdu, "fake"): # Replaying a packet
            enterprise = pdu.enterprise
        else:
            enterprise = lp2oid(pdu.enterprise, pdu.enterprise_length)
        return enterprise


    def getResult(self, pdu):
        """
        Get the values from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: variables from the PDU or Fake packet
        @rtype: dictionary
        """
        if hasattr(pdu, "fake"): # Replaying a packet
            variables = pdu.variables
        else:
            variables = netsnmp.getResult(pdu)
        return variables



    def getCommunity(self, pdu):
        """
        Get the communitry string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: SNMP community
        @rtype: string
        """
        community = ''
        if hasattr(pdu, "fake"): # Replaying a packet
            community = pdu.community
        elif pdu.community_len:
                community = c.string_at(pdu.community, pdu.community_len)

        return community


    def convertPacketToPython(self, addr, pdu):
        """
        Store the raw packet for later examination and troubleshooting.

        @param addr: packet-sending host's IP address and port
        @type addr: (string, number)
        @param pdu: raw packet
        @type pdu: binary
        @return: Python FakePacket object
        @rtype: Python FakePacket object
        """
        packet = FakePacket()
        packet.version = pdu.version
        packet.host = addr[0]
        packet.port = addr[1]
        packet.variables = netsnmp.getResult(pdu)
        packet.community = ''

        # Here's where we start to encounter differences between packet types
        if pdu.version == 0:
            packet.agent_addr = pdu.agent_addr
            packet.trap_type = pdu.trap_type
            packet.specific_type = pdu.specific_type
            packet.enterprise = self.getEnterpriseString(pdu)
            packet.community = self.getCommunity(pdu)

        return packet


    def capturePacket(self, addr, pdu):
        """
        Store the raw packet for later examination and troubleshooting.

        @param addr: packet-sending host's IP address and port
        @type addr: (string, number)
        @param pdu: raw packet
        @type pdu: binary
        """
        # Save the raw data if requested to do so
        if not self.options.captureFilePrefix:
            return
        host = addr[0]
        if not self.options.captureAll and host not in self.captureIps:
            self.log.debug( "Received packet from %s, but not in %s" % (host,
                            self.captureIps))
            return

        self.log.debug( "Capturing packet from %s" % host )
        name = "%s-%s-%d" % (self.options.captureFilePrefix, host, self.captureSerialNum)
        try:
            packet = self.convertPacketToPython(addr, pdu)
            capFile = open( name, "wb")
            data= cPickle.dumps(packet, cPickle.HIGHEST_PROTOCOL)
            capFile.write(data)
            capFile.close()
            self.captureSerialNum += 1
        except:
            self.log.exception("Couldn't write capture data to '%s'" % name )


    def replayAll(self):
        """
        Replay all captured packets using the files specified in
        the --replayFilePrefix option and then exit.

        Note that this calls the Twisted stop() method
        """
        # Note what you are about to see below is a direct result of optparse
        # adding in the arguments *TWICE* each time --replayFilePrefix is used.
        import glob
        files = []
        for filespec in self.options.replayFilePrefix:
            files += glob.glob( filespec + '*' )

        self.loaded = 0
        self.replayed = 0
        from sets import Set
        for file in Set(files):
            self.log.debug( "Attempting to read packet data from '%s'" % file )
            try:
                fp = open( file, "rb" )
                pdu= cPickle.load(fp)
                fp.close()
                self.loaded += 1

            except IOError:
                fp.close()
                self.log.exception( "Unable to load packet data from %s" % file )

            self.replay(pdu)

        self.replayStop()


    def replay(self, pdu):
        """
        Replay a captured packet

        @param pdu: raw packet
        @type pdu: binary
        """
        ts = time.time()
        d = self.asyncHandleTrap((pdu.host, pdu.port), pdu, ts)


    def replayStop(self):
        """
        Twisted method that we use to override the default stop() method
        for when we are replaying packets.  This version waits to make
        sure that all of our deferreds have exited before pulling the plug.
        """
        self.log.debug( "Replayed %d of %d packets" % (self.replayed, self.loaded ) )
        if self.replayed == self.loaded:
            self.log.info( "Loaded and replayed %d packets" % self.replayed )
            self.stop()
        else:
            reactor.callLater( 1, self.replayStop )



    def oid2name(self, oid, exactMatch=True, strip=False):
        """
        Get OID name from cache or ZenHub

        @param oid: SNMP Object IDentifier
        @type oid: string
        @param exactMatch: find the full OID or don't match
        @type exactMatch: boolean
        @param strip: show what matched, or matched + numeric OID remainder
        @type strip: boolean
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        @todo: make exactMatch and strip work
        """
        if type(oid) == type(()):
            oid = '.'.join(map(str, oid))
        cacheKey = "%s:%r:%r" % (oid, exactMatch, strip)
        if self.oidCache.has_key(cacheKey):
            return defer.succeed(self.oidCache[cacheKey])

        self.log.debug("OID cache miss on %s (exactMatch=%r, strip=%r)" % (
            oid, exactMatch, strip))
        # Note: exactMatch and strip are ignored by zenhub
        d = self.model().callRemote('oid2name', oid, exactMatch, strip)

        def cache(name, key):
            """
            Twisted callback to cache and return the name

            @param name: human-readable-name form of OID
            @type name: string
            @param key: key of OID and params
            @type key: string
            @return: the name parameter
            @rtype: string
            """
            self.oidCache[key] = name
            return name

        d.addCallback(cache, cacheKey)
        return d


    def receiveTrap(self, pdu):
        """
        Accept a packet from the network and spin off a Twisted
        deferred to handle the packet.

        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        """
        ts = time.time()

        # Is it a trap?
        if pdu.sessid != 0: return

        if pdu.version not in [ 0, 1 ]:
            self.log.error("Unable to handle trap version %d", pdu.version)
            return

        # What address did it come from?
        #   for now, we'll make the scary assumption this data is a
        #   sockaddr_in
        transport = c.cast(pdu.transport_data, c.POINTER(sockaddr_in))
        if not transport: return
        transport = transport.contents

        #   Just to make sure, check to see that it is type AF_INET
        if transport.family != socket.AF_INET: return
        # get the address out as ( host-ip, port)
        addr = [bp2ip(transport.addr),
                transport.port[0] << 8 | transport.port[1]]

        self.log.debug( "Received packet from %s at port %s" % (addr[0], addr[1]) )
        self.processPacket(addr, pdu, ts)


    def processPacket(self, addr, pdu, ts):
        """
        Wrapper around asyncHandleTrap to process the provided packet.

        @param addr: packet-sending host's IP address, port info
        @type addr: ( host-ip, port)
        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        @param ts: time stamp
        @type ts: datetime
        """
        # At the end of this callback, pdu will be deleted, so copy it
        # for asynchronous processing
        dup = netsnmp.lib.snmp_clone_pdu(c.addressof(pdu))
        if not dup:
            self.log.error("Could not clone PDU for asynchronous processing")
            return
        
        def cleanup(result):
            """
            Twisted callback to delete a previous memory allocation

            @param result: Net-SNMP object
            @type result: netsnmp_pdu object
            @return: the result parameter
            @rtype: binary
            """
            netsnmp.lib.snmp_free_pdu(dup)
            return result

        d = self.asyncHandleTrap(addr, dup.contents, ts)
        d.addBoth(cleanup)


    def asyncHandleTrap(self, addr, pdu, ts):
        """
        Twisted callback to process a trap

        @param addr: packet-sending host's IP address, port info
        @type addr: ( host-ip, port)
        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        @param ts: time stamp
        @type ts: datetime
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        def inner(driver):
            """
            Generator function that actually processes the packet

            @param driver: Twisted deferred object
            @type driver: Twisted deferred object
            @return: Twisted deferred object
            @rtype: Twisted deferred object
            """
            self.capturePacket( addr, pdu)

            eventType = 'unknown'
            result = {}
            if pdu.version == 1:
                # SNMP v2
                variables = self.getResult(pdu)
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    # SNMPv2-MIB/snmpTrapOID
                    if oid == '1.3.6.1.6.3.1.1.4.1.0':
                        yield self.oid2name(value, exactMatch=False, strip=False)
                        eventType = driver.next()
                    else:
                        yield self.oid2name(oid, exactMatch=False, strip=True)
                        result[driver.next()] = value

            elif pdu.version == 0:
                # SNMP v1
                variables = self.getResult(pdu)
                addr[0] = '.'.join(map(str, [pdu.agent_addr[i] for i in range(4)]))
                enterprise = self.getEnterpriseString(pdu)
                yield self.oid2name(enterprise, exactMatch=False, strip=False)
                eventType = driver.next()
                generic = pdu.trap_type
                specific = pdu.specific_type
                oid = "%s.%d" % (enterprise, specific)
                for oidPrefix in expandableV1Prefixes:
                    if enterprise.startswith(oidPrefix):
                        oid = "%s.0.%d" % (enterprise, specific)
                                
                yield self.oid2name(oid, exactMatch=False, strip=False)
                eventType = { 0 : 'snmp_coldStart',
                              1 : 'snmp_warmStart',
                              2 : 'snmp_linkDown',
                              3 : 'snmp_linkUp',
                              4 : 'snmp_authenticationFailure',
                              5 : 'snmp_egpNeighorLoss',
                              6 : driver.next()
                              }.get(generic, eventType + "_%d" % specific)
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    yield self.oid2name(oid, exactMatch=False, strip=True)
                    result[driver.next()] = value
            else:
                self.log.error("Unable to handle trap version %d", pdu.version)
                return

            summary = 'snmp trap %s' % eventType
            self.log.debug(summary)
            community = self.getCommunity(pdu)
            result['device'] = addr[0]
            result.setdefault('component', '')
            result.setdefault('eventClassKey', eventType)
            result.setdefault('eventGroup', 'trap')
            result.setdefault('severity', 3)
            result.setdefault('summary', summary)
            result.setdefault('community', community)
            result.setdefault('firstTime', ts)
            result.setdefault('lastTime', ts)
            result.setdefault('monitor', self.options.monitor)
            self.sendEvent(result)

            # Dont' attempt to respond back if we're replaying packets
            if len(self.options.replayFilePrefix) > 0:
                self.replayed += 1
                return

            # respond to INFORM requests
            if pdu.command == netsnmp.SNMP_MSG_INFORM:
                reply = netsnmp.lib.snmp_clone_pdu(c.addressof(pdu))
                if not reply:
                    self.log.error("Could not clone PDU for INFORM response")
                    raise RuntimeError("Cannot respond to INFORM PDU")
                reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
                reply.contents.errstat = 0
                reply.contents.errindex = 0
                sess = netsnmp.Session(peername='%s:%d' % tuple(addr),
                                       version=pdu.version)
                sess.open()
                if not netsnmp.lib.snmp_send(sess.sess, reply):
                    netsnmp.lib.snmp_sess_perror("Unable to send inform PDU",
                                                 self.session.sess)
                    netsnmp.lib.snmp_free_pdu(reply)
                sess.close()
        return drive(inner)


    def buildOptions(self):
        """
        Command-line options to be supported
        """
        EventServer.buildOptions(self)
        self.parser.add_option('--trapport', '-t',
            dest='trapport', type='int', default=TRAP_PORT,
            help="Listen for SNMP traps on this port rather than the default")
        self.parser.add_option('--listenip',
            dest='listenip', default='0.0.0.0',
            help="IP address to listen on. Default is 0.0.0.0")
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               help=("Read from an existing connection "
                                     " rather than opening a new port."),
                               default=None)
        self.parser.add_option('--captureFilePrefix',
                               dest='captureFilePrefix',
                               default=None,
                               help="Directory and filename to use as a template" + \
                               "  to store captured raw trap packets.")
        self.parser.add_option('--captureAll',
                               dest='captureAll',
                               action='store_true',
                               default=False,
                               help="Capture all packets.")
        self.parser.add_option('--captureIps',
                               dest='captureIps',
                               default='',
                               help="Comma-separated list of IP addresses to capture.")
        self.parser.add_option('--replayFilePrefix',
                               dest='replayFilePrefix',
                               action='append',
                               default=[],
             help="Filename prefix containing captured packet data. Can specify more than once.")



if __name__ == '__main__':
    z = ZenTrap()
    z.run()
    z.report()


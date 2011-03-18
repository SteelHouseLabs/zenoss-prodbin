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
import base64
from struct import unpack
from ipaddr import IPAddress
from exceptions import EOFError, IOError

# Magical interfacing with C code
import ctypes as c

import Globals

from EventServer import EventServer

from pynetsnmp import netsnmp, twistedsnmp

from twisted.internet import defer, reactor
from Products.ZenHub.PBDaemon import FakeRemote
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.captureReplay import CaptureReplay



# This is what struct sockaddr_in {} looks like
family = [('family', c.c_ushort)]
if sys.platform == 'darwin':
    family = [('len', c.c_ubyte), ('family', c.c_ubyte)]

class sockaddr_in(c.Structure):
    _fields_ = family + [
        ('port', c.c_ubyte * 2),        # need to decode from net-byte-order
        ('addr', c.c_ubyte * 4)
        ];

class sockaddr_in6(c.Structure):
    _fields_ = family + [
        ('port', c.c_ubyte * 2),        # need to decode from net-byte-order
        ('flow', c.c_ubyte * 4),
        ('addr', c.c_ubyte * 16),
        ('scope_id', c.c_ubyte * 4)
        ];


# teach python that the return type of snmp_clone_pdu is a pdu pointer
netsnmp.lib.snmp_clone_pdu.restype = netsnmp.netsnmp_pdu_p

TRAP_PORT = 162
try:
    TRAP_PORT = socket.getservbyname('snmptrap', 'udp')
except socket.error:
    pass

def lp2oid(ptr, length):
    "Convert a pointer to an array of longs to an OID"
    return '.'.join([str(ptr[i]) for i in range(length)])


class FakePacket(object):
    """
    A fake object to make packet replaying feasible.
    """
    def __init__(self):
        self.fake = True


class ZenTrap(EventServer, CaptureReplay):
    """
    Listen for SNMP traps and turn them into events
    Connects to the TrapService service in zenhub.
    """

    name = 'zentrap'
    initialServices = EventServer.initialServices + ['TrapService']
    oidMap = {}
    haveOids = False

    def __init__(self):
        EventServer.__init__(self)

        # Command-line argument sanity checking
        self.processCaptureReplayOptions()

        # Check for IPv6-ness
        listenip = self.options.listenip
        #if IPAddress(listenip).version == 6:
        #    listenip = 'udp6:' + listenip

        if not self.options.useFileDescriptor and self.options.trapport < 1024:
            # Makes call to zensocket here
            self.openPrivilegedPort('--listen', '--proto=udp',
                '--port=%s:%d' % (listenip, self.options.trapport))

        self.session = netsnmp.Session()
        if self.options.useFileDescriptor is not None:
            fileno = int(self.options.useFileDescriptor)
            # open port 1162, but then dup fileno onto it
            self.session.awaitTraps('%s:1162' % listenip, fileno)
        else:
            # NOTE: on bad input listenip, pukes with SnmpError exception
            self.session.awaitTraps('%s:%d' % (listenip, self.options.trapport))
        self.session.callback = self.receiveTrap

        twistedsnmp.updateReactor()

    def isReplaying(self):
        """
        @returns True if we are replaying a packet instead of capturing one
        """
        return len(self.options.replayFilePrefix) > 0

    def configure(self):
        def inner(driver):
            self.log.info("fetching default RRDCreateCommand")
            yield self.model().callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            self.log.info("getting threshold classes")
            yield self.model().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())

            self.log.info("getting collector thresholds")
            yield self.model().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor, self.name,
                                 driver.next(), createCommand)

            self.log.info("getting OID -> name mappings")
            yield self.getServiceNow('TrapService').callRemote('getOidMap')
            self.oidMap = driver.next()
            self.haveOids = True
            # Trac #6563 the heartbeat shuts down the service
            # before the eventserver is ready to send the events
            # so we ignore the heartbeat
            # (replay is always in non-cycle mode)
            if not self.isReplaying():
                self.heartbeat()
            self.reportCycle()

        d = drive(inner)
        def error(result):
            self.log.error("Unexpected error in configure: %s" % result)
        d.addErrback(error)
        return d

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
        packet.enterprise_length = pdu.enterprise_length
        # Here's where we start to encounter differences between packet types
        if pdu.version == 0:
            # SNMPv1 can't be received via IPv6
            packet.agent_addr =  [pdu.agent_addr[i] for i in range(4)]
            packet.trap_type = pdu.trap_type
            packet.specific_type = pdu.specific_type
            packet.enterprise = self.getEnterpriseString(pdu)
            packet.community = self.getCommunity(pdu)

        return packet

    def replay(self, pdu):
        """
        Replay a captured packet

        @param pdu: raw packet
        @type pdu: binary
        """
        ts = time.time()
        d = self.asyncHandleTrap([pdu.host, pdu.port], pdu, ts)

    def oid2name(self, oid, exactMatch=True, strip=False):
        """
        Returns a MIB name based on an OID and special handling flags.

        @param oid: SNMP Object IDentifier
        @type oid: string
        @param exactMatch: find the full OID or don't match
        @type exactMatch: boolean
        @param strip: show what matched, or matched + numeric OID remainder
        @type strip: boolean
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        if type(oid) == type(()):
            oid = '.'.join(map(str, oid))

        oid = oid.strip('.')
        if exactMatch:
            if oid in self.oidMap:
                return self.oidMap[oid]
            else:
                return oid

        oidlist = oid.split('.')
        for i in range(len(oidlist), 0, -1):
            name = self.oidMap.get('.'.join(oidlist[:i]), None)
            if name is None:
                continue

            oid_trail = oidlist[i:]
            if len(oid_trail) > 0 and not strip:
                return "%s.%s" % (name, '.'.join(oid_trail))
            else:
                return name

        return oid

    def receiveTrap(self, pdu):
        """
        Accept a packet from the network and spin off a Twisted
        deferred to handle the packet.

        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        """
        if not self.haveOids:
            return

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
        if not transport:
            self.log.warn("Not able to convert a trap into a readable object -- ignoring")
            return

        if transport.contents.family == socket.AF_INET6:
            transport = c.cast(pdu.transport_data, c.POINTER(sockaddr_in6))
            if not transport:
                self.log.warn("Not able to convert a trap into a readable object -- ignoring")
                return

        transport = transport.contents
        import pdb;pdb.set_trace()

        #  Just to make sure, check to see that it is type AF_INET or AF_INET6
        if transport.family not in (socket.AF_INET, socket.AF_INET6):
            self.log.warn("Got a packet with unrecognized network family: %s",
                          transport.family)
            return

        # get the address out as ( host-ip, port)
        addr = [self.getPacketIp(transport), transport.port[0] << 8 | transport.port[1]]

        self.log.debug( "Received packet from %s at port %s" % (addr[0], addr[1]) )
        self.processPacket(addr, pdu, ts)

    def getPacketIp(self, transport):
        """
        For IPv4, convert a pointer to 4 bytes to a dotted-ip-address
        For IPv6, convert a pointer to 16 bytes to a canonical IPv6 address.
        """
        if transport.family == socket.AF_INET:
            return '.'.join([str(transport.addr[i]) for i in range(4)])
        elif transport.family == socket.AF_INET6:
            # To form an IPv6 address, need to combine pairs of octets (in hex)
            # and join them with a colon
            self.log.error("transport.addr = %s", [i for i in transport.addr])
            ipv6 = ':'.join([ "%x%x" % tuple(map(int, x)) \
                                  for x in zip(transport.addr[::2], transport.addr[1::2]) ])
            # Now canonicalize the IP
            try:
                ip = str(IPAddress(ipv6))
                return ip
            except ValueError:
                self.log.warn("The IPv6 address is incorrect: %s", ipv6)
                return "::"

        self.log.error("Unknown address family %s", transport.family)
        return "0.0.0.0"

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
        dup = netsnmp.lib.snmp_clone_pdu(c.byref(pdu))
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

    def _value_from_dateandtime(self, value):
        """
        Tries convering a DateAndTime value to printable string.
        A date-time specification.
        field  octets  contents                  range
                -----  ------  --------                  -----
                  1      1-2   year*                     0..65536
                  2       3    month                     1..12
                  3       4    day                       1..31
                  4       5    hour                      0..23
                  5       6    minutes                   0..59
                  6       7    seconds                   0..60
                               (use 60 for leap-second)
                  7       8    deci-seconds              0..9
                  8       9    direction from UTC        '+' / '-'
                  9      10    hours from UTC*           0..13
                 10      11    minutes from UTC          0..59
        """
        strval = None
        vallen = len(value)
        if vallen == 8 or (vallen == 11 and value[8] in ('+','-')):
            (year, mon, day, hour, mins, secs, dsecs) = unpack(">HBBBBBB", value[:8])
            # Ensure valid date representation
            if mon < 1 or mon > 12:
                return None
            if day < 1 or day > 31:
                return None
            if hour < 0 or hour > 23:
                return None
            if mins > 60:
                return None
            if secs > 60:
                return None
            if dsecs > 9:
                return None
            if vallen == 11:
                utc_dir = value[8]
                (utc_hours, utc_mins) = unpack(">BB", value[9:])
            else:
                tz_mins = time.timezone / 60
                if tz_mins < 0:
                    utc_dir = '-'
                    tz_mins = -tz_mins
                else:
                    utc_dir = '+'
                utc_hours = tz_mins / 60
                utc_mins = tz_mins % 60
            strval = "%04d-%02d-%02dT%02d:%02d:%02d.%d00%s%02d:%02d" % (year,
                mon, day, hour, mins, secs, dsecs, utc_dir, utc_hours, utc_mins)

        return strval

    def _convert_value(self, value):
        if not isinstance(value, basestring):
            return value
        try:
            value.decode('utf8')
            return value
        except UnicodeDecodeError:
            # Try converting to a date
            decoded = self._value_from_dateandtime(value)
            if not decoded:
                decoded = 'BASE64:' + base64.b64encode(value)
            return decoded

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
            self.capturePacket(addr[0], addr, pdu)

            oid = ''
            eventType = 'unknown'
            result = {}

            # Some misbehaving agents will send SNMPv1 traps contained within
            # an SNMPv2c PDU. So we can't trust tpdu.version to determine what
            # version trap exists within the PDU. We need to assume that a
            # PDU contains an SNMPv1 trap if the enterprise_length is greater
            # than zero in addition to the PDU version being 0.

            if pdu.version == 0 or pdu.enterprise_length > 0:
                # SNMP v1
                variables = self.getResult(pdu)

                # Sometimes the agent_addr is useless. Use addr[0] unchanged in
                # this case.
                # Note that SNMPv1 packets *cannot* come in via IPv6
                new_addr = '.'.join(map(str, [
                    pdu.agent_addr[i] for i in range(4)]))

                if new_addr != '0.0.0.0':
                    addr[0] = new_addr

                enterprise = self.getEnterpriseString(pdu)
                eventType = self.oid2name(
                    enterprise, exactMatch=False, strip=False)
                generic = pdu.trap_type
                specific = pdu.specific_type

                # Try an exact match with a .0. inserted between enterprise and
                # specific OID. It seems that MIBs frequently expect this .0.
                # to exist, but the device's don't send it in the trap.
                oid = "%s.0.%d" % (enterprise, specific)
                name = self.oid2name(oid, exactMatch=True, strip=False)

                # If we didn't get a match with the .0. inserted we will try
                # resolving with the .0. inserted and allow partial matches.
                if name == oid:
                    oid = "%s.%d" % (enterprise, specific)
                    name = self.oid2name(oid, exactMatch=False, strip=False)

                # Look for the standard trap types and decode them without
                # relying on any MIBs being loaded.
                eventType = {
                    0: 'snmp_coldStart',
                    1: 'snmp_warmStart',
                    2: 'snmp_linkDown',
                    3: 'snmp_linkUp',
                    4: 'snmp_authenticationFailure',
                    5: 'snmp_egpNeighorLoss',
                    6: name,
                    }.get(generic, name)

                # Decode all variable bindings. Allow partial matches and strip
                # off any index values.
                for vb_oid, vb_value in variables:
                    vb_value = self._convert_value(vb_value)
                    vb_oid = '.'.join(map(str, vb_oid))
                    # Add a detail for the variable binding.
                    r = self.oid2name(vb_oid, exactMatch=False, strip=False)
                    result[r] = vb_value
                    # Add a detail for the index-stripped variable binding.
                    r = self.oid2name(vb_oid, exactMatch=False, strip=True)
                    result[r] = vb_value

            elif pdu.version == 1:
                # SNMP v2
                variables = self.getResult(pdu)
                for vb_oid, vb_value in variables:
                    vb_value = self._convert_value(vb_value)
                    vb_oid = '.'.join(map(str, vb_oid))
                    # SNMPv2-MIB/snmpTrapOID
                    if vb_oid == '1.3.6.1.6.3.1.1.4.1.0':
                        oid = '.'.join(map(str, vb_value))
                        eventType = self.oid2name(
                            vb_value, exactMatch=False, strip=False)
                    else:
                        # Add a detail for the variable binding.
                        r = self.oid2name(vb_oid, exactMatch=False, strip=False)
                        result[r] = vb_value
                        # Add a detail for the index-stripped variable binding.
                        r = self.oid2name(vb_oid, exactMatch=False, strip=True)
                        result[r] = vb_value

            else:
                self.log.error("Unable to handle trap version %d", pdu.version)
                return

            summary = 'snmp trap %s' % eventType
            self.log.debug(summary)
            community = self.getCommunity(pdu)
            result['oid'] = oid
            result['device'] = addr[0]
            result.setdefault('component', '')
            result.setdefault('eventClassKey', eventType)
            result.setdefault('eventGroup', 'trap')
            result.setdefault('severity', 2)
            result.setdefault('summary', summary)
            result.setdefault('community', community)
            result.setdefault('firstTime', ts)
            result.setdefault('lastTime', ts)
            result.setdefault('monitor', self.options.monitor)
            self.sendEvent(result)

            # Don't attempt to respond back if we're replaying packets
            if len(self.options.replayFilePrefix) > 0:
                self.replayed += 1
                return

            # respond to INFORM requests
            if pdu.command == netsnmp.SNMP_MSG_INFORM:
                reply = netsnmp.lib.snmp_clone_pdu(c.byref(pdu))
                if not reply:
                    self.log.error("Could not clone PDU for INFORM response")
                    raise RuntimeError("Cannot respond to INFORM PDU")
                reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
                reply.contents.errstat = 0
                reply.contents.errindex = 0
                # FIXME: might need to add udp6 for IPv6 addresses
                sess = netsnmp.Session(peername='%s:%d' % tuple(addr),
                                       version=pdu.version)
                sess.open()
                if not netsnmp.lib.snmp_send(sess.sess, reply):
                    netsnmp.lib.snmp_sess_perror("Unable to send inform PDU",
                                                 self.session.sess)
                    netsnmp.lib.snmp_free_pdu(reply)
                sess.close()

            yield defer.succeed(True)
            driver.next()
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
            # FIXME: need :: to listen on all IPv6 + IPv4
            #dest='listenip', default='::',
            dest='listenip', default='0.0.0.0',
            help="IP address to listen on. Default is ::")
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               help=("Read from an existing connection "
                                     " rather than opening a new port."),
                               default=None)

        self.buildCaptureReplayOptions()


if __name__ == '__main__':
    z = ZenTrap()
    z.run()
    z.report()

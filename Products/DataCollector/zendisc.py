#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################

import sys
import re
import socket

import Globals

import transaction

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.IpUtil import isip
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenEvents.Event import Event, Info
from Products.ZenStatus.Ping import Ping
from Products.ZenModel.Device import manage_createDevice

from zenmodeler import ZenModeler

class ZenDisc(ZenModeler):


    def __init__(self,noopts=0,app=None,single=True,
                threaded=False,keeproot=True):
        ZenModeler.__init__(self, noopts, app, single, threaded, keeproot)


    def discoverRouters(self, rootdev, seenips=[]):
        """Discover all default routers based on dmd configuration.
        """
        for ip in rootdev.followNextHopIps():
            if ip in seenips: continue
            self.log.info("device '%s' next hop '%s'", rootdev.id, ip)
            seenips.append(ip)
            router = self.discoverDevice(ip,devicepath="/Network/Router")
            if not router: continue
            self.discoverRouters(router, seenips)
            

    def discoverIps(self, nets=None):
        """Ping all ips create if nessesary and perform reverse lookup.
        """
        ips = []
        ping = Ping(tries=self.options.tries, timeout=self.options.timeout,
                    chunkSize=self.options.chunkSize)
        pingthresh = 168
        if not nets:
            nets = self.dmd.Networks.getSubNetworks()
            pingthresh = getattr(self.dmd.Networks, "zPingFailThresh", 168)
        goodCount = 0
        for net in nets:
            if not getattr(net, "zAutoDiscover", False): continue
            self.log.info("discover network '%s'", net.id)
            goodips, badips = ping.ping(net.fullIpList())
            goodCount += len(goodips)
            for ip in goodips:
                ipobj = net.createIp(ip)
                if self.options.resetPtr:
                    ipobj.setPtrName()
                if not ipobj.device():
                    ips.append(ip)
                if ipobj.getStatus(PingStatus) > 0:
                    self.sendEvent(ipobj, sev=0)
            for ip in badips:
                ipobj = self.dmd.Networks.findIp(ip)
                if self.options.addInactive:
                    if not ipobj:
                        ipobj = net.createIp(ip)
                    self.sendEvent(ipobj)
                elif ipobj and ipobj.getStatus(PingStatus) > pingthresh:
                    net.ipaddresses.removeRelation(ipobj)
                if ipobj and self.options.resetPtr:
                    ipobj.setPtrName()

            transaction.commit()
        self.log.info("discovered %s active ips", goodCount)    
        return ips
       

    def sendEvent(self, ipobj, sev=2):
        """Send an ip down event.  These are used to cleanup unused ips.
        """
        ip = ipobj.id
        dev = ipobj.device()
        if sev == 0:
            msg = "ip %s is up" % ip
        else:
            msg = "ip %s is down" % ip
        if dev: 
            devname = dev.id
            comp = ipobj.interface().id
        else: 
            devname = comp = ip
        evt = Event(device=devname,ipAddress=ip,eventKey=ip,
                    component=comp,eventClass=PingStatus,
                    summary=msg, severity=sev,
                    agent="Discover")
        self.dmd.ZenEventManager.sendEvent(evt)

    
    def discoverDevices(self, ips, devicepath="/Discovered"):
        """Discover devices by active ips that are not associated with a device.
        """
        for ip in ips: self.discoverDevice(ip)


    def discoverDevice(self, ip, devicepath="/Discovered"):
        """Discover a device based on its ip address.
        """
        devname = ""
        if not isip(ip):
            devname = ip
            ip = socket.gethostbyname(ip)
        try:
            ipobj = self.dmd.Networks.findIp(ip)
            if ipobj:
                if not getattr(ipobj, "zAutoDiscover", True): 
                    self.log.info("ip '%s' on no auto-discover, skipping",ip)
                    return
                dev = ipobj.device() 
                if dev:
                    if not self.options.remodel:
                        self.log.info("ip '%s' on device '%s' skipping",
                                        ip, dev.id)
                        return dev.primaryAq()
                    else:
                        self.log.info("ip '%s' on device '%s' remodel",
                                        ip, dev.id)
            dev = manage_createDevice(self.dmd, ip, devicepath)
            transaction.commit()
            dev.collectDevice()
            return dev
        except ZentinelException, e:
            self.log.warn(e)
            #FIXME add event showing problem so we don't remodel later
            evt = Event(device=ip,
                        component=ip,
                        ipAddress=ip,
                        eventKey=ip,
                        eventClass="/Status/Snmp",
                        summary=str(e),
                        severity=Info,
                        agent="Discover")
            if self.options.snmpMissing:
                self.dmd.ZenEventManager.sendEvent(evt)
        except Exception, e:
            self.log.exception("failed device discovery for '%s'", ip)


    def run(self):
        if self.options.net:
            for net in self.options.net:
                try:
                    netobj = self.dmd.Networks._getOb(net,None) 
                    if not netobj:
                        raise SystemExit("network %s not found in dmd",net)
                    for ip in self.discoverIps((netobj,)):
                        self.dmd._p_jar.sync()
                        if not self.options.nosnmp: 
                            self.discoverDevice(ip, self.options.deviceclass)
                except Exception, ex:
                    self.log.exception("Error performing net descovery on %s",
                                       ex)
            return
        myname = socket.getfqdn()
        self.log.info("my hostname = %s", myname)
        myip = None
        try:
            myip = socket.gethostbyname(myname)
            self.log.info("my ip = %s", myip)
        except socket.error, e:
            self.log.warn("failed lookup of my ip for name %s", myname) 
        me = self.dmd.Devices.findDevice(myname)
        if not me or self.options.remodel:
            me = self.discoverDevice(myname, devicepath="/") 
        if not me:
            raise SystemExit("snmp discover of self '%s' failed" % myname)
        if not myip: myip = me.getManageIp()
        if not myip: 
            raise SystemExit("can't find my ip for name %s" % myname)
        self.discoverRouters(me, [myip])
        if self.options.routersonly:
            self.log.info("only routers discovered, skiping ping sweep.")
        else:
            ips = self.discoverIps()
            if not self.options.nosnmp: 
                self.discoverDevices(ips)
        self.stop()


    def buildOptions(self):
        ZenModeler.buildOptions(self)
        self.parser.add_option('--net', dest='net', action="append",
                    help="discover all device on this network")
        self.parser.add_option('--deviceclass', dest='deviceclass',
                    default="/Discovered",
                    help="default device class for discovered devices")
        self.parser.add_option('--remodel', dest='remodel',
                    action="store_true", default=False,
                    help="remodel existing objects")
        self.parser.add_option('--routers', dest='routersonly',
                    action="store_true", default=False,
                    help="only discover routers")
        self.parser.add_option('--tries', dest='tries', default=1, type="int",
                    help="how many ping tries")
        self.parser.add_option('--timeout', dest='timeout', 
                    default=2, type="float",
                    help="ping timeout in seconds")
        self.parser.add_option('--chunk', dest='chunkSize', 
                    default=10, type="int",
                    help="number of in flight ping packets")
        self.parser.add_option('--snmp-missing', dest='snmpMissing',
                    action="store_true", default=False,
                    help="send an event if SNMP is not found on the device")
        self.parser.add_option('--add-inactive', dest='addInactive',
                    action="store_true", default=False,
                    help="add all IPs found, even if they are unresponsive")
        self.parser.add_option('--reset-ptr', dest='resetPtr',
                    action="store_true", default=False,
                    help="Reset all ip PTR records")
        self.parser.add_option('--no-snmp', dest='nosnmp',
                    action="store_true", default=False,
                    help="Perform snmp discovery on found IP addresses")

if __name__ == "__main__":
    try:
        d = ZenDisc()
        d.run()
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception, e:
        print "Error: " + str(e)

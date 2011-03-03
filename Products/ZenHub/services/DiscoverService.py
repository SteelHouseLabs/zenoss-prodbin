###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger('zen.DiscoverService')

from Products.ZenUtils.IpUtil import numbip, strip
from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenModel.Device import manage_createDevice
from Products.Jobber.status import JobStatusProxy
from Products.ZenHub.PBDaemon import translateError
from Products.ZenModel.Exceptions import DeviceExistsError

import transaction

from twisted.spread import pb
import math
import re

from ModelerService import ModelerService

DEFAULT_PING_THRESH = 168


class IpNetProxy(pb.Copyable, pb.RemoteCopy):
    "A class that will represent a ZenModel/IpNetwork in zendisc"
    
    id = ''
    _children = None
    netmask = None

    def __init__(self, ipnet):
        self.id = ipnet.id
        self._children = map(IpNetProxy, ipnet.children())
        self.netmask = ipnet.netmask
        for prop in 'zAutoDiscover zDefaultNetworkTree zPingFailThresh'.split():
            if hasattr(ipnet, prop):
                setattr(self, prop, getattr(ipnet, prop))

    def children(self):
        return self._children

    def fullIpList(self):
        "copied from IpNetwork"
        if (self.netmask == 32): return [self.id]
        ipnumb = numbip(self.id)
        maxip = math.pow(2, 32 - self.netmask)
        start = int(ipnumb + 1)
        end = int(ipnumb + maxip - 1)
        return map(strip, range(start,end))
    
    def getNetworkName(self):
        return "%s/%d" % (self.id, self.netmask)

pb.setUnjellyableForClass(IpNetProxy, IpNetProxy)

class DiscoverService(ModelerService):

    @translateError
    def remote_getNetworks(self, net, includeSubNets):
        "Get network objects to scan networks should be in CIDR form 1.1.1.0/24"
        netObj = self.dmd.Networks.getNetworkRoot().findNet(net)
        if not netObj:
            return None
        nets = [netObj]
        if includeSubNets:
            nets += netObj.getSubNetworks()
        return map(IpNetProxy, nets)


    @translateError
    def remote_pingStatus(self, net, goodips, badips, resetPtr, addInactive):
        "Create objects based on ping results"
        net = self.dmd.Networks.getNetworkRoot().findNet(net.id, net.netmask)
        pingthresh = getattr(net, "zPingFailThresh", DEFAULT_PING_THRESH)
        ips = []
        for ip in goodips:
            ipobj = net.createIp(ip, net.netmask)
            if resetPtr:
                ipobj.setPtrName()
            if not ipobj.device():
                ips.append(ip)
            self.sendIpStatusEvent(ipobj, sev=0)
        for ip in badips:
            ipobj = self.dmd.Networks.getNetworkRoot().findIp(ip)
            if not ipobj and addInactive:
                ipobj = net.createIp(ip, net.netmask)
            if ipobj:
                if resetPtr:
                    ipobj.setPtrName()
                elif ipobj.getStatus(Status_Ping) > pingthresh:
                    net.ipaddresses.removeRelation(ipobj)
                if ipobj:
                    self.sendIpStatusEvent(ipobj)
        transaction.commit()
        return ips

                    
    def sendIpStatusEvent(self, ipobj, sev=2):
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
        self.sendEvent(dict(device=devname, ipAddress=ip, eventKey=ip,
            component=comp, eventClass=Status_Ping, summary=msg, severity=sev,
            agent="Discover"))


    @translateError
    def remote_createDevice(self, ip, force=False, **kw):
        """Create a device.

        @param ip: The manageIp of the device
        @param kw: The args to manage_createDevice.
        """
        from Products.ZenModel.Device import getNetworkRoot
        try:
            netroot = getNetworkRoot(self.dmd, 
                kw.get('performanceMonitor', 'localhost'))
            netobj = netroot.getNet(ip)
            netmask = 24
            if netobj is not None:
                netmask = netobj.netmask
            else:
                defaultNetmasks = getattr(netroot, 'zDefaultNetworkTree', [])
                if defaultNetmasks:
                    netmask = defaultNetmasks[0]
            netroot.createIp(ip, netmask)
            autoDiscover = getattr(netobj, 'zAutoDiscover', True)
            # If we're not supposed to discover this IP, return None
            if not force and not autoDiscover:
                return None, False
            kw['manageIp'] = ip
            dev = manage_createDevice(self.dmd, **kw)
        except DeviceExistsError, e:
            # Update device with latest info from zendisc
            e.dev.setManageIp(kw['manageIp'])
            # only overwrite title if it has not been set
            if e.dev.title is None or len(e.dev.title) <= 0 or \
               re.match('^(0*([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}0*([0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|25[0-5]){1}$', e.dev.title):
                e.dev.setTitle(kw['deviceName'])
            for key in ('manageIp', 'deviceName', 'devicePath', 
                        'discoverProto'): 
                del kw[key]
            # use updateDevice so we don't clobber existing device properties.
            e.dev.updateDevice(**kw)
            # Make and return a device proxy
            return self.createDeviceProxy(e.dev), False
        except Exception, ex:
            log.exception("IP address %s (kw = %s) encountered error", ip, kw)
            raise pb.CopyableFailure(ex)
        transaction.commit()
        return self.createDeviceProxy(dev), True

    @translateError
    def remote_getJobProperties(self, jobid):
        jobstatus = self.dmd.JobManager.getJob(jobid)
        if jobstatus: 
            return JobStatusProxy(jobstatus)

    @translateError
    def remote_succeedDiscovery(self, id):
        dev = self.dmd.Devices.findDeviceByIdOrIp(id)
        if dev: 
            dev._temp_device = False
        transaction.commit()
        return True

    @translateError
    def remote_followNextHopIps(self, device):
        """
        Return the ips that the device's indirect routes point to
        which aren't currently connected to devices.
        """
        dev = self.getPerformanceMonitor().findDevice(device)
        ips = []
        for r in dev.os.routes():
            ipobj = r.nexthop()
            if ipobj: ips.append(ipobj.id)
        return ips


    @translateError
    def remote_getSubNetworks(self):
        "Fetch proxies for all the networks"
        return map(IpNetProxy,
                self.dmd.Networks.getNetworkRoot().getSubNetworks())


    @translateError
    def remote_getSnmpConfig(self, devicePath):
        "Get the snmp configuration defaults for scanning a device"
        devroot = self.dmd.Devices.createOrganizer(devicePath)
        return (devroot.zSnmpCommunities,
                devroot.zSnmpPort,
                devroot.zSnmpVer,
                devroot.zSnmpTimeout,
                devroot.zSnmpTries)
        

    @translateError
    def remote_moveDevice(self, dev, path):
        self.dmd.Devices.moveDevices(path, [dev])
        transaction.commit()

    @translateError
    def remote_getDefaultNetworks(self):
        monitor = self.dmd.Monitors.Performance._getOb(self.instance)
        return [net for net in monitor.discoveryNetworks]

###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """PingConfig

Provides configuration to zenping per-device based on:
 * the zPingMonitorIgnore
 * whether the datasource is enabled or not for the interface
"""

import logging
log = logging.getLogger('zen.HubService.PingPerformanceConfig')

from ipaddr import IPAddress
from twisted.spread import pb

import Globals
from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenEvents.ZenEventClasses import Error, Clear
from Products.ZenUtils.IpUtil import ipunwrap


class IpAddressProxy(pb.Copyable, pb.RemoteCopy):
    """
    Represents a pingable IP address on an IP interface. A single
    DeviceProxy config will have multiple IP address proxy components
    (for each IP address on each IP interface zenping should monitor)
    """
    def __init__(self, ip, ipVersion=4, iface='', basepath='', ds=None,
                 perfServer='localhost'):
        self.ip = ipunwrap(ip)
        self.ipVersion = ipVersion
        self.iface = iface
        self.cycleTime =  getattr(ds, 'cycleTime', 60)
        self.tries =      getattr(ds, 'attempts', 2)
        self.sampleSize = getattr(ds, 'sampleSize', 1)
        self.points = []

        if not ds:
            # Don't need the datapoints to get the IP monitored
            return

        for dp in ds.getRRDDataPoints():
            ipdData = (dp.id,
                       "/".join((basepath, dp.name())),
                       dp.rrdtype,
                       dp.getRRDCreateCommand(perfServer).strip(),
                       dp.rrdmin, dp.rrdmax)

            self.points.append(ipdData)

    def __str__(self):
        return "IPv%d %s iface: '%s' cycleTime: %ss attempts: %d" % (
               self.ipVersion, self.ip, self.iface, self.cycleTime,
               self.tries)

pb.setUnjellyableForClass(IpAddressProxy, IpAddressProxy)


class PingPerformanceConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        deviceProxyAttributes = (
                                 'zPingMonitorIgnore',
                                )
        CollectorConfigService.__init__(self, dmd, instance, 
                                        deviceProxyAttributes)

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)

        if not device.monitorDevice():
            include = False

        if device.zPingMonitorIgnore:
            include = False

        if not device.getManageIp():
            self.log.debug("Device %s skipped because its management IP address is blank.",
                           device.id)
            include = False

        return include

    def _getComponentConfig(self, iface, perfServer, monitoredIps):
        """
        All IP addresses on all IP interfaces can be pingable.
        """
        basepath = iface.rrdPath()
        title = iface.titleOrId()
        for templ in iface.getRRDTemplates():
            for ipAddress in iface.ipaddresses():
                ip = ipAddress.id
                if not ip or ip in ('127.0.0.1', '0.0.0.0', '::', '::1'):
                    log.debug("The %s interface IP is '%s' -- ignoring",
                              title, ip)
                    continue

                dsList = [ds for ds in templ.getRRDDataSources('PING') \
                             if ds.enabled]
                if dsList:
                    ipVersion = getattr(ipAddress, 'version', 4)
                    ipProxy = IpAddressProxy(ip, ipVersion=ipVersion,
                                             iface=title, ds=dsList[0],
                                             basepath=basepath, perfServer=perfServer)
                    monitoredIps.append(ipProxy)

    def _addManageIp(self, device, perfServer, proxy):
        """
        Add the management IP and any associated datapoints to the IPs to monitor.
        """
        basepath = device.rrdPath()
        title = "Manage_IP"
        ip = device.manageIp
        if not ip or ip in ('127.0.0.1', '0.0.0.0', '::', '::1'):
            return
        ipObj = IPAddress(ip)

        # Look for device-level templates with PING datasources
        addedIp = False
        for templ in device.getRRDTemplates():
            dsList = [ds for ds in templ.getRRDDataSources('PING') \
                             if ds.enabled]
            if dsList:
                ipProxy = IpAddressProxy(ip, ipVersion=ipObj.version,
                                         iface=title, ds=dsList[0],
                                         basepath=basepath, perfServer=perfServer)
                proxy.monitoredIps.append(ipProxy)
                addedIp = True

        threshs = device.getThresholdInstances('PING')
        if threshs:
            proxy.thresholds.extend(threshs)

        # Add without datapoints if nothing's defined....
        if not addedIp:
            ipProxy = IpAddressProxy(ip, ipVersion=ipObj.version,
                                     iface=title,
                                     basepath=basepath, perfServer=perfServer)
            proxy.monitoredIps.append(ipProxy)

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.lastChangeTime = float(device.getLastChange())

        perfServer = device.getPerformanceServer()
        proxy.thresholds = []
        proxy.monitoredIps = []
        for iface in device.os.interfaces():
            self._getComponentConfig(iface, perfServer, proxy.monitoredIps)
            threshs = iface.getThresholdInstances('PING')
            if threshs:
                proxy.thresholds.extend(threshs)

        if not proxy.monitoredIps:
            log.debug("%s has no interface templates -- just using management IP %s",
                      device.titleOrId(), device.manageIp)
            self._addManageIp(device, perfServer, proxy)

        elif device.manageIp not in [x.ip for x in proxy.monitoredIps]:
            # Note: most commonly occurs for SNMP fakeout devices which replay
            #       data from real devices, but from a different IP address
            #       than what captured the data
            log.debug("%s doesn't have an interface for management IP %s",
                      device.titleOrId(), device.manageIp)
            self._addManageIp(device, perfServer, proxy)

        return proxy


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(PingPerformanceConfig)
    def printer(config):
        for ip in config.monitoredIps:
            print '\t', ip
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import logging
from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenEvents.ZenEventClasses import Status_IpService
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.Service import Service
from twisted.spread import pb

log = logging.getLogger('zen.ZenStatusConfig')


class ServiceProxy(pb.Copyable, pb.RemoteCopy):
    """
    Represents a service component. A single DeviceProxy config will have
    multiple service proxy components (for each service zenstatus should
    monitor)
    """
    def __init__(self, svc, status):
        self.device = svc.hostname()
        self.component = svc.name()
        self.ip = svc.getManageIp()
        self.port = svc.getPort()
        self.sendString = svc.getSendString()
        self.expectRegex = svc.getExpectRegex()
        self.timeout = svc.zStatusConnectTimeout
        self.failSeverity = svc.getFailSeverity()
        self.status = status
        self.key = svc.key()

pb.setUnjellyableForClass(ServiceProxy, ServiceProxy)


class ZenStatusConfig(CollectorConfigService):

    def __init__(self, dmd, instance):
        # Any additional attributes we want to send to daemon should be
        # added here
        deviceProxyAttributes = ()
        CollectorConfigService.__init__(self, dmd,
                                        instance,
                                        deviceProxyAttributes)

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)
        hasTcpComponents = False
        for svc in device.getMonitoredComponents(collector='zenstatus'):
            if svc.getProtocol() == "tcp":
                hasTcpComponents = True

        return include and hasTcpComponents

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = self._prefs.statusCycleInterval

        # add each component
        proxy.components = []
        for svc in device.getMonitoredComponents(collector='zenstatus'):
            if svc.getProtocol() == 'tcp':
                # get component status
                status = svc.getStatus(Status_IpService)
                proxy.components.append(ServiceProxy(svc, status))

        # don't bother adding this device proxy if there aren't any services
        # to monitor
        if not proxy.components:
            log.debug("Device %s skipped because there are no components",
                      proxy.id)
            return None

        return proxy

    def _getNotifiableClasses(self):
        """
        When zProperties are changed on either of these two classes we
        need to refresh which devices we are monitoring
        """
        return (Service, ServiceOrganizer)

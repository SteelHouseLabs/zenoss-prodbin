###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals

from Acquisition import aq_base
from twisted.internet import defer, reactor
from ZODB.transact import transact
from PerformanceConfig import PerformanceConfig
from Products.ZenHub.PBDaemon import translateError
from Products.DataCollector.DeviceProxy import DeviceProxy

from Products.DataCollector.Plugins import loadPlugins

import logging
log = logging.getLogger('zen.ModelerService')

class ModelerService(PerformanceConfig):

    plugins = None

    def __init__(self, dmd, instance):
        PerformanceConfig.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.methodPriorityMap = {
            'applyDataMaps': 0.5,
            }

    def createDeviceProxy(self, dev):
        if self.plugins is None:
            self.plugins = {}
            for loader in loadPlugins(self.dmd):
                try:
                    plugin = loader.create()
                    plugin.loader = loader
                    self.plugins[plugin.name()] = plugin
                except Exception, ex:
                    log.exception(ex)

        result = DeviceProxy()
        result.id = dev.getId()
        if not dev.manageIp:
            dev.setManageIp()
        result.manageIp = dev.manageIp
        result.plugins = []
        for name in dev.zCollectorPlugins:
            plugin = self.plugins.get(name, None)
            log.debug('checking plugin %s for device %s' % (name, dev.getId()))
            if plugin and plugin.condition(dev, log):
                log.debug('adding plugin %s for device %s' % (name,dev.getId()))
                result.plugins.append(plugin.loader)
                plugin.copyDataToProxy(dev, result)
        result.temp_device = dev.isTempDevice()
        return result

    @translateError
    def remote_getClassCollectorPlugins(self):
        result = []
        for dc in self.dmd.Devices.getSubOrganizers():
            localPlugins = getattr(aq_base(dc), 'zCollectorPlugins', False)
            if not localPlugins: continue
            result.append((dc.getOrganizerName(), localPlugins))
        return result

    @translateError
    def remote_getDeviceConfig(self, names, checkStatus=False):
        result = []
        for name in names:
            device = self.getPerformanceMonitor().findDevice(name)
            if not device:
                continue
            device = device.primaryAq()
            if checkStatus and (device.getPingStatus() > 0
                                or device.getSnmpStatus() > 0):
                log.info("device %s is down skipping modeling", device.id)
                continue

            if (device.productionState <
                device.getProperty('zProdStateThreshold', 0)):
                log.info("device %s is below zProdStateThreshold", device.id)
                continue
            result.append(self.createDeviceProxy(device))
        return result

    @translateError
    def remote_getDeviceListByMonitor(self, monitor=None):
        if monitor is None:
            monitor = self.instance
        monitor = self.dmd.Monitors.Performance._getOb(monitor)
        return [d.id for d in monitor.devices.objectValuesGen()]

    @translateError
    def remote_getDeviceListByOrganizer(self, organizer, monitor=None):
        if monitor is None:
            monitor = self.instance
        root = self.dmd.Devices.getOrganizer(organizer)
        return [d.id for d in root.getSubDevicesGen() \
            if d.getPerformanceServerName() == monitor]

    @translateError
    def remote_applyDataMaps(self, device, maps, devclass=None):
        from Products.DataCollector.ApplyDataMap import ApplyDataMap
        device = self.getPerformanceMonitor().findDevice(device)
        adm = ApplyDataMap(self)
        adm.setDeviceClass(device, devclass)
        def inner(map):
            def action():
                return bool(adm._applyDataMap(device, map))
            return self._do_with_retries(action)

        changed = False
        for map in maps:
            result = inner(map)
            changed = changed or result
        return changed

    @translateError
    def remote_setSnmpLastCollection(self, device):
        device = self.getPerformanceMonitor().findDevice(device)
        device.setSnmpLastCollection()
        from transaction import commit
        self._do_with_retries(commit)


    def _do_with_retries(self, action):
        from ZODB.POSException import StorageError
        max_attempts = 3
        for attempt_num in range(max_attempts):
            try:
                return action()
            except StorageError as e:
                if attempt_num == max_attempts-1:
                    msg = "{0}, maximum retries reached".format(e)
                else:
                    msg = "{0}, retrying".format(e)
                log.info(msg)


    @transact
    @translateError
    def remote_setSnmpConnectionInfo(self, device, version, port, community):
        device = self.getPerformanceMonitor().findDevice(device)
        device.updateDevice(zSnmpVer=version,
                            zSnmpPort=port,
                            zSnmpCommunity=community)

    def pushConfig(self, device):
        from twisted.internet.defer import succeed
        return succeed(device)


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(ModelerService)

    def configprinter(config):
        print "%s (%s) Plugins" % (config.id, config.manageIp)
        print sorted(x.pluginName for x in config.plugins)

    def showDeviceInfo():
        if tester.options.device:
            name = tester.options.device
            config = tester.service.remote_getDeviceConfig([name])
            if config:
                print "Config for %s =" % name
                configprinter(config[0])
            else:
                log.warn("No configs found for %s", name)
        else:
            collector = tester.options.monitor
            devices = tester.service.remote_getDeviceListByMonitor(collector)
            devices = sorted(devices)
            print "Device list = %s" % devices

    showDeviceInfo()


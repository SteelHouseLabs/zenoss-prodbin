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

__doc__='''WmiService

Provides Wmi config to zenwin clients.
'''

from Products.ZenHub.HubService import HubService
from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass

from Procrastinator import Procrastinate
from ThresholdMixin import ThresholdMixin

from Products.ZenHub.PBDaemon import translateError

class WmiConfig(HubService, ThresholdMixin):
    
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.push)


    @translateError
    def remote_getDeviceWinInfo(self):
        """Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """

        devinfo = []
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            sev = getattr(dev, 'zWinEventlogMinSeverity', '')
            devinfo.append((dev._lastChange,
                            dev.id,
                            dev.getManageIp(),
                            str(user),
                            str(passwd),
                            sev,
                            dev.absolute_url()))
        return devinfo
    
    
    @translateError
    def remote_getWinServices(self):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        svcinfo = []
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            svcs = {}
            for s in dev.getMonitoredComponents(type='WinService'):
                name = s.name()
                if type(name) == type(u''):
                    name = name.encode(s.zCollectorDecoding)
                svcs[name] = (s.getStatus(), s.getAqProperty('zFailSeverity'))
            if not svcs and not dev.zWinEventlog: continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            svcinfo.append((dev.id, dev.getManageIp(), str(user), str(passwd), svcs))
        return svcinfo


    @translateError
    def remote_getConfig(self):
        return self.config.propertyItems()


    @translateError
    def remote_applyDataMap(self,
                            url,
                            datamap,
                            relname="",
                            compname="",
                            modname=""):
        dev = self.dmd.getObjByPath(url)
        adm = ApplyDataMap()
        result = adm.applyDataMap(dev,
                                  datamap,
                                  relname=relname,
                                  compname=compname,
                                  modname=modname)
        import transaction
        transaction.commit()
        return result
        
    def update(self, object):
        if isinstance(object, DeviceClass):
            objects = object.getSubDevices()
        else:
            objects = [object]
        for object in objects:
            if not isinstance(object, Device):
                continue
            self.procrastinator.doLater(object)

    def push(self, object):
        if (not object.monitorDevice() or
            getattr(object, 'zWmiMonitorIgnore', False)):
            self.deleted(object)
        else:
            for listener in self.listeners:
                listener.callRemote('notifyConfigChanged')
            self.procrastinator.clear()

    def deleted(self, obj):
        for listener in self.listeners:
            if isinstance(obj, Device):
                listener.callRemote('deleteDevice', obj.id)

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
#! /usr/bin/env python 

import Globals
from Products.ZenEvents.ZenEventClasses import Status_Snmp

from Products.ZenHub.HubService import HubService

from Products.ZenModel.Device import Device
from Acquisition import aq_parent, aq_base

from twisted.internet import reactor, defer

from Procrastinator import Procrastinate

class PerformanceConfig(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.pushConfig)


    def remote_propertyItems(self):
        return self.config.propertyItems()

        
    def remote_getSnmpStatus(self, devname=None):
        "Return the failure counts for Snmp" 
        result = []
        counts = {}
        try:
            # get all the events with /Status/Snmp
            conn = self.zem.connect()
            try:
                curs = conn.cursor()
                cmd = ('SELECT device, sum(count)  ' +
                       '  FROM status ' +
                       ' WHERE eventClass = "%s"' % Status_Snmp)
                if devname:
                    cmd += ' AND device = "%s"' % devname
                cmd += ' GROUP BY device'
                curs.execute(cmd);
                counts = dict([(d, int(c)) for d, c in curs.fetchall()])
            finally:
                self.zem.close(conn)
        except Exception, ex:
            self.log.exception('Unable to get Snmp Status')
            raise
        if devname:
            return [(devname, counts.get(devname, 0))]
        return [(dev.id, counts.get(dev.id, 0)) for dev in self.config.devices()]


    def remote_getDefaultRRDCreateCommand(self, *args, **kwargs):
        return self.config.getDefaultRRDCreateCommand(*args, **kwargs)


    def remote_getThresholdClasses(self):
        from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
        classes = [MinMaxThreshold]
        for pack in self.dmd.packs():
            classes += pack.getThresholdClasses()
        return map(lambda c: c.__module__, classes)


    def notifyAll(self, device):
        if device.perfServer.getRelatedId() == self.instance:
            self.procrastinator.doLater(device)


    def pushConfig(self, device):
        deferreds = []
        cfg = self.getDeviceConfig(device)
        for listener in self.listeners:
            if cfg is None:
                deferreds.append(listener.callRemote('deleteDevice', device.id))
            else:
                deferreds.append(self.sendDeviceConfig(listener, cfg))
        return defer.DeferredList(deferreds)


    def getDeviceConfig(self, device):
        "How to get the config for a device"
        return None


    def sendDeviceConfig(self, listener, config):
        "How to send the config to a device, probably via callRemote"
        pass


    def update(self, object):
        if not self.listeners:
            return

        # the PerformanceConf changed
        from Products.ZenModel.PerformanceConf import PerformanceConf
        if isinstance(object, PerformanceConf) and object.id == self.instance:
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())
                devices = [
                    (d.id, float(d.getLastChange())) for d in object.devices()
                     ]
                # listener.callRemote('updateDeviceList', devices)

        # a ZenPack is installed
        from Products.ZenModel.ZenPack import ZenPack
        if isinstance(object, ZenPack):
            for listener in self.listeners:
                try:
                    listener.callRemote('updateThresholdClasses',
                                        self.remote_getThresholdClasses())
                except Exception, ex:
                    self.log.exception("Error notifying a listener of new classes")

        # device has been changed:
        if isinstance(object, Device):
            self.notifyAll(object)
            return
            
        # somethinge else... mark the devices as out-of-date
        from Products.ZenModel.DeviceClass import DeviceClass

        import transaction
        while object:
            # walk up until you hit an organizer or a device
            if isinstance(object, DeviceClass):
                for device in object.getSubDevices():
                    self.notifyAll(device)
                break

            if isinstance(object, Device):
                self.notifyAll(object)
                break

            object = aq_parent(object)


    def deleted(self, obj):
        for listener in self.listeners:
            if isinstance(obj, Device):
                listener.callRemote('deleteDevice', obj.id)

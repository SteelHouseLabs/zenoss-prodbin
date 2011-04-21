###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Change the Cricket relationship in Devices to Performance
to reflect the change from Cricket to zenperfsnmp performance
monitoring.

'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate

from Products.ZenUtils.Utils import zenPath

class KillCricket(Migrate.Step):
    version = Migrate.Version(0, 20, 0)

    def convert(self, dc):
        """Convert DeviceClass objects.
        """
        dc.buildRelations()
        if hasattr(aq_base(dc), "zCricketDeviceType"):
            dc._delProperty("zCricketDeviceType")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreNames"):
            dc._delProperty("zCricketInterfaceIgnoreNames")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreTypes"):
            dc._delProperty("zCricketInterfaceIgnoreTypes")
        if hasattr(aq_base(dc), "zCricketInterfaceMap"):
            dc._delProperty("zCricketInterfaceMap")


    def cutover(self, dmd):
        from Products.ZenModel.MonitorClass import manage_addMonitorClass
        if not hasattr(dmd.Monitors, 'Performance'):
            manage_addMonitorClass(dmd.Monitors, 'Performance')

        from Products.ZenModel.PerformanceConf import manage_addPerformanceConf
        if hasattr(dmd.Monitors, 'Cricket'):
            for c in dmd.Monitors.Cricket.objectValues():
                if not hasattr(dmd.Monitors.Performance, c.id):
                    manage_addPerformanceConf(dmd.Monitors.Performance, c.id)
                    p = dmd.Monitors.Performance._getOb(c.id)
                    p.renderurl = c.cricketurl
                    p.renderuser = c.cricketuser
                    p.renderpass = c.cricketpass
            if hasattr(dmd.Monitors.Cricket, 'localhost'):
                dmd.Monitors.Cricket._delObject('localhost')
            dmd.Monitors._delObject("Cricket")

        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
            if hasattr(dev, 'cricket') and dev.cricket.getRelatedId():
                dev.setPerformanceMonitor(dev.cricket.getRelatedId())
            if hasattr(dev, '_snmpUpTime'):
                delattr(dev, '_snmpUpTime')
            for fs in dev.os.filesystems():
                if not callable(fs.totalBytes):
                    delattr(fs, 'totalBytes')
                if not callable(fs.usedBytes):
                    delattr(fs, 'usedBytes')
                if not callable(fs.availBytes):
                    delattr(fs, 'availBytes')
                if not callable(fs.availFiles):
                    delattr(fs, 'availFiles')
                if not callable(fs.capacity):
                    delattr(fs, 'capacity')
                if not callable(fs.inodeCapacity):
                    delattr(fs, 'inodeCapacity')

        for dc in dmd.Devices.getSubOrganizers():
            self.convert(dc)
        self.convert(dmd.Devices)

        if not hasattr(dmd.Devices, 'zProdStateThreshold'):
            dmd.Devices._setProperty("zProdStateThreshold", 500, type="int")

        if getattr(dmd.Devices.rrdTemplates, 'Device', None) is None:
            from Products.ZenRelations.ImportRM import ImportRM
            imp = ImportRM(noopts=True, app=dmd.getPhysicalRoot())
            imp.options.noCommit = True
            imp.options.infile = zenPath(
                'Products', 'ZenModel', 'data', 'rrdconfig.update')
            imp.loadDatabase()


KillCricket()

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

__doc__="""DmdBuilder
DmdBuilder builds out the core containment structure used in the dmd database.

Devices
Groups
Locations
Networks
ServiceAreas
Services
Systems
"""

from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.IpNetwork import manage_addIpNetwork
from Products.ZenModel.ManufacturerRoot import ManufacturerRoot
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.System import System
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.DeviceReportClass import DeviceReportClass
from Products.ZenModel.CustomDeviceReportClass import CustomDeviceReportClass
from Products.ZenModel.GraphReportClass import GraphReportClass
from Products.ZenModel.MultiGraphReportClass import MultiGraphReportClass
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.ZDeviceLoader import manage_addZDeviceLoader
from Products.ZenModel.ZenossInfo import manage_addZenossInfo
from Products.ZenWidgets.ZenTableManager import manage_addZenTableManager
from Products.ZenModel.PerformanceConf import manage_addPerformanceConf
from Products.ZenRRD.RenderServer import manage_addRenderServer
from Products.ZenReports.ReportServer import manage_addReportServer
from Products.ZenEvents.MySqlEventManager import manage_addMySqlEventManager
from Products.ZenEvents.EventClass import manage_addEventClass
from Products.CMFCore.DirectoryView import manage_addDirectoryView
from Products.ZenModel.UserSettings import manage_addUserSettingsManager
from Products.ZenModel.LinkManager import manage_addLinkManager
from Products.ZenWidgets.PortletManager import manage_addPortletManager
from Products.ZenWidgets.ZenossPortlets import ZenossPortlets
from Products.ZenModel.ZenPackManager import manage_addZenPackManager
from Products.Jobber.manager import manage_addJobManager
from Products.ZenModel.ZenPackPersistence import CreateZenPackPersistenceCatalog
from Products.ZenModel.RRDTemplate import CreateRRDTemplatesCatalog
from Products.ZenModel.MaintenanceWindow import createMaintenanceWindowCatalog
from Products.Zuul.catalog.global_catalog import createGlobalCatalog
from Products.ZenModel.ZenossSecurity import \
     MANAGER_ROLE, ZEN_MANAGER_ROLE, ZEN_USER_ROLE, OWNER_ROLE
from Products.ZenModel.NotificationSubscription import manage_addNotificationSubscriptionManager
from Products.ZenModel.Trigger import manage_addTriggerManager


class DmdBuilder(object):

    def __init__(self, portal, evthost, evtuser, evtpass, evtdb, evtport,
                    smtphost, smtpport, pagecommand):
        self.portal = portal
        self.evthost = evthost
        self.evtuser = evtuser
        self.evtpass = evtpass
        self.evtport = evtport
        self.evtdb = evtdb
        dmd = DataRoot('dmd')
        self.portal._setObject(dmd.id, dmd)
        self.dmd = self.portal._getOb('dmd')
        self.dmd._rq = False
        self.dmd.smtpHost = smtphost
        self.dmd.smtpPort = smtpport
        self.dmd.pageCommand = pagecommand
        self.dmd.propertyTransformers = {}
        self.dmd.manage_permission('Access contents information',
                                   ['Authenticated',
                                    MANAGER_ROLE,
                                    ZEN_MANAGER_ROLE,
                                    ZEN_USER_ROLE,
                                    OWNER_ROLE],
                                   0)

    def buildRoots(self):
        roots = [('Devices', DeviceClass),
                 ('Groups', DeviceGroup),
                 ('Locations', Location),
                 ('Manufacturers', ManufacturerRoot),
                 ('Monitors', MonitorClass),
                 ('Mibs', MibOrganizer),
                 ('Processes', OSProcessOrganizer),
                 ('Reports', ReportClass),
                 ('Services', ServiceOrganizer),
                 ('Systems', System),
                 ]
        for objectId, construct in roots:
            if objectId not in self.dmd.objectIds():
                object = construct(objectId)
                object.isInTree = True
                self.dmd._setObject(objectId, object)
        devices = self.dmd._getOb('Devices')
        devices.createCatalog()
        devices.buildDeviceTreeProperties()

    def buildMonitors(self):
        perfId = 'Performance'
        monitors = self.dmd._getOb('Monitors')
        if perfId not in monitors.objectIds():
            monitors._setObject(perfId, MonitorClass(perfId))
            perf = monitors._getOb(perfId)
            perf.isInTree = False
            perf.sub_class = 'PerformanceConf'
            perfConfId = 'localhost'
            manage_addPerformanceConf(perf, perfConfId)
            perfConf = monitors.Performance._getOb(perfConfId)
            perfConf.renderurl = '/zport/RenderServer'

    def buildUserCommands(self):
        for id, cmd, desc in (
                ('ping', 'dcsh --collector=${device/getPerformanceServerName} -n "${device/pingCommand} -c2 ${device/manageIp}"',
                 "Is the device responding to ping?"),
                ('traceroute', 'dcsh --collector=${device/getPerformanceServerName} -n "${device/tracerouteCommand} -q 1 -w 2 ${device/manageIp}"',
                 "Show the route to the device"),
                ('DNS forward', 'dcsh --collector=${device/getPerformanceServerName} -n "host ${device/id}"',
                 "Name to IP address lookup"),
                ('DNS reverse', 'dcsh --collector=${device/getPerformanceServerName} -n "host ${device/manageIp}"',
                 "IP address to name lookup"),
                ('snmpwalk', 'dcsh --collector=${device/getPerformanceServerName} -n "snmpwalk -${device/zSnmpVer} -c${device/zSnmpCommunity} ${device/snmpwalkPrefix}${here/manageIp} system"',
                 "Display the OIDs available on a device"),
                ):
            self.dmd.manage_addUserCommand(id, cmd=cmd, desc=desc)

    def buildReportClasses(self):
        if not hasattr(self.dmd.Reports, 'Device Reports'):
            rc = DeviceReportClass('Device Reports')
            self.dmd.Reports._setObject(rc.id, rc)
        if not hasattr(self.dmd.Reports, 'Custom Device Reports'):
            rc = CustomDeviceReportClass('Custom Device Reports')
            self.dmd.Reports._setObject(rc.id, rc)
        if not hasattr(self.dmd.Reports, 'Graph Reports'):
            rc = GraphReportClass('Graph Reports')
            self.dmd.Reports._setObject(rc.id, rc)
        if not hasattr(self.dmd.Reports, 'Multi-Graph Reports'):
            rc = MultiGraphReportClass('Multi-Graph Reports')
            self.dmd.Reports._setObject(rc.id, rc)

    def buildPortlets(self):
        manage_addPortletManager(self.portal)
        zpmgr = self.portal.ZenPortletManager
        ZenossPortlets.register_default_portlets(zpmgr)

    def build(self):
        createGlobalCatalog(self.portal)
        self.buildRoots()
        self.buildMonitors()
        self.buildUserCommands()
        self.buildReportClasses()
        self.buildPortlets()
        manage_addEventClass(self.dmd)
        manage_addZDeviceLoader(self.dmd)
        manage_addZenTableManager(self.portal)
        manage_addZenossInfo(self.portal)
        manage_addDirectoryView(self.portal,'ZenUtils/js', 'js')
        manage_addRenderServer(self.portal, "RenderServer")
        manage_addReportServer(self.portal, "ReportServer")
        manage_addMySqlEventManager(self.dmd, evthost=self.evthost,
                                    evtuser=self.evtuser, evtpass=self.evtpass,
                                    evtdb=self.evtdb, evtport=self.evtport)
        manage_addMySqlEventManager(self.dmd, evthost=self.evthost,
                                    evtuser=self.evtuser, evtpass=self.evtpass,
                                    evtdb=self.evtdb, evtport=self.evtport,
                                    history=True)
        manage_addUserSettingsManager(self.dmd)
        manage_addNotificationSubscriptionManager(self.dmd)
        manage_addTriggerManager(self.dmd)
        manage_addLinkManager(self.dmd)
        manage_addJobManager(self.dmd)
        manage_addIpNetwork(self.dmd, "Networks")
        manage_addIpNetwork(self.dmd, "IPv6Networks", 64, version=6)
        manage_addZenPackManager(self.dmd)
        CreateZenPackPersistenceCatalog(self.dmd)
        CreateRRDTemplatesCatalog(self.dmd)
        createMaintenanceWindowCatalog(self.dmd)

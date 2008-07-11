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

import logging
log = logging.getLogger("zen.OS")

import types

from Software import Software

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Exceptions import *

from IpInterface import manage_addIpInterface
from WinService import manage_addWinService
from IpService import manage_addIpService
from OSProcess import manage_addOSProcess
from IpRouteEntry import manage_addIpRouteEntry
from FileSystem import manage_addFileSystem

from Products.ZenUtils.Utils import prepId

class OperatingSystem(Software):

    totalSwap = 0L
    uname = ""

    _properties = Software._properties + (
        {'id':'totalSwap', 'type':'long', 'mode':'w'},
        {'id':'uname', 'type':'string', 'mode':''},
    )

    _relations = Software._relations + (
        ("interfaces", ToManyCont(ToOne, 
            "Products.ZenModel.IpInterface", "os")),
        ("routes", ToManyCont(ToOne, "Products.ZenModel.IpRouteEntry", "os")),
        ("ipservices", ToManyCont(ToOne, "Products.ZenModel.IpService", "os")),
        ("winservices", ToManyCont(ToOne, 
            "Products.ZenModel.WinService", "os")),
        ("processes", ToManyCont(ToOne, "Products.ZenModel.OSProcess", "os")),
        ("filesystems", ToManyCont(ToOne, 
            "Products.ZenModel.FileSystem", "os")),
        ("software", ToManyCont(ToOne, "Products.ZenModel.Software", "os")),
    )

    security = ClassSecurityInfo()

    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')
            
    factory_type_information = (
        {
            'id'             : 'Device',
            'meta_type'      : 'Device',
            'description'    : """Base class for all devices""",
            'icon'           : 'Device_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDevice',
            'immediate_view' : '../deviceOsDetail',
            'actions'        : ()
         },
        )


    def __init__(self):
        id = "os"
        Software.__init__(self, id)
        self._delObject("os")   # OperatingSystem is a software 
                                # but doens't have os relationship


    def totalSwapString(self):
        return self.totalSwap and convToUnits(self.totalSwap) or 'unknown'

    def traceRoute(self, target, ippath):
        """Trace the route to target using our routing table.
        """
        log.debug("device %s target %s", self.getDeviceName(), target)
        nextdev = None
        for route in self.getRouteObjs():
            ip = route.getNextHopIp()
            log.debug("target %s next hop %s", route.getTarget(), ip)
            if ip == target.getManageIp():
                ippath.append(ip)
                return ippath
            if route.matchTarget(target.getManageIp()):
                if route.routetype == 'direct':
                    nextdev = target
                    break
                nextdev = route.getNextHopDevice()
                break
        else:
            log.debug("device %s default route", self.getDeviceName())
            ip = ""
            default = self.routes._getOb("0.0.0.0_0", None)
            if default:
                ip = default.getNextHopIp()
                nextdev = default.getNextHopDevice()
        if target == nextdev or ip=="0.0.0.0":
            ippath.append(target.id)
            return ippath
        if nextdev:
            ippath.append(ip)
            return nextdev.traceRoute(target, ippath)
        raise TraceRouteGap("unable to trace to %s, gap at %s" % (target.id,
                            self.getDeviceName()))


    def getRouteObjs(self):
        """Return our real route objects.
        """
        return filter(lambda r: r.target(), self.routes())


    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()

    def deleteDeviceComponents(self, context, componentNames=[], REQUEST=None):
        """Delete device components"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: 
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.manage_deleteComponent()
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def unlockDeviceComponents(self, context, componentNames=[], REQUEST=None):
        """Unlock device components"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: 
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.unlock()
        if REQUEST:
            return self.callZenScreen(REQUEST)
            
    def lockDeviceComponentsFromDeletion(self, context, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from deletion"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: 
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.lockFromDeletion(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def lockDeviceComponentsFromUpdates(self, context, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from updates"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: 
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.lockFromUpdates(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def addIpInterface(self, id, userCreated, REQUEST=None):
        """Add IpInterfaces.
        """
        manage_addIpInterface(self.interfaces, id, userCreated)
        if REQUEST:
            REQUEST['message'] = 'IpInterface created'
            REQUEST['RESPONSE'].redirect(
                self.interfaces._getOb(id).absolute_url())
            self._p_changed = True
            return self.callZenScreen(REQUEST)

    def deleteIpInterfaces(self, componentNames=[], REQUEST=None):
        """Delete IpInterfaces"""
        self.deleteDeviceComponents(self.interfaces, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpInterfaces deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)

    def unlockIpInterfaces(self, componentNames=[], REQUEST=None):
        """Unlock IpInterfaces"""
        self.unlockDeviceComponents(self.interfaces, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpInterfaces unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpInterfacesFromDeletion(self, componentNames=[],
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from deletion"""
        self.lockDeviceComponentsFromDeletion(self.interfaces, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpInterfaces locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpInterfacesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from updates"""
        self.lockDeviceComponentsFromUpdates(self.interfaces, componentNames,
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpInterfaces locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)

    def addWinService(self, className, userCreated, REQUEST=None):
        """Add an WinService.
        """
        org = self.dmd.Services.WinService
        wsc = org.find(org.parseServiceLiveSearchString(className))
        if wsc is not None:
            ws = manage_addWinService(self.winservices, 
                                    wsc.id,
                                    wsc.description,
                                    userCreated=userCreated)
            self._p_changed = True
        elif REQUEST:
            REQUEST['message'] = \
                'Could not find a WinService named %s' % className
            return self.callZenScreen(REQUEST)
            
        if REQUEST: 
            REQUEST['message'] = 'WinService added'
            REQUEST['RESPONSE'].redirect(ws.absolute_url())
            return self.callZenScreen(REQUEST)

    def deleteWinServices(self, componentNames=[], REQUEST=None):
        """Delete WinServices"""
        self.deleteDeviceComponents(self.winservices, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'WinServices deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def unlockWinServices(self, componentNames=[], REQUEST=None):
        """Unlock WinServices"""
        self.unlockDeviceComponents(self.winservices, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'WinServices unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockWinServicesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from deletion"""
        self.lockDeviceComponentsFromDeletion(self.winservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'WinServices locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockWinServicesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from updates"""
        self.lockDeviceComponentsFromUpdates(self.winservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'WinServices locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
    
    def getSubOSProcessClassesGen(self, REQUEST=None):
        """Get OS Process
        """
        return self.getDmdRoot('Processes').getSubOSProcessClassesGen()
        
    def addOSProcess(self, className, userCreated, REQUEST=None):
        """Add an OSProcess.
        """
        osp = manage_addOSProcess(self.processes, className, userCreated)
        self._p_changed = True
        if REQUEST:
            REQUEST['message'] = 'OSProcess created'
            REQUEST['RESPONSE'].redirect(osp.absolute_url())

    def deleteOSProcesses(self, componentNames=[], REQUEST=None):
        """Delete OSProcesses"""
        self.deleteDeviceComponents(self.processes, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'OSProcesses deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def unlockOSProcesses(self, componentNames=[], REQUEST=None):
        """Unlock OSProcesses"""
        self.unlockDeviceComponents(self.processes, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'OSProcesses unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockOSProcessesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from deletion"""
        self.lockDeviceComponentsFromDeletion(self.processes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'OSProcesses locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockOSProcessesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from updates"""
        self.lockDeviceComponentsFromUpdates(self.processes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'OSProcesses locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)

    def addIpService(self, className, protocol, userCreated, REQUEST=None):
        """Add IpServices.
        """
        org = self.dmd.Services.IpService
        ipsc = org.find(org.parseServiceLiveSearchString(className))
        if ipsc is not None:
            ips = manage_addIpService(self.ipservices,
                                ipsc.id,
                                protocol,
                                ipsc.port, 
                                userCreated=userCreated)
            self._p_changed = True
        elif REQUEST:
            REQUEST['message'] = \
                'Could not find an IpService named %s' % className
            return self.callZenScreen(REQUEST)
                
        if REQUEST:
            REQUEST['message'] = 'IpService added'
            REQUEST['RESPONSE'].redirect(ips.absolute_url())
            return self.callZenScreen(REQUEST)

    def deleteIpServices(self, componentNames=[], REQUEST=None):
        """Delete IpServices"""
        self.deleteDeviceComponents(self.ipservices, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpServices deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def unlockIpServices(self, componentNames=[], REQUEST=None):
        """Unlock IpServices"""
        self.unlockDeviceComponents(self.ipservices, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpServices unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpServicesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from deletion"""
        self.lockDeviceComponentsFromDeletion(self.ipservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpServices locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpServicesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from updates"""
        self.lockDeviceComponentsFromUpdates(self.ipservices, componentNames,
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpServices locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)

    def addFileSystem(self, id, userCreated, REQUEST=None):
        """Add a FileSystem.
        """
        fsid = prepId(id)
        manage_addFileSystem(self.filesystems, id, userCreated)
        self._p_changed = True
        if REQUEST:
            REQUEST['message'] = 'FileSystem created'
            REQUEST['RESPONSE'].redirect(
                self.filesystems._getOb(fsid).absolute_url())
            return self.callZenScreen(REQUEST)
            
    def deleteFileSystems(self, componentNames=[], REQUEST=None):
        """Delete FileSystems"""
        self.deleteDeviceComponents(self.filesystems, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'FileSystems deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def unlockFileSystems(self, componentNames=[], REQUEST=None):
        """Unlock FileSystems"""
        self.unlockDeviceComponents(self.filesystems, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'FileSystems unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockFileSystemsFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from deletion"""
        self.lockDeviceComponentsFromDeletion(self.filesystems, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'FileSystems locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockFileSystemsFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from updates"""
        self.lockDeviceComponentsFromUpdates(self.filesystems, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'FileSystems locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)

    def addIpRouteEntry(self, dest, routemask, nexthopid, interface, 
                        routeproto, routetype, userCreated, REQUEST=None):
        """Add an IpRouteEntry.
        """
        manage_addIpRouteEntry(self.routes, 
                                dest,
                                routemask, 
                                nexthopid, 
                                interface, 
                                routeproto, 
                                routetype, 
                                userCreated=userCreated)
        self._p_changed = True
        if REQUEST:
            REQUEST['message'] = 'IpRouteEntry created'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
            
    def deleteIpRouteEntries(self, componentNames=[], REQUEST=None):
        """Delete IpRouteEntries"""
        self.deleteDeviceComponents(self.routes, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpRouteEntries deleted'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def unlockIpRouteEntries(self, componentNames=[], REQUEST=None):
        """Unlock IpRouteEntries"""
        self.unlockDeviceComponents(self.routes, componentNames, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpRouteEntries unlocked'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpRouteEntriesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from deletion"""
        self.lockDeviceComponentsFromDeletion(self.routes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = 'IpRouteEntries locked from deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
    def lockIpRouteEntriesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from updates"""
        self.lockDeviceComponentsFromUpdates(self.routes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            REQUEST['message'] = \
                'IpRouteEntries locked from updates and deletion'
            REQUEST['RESPONSE'].redirect(self.absolute_url())
            return self.callZenScreen(REQUEST)
        
InitializeClass(OperatingSystem)

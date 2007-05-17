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

__doc__="""DeviceResult

A mixin for objects that get listed like devices
The primary object must implement device.

$Id: DeviceResultInt.py,v 1.9 2004/04/23 01:24:48 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

class DeviceResultInt:
    
    security = ClassSecurityInfo()

    security.declareProtected('View', 'getDeviceName')
    def getDeviceName(self):
        '''Get the device name of this device or associated device'''
        d = self.device()
        if d:
            return d.getId()
        return "No Device"


    security.declareProtected('View', 'getDeviceUrl')
    def getDeviceUrl(self):
        '''Get the primary url path of the device in which this
        interface is located'''
        d = self.device()
        if d:
            return d.getPrimaryUrlPath()
        return ""


    security.declareProtected('View', 'getDeviceLink')
    def getDeviceLink(self, screen=""):
        '''Get the primary link for the device'''
        d = self.device()
        if d:
            return "<a href='%s/%s'>%s</a>" % (
                d.getPrimaryUrlPath(), screen, d.getId())
        return ""


    security.declareProtected('View', 'getDeviceClassPath')
    def getDeviceClassPath(self):
        '''Get the device class for this device'''
        d = self.device()
        if d:
            return d.deviceClass().getOrganizerName()
        return "No Device"
    security.declareProtected('View', 'getDeviceClassName')
    getDeviceClassName = getDeviceClassPath


    security.declareProtected('View', 'getProdState')
    def getProdState(self):
        '''Get the production state of the device associated with
        this interface'''
        d = self.device()
        if d:
            return self.convertProdState(d.productionState)
        return "None" 


    security.declareProtected('View', 'getPingStatus')
    def getPingStatus(self):
        """get the ping status of the box if there is one"""
        from Products.ZenEvents.ZenEventClasses import Status_Ping
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            if (dev.monitorDevice() and 
                not getattr(dev, 'zPingMonitorIgnore', False)):
                return dev.getStatus(Status_Ping)
        else:
            return self.getStatus(Status_Ping)
        return -1
    security.declareProtected('View', 'getPingStatusNumber')
    getPingStatusNumber = getPingStatus


    security.declareProtected('View', 'getSnmpStatus')
    def getSnmpStatus(self):
        """get the snmp status of the box if there is one"""
        from Products.ZenEvents.ZenEventClasses import Status_Snmp
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            if (not getattr(dev, 'zSnmpMonitorIgnore', False)
                and getattr(dev, 'zSnmpCommunity', "")
                and dev.monitorDevice()):
                return dev.getStatus(Status_Snmp)
        return -1
    getSnmpStatusNumber = getSnmpStatus
    security.declareProtected('View', 'getSnmpStatusNumber')

    
    security.declareProtected('View', 'getXmlRpcStatus')
    def getXmlRpcStatus(self):
        """get the xmlrpc status of the box if there is one"""
        from Products.ZenEvents.ZenEventClasses import Status_XmlRpc
        dev = self.device()
        if dev:
            dev = dev.primaryAq()
            if (not getattr(dev, 'zXmlRpcMonitorIgnore', False)
                and dev.monitorDevice()):
                return dev.getStatus(Status_XmlRpc)
        return -1
    getXmlRpcStatusNumber = getXmlRpcStatus
    security.declareProtected('View', 'getXmlRpcStatusNumber')


    security.declareProtected('View', 'isResultLockedFromUpdates')
    def isResultLockedFromUpdates(self):
        """Return the locked from updates flag"""
        d = self.device()
        if d:
            return d.isLockedFromUpdates()
        return False

    security.declareProtected('View', 'isResultLockedFromDeletion')
    def isResultLockedFromDeletion(self):
        """Return the locked from deletion flag"""
        d = self.device()
        if d:
            return d.isLockedFromDeletion()
        return False

    security.declareProtected('View', 'sendEventWhenResultBlocked')
    def sendEventWhenResultBlocked(self):
        """Return the send event flag"""
        d = self.device()
        if d:
            return d.sendEventWhenBlocked()
        return False


    security.declareProtected('View', 'getDeviceIp')
    def getDeviceIp(self):
        """Get the management ip (only) of a device"""
        d = self.device()
        if d:
            return d.manageIp
        return ""


    security.declareProtected('View', 'getDeviceIpAddress')
    def getDeviceIpAddress(self):
        """Get the management ip with netmask (1.1.1.1/24) of a device"""
        d = self.device()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getIpAddress()
        return ""
           

    security.declareProtected('View', 'getDeviceMacaddress')
    def getDeviceMacaddress(self):
        """get the mac address if there is one of the primary interface"""
        d = self.device()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getInterfaceMacaddress()
        return ""
   
    
InitializeClass(DeviceResultInt)

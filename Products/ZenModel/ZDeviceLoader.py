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

__doc__="""ZDeviceLoader.py

load devices from a GUI screen in the ZMI

$Id: ZDeviceLoader.py,v 1.19 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.19 $"[11:-2]

from logging import StreamHandler, Formatter, getLogger
log = getLogger("zen.DeviceLoader")

import transaction
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from OFS.SimpleItem import SimpleItem

from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader, clearWebLoggingStream
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenModel.Exceptions import DeviceExistsError, NoSnmp
from Products.ZenWidgets import messaging
from ZenModelItem import ZenModelItem
from zExceptions import BadRequest


def manage_addZDeviceLoader(context, id="", REQUEST = None):
    """make a DeviceLoader"""
    if not id: id = "DeviceLoader"
    d = ZDeviceLoader(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


class ZDeviceLoader(ZenModelItem,SimpleItem):
    """Load devices into the DMD database"""

    portal_type = meta_type = 'DeviceLoader'

    manage_options = ((
            {'label':'ManualDeviceLoader', 'action':'manualDeviceLoader'},
            ) + SimpleItem.manage_options)


    security = ClassSecurityInfo()

    factory_type_information = (
        {
            'immediate_view' : 'addDevice',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'addDevice'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
        },
        )

    def __init__(self, id):
        self.id = id


    def loadDevice(self, deviceName, devicePath="/Discovered",
            tag="", serialNumber="",
            zSnmpCommunity="", zSnmpPort=161, zSnmpVer=None,
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="",
            osManufacturer="", osProductName="",
            locationPath="", groupPaths=[], systemPaths=[],
            performanceMonitor="localhost",
            discoverProto="snmp",priority=3,REQUEST=None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration.
        """
        if not deviceName: return self.callZenScreen(REQUEST)
        deviceName = deviceName.replace(' ', '')
        device = None

        xmlrpc = isXmlRpc(REQUEST)

        """
        Get performance monitor and call createDevice so that the correct
        version (local/remote) of createDevice gets invoked
        """
        monitor = self.getDmdRoot("Monitors").getPerformanceMonitor(
                                                performanceMonitor)

        try:
            device = monitor.createDevice(self, deviceName, devicePath,
                                    tag, serialNumber,
                                    zSnmpCommunity, zSnmpPort, zSnmpVer,
                                    rackSlot, productionState, comments,
                                    hwManufacturer, hwProductName,
                                    osManufacturer, osProductName,
                                    locationPath, groupPaths, systemPaths,
                                    performanceMonitor, discoverProto, 
                                    priority, "", REQUEST)
        except (SystemExit, KeyboardInterrupt): raise
        except ZentinelException, e:
            log.info(e)
            if xmlrpc: return 1
        except DeviceExistsError, e:
            log.info(e)
            if xmlrpc: return 2
        except NoSnmp, e:
            log.info(e)
            if xmlrpc: return 3
        except Exception, e:
            log.exception(e)
            log.exception('load of device %s failed' % deviceName)
            transaction.abort()

        if device is None:
            log.error("Unable to add the device %s" % deviceName)
        else:
            log.info("Discovery job scheduled.")

        if REQUEST and not xmlrpc:
            REQUEST.RESPONSE.redirect('/zport/dmd/JobManager/joblist')
        if xmlrpc: return 0


    def addManufacturer(self, newHWManufacturerName=None,
                        newSWManufacturerName=None, REQUEST=None):
        """add a manufacturer to the database"""
        mname = newHWManufacturerName
        field = 'hwManufacturer'
        if not mname:
            mname = newSWManufacturerName
            field = 'osManufacturer'
        try:
            self.getDmdRoot("Manufacturers").createManufacturer(mname)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        if REQUEST:
            REQUEST[field] = mname
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setHWProduct')
    def setHWProduct(self, newHWProductName, hwManufacturer, REQUEST=None):
        """set the productName of this device"""
        if not hwManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select a HW Manufacturer',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST) 

        self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        newHWProductName, hwManufacturer)
        if REQUEST:
            REQUEST['hwProductName'] = newHWProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setOSProduct')
    def setOSProduct(self, newOSProductName, osManufacturer, REQUEST=None):
        """set the productName of this device"""
        if not osManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select an OS Manufacturer.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        self.getDmdRoot("Manufacturers").createSoftwareProduct(
                                        newOSProductName, osManufacturer, isOS=True)
        if REQUEST:
            REQUEST['osProductName'] = newOSProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addLocation')
    def addLocation(self, newLocationPath, REQUEST=None):
        """add a location to the database"""
        try:
            self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e
            
        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a system to the database"""
        try:
            self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e

        syss = REQUEST.get('systemPaths', [])
        syss.append(newSystemPath)
        if REQUEST:
            REQUEST['systemPaths'] = syss
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database"""
        try:
            self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e

        groups = REQUEST.get('groupPaths', [])
        groups.append(newDeviceGroupPath)
        if REQUEST:
            REQUEST['groupPaths'] = groups
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setPerformanceMonitor')
    def setPerformanceMonitor(self, newPerformanceMonitor, REQUEST=None):
        """add new performance monitor to the database"""
        try:
            self.getDmdRoot("Monitors").getPerformanceMonitor(newPerformanceMonitor)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e 
        if REQUEST:
            REQUEST['performanceMonitor'] = newPerformanceMonitor
            return self.callZenScreen(REQUEST)


    def setupLog(self, response):
        """setup logging package to send to browser"""
        root = getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        alog = getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)


    def loaderFooter(self, devObj, response):
        """add navigation links to the end of the loader output"""
        if not devObj: return
        devurl = devObj.absolute_url()
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to device <a href=%s>%s</a></td></tr>""" 
            % (devurl, devObj.getId()))
        response.write("</table></body></html>")

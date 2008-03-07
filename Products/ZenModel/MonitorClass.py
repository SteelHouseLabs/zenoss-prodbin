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

__doc__="""MonitorClass

Organizes Monitors

$Id: MonitorClass.py,v 1.11 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision$"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_base
from OFS.Folder import Folder
from Products.ZenUtils.Utils import checkClass
from ZenModelRM import ZenModelRM

from RRDTemplate import RRDTemplate

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())

from Products.ZenRelations.RelSchema import ToManyCont, ToOne


class MonitorClass(ZenModelRM, Folder):
    #isInTree = 1
    meta_type = "MonitorClass"
    sub_class = 'MonitorClass'
    dmdRootName = 'Monitors'

    _properties = (
        {'id':'title', 'type':'string', 'mode':'w'},
        {'id':'sub_class', 'type':'string', 'mode':'w'},
        {'id':'sub_meta_types', 'type':'lines', 'mode':'w'},
    )

    factory_type_information = ( 
        { 
            'id'             : 'MonitorClass',
            'meta_type'      : meta_type,
            'description'    : "Monitor Class",
            'icon'           : 'Classification_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addMonitorClass',
            'immediate_view' : 'monitorList',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'monitorList'
                , 'permissions'   : (
                  permissions.view, )
                , 'visible'       : 0
                },
            )
          },
        )
    
    security = ClassSecurityInfo()
    _relations = ZenModelRM._relations + (
        ('rrdTemplates', ToManyCont(ToOne, 'Products.ZenModel.RRDTemplate', 'deviceClass')),
        )


    def __init__(self, id, title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)

    def getStatusMonitor(self, monitorName):
        """get or create the status monitor name"""
        from Products.ZenModel.StatusMonitorConf \
            import manage_addStatusMonitorConf
        statusMonitorObj = self.getDmdRoot("Monitors").StatusMonitors
        if not hasattr(statusMonitorObj, monitorName):
            manage_addStatusMonitorConf(statusMonitorObj, monitorName)
        return statusMonitorObj._getOb(monitorName)


    def getStatusMonitorNames(self):
        """return a list of all status monitor names"""
        status = self.getDmdRoot("Monitors").StatusMonitors
        snames = status.objectIds(spec='StatusMonitorConf')
        snames.sort()
        return snames

    def getPerformanceMonitor(self, monitorName):
        """get or create the performance monitor name"""
        from Products.ZenModel.PerformanceConf \
            import manage_addPerformanceConf
        perfServerObj = self.getDmdRoot("Monitors").Performance
        if not hasattr(perfServerObj, monitorName):
            manage_addPerformanceConf(perfServerObj, monitorName)
        return perfServerObj._getOb(monitorName)


    def getPerformanceMonitorNames(self):
        """return a list of all performance monitor names"""
        perfServer = self.getDmdRoot("Monitors").Performance
        cnames = perfServer.objectIds(spec=('PerformanceConf'))
        cnames.sort()
        return cnames
            

    def objectSubValues(self):
        """get contained objects that are sub classes of sub_class"""
        retdata = []
        for obj in self.objectValues():
            if checkClass(obj.__class__, self.sub_class):
                retdata.append(obj)
        return retdata


    def manage_removeMonitor(self, ids = None, submon = None, REQUEST=None):
        'Add an object of sub_class, from a module of the same name'
        msg = ''
        child = self._getOb(submon) or self
        if ids:
            if len(ids) < len(child._objects):
                num = 0
                for id in ids:
                    if child.hasObject(id):
                        child._delObject(id)
                        num += 1
                msg = 'Deleted %s monitors' % num
                        
            else:
                msg = 'You must have at least one monitor'
        else:
            msg = 'No monitors are selected'
        if REQUEST:
            if msg:
                REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)


    def manage_addMonitor(self, id, submon=None, REQUEST=None):
        'Remove an object from this one'
        values = {}
        child = self._getOb(submon) or self
        exec('from Products.ZenModel.%s import %s' % (child.sub_class,
                                                      child.sub_class), values)
        ctor = values[child.sub_class]
        if id: child._setObject(id, ctor(id))
        if REQUEST: 
            REQUEST['message'] = 'Monitor created'
            return self.callZenScreen(REQUEST)


    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        for o in self.objectValues():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)


    def getAllRRDTemplates(self):
        "return the list of RRD Templates available at all levels"
        return self.rrdTemplates()


    def getRRDTemplates(self):
        "return the list of RRD Templates available at this level"
        return self.rrdTemplates()


    security.declareProtected('Add DMD Objects', 'manage_addRRDTemplate')
    def manage_addRRDTemplate(self, id, REQUEST=None):
        """Add an RRDTemplate to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        id = self.prepId(id)
        org = RRDTemplate(id)
        self.rrdTemplates._setObject(org.id, org)
        if REQUEST: 
            REQUEST['message'] = "Template added"
            return self.callZenScreen(REQUEST)
            

    def manage_deleteRRDTemplates(self, ids=(), paths=(), REQUEST=None):
        """Delete RRDTemplates from this MonitorClass 
        (skips ones in other Classes)
        """
        if not ids and not paths:
            return self.callZenScreen(REQUEST)
        for id in ids:
            self.rrdTemplates._delObject(id)
        for path in paths:
            id = path.split('/')[-1]
            self.rrdTemplates._delObject(id)
        if REQUEST: 
            REQUEST['message'] = "Templates deleted"
            return self.callZenScreen(REQUEST)

    def getSubDevicesGen(self):
        return []

    
InitializeClass(MonitorClass)

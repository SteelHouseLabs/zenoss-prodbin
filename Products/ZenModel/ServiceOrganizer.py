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

import types
import logging
log = logging.getLogger("zen.ServiceOrganizer")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base
from Commandable import Commandable
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *

from Organizer import Organizer
from ServiceClass import ServiceClass
from IpServiceClass import IpServiceClass

def manage_addServiceOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = ServiceOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addServiceOrganizer = DTMLFile('dtml/addServiceOrganizer',globals())

class ServiceOrganizer(Organizer, Commandable, ZenPackable):
    meta_type = "ServiceOrganizer"
    dmdRootName = "Services"
    default_catalog = "serviceSearch"

    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        ) 

    _relations = Organizer._relations + ZenPackable._relations + (
        ("serviceclasses", ToManyCont(ToOne,"Products.ZenModel.ServiceClass","serviceorganizer")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )
        
    factory_type_information = ( 
        { 
            'id'             : 'ServiceOrganizer',
            'meta_type'      : 'ServiceOrganizer',
            'icon'           : 'ServiceOrganizer.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServiceOrganizer',
            'immediate_view' : 'serviceOrganizerOverview',
            'actions'        :
            ( 
                { 'id'            : 'classes'
                , 'name'          : 'Classes'
                , 'action'        : 'serviceOrganizerOverview'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'serviceOrganizerManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id=None):
        if not id: id = self.dmdRootName
        super(ServiceOrganizer, self).__init__(id)
        if self.id == self.dmdRootName:
            self.createCatalog()
            self.buildZProperties()
   

    def find(self, query):
        """Find a service class by is serviceKey.
        """
        cat = getattr(self, self.default_catalog, None)
        if not cat: return 
        brains = cat({'serviceKeys': query})
        if not brains: return None
        try:
            return self.getObjByPath(brains[0].getPrimaryId) 
        except KeyError:
            log.warn("bad path '%s' for index '%s'", brains[0].getPrimaryId,
                        self.default_catalog)

    
    def countClasses(self):
        """Count all serviceclasses with in a ServiceOrganizer.
        """
        count = self.serviceclasses.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    def createServiceClass(self, name="", description="",
                           path="", factory=ServiceClass, **kwargs):
        """Create a service class (or retrun existing) based on keywords.
        """
        svcs = self.getDmdRoot(self.dmdRootName)
        svccl = svcs.find(name)
        if not svccl: 
            svcorg = svcs.createOrganizer(path)
            svccl = factory(name, (name,),description=description, **kwargs)
            svcorg.serviceclasses._setObject(svccl.id, svccl)
            svccl = svcorg.serviceclasses._getOb(svccl.id)
        return svccl 

    
    def manage_addServiceClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = ServiceClass(id)
            self.serviceclasses._setObject(id, sc)
        if REQUEST or not id:
            return self.callZenScreen(REQUEST)
        else:
            return self.serviceclasses._getOb(id)

    
    def manage_addIpServiceClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = IpServiceClass(id)
            self.serviceclasses._setObject(id, sc)
        if REQUEST or not id:
            return self.callZenScreen(REQUEST)
        else:
            return self.serviceclasses._getOb(id)

    
    def unmonitorServiceClasses(self, ids=None, REQUEST=None):
        return self.monitorServiceClasses(ids, False, REQUEST)

   
    def monitorServiceClasses(self, ids=None, monitor=True, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            svc = self.serviceclasses._getOb(id)
            svc.setZenProperty("zMonitor", monitor)
        if REQUEST: return self()


    def removeServiceClasses(self, ids=None, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        for id in ids:
            self.serviceclasses._delObject(id)
        if REQUEST: return self()


    def moveServiceClasses(self, moveTarget, ids=None, REQUEST=None):
        """Move ServiceClasses from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) == types.StringType: ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.serviceclasses._getOb(id)
            rec._operation = 1 # moving object state
            self.serviceclasses._delObject(id)
            target.serviceclasses._setObject(id, rec)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def buildZProperties(self):
        if hasattr(aq_base(self), "zMonitor"): return
        self._setProperty("zMonitor", False, type="boolean")
        self._setProperty("zFailSeverity", 5, type="int")
        self._setProperty("zHideFieldsFromList", [], type="lines")


    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for srv in self.getSubOrganizers():
            for inst in srv.serviceclasses(): 
                inst.index_object()


    def createCatalog(self):
        """Create a catalog for ServiceClass searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('serviceKeys', 'KeywordIndex')
        zcat.addColumn('getPrimaryId')


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        targets = []
        for sc in self.serviceclasses():
            targets += sc.getUserCommandTargets()
        for so in self.children():
            targets += so.getUserCommandTargets()
        return targets            


    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/serviceOrganizerManage'

    
    def getServiceLiveSearchList(self):
        """ Get a list of id and descriptions for a live search
        """
        liveSearchList = []
        for srv in self.getSubInstancesGen(rel='serviceclasses'):
            if getattr(srv, 'description', None):
                liveSearchList.append('%s [%s]' % (srv.id, srv.description))
            else:
                liveSearchList.append(srv.id)
        return liveSearchList
    
    def parseServiceLiveSearchString(self, str):
        """ Parse a string of id and description from a live search
        """
        id = str.split(' ')
        if type(id) == types.TupleType:
            id = id[0]
        return id


InitializeClass(ServiceOrganizer)

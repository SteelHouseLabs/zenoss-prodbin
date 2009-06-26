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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging

from Service import Service

def manage_addWinService(context, id, description, userCreated=None, 
                         REQUEST=None):
    """make a device"""
    s = WinService(id)
    context._setObject(id, s)
    s = context._getOb(id)
    s.description = description
    args = {'name':id, 'description':description}
    s.setServiceClass(args)
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                  +'/manage_main')
    return s


class WinService(Service):
    """Windows Service Class
    """
    portal_type = meta_type = 'WinService'

    acceptPause = False
    acceptStop = False
    pathName = ""
    serviceType = ""
    startMode = ""
    startName = ""
    collectors = ('zenwin',)

    _properties = Service._properties + (
        {'id': 'acceptPause', 'type':'boolean', 'mode':'w'},
        {'id': 'acceptStop', 'type':'boolean', 'mode':'w'},
        {'id': 'pathName', 'type':'string', 'mode':'w'},
        {'id': 'serviceType', 'type':'string', 'mode':'w'},
        {'id': 'startMode', 'type':'string', 'mode':'w'},
        {'id': 'startName', 'type':'string', 'mode':'w'},
    )

    _relations = Service._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "winservices")),
    )

    factory_type_information = (
        {
            'immediate_view' : 'winServiceDetail',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'winServiceDetail'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'winServiceManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "'%s' StartMode:%s StartName:%s" % (self.caption(), 
                        self.startMode, self.startName)

    def monitored(self):
        """Should this Windows Service be monitored
        """
        startMode = getattr(self, startMode, None)
        #don't monitor Disabled services
        if startMode and startMode == "Disabled": return False
        return Service.monitored(self)

    def getServiceClass(self):
        """Return a dict like one set by zenwinmodeler for services.
        """
        desc = self.description
        if not desc:
            svccl = self.serviceclass()
            if svccl: desc = svccl.description
        return {'name': self.name(), 'description': desc }


    def setServiceClass(self, kwargs):
        """Set the service class where name=ServiceName and description=Caption.
        """
        name = kwargs['name']
        description = kwargs['description']
        path = "/WinService/"
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, description=description, 
                                           path=path)
        self.serviceclass.addRelation(srvclass)


    def caption(self):
        """Return the windows caption for this service.
        """
        svccl = self.serviceclass()
        if svccl: return svccl.description
        return ""
    primarySortKey = caption

    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, id=None, description=None, 
                            acceptPause=None, acceptStop=None,
                            pathName=None, serviceType=None,
                            startMode=None, startName=None,
                            monitor=False, severity=5, 
                            REQUEST=None):
        """Edit a Service from a web page.
        """
        renamed = False
        if id is not None:
            self.description = description
            self.acceptPause = acceptPause
            self.acceptStop = acceptStop
            self.pathName = pathName
            self.serviceType = serviceType
            self.startMode = startMode
            self.startName = startName
            if self.id != id:
                id = prepId(id)
                self.setServiceClass(dict(name=id, description=description))
                renamed = self.rename(id)
        tmpl = super(WinService, self).manage_editService(monitor, severity,
                                                    REQUEST=REQUEST)
        if REQUEST and renamed:
            messaging.IMessageSender(self).sendToBrowser(
                'Service Renamed',
                "Object renamed to: %s" % self.id
            )
            return self.callZenScreen(REQUEST, renamed)
        return tmpl

InitializeClass(WinService)


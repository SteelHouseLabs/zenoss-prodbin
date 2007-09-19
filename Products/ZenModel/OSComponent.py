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

from Linkable import Linkable
from ManagedEntity import ManagedEntity
from DeviceComponent import DeviceComponent


class OSComponent(DeviceComponent, ManagedEntity, Linkable):
    """
    Logical Operating System component like a Process, IpInterface, etc.
    """
    isUserCreatedFlag = False

    _relations = ManagedEntity._relations + Linkable._relations
    
    def setUserCreateFlag(self):
        self.isUserCreatedFlag = True
        
    def isUserCreated(self):
        return self.isUserCreatedFlag

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        os = self.os()
        if os: return os.device()

    def manage_deleteComponent(self, REQUEST=None):
        """
        Delete OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url()
        self.getPrimaryParent()._delObject(self.id)
        '''
        eventDict = {
            'eventClass': Change_Remove,
            'device': self.device().id,
            'component': self.id or '',
            'summary': 'Deleted by user: %s' % 'user',
            'severity': Event.Info,
            }
        self.dmd.ZenEventManager.sendEvent(eventDict)
        '''
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)

    def manage_updateComponent(context, datamap, REQUEST=None):
        """
        Update OSComponent
        """
        url = None
        if REQUEST is not None:
            url = self.device().os.absolute_url()
        self.getPrimaryParent()._updateObject(self, datamap)
        '''
        eventDict = {
            'eventClass': Change_Set,
            'device': self.device().id,
            'component': self.id or '',
            'summary': 'Updated by user: %s' % 'user',
            'severity': Event.Info,
            }
        self.dmd.ZenEventManager.sendEvent(eventDict)
        '''
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(url)

    def getEndpointName(self):
        """ Implement the Linkable interface for
            naming endpoints. See Linkable.py.
        """
        return "%s/%s" % (self.device().getId(), self.id)

    def isInLocation(self, context):
        """ Implement the Linkable interface for
            checking Location. See Linkable.py.
        """
        here = self.device().getLocationName()
        return here.startswith(context.getLocationName())

    def getIconPath(self):
        """ Override the device's zProperty and return
            an icon based on the class name
        """
        return "/zport/dmd/img/icons/%s.png" % self.meta_type.lower()

    def getPrettyLink(self):
        """ Gets a link to this object, plus an icon """
        template = ("<a href='%s' class='prettylink'>"
                    "<div class='device-icon-container'> "
                    "<img class='device-icon' src='%s'/> "
                    "</div>%s</a>")
        icon = self.getIconPath()
        href = self.getPrimaryUrlPath()
        name = self.id
        return template % (href, icon, name)

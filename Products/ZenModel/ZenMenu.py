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
from Products.ZenModel.ZenModelRM import ZenModelRM
from ZenMenuItem import ZenMenuItem
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo, Permissions
import logging
log = logging.getLogger("zen.Menu")

from ZenPackable import ZenPackable


class ZenMenu(ZenModelRM, ZenPackable):
    """ A Menu object that holds Menu Items. 
    """
    
    meta_type = 'ZenMenu'
    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("zenMenuItems", ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenuItem', 'zenMenus')),
        ("menuable", ToOne(
            ToManyCont, 'Products.ZenModel.ZenMenuable', 'zenMenus')),
        ) 

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, id=None, description='', action='', 
            permissions=(Permissions.view,), isdialog=False, isglobal=True, 
            banned_classes=(), allowed_classes=(), ordering=0.0, REQUEST=None):
        """ Add a menu item to a menu """
        mi = None
        if id:
            mi = ZenMenuItem(id)
            try: self.zenMenuItems._delObject(id)
            except AttributeError: pass
            self.zenMenuItems._setObject(id, mi)
            mi = self.zenMenuItems._getOb(mi.id)
            mi.description = description
            mi.action = action
            mi.permissions = permissions
            mi.isdialog = isdialog
            mi.isglobal = isglobal
            mi.banned_classes = list(banned_classes)
            mi.allowed_classes = list(allowed_classes)
            mi.ordering = ordering
        return mi
 
    security.declareProtected('Change Device', 'manage_deleteZenMenuItem')
    def manage_deleteZenMenuItem(self, delids=(), REQUEST=None):
        """ Delete Menu Items """
        if isinstance(delids, (str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenuItems._delObject(id)
        

InitializeClass(ZenMenu)


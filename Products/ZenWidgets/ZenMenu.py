################################################################################
#
#     Copyright (c) 2007 Zenoss, Inc.
#
################################################################################


from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from ZenMenuItem import ZenMenuItem
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo
import logging
log = logging.getLogger("zen.Menu")


class ZenMenu(ZenModelRM):
    """ A Menu object that holds Menu Items. 
    """
    
    meta_type = 'ZenMenu'
    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations =  (
        ("zenMenuItems", ToManyCont(
            ToOne, 'Products.ZenWidgets.ZenMenuItem', 'zenMenus')),
        ("menuable", ToOne(
            ToManyCont, 'Products.ZenWidgets.ZenMenuable', 'zenMenus')),
        ) 

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, id=None, desc='', action='', REQUEST=None):
        """ Add a menu item to a menu """
        mi = None
        if id:
            mi = ZenMenuItem(id)
            self.zenMenuItems._setObject(id, mi)
            mi.description = desc
            mi.action = action
        return mi
 
    security.declareProtected('Change Device', 'manage_deleteZenMenuItem')
    def manage_deleteZenMenuItem(self, delids=(), REQUEST=None):
        """ Delete Menu Items """
        if isinstance(delids, (str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenuItems._delObject(id)
        

InitializeClass(ZenMenu)


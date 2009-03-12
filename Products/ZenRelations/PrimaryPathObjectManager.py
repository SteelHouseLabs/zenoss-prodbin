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

__doc__="""PrimaryPathObjectManager

$Id: RelationshipBase.py,v 1.26 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

import logging
log = logging.getLogger("zen.PrimaryPathObjectManager")

# base classes for PrimaryPathObjectManager
from RelCopySupport import RelCopyContainer
from Acquisition import Implicit, aq_base
from OFS.ObjectManager import ObjectManager
from AccessControl.Role import RoleManager
import App.Undo

from ZItem import ZItem


from Products.ZenUtils.Utils import getObjByPath

from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2



class PrimaryPathManager(ZItem, Implicit, RoleManager):

    def getPrimaryPath(self, fromNode=None):
        """
        Return the primary path of this object by following __primary_parent__
        """
        ppath = []
        obj = aq_base(self)
        while True:
            ppath.append(obj.id)
            parent = getattr(obj, "__primary_parent__", None)
            if parent is None: break
            obj = parent
        ppath.reverse()
        basepath = getattr(obj, "zPrimaryBasePath", [])
        for i in range(len(basepath)-1,-1,-1): ppath.insert(0,basepath[i])
        try:
            idx = ppath.index(fromNode)
            ppath = ppath[idx+1:]
        except ValueError: pass
        return tuple(ppath)

    
    def getPrimaryId(self, fromNode=None):
        """Return the primary path in the form /zport/dmd/xyz"""
        pid = "/".join(self.getPrimaryPath(fromNode))
        if fromNode: pid = "/" + pid
        return pid


    def getPrimaryUrlPath(self, full=False):
        """Return the primary path as an absolute url"""
        objaq = self.primaryAq()
        if full: return objaq.absolute_url()
        return objaq.absolute_url_path()
        


    def primaryAq(self):
        """Return self with is acquisition path set to primary path"""
        app = self.getPhysicalRoot()
        return getObjByPath(app, self.getPrimaryPath())
       

    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()


class PrimaryPathObjectManager(
            RelCopyContainer,
            ObjectManager, 
            PrimaryPathManager, 
            App.Undo.UndoSupport,
            ):
    """
    PrimaryPathObjectManager with basic Zope persistent classes.
    """
    manage_options = (ObjectManager.manage_options +
                      RoleManager.manage_options +
                      ZItem.manage_options)

    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)


    def _delObject(self, id, dp=1):
        """When deleted clear __primary_parent__."""
        obj = self._getOb(id, False)
        if not obj:
            # Added this check because we are seeing stack traces in the UI. 
            # We aren't 100% sure what is causing the object to disappear from 
            # the ObjectManager. It could be that a different user had already 
            # deleted it or that a single user had two brower tabs open. Ian saw 
            # a case were the references on an object were wrong (getPrimaryId
            # pointed to the wrong location) but I'm not sure that is what is 
            # causing this problem. -EAD
            log.warning(
            "Tried to delete object id '%s' but didn't find it on %s", 
            id, self.getPrimaryId())
            return
        ObjectManager._delObject(self, id, dp)
        obj.__primary_parent__ = None


class PrimaryPathBTreeFolder2(BTreeFolder2):
    """
    BTreeFolder2 PrimaryPathObjectManager.
    """
    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)


    def _delObject(self, id, dp=1):
        """When deleted clear __primary_parent__."""
        obj = self._getOb(id)
        ObjectManager._delObject(self, id, dp)
        obj.__primary_parent__ = None

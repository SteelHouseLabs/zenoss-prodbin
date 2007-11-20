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

__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

import logging
log = logging.getLogger("zen.Relations")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from OFS.ObjectManager import checkValidId

from BTrees.OOBTree import OOBTree

from ToManyRelationshipBase import ToManyRelationshipBase

from Products.ZenRelations.Exceptions import *


def manage_addToManyContRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel =  ToManyContRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id 


addToManyContRelationship = DTMLFile('dtml/addToManyContRelationship',globals())


class ToManyContRelationship(ToManyRelationshipBase):
    """
    ToManyContRelationship is the ToMany side of a realtionship that 
    contains its related objects (like the normal Zope ObjectManager)
    """

    meta_type = "ToManyContRelationship"

    security = ClassSecurityInfo()


    def __init__(self, id):
        """set our instance values"""
        self.id = id
        self._objects = OOBTree()


    def __call__(self):
        """when we are called return our related object in our aq context"""
        return [ob.__of__(self) for ob in self._objects.values()]


    def __getattr__(self, name):
        """look in the two object stores for related objects"""
        if self.__dict__.has_key("_objects"):
            objects = self.__dict__['_objects']
            if objects.has_key(name): return objects[name]
        raise AttributeError, name


    def __hasattr__(self, name):
        """check to see if we have an object by an id
        this will fail if passed a short id and object is stored
        with fullid (ie: it is related not contained)
        use hasobject to get around this issue"""
        return self._objects.has_key(name)
            
            
    def hasobject(self, obj):
        "check to see if we have this object"
        return self._objects.get(obj.id) == obj
    

    def addRelation(self, obj):
        """Override base to run manage_afterAdd like ObjectManager"""
        ToManyRelationshipBase.addRelation(self, obj)
        obj = obj.__of__(self)
        obj.manage_afterAdd(obj, self)


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """ObjectManager interface to add contained object."""
        object.__primary_parent__ = aq_base(self)
        self.addRelation(object)
        object.manage_afterAdd(object, self)
        return object.getId()


    def manage_afterAdd(self, item, container):
        """
        Copied code from ObjectManager
        """
        for object in self.objectValues():
            try: s=object._p_changed
            except: s=0
            if hasattr(aq_base(object), 'manage_afterAdd'):
                object.manage_afterAdd(item, container)
            if s is None: object._p_deactivate()


    def manage_afterClone(self, item):
        """
        Copied code from ObjectManager
        """
        for object in self.objectValues():
            try: s=object._p_changed
            except: s=0
            if hasattr(aq_base(object), 'manage_afterClone'):
                object.manage_afterClone(item)
            if s is None: object._p_deactivate()


    def manage_beforeDelete(self, item, container):
        """
        Copied code from ObjectManager
        """
        for object in self.objectValues():
            try: s=object._p_changed
            except: s=0
            try:
                if hasattr(aq_base(object), 'manage_beforeDelete'):
                    object.manage_beforeDelete(item, container)
            except BeforeDeleteException, ob:
                raise
            except ConflictError:
                raise
            except:
                LOG('Zope',ERROR,'manage_beforeDelete() threw',
                    error=sys.exc_info())
                # In debug mode when non-Manager, let exceptions propagate.
                if getConfiguration().debug_mode:
                    if not getSecurityManager().getUser().has_role('Manager'):
                        raise
            if s is None: object._p_deactivate()
       

    def _add(self,obj):
        """add an object to one side of a ToManyContRelationship.
        """
        id = obj.id
        if self._objects.has_key(id):
            raise RelationshipExistsError
        v=checkValidId(self, id)
        if v is not None: id=v
        self._objects[id] = aq_base(obj)
        obj = aq_base(obj).__of__(self)


    def _remove(self, obj=None):
        """remove object from our side of a relationship"""
        if obj: objs = [obj]
        else: objs = self.objectValuesAll()
        for robj in objs:
            robj.manage_beforeDelete(robj, self)
        if obj:
            id = obj.id
            if not self._objects.has_key(id):
                raise ObjectNotFound(
                    "Object with id %s not found on relation %s" %
                    (id, self.id))
            del self._objects[id]
        else:
            self._objects = OOBTree()
            self.__primary_parent__._p_changed = True


    def _remoteRemove(self, obj=None):
        """remove an object from the far side of this relationship
        if no object is passed in remove all objects"""
        if obj:
            if not self._objects.has_key(obj.id): raise ObjectNotFround
            objs = [obj]
        else: objs = self.objectValuesAll()
        remoteName = self.remoteName()
        for obj in objs:
            rel = getattr(obj, remoteName)
            rel._remove(self.__primary_parent__)
   

    def _getOb(self, id, default=zenmarker):
        """look up in our local store and wrap in our aq_chain"""
        if self._objects.has_key(id):
            return self._objects[id].__of__(self)
        elif default == zenmarker:
            raise AttributeError, id
        return default


    security.declareProtected('View', 'objectIds')
    def objectIds(self, spec=None):
        """only return contained objects"""
        if spec:
            if type(spec)==type('s'): spec=[spec]
            return [obj.id for obj in self._objects.values() \
                        if obj.meta_type in spec]
        return [ k for k in self._objects.keys() ]
    objectIdsAll = objectIds


    security.declareProtected('View', 'objectValues')
    def objectValues(self, spec=None):
        """override to only return owned objects for many to many rel"""
        if spec:
            retval = []
            if type(spec)==type('s'): spec=[spec]
            return [ob.__of__(self) for ob in self._objects.values() \
                        if ob.meta_type in spec]
        return [ob.__of__(self) for ob in self._objects.values()]
    security.declareProtected('View', 'objectValuesAll')
    objectValuesAll = objectValues


    def objectValuesGen(self):
        """Generator that returns all related objects."""
        for obj in self._objects.values():
            yield obj.__of__(self)


    def objectItems(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if spec:
            if type(spec)==type('s'): spec=[spec]
            return [(key,value.__of__(self)) \
                for (key,value) in self._objects.items() \
                    if value.meta_type in spec]
        return [(key,value.__of__(self)) \
                    for (key,value) in self._objects.items()]
    objectItemsAll = objectItems


#FIXME - need to make this work
#    def all_meta_types(self, interfaces=None):
#        mts = []
#        for mt in ToManyRelationshipBase.all_meta_types(self, interfaces):
#            if (mt.has_key('instance') and mt['instance']):
#                for cl in self.sub_classes:
#                    if checkClass(mt['instance'], cl):
#                        mts.append(mt)
#        return mts
   

    def _getCopy(self, container):
        """
        make new relation add copies of contained objs 
        and refs if the relation is a many to many
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy: return rel
        for oobj in self.objectValuesAll():
            cobj = oobj._getCopy(rel)
            rel._setObject(cobj.id, cobj)
        return rel


    def exportXml(self, ofile, ignorerels=[]):
        """Return an xml representation of a ToManyContRelationship
        <tomanycont id='interfaces'>
            <object id='hme0' 
                module='Products.Confmon.IpInterface' class='IpInterface'>
                <property></property> etc....
            </object>
        </tomanycont>
        """
        if self.countObjects() == 0: return
        ofile.write("<tomanycont id='%s'>\n" % self.id)
        for obj in self.objectValues():
            obj.exportXml(ofile, ignorerels)
        ofile.write("</tomanycont>\n")

    
InitializeClass(ToManyContRelationship)

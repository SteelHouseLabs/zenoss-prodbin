#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]

import logging
log = logging.getLogger("zen.Relations")

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

from ToManyRelationshipBase import ToManyRelationshipBase

from Products.ZenRelations.Exceptions import *

def manage_addToManyRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel =  ToManyRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return rel.id 


addToManyRelationship = DTMLFile('dtml/addToManyRelationship',globals())


class ToManyRelationship(ToManyRelationshipBase):
    """
    ToManyRelationship manages the ToMany side of a bi-directional relation
    between to objects.  It does not return values for any of the object* 
    calls defined on ObjectManager so that Zope can still work with its
    containment assumptions.  It provides object*All calles that return
    its object in the same way that ObjectManager does.

    Related references are maintained in a list.
    """

    meta_type = "ToManyRelationship"


    def __init__(self, id):
        """ToManyRelationships use an array to store related objects"""
        self.id = id
        self._objects = []


    def __call__(self):
        """when we are called return our related object in our aq context"""
        return [ob.__of__(self) for ob in self._objects]


    def hasobject(self, obj):
        "check to see if we have this object"
        try:
            idx = self._objects.index(obj)
            return self._objects[idx]
        except ValueError:
            return None
            

    def manage_beforeDelete(self, item, container):
        """
        there are 4 possible states for _operation during beforeDelete
        -1 = object being deleted remove relation
        0 = copy, 1 = move, 2 = rename
        ToMany unlinks from its remote relations if its being deleted.
        ToMany will not propagate beforeDelete because its not a container.
        """
        if getattr(item, "_operation", -1) < 1: 
            self._remoteRemove()
        

    def manage_pasteObjects(self, cb_copy_data=None, REQUEST=None):
        """ToManyRelationships link instead of pasting"""
        return self.manage_linkObjects(cb_copy_data=cb_copy_data, 
                                        REQUEST=REQUEST)

        
    def _add(self,obj):
        """add an object to one side of this toMany relationship"""
        if obj in self._objects: return
        self._objects.append(aq_base(obj))
        self._count=len(self._objects)
        self._p_changed = 1


    def _remove(self, obj=None):
        """remove object from our side of a relationship"""
        if obj:
            try:
                self._objects.remove(obj)
            except ValueError:
                raise ObjectNotFound(
                    "Object with id %s not found on relation %s" % 
                    (obj.id, self.id))
        else:
            self._objects = []
        self._count=len(self._objects)
        self._p_changed = 1


    def _setObject(self,id,object,roles=None,user=None,set_owner=1):
        """Set and object onto a ToMany by calling addRelation"""
        self.addRelation(object)

    
    def _delObject(self, id):
        """
        Delete object by its absolute id (ie /zport/dmd/bla/bla)
        (this is sent out in the object*All API)
        """
        obj = self.unrestrictedTraverse(id)
        self.removeRelation(obj)

    
    def _getOb(self, id, default=zenmarker):
        """
        Return object based on its primaryId. plain id will not work!!!
        """
        objs = filter(lambda x: x.getPrimaryId() == id, self._objects)
        if len(objs) == 1: return objs[0]
        if default != zenmarker: return default
        raise AttributeError(id)


    def objectIdsAll(self):
        """
        Return object ids as their absolute primaryId. 
        """
        return [obj.getPrimaryId() for obj in self._objects]
           

    def objectIds(self, spec=None):
        """
        ToManyRelationship doesn't publish objectIds to prevent 
        zope recursion problems. 
        """
        return []
             

    def objectValuesAll(self):
        """return all related object values"""
        return [ob.__of__(self) for ob in self._objects]


    def objectValuesGen(self):
        """Generator that returns all related objects."""
        for obj in self._objects:
            yield obj.__of__(self)


    def objectValues(self, spec=None):
        """
        ToManyRelationship doesn't publish objectValues to prevent 
        zope recursion problems. 
        """
        return []


    def objectItemsAll(self):
        """
        Return object items where key is primaryId.
        """
        objs = []
        for obj in self._objects:
            objs.append((obj.getPrimaryId(), obj))
        return objs
           

    def objectItems(self, spec=None):
        """
        ToManyRelationship doesn't publish objectItems to prevent 
        zope recursion problems. 
        """
        return []


    def _getCopy(self, container):
        """
        create copy and link remote objects if remote side is TO_MANY
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, 'zNoRelationshipCopy', [])
        if self.id in norelcopy: return rel
        if self.remoteTypeName() == "ToMany":
            for robj in self.objectValuesAll():
                rel.addRelation(robj)
        return rel    


    def exportXml(self,ofile):
        """Return an xml representation of a ToManyRelationship
        <tomany id='interfaces'>
            <link>/Systems/OOL/Mail</link>
        </tomany>
        """
        if self.countObjects() == 0: return
        ofile.write("<tomany id='%s'>\n" % self.id)
        for id in self.objectIdsAll():
            ofile.write("<link objid='%s'/>\n" % id)
        ofile.write("</tomany>\n")

    
    def all_meta_types(self, interfaces=None):
        """Return empty list not allowed to add objects to a ToManyRelation"""
        return []


    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok.
        """
        if len(self._objects): log.info("checking relation: %s", self.id)
        rname = self.remoteName()
        parobj = self.getPrimaryParent()
        for obj in self._objects:
            rrel = getattr(obj, rname)
            if not rrel.hasobject(parobj):
                log.critical("obj:%s rel:%s robj:%s rrel:%s doesn't point back",
                    parobj.getPrimaryId(), self.id, obj.getPrimaryId(),rname)
                if repair:
                    log.warn("adding obj:%s to rrel:%s", 
                            self.getPrimaryId(),rname)
                    rrel._add(parobj)
            try:
                ppath = obj.getPrimaryPath()
                self.unrestrictedTraverse(ppath)
            except KeyError:
                log.critical("obj:%s rel:%s obj:%s no longer exists",
                        self.getPrimaryId(), self.id, obj.getPrimaryId())
                if repair: 
                    log.warn("removing rel to:%s", obj.getPrimaryId())
                    self._objects.remove(obj)
                    self._p_changed = 1
        keycount = {}
        for obj in self._objects:
            key = obj.getPrimaryId()
            c = keycount.setdefault(key, 0)
            c += 1
            keycount[key] = c
        dupkeys = []
        for k, v in keycount.items():
            if v > 1: 
                log.critical("obj:%s rel:%s dup found obj:%s count:%s", 
                             self.getPrimaryId(), self.id, key, v)
                dupkeys.append(k)
        for obj in self._objects:
            key = obj.getPrimaryId()
            if repair and key in dupkeys and keycount[key] > 1:
                while keycount[key] > 0:
                    log.critical("rel:%s remove dup obj:%s", self.id, key)
                    self._objects.remove(obj)
                    self._p_changed = 1
                    keycount[key] -= 1




InitializeClass(ToManyRelationship)

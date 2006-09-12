#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ImportRM

Export RelationshipManager objects from a zope database

$Id: ImportRM.py,v 1.3 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import sys
import os
import types
import transaction
from urlparse import urlparse

from xml.sax import make_parser, saxutils
from xml.sax.handler import ContentHandler

from Acquisition import aq_base

from DateTime import DateTime

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import importClass

from Products.ZenRelations.Exceptions import *

class ImportRM(ZCmdBase, ContentHandler):

    rootobj = None

    def context(self):
        return self.objstack[-1]


    def cleanattrs(self, attrs):
        myattrs = {}
        for key, val in attrs.items():
            myattrs[key] = str(val)
        return myattrs

        
    def startElement(self, name, attrs):
        attrs = self.cleanattrs(attrs)
        self.state = name
        self.log.debug("tag %s, context %s", name, self.context().id)
        if name == 'object':
            obj = self.createObject(attrs)
            if (not self.options.noindex and len(self.objstack) == 1 
                and hasattr(aq_base(obj), 'reIndex')):
                self.rootobj = obj
            self.objstack.append(obj)
        elif name == 'tomanycont' or name == 'tomany':
            self.objstack.append(self.context()._getOb(attrs['id']))
        elif name == 'toone':
            relname = attrs.get('id')
            self.log.debug("toone %s, on object %s", relname, self.context().id)
            rel = getattr(aq_base(self.context()),relname) 
            objid = attrs.get('objid')
            self.addLink(rel, objid)
        elif name == 'link':
            self.addLink(self.context(), attrs['objid'])
        elif name == 'property':
            self.curattrs = attrs


    def endElement(self, name):
        if name in ('object', 'tomany', 'tomanycont'):
            self.objstack.pop()
        elif name == 'objects':
            self.log.info("End loading objects")
            self.log.info("Processing links")
            self.processLinks()
            if self.rootobj is not None:
                self.log.info("calling reIndex %s", self.rootobj.getPrimaryId())
                self.rootobj.reIndex()
            if not self.options.noCommit:
                self.commit()
            self.log.info("Loaded %d objects into database" % self.objectnumber)
        elif name == 'property':
            self.setProperty(self.context(), self.curattrs, self.charvalue)
            self.charvalue = ""
       

    def characters(self, chars):
        self.charvalue += saxutils.unescape(chars)


    def createObject(self, attrs):
        """create an object and set it into its container"""
        id = attrs.get('id')
        obj = None
        try:
            if callable(self.context().id):
                obj = self.app.unrestrictedTraverse(id)
            else:
                obj = self.context()._getOb(id)
        except (KeyError, AttributeError): pass
        if obj is None:
            klass = importClass(attrs.get('module'), attrs.get('class'))
            if id.find("/") > -1:
                contextpath, id = os.path.split(id)
                self.objstack.append(
                    self.context().unrestrictedTraverse(contextpath))
            obj = klass(id)
            self.context()._setObject(obj.id, obj) 
            obj = self.context()._getOb(obj.id)
            transaction.savepoint()
            self.objectnumber += 1
            self.log.debug("Added object %s to database" % obj.getPrimaryId())
        else:
            self.log.warn("Object %s already exists skipping" % id)
        return obj


    def setProperty(self, obj, attrs, value):
        """Set the value of a property on an object.
        """
        name = attrs.get('id')
        proptype = attrs.get('type')
        setter = attrs.get("setter",None)
        self.log.debug("setting object %s att %s type %s value %s" 
                            % (obj.id, name, proptype, value))
        value = value.strip()
        if proptype == 'selection':
            try:
                firstElement = getattr(obj, name)[0]
                if type(firstElement) in types.StringTypes:
                    proptype = 'string'
            except IndexError:
		proptype = 'string'
        if proptype == "date":
            value = DateTime(value)
        elif proptype != "string" and proptype != 'text':
            value = eval(value)
        if not obj.hasProperty(name):
            obj._setProperty(name, value, type=proptype, setter=setter)
        else:
            obj._updateProperty(name, value)


    def addLink(self, rel, objid):
        """build list of links to form after all objects have been created
        make sure that we don't add other side of a bidirectional relation"""
        self.links.append((rel.getPrimaryId(), objid))


    def processLinks(self):
        """walk through all the links that we saved and link them up"""
        for relid, objid in self.links:
            try:
                self.log.debug("Linking relation %s to object %s",
                                relid,objid)
                rel = self.app.unrestrictedTraverse(relid)
                obj = self.app.unrestrictedTraverse(objid)
                if not rel.hasobject(obj):
                    rel.addRelation(obj)
            except:
                self.log.critical(
                    "Failed linking relation %s to object %s",relid,objid)
                raise
                                


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-i', '--infile',
                    dest="infile",
                    help="input file for import default is stdin")
        
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('--noindex',
                    dest='noindex',action="store_true",default=False,
                    help='Do not try to index data that was just loaded')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')

    def loadObjectFromXML(self, objstack=None, xmlfile=''):
        """This method can be used to load data for the root of Zenoss (default
        behavior) or it can be used to operate on a specific point in the
        Zenoss hierarchy (ZODB).

        Upon loading the XML file to be processed, the content of the XML file
        is handled (processed) by the methods in this class.
        """
        if objstack:
            self.objstack = [objstack]
        else:
            self.objstack = [self.app]
        self.links = []
        self.objectnumber = 0
        self.charvalue = ""
        if xmlfile:
            # check to see if we're getting the XML from a URL ...
            schema, host, path, null, null, null = urlparse(xmlfile)
            if schema and host:
                import urllib2
                self.infile = urllib2.urlopen(xmlfile)
            # ... or from a file on the file system
            else:
                self.infile = open(xmlfile)
        elif self.options.infile:
            self.infile = open(self.options.infile)
        else:
            self.infile = sys.stdin
        parser = make_parser()
        parser.setContentHandler(self)
        parser.parse(self.infile)
        self.infile.close()

    def loadDatabase(self):
        """The default behavior of loadObjectFromXML() will be to use the Zope
        app object, and thus operatate on the whole of Zenoss.
        """
        self.loadObjectFromXML()

    def commit(self):
        trans = transaction.get()
        trans.note('Import from file %s using %s' 
                    % (self.options.infile, self.__class__.__name__))
        trans.commit()


if __name__ == '__main__':
    im = ImportRM()
    im.loadDatabase()

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

__doc__="""ImportRM

Export RelationshipManager objects from a zope database

$Id: ImportRM.py,v 1.3 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import sys
import urllib2
import transaction
from urlparse import urlparse
from xml.dom.minidom import parse

from Products.ZenUtils.ZCmdBase import ZCmdBase

from Products.ZenRelations.Exceptions import *


class ImportDevices(ZCmdBase):

    def getDevicePath(self, device):
        
        def _getParentDevClass(node):
            ancestor = node.parentNode
            while ancestor.getAttribute('class') != 'DeviceClass':
                ancestor = ancestor.parentNode
            return ancestor

        ancestor = _getParentDevClass(device)
        path = []
        while ancestor.getAttribute('id') != '/zport/dmd/Devices':
            path.append(ancestor.getAttribute('id'))
            ancestor = _getParentDevClass(ancestor)
        path.reverse()
        return '/' + '/'.join(path)

    def processLinks(self, device):
        def parse_objid(objid, last=False):
            if last: objid = objid.split('/')[-1]
            else: objid = '/'.join(objid.split('/')[4:])
            objid = objid.encode('ascii')
            return objid
        d = dict(
            systemPaths = [],
            groupPaths = [],
            statusMonitors = [],
            performanceMonitor = '',
            locationPath = ''
        )
        tomanys = device.getElementsByTagName('tomany')
        toones = device.getElementsByTagName('toone')
        for tomany in tomanys:
            id = tomany.getAttribute('id')
            links = tomany.getElementsByTagName('link')
            if id == 'monitors':
                for link in links:
                    d['statusMonitors'].append(parse_objid(link.getAttribute('objid'),
                                                           True))
            elif id == 'systems':
                for link in links:
                    d['systemPaths'].append(parse_objid(link.getAttribute('objid')))
            elif id == 'groups':
                for link in links:
                    d['groupPaths'].append(parse_objid(link.getAttribute('objid')))
        for toone in toones:
            id = toone.getAttribute('id')
            objid = toone.getAttribute('objid')
            if id=='perfServer': d['performanceMonitor'] = parse_objid(objid,
                                                                       True)
            elif id=='location': d['locationPath'] = parse_objid(objid)
        return d


    def handleDevices(self):
        devs = self.doc.getElementsByTagName('object')
        for dev in devs:
            if dev.getAttribute('class') != 'Device': continue
            device = {
                'deviceName' : dev.getAttribute('id').encode('ascii'),
                'devicePath' : self.getDevicePath(dev).encode('ascii')
                }
            device.update(self.processLinks(dev))
            print "Loading %s into %s..." % (device['deviceName'],
                                             device['devicePath'])
            self.dmd.DeviceLoader.loadDevice(**device)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-i', '--infile',
                    dest="infile",
                    help="input file for import default is stdin")
        print "Build option infile"
        
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
        from Products.ZenUtils.Utils import unused
        unused(objstack)
        if xmlfile:
            # check to see if we're getting the XML from a URL ...
            schema, host, path, null, null, null = urlparse(xmlfile)
            if schema and host:
                self.infile = urllib2.urlopen(xmlfile)
            # ... or from a file on the file system
            else:
                self.infile = open(xmlfile)
        elif self.options.infile:
            self.infile = open(self.options.infile)
        else:
            self.infile = sys.stdin
        self.doc = parse(self.infile)
        self.handleDevices()
        self.doc.unlink()
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
    im = ImportDevices()
    im.loadDatabase()

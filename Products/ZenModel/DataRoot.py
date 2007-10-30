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

__doc__="""DataRoot

DataRoot is the object manager which contains all confmon
data objects.  It can be used as a global acquisition 
name space.
"""

import re
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from OFS.OrderedFolder import OrderedFolder
from OFS.CopySupport import CopyError, eNotSupported
from Products.CMFCore.DirectoryView import registerDirectory
from ImageFile import ImageFile
from Globals import HTMLFile, DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenModel.SiteError import SiteError
from ImageFile import ImageFile
from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenModel.ZenMenuable import ZenMenuable
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.IpUtil import IpAddressError
from Commandable import Commandable
import DateTime
import socket
import os
import sys

from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.Utils import extractPostContent

from AccessControl import Permissions as permissions

from ZenModelRM import ZenModelRM
from ZenossSecurity import ZEN_COMMON, ZEN_MANAGE_DMD

def manage_addDataRoot(context, id, title = None, REQUEST = None):
    """make a device"""
    dr = DataRoot(id, title)
    context._setObject(id, dr)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')
                                     

addDataRoot = DTMLFile('dtml/addDataRoot',globals())

class DataRoot(ZenModelRM, OrderedFolder, Commandable, ZenMenuable):
    meta_type = portal_type = 'DataRoot'

    manage_main = OrderedFolder.manage_main

    manage_options = OrderedFolder.manage_options

    #setTitle = DTMLFile('dtml/setTitle',globals())

    uuid = None
    availableVersion = None
    lastVersionCheck = 0
    lastVersionCheckAttempt = 0
    versionCheckOptIn = True
    reportMetricsOptIn = True
    acceptedTerms = True
    smtpHost = 'localhost'
    snppHost = 'localhost'
    smtpPort = 25
    snppPort = 444
    smtpUser = ''
    smtpPass = ''
    smtpUseTLS = 0
    emailFrom = ''
    iconMap = {}
    geomapapikey = ''
    geocache = ''
    version = ""

    _properties=(
        {'id':'title', 'type': 'string', 'mode':'w'},
        {'id':'prodStateDashboardThresh','type':'int','mode':'w'},
        {'id':'prodStateConversions','type':'lines','mode':'w'},
        {'id':'priorityConversions','type':'lines','mode':'w'},
        {'id':'priorityDashboardThresh','type':'int','mode':'w'},
        {'id':'statusConversions','type':'lines','mode':'w'},
        {'id':'interfaceStateConversions','type':'lines','mode':'w'},
        {'id':'administrativeRoles','type':'lines','mode':'w'},
        {'id':'uuid', 'type': 'string', 'mode':'w'},
        {'id':'availableVersion', 'type': 'string', 'mode':'w'},
        {'id':'lastVersionCheck', 'type': 'long', 'mode':'w'},
        {'id':'lastVersionCheckAttempt', 'type': 'long', 'mode':'w'},
        {'id':'versionCheckOptIn', 'type': 'boolean', 'mode':'w'},
        {'id':'reportMetricsOptIn', 'type': 'boolean', 'mode':'w'},
        {'id':'smtpHost', 'type': 'string', 'mode':'w'},
        {'id':'smtpPort', 'type': 'int', 'mode':'w'},
        {'id':'snppHost', 'type': 'string', 'mode':'w'},
        {'id':'snppPort', 'type': 'int', 'mode':'w'},
        {'id':'smtpUser', 'type': 'string', 'mode':'w'},
        {'id':'smtpPass', 'type': 'string', 'mode':'w'},
        {'id':'smtpUseTLS', 'type': 'int', 'mode':'w'},
        {'id':'emailFrom', 'type': 'string', 'mode':'w'},
        {'id':'geomapapikey', 'type': 'string', 'mode':'w'},
        {'id':'geocache', 'type': 'string', 'mode':'w'},
        )

    _relations =  (
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        ('packs',        ToManyCont(ToOne, 'Products.ZenModel.ZenPack',     'root')),
        ('zenMenus', ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenu', 'menuable')),
       )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'DataRoot',
            'meta_type'      : 'DataRoot',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'DataRoot_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addStatusMonitorconf',
            'immediate_view' : 'Dashboard',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : 'editSettings'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : 'dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : 'ZenUsers/manageUserFolder'
                , 'permissions'   : ( 'Manage DMD', )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'menus'
                , 'name'          : 'Menus'
                , 'action'        : 'editMenus'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : 'editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : '../About/zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../About/zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    # production state threshold at which devices show on dashboard
    prodStateDashboardThresh = 1000
    
    # priority threshold at which devices show on dashboard
    priorityDashboardThresh = 2

    prodStateConversions = [
                'Production:1000',
                'Pre-Production:500',
                'Test:400',
                'Maintenance:300',
                'Decommissioned:-1',
                ]

    priorityConversions = [
                'Highest:5',
                'High:4',
                'Normal:3',
                'Low:2',
                'Lowest:1',
                'Trivial:0',
                ]

    statusConversions = [
                'Up:0',
                'None:-1',
                'No DNS:-2',
                ]

    interfaceStateConversions = [
                'up:1',
                'down:2',
                'testing:3',
                'unknown:4',
                'dormant:5',
                'notPresent:6',
                'lowerLayerDown:7',
                ]

    administrativeRoles = (
        "Administrator",
        "Analyst",
        "Engineer",
        "Tester",
    )

    defaultDateRange = 129600 
    performanceDateRanges = [
        ('Hourly',129600,),
        ('Daily',864000,),
        ('Weekly',3628800,),
        ('Monthly',41472000,),
        ('Yearly',62208000,)
    ]


    # when calculating the primary path this will be its root
    zPrimaryBasePath = ("", "zport")


    def __init__(self, id, title=None):
        ZenModelRM.__init__(self, id, title)
        from ZVersion import VERSION
        self.version = "Zenoss " + VERSION


    def getEventCount(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.ZenEventManager.getEventCount(**kwargs)


    def getDmdRoots(self):
        return filter(lambda o: o.isInTree, self.objectValues())


    def exportXmlHook(self,ofile, ignorerels):
        map(lambda x: x.exportXml(ofile, ignorerels), self.getDmdRoots())
            
    
    security.declareProtected(ZEN_COMMON, 'getProdStateConversions')
    def getProdStateConversions(self):
        """getProdStateConversions() -> return a list of tuples 
        for prodstat select edit box"""
        return self.getConversions(self.prodStateConversions)

    
    security.declareProtected(ZEN_COMMON, 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        return self.convertAttribute(prodState, self.prodStateConversions)


    security.declareProtected(ZEN_COMMON, 'getStatusConversions')
    def getStatusConversions(self):
        """get text strings for status field"""
        return self.getConversions(self.statusConversions)


    security.declareProtected(ZEN_COMMON, 'convertStatus')
    def convertStatus(self, status):
        """get text strings for status field"""
        return self.convertAttribute(status, self.statusConversions)

    security.declareProtected(ZEN_COMMON, 'getPriorityConversions')
    def getPriorityConversions(self):
        return self.getConversions(self.priorityConversions)

    security.declareProtected(ZEN_COMMON, 'convertPriority')
    def convertPriority(self, priority):
        return self.convertAttribute(priority, self.priorityConversions)

    security.declareProtected(ZEN_COMMON, 'getInterfaceStateConversions')
    def getInterfaceStateConversions(self):
        """get text strings for interface status"""
        if hasattr(self, 'interfaceStateConversions'):
            return self.getConversions(self.interfaceStateConversions)


    security.declareProtected(ZEN_COMMON, 'convertAttribute')
    def convertAttribute(self, numbValue, conversions):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        numbValue = int(numbValue)
        for line in conversions:
            line = line.rstrip()
            (name, number) = line.split(':')
            if int(number) == numbValue:
                return name
        return numbValue


    security.declareProtected(ZEN_COMMON, 'getConversions')
    def getConversions(self, attribute):
        """get the text list of itmes that convert to ints"""
        convs = []
        for item in attribute:
            tup = item.split(':')
            tup[1] = int(tup[1])
            convs.append(tup)
        return convs

    security.declarePublic('filterObjectsRegex')
    def filterObjectsRegex(self, filter, objects,
                            filteratt='id', negatefilter=0):
        """filter a list of objects based on a regex"""
        filter = re.compile(filter).search
        filteredObjects = []
        for obj in objects:
            value = getattr(obj, filteratt, None)
            if callable(value):
                value = value()
            fvalue =  filter(value)
            if (fvalue and not negatefilter) or (not fvalue and negatefilter):
                filteredObjects.append(obj)
        return filteredObjects


    security.declareProtected('View', 'myUserGroups')
    def myUserGroups(self):
        user = self.REQUEST.get('AUTHENTICATED_USER')
        if hasattr(user, 'getGroups'):
            return user.getGroups()
        else:
            return ()


    security.declareProtected('View', 'getAllUserGroups')
    def getAllUserGroups(self):
        return self.acl_users.getGroups()

    def reportError(self):
        ''' send an email to the zenoss error email address
            then send user to a thankyou page or an email error page.
        '''
        mailSent = SiteError.sendErrorEmail(
                    self.REQUEST.errorType,
                    self.REQUEST.errorValue,
                    self.REQUEST.errorTrace,
                    self.REQUEST.errorUrl,
                    self.About.getZenossRevision(),
                    self.About.getZenossVersionShort(),
                    self.REQUEST.contactName,
                    self.REQUEST.contactEmail,
                    self.REQUEST.comments)
        if not mailSent:
            toAddress = SiteError.ERRORS_ADDRESS
            body = SiteError.createReport(
                                self.REQUEST.errorType,
                                self.REQUEST.errorValue,
                                self.REQUEST.errorTrace,
                                self.REQUEST.errorUrl,
                                self.About.getZenossRevision(),
                                self.About.getZenossVersionShort(),
                                True,
                                self.REQUEST.contactName,
                                self.REQUEST.contactEmail,
                                self.REQUEST.comments)
            return getattr(self, 'errorEmailFailure')(
                        toAddress=SiteError.ERRORS_ADDRESS,
                        body=body)
        return getattr(self, 'errorEmailThankYou')()


    #security.declareProtected('View', 'writeExportRows')
    def writeExportRows(self, fieldsAndLabels, objects, out=None):
        '''Write out csv rows with the given objects and fields.
        If out is not None then call out.write() with the result and return None
        otherwise return the result.
        Each item in fieldsAndLabels is either a string representing a 
         field/key/index (see getDataField) or it is a tuple of (field, label)
         where label is the string to be used in the first row as label
         for that column.
        Objects can be either dicts, lists/tuples or other objects. Field
         is interpreted as a key, index or attribute depending on what
         object is.
        Method names can be passed instead of attribute/key/indices as field.
         In this case the method is called and the return value is used in
         the export.
        '''
        import csv
        import StringIO
        if out:
            buffer = out
        else:
            buffer = StringIO.StringIO()
        fields = []
        labels = []
        if not fieldsAndLabels:
            fieldsAndLabels = []
        if not objects:
            objects = []
        for p in fieldsAndLabels:
            if isinstance(p, tuple):
                fields.append(p[0])
                labels.append(p[1])
            else:
                fields.append(p)
                labels.append(p)
        writer = csv.writer(buffer)
        writer.writerow(labels)
        def getDataField(thing, field):
            if isinstance(thing, dict):
                value = thing.get(field, '')
            elif isinstance(thing, list) or isinstance(thing, tuple):
                value = thing[int(field)]
            else:
                value = getattr(thing, field, '')
            if isinstance(value, ZenModelBase):
                value = value.id
            elif callable(value):
                value = value()
            if value == None:
                value = ''
            return str(value)
        for o in objects:
            writer.writerow([getDataField(o,f) for f in fields])
        if out:
            result = None
        else:
            result = buffer.getvalue()
        return result


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        raise 'Not supported on DataRoot'
        
        
    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/dataRootManage'
        

    def getEmailFrom(self):
        ''' Return self.emailFrom or a suitable default
        '''
        return self.emailFrom or 'zenossuser_%s@%s' % (
            getSecurityManager().getUser().getId(), socket.getfqdn())

    def manage_addZenPack(self, id,
                          author="",
                          organization="",
                          version="",
                          REQUEST = None):
        """make a new ZenPack"""
        from ZenPack import ZenPack
        pack = ZenPack(id)
        pack.author = author
        pack.organization = organization
        pack.version = version
        self.packs._setObject(id, pack)
        zp = zenPath('Products', id)
        if not os.path.isdir(zp):
            os.makedirs(zp, 0750)
            for d in ['objects', 'skins', 'modeler/plugins',
                      'reports', 'daemons']:
                os.makedirs(os.path.join(zp, d), 0750)
        skinsDir = os.path.join(zp, 'skins')
        skinsDir2 = os.path.join(skinsDir, id)
        if not os.path.isdir(skinsDir2):
            os.makedirs(skinsDir2, 0750)
        registerDirectory(skinsDir, globals())
        # Install in order to register the skins directory
        pack.install(self.getPhysicalRoot())
        if REQUEST is not None:
            return self.callZenScreen(REQUEST, redirect=True)


    def removeZenPacks(self, ids=(), REQUEST = None):
        """remove a ZenPack"""
        zp = zenPath('bin', 'zenpack')
        for pack in ids:
            os.system('%s run --remove %s' % (zp, pack))
        self._p_jar.sync()
        if REQUEST is not None:
            return self.callZenScreen(REQUEST, redirect=True)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_installZenPack')
    def manage_installZenPack(self, zenpack=None, REQUEST=None):
        """
        Installs the given zenpack.  Zenpack is a file upload from the browser.
        """
        import tempfile
        import fcntl
        import popen2
        import signal
        import time
        import select
        
        ZENPACK_INSTALL_TIMEOUT = 120
        
        def write(out, lines):
            # Looks like firefox renders progressive output more smoothly
            # if each line is stuck into a table row.  
            startLine = '<tr><td class="tablevalues">'
            endLine = '</td></tr>\n'
            if out:
                if not isinstance(lines, list):
                    lines = [lines]
                for l in lines:
                    if not isinstance(l, str):
                        l = str(l)
                    l = l.strip()
                    l = cgi.escape(l)
                    l = l.replace('\n', endLine + startLine)
                    out.write(startLine + l + endLine)

        if REQUEST:
            REQUEST['cmd'] = ''
            header, footer = self.commandOutputTemplate().split('OUTPUT_TOKEN')
            REQUEST.RESPONSE.write(str(header))
            out = REQUEST.RESPONSE
        else:
            out = None
        
        tFile = None
        child = None
        try:
            try:
                # Write the zenpack to the filesystem
                tFile = tempfile.NamedTemporaryFile()
                tFile.write(zenpack.read())
                tFile.flush()
            
                cmd = 'zenpack --install %s' % tFile.name
                child = popen2.Popen4(cmd)
                flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
                fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
                endtime = time.time() + ZENPACK_INSTALL_TIMEOUT
                self.write(out, '%s' % cmd)
                self.write(out, '')
                pollPeriod = 1
                firstPass = True
                while time.time() < endtime and (firstPass or child.poll()==-1):
                    firstPass = False
                    r, w, e = select.select([child.fromchild],[],[], pollPeriod)
                    if r:
                        t = child.fromchild.read()
                        #We are sometimes getting to this point without any data
                        # from child.fromchild. I don't think that should happen
                        # but the conditional below seems to be necessary.
                        if t:
                            self.write(out, t)
                if child.poll() == -1:
                    self.write(out, 'Command timed out for %s' % target.id +
                                    ' (timeout is %s seconds)' % timeout)
            except:
                self.write(out, 'Error installing ZenPack.')
                self.write(
                    out, 'type: %s  value: %s' % tuple(sys.exc_info()[:2]))
                self.write(out, '')
        finally:
            tFile.close()
            if child and child.poll() == -1:
                os.kill(child.pid, signal.SIGKILL)
        
        self.write(out, '')
        self.write(out, 'Done installing ZenPack.')
        if REQUEST:
            REQUEST.RESPONSE.write(footer)


    def getBrokenPackName(self, pack):
        ''' Extract the zenpack name from the broken module
        '''
        return pack.__class__.__module__.split('.')[1]

    def getIconPath(self, obj):
        """ Retrieve the appropriate image path associated
            with a given object.
        """
        try:
            return obj.primaryAq().zIcon 
        except AttributeError:
            return '/zport/dmd/img/icons/noicon.png'

    def setGeocodeCache(self, REQUEST=None):
        """ Store a JSON representation of
            the Google Maps geocode cache
        """
        cache = extractPostContent(REQUEST)
        self.geocache = cache
        return True

    security.declareProtected(ZEN_COMMON, 'getGeoCache')
    def getGeoCache(self, REQUEST=None):
        cachestr = self.geocache
        for char in ('\\r', '\\n'):
            cachestr = cachestr.replace(char, ' ')
        return cachestr

    def goToStatusPage(self, objid, REQUEST=None):
        """ Find a device or network and redirect 
            to its status page.
        """
        import urllib
        objid = urllib.unquote(objid)
        try:
            devid = objid
            if not devid.endswith('*'): devid += '*'
            obj = self.Devices.findDevice(devid)
        except: 
            obj=None
        if not obj:
            try:
                obj = self.Networks.getNet(objid)
            except IpAddressError:
                return None
        if not obj: return None
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(obj.getPrimaryUrlPath())


    def getXMLEdges(self, objid, depth=1, filter="/"):
        """ Get the XML representation of network nodes
            and edges using the obj with objid as a root
        """
        import urllib
        objid = urllib.unquote(objid)
        try:
            devid = objid
            if not devid.endswith('*'): devid += '*'
            obj = self.Devices.findDevice(devid)
        except: obj=None
        if not obj:
            obj = self.Networks.getNet(objid)
        if not obj:
            return '<graph><Start name="%s"/></graph>' % objid
        return obj.getXMLEdges(int(depth), filter, 
                               start=(obj.id,obj.getPrimaryUrlPath()))

InitializeClass(DataRoot)

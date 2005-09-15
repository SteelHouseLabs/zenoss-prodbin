#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DataRoot

DataRoot is the object manager which contains all confmon
data objects.  It can be used as a global acquisition 
name space.

$Id: DataRoot.py,v 1.25 2004/02/27 23:19:12 edahl Exp $"""

__version__ = "$Revision: 1.25 $"[11:-2]

import re

from AccessControl import ClassSecurityInfo
from OFS.Folder import Folder
from OFS.CopySupport import CopyError, eNotSupported
from ImageFile import ImageFile
from Globals import HTMLFile, DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from ImageFile import ImageFile
import DateTime

from Products.CMFCore import permissions

from ConfmonBase import ConfmonBase

def manage_addDataRoot(context, id, title = None, REQUEST = None):
    """make a device"""
    dr = DataRoot(id, title)
    context._setObject(id, dr)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 
                                     

addDataRoot = DTMLFile('dtml/addDataRoot',globals())

class DataRoot(ConfmonBase, Folder):
    meta_type = portal_type = 'DataRoot'

    manage_main = Folder.manage_main

    manage_options = Folder.manage_options

    #setTitle = DTMLFile('dtml/setTitle',globals())

    _properties=(
                {'id':'title', 'type': 'string', 'mode':'w'},
                {'id':'prodStateConversions','type':'lines','mode':'w'},
                {'id':'statusConversions','type':'lines','mode':'w'},
                {'id':'interfaceStateConversions','type':'lines','mode':'w'},
                {'id':'previousYearRange', 'type': 'int', 'mode':'w'},
                {'id':'futureYearRange', 'type': 'int', 'mode':'w'},
                {'id':'defaultBatchSize', 'type': 'int', 'mode':'w'},
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
            'immediate_view' : 'dmdIndex',
            'actions'        :
            ( 
                { 'id'            : 'dmdIndex'
                , 'name'          : 'Index'
                , 'action'        : 'dmdIndex'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    prodStateConversions = [
                'Production:1000',
                'Pre-Production:500',
                'Test:400',
                'Maintenance:300',
                'Decommissioned:-1',
                ]

    statusConversions = [
                'Not Tested:-1',
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

    # number of previous year in date popup
    previousYearRange = 2
   
    # number of future years in date popup
    futureYearRange = 2
    
    #default batch size of large lists
    defaultBatchSize = 20


    def __init__(self, id, title=None):
        ConfmonBase.__init__(self, id, title)


    security.declareProtected('View', 'getProdStateConversions')
    def getProdStateConversions(self):
        """getProdStateConversions() -> return a list of tuples 
        for prodstat select edit box"""
        return self.getConversions(self.prodStateConversions)

    
    security.declareProtected('View', 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        return self.convertAttribute(prodState, self.prodStateConversions)


    security.declareProtected('View', 'getStatusConversions')
    def getStatusConversions(self):
        """get text strings for status field"""
        return self.getConversions(self.statusConversions)


    security.declareProtected('View', 'convertStatus')
    def convertStatus(self, status):
        """get text strings for status field"""
        return self.convertAttribute(status, self.statusConversions)


    security.declareProtected('View', 'getInterfaceStateConversions')
    def getInterfaceStateConversions(self):
        """get text strings for interface status"""
        if hasattr(self, 'interfaceStateConversions'):
            return self.getConversions(self.interfaceStateConversions)


    security.declareProtected('View', 'convertAttribute')
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


    security.declareProtected('View', 'getConversions')
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
    
InitializeClass(DataRoot)

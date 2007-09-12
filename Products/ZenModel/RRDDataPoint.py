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

__doc__="""RRDDataPoint

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.

$Id:$"""

__version__ = "$Revision:$"[11:-2]

import os

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Acquisition import aq_parent

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

def manage_addRRDDataPoint(context, id, REQUEST = None):
    """make a RRDDataPoint"""
    dp = RRDDataPoint(id)
    context._setObject(dp.id, dp)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     
#addRRDDataPoint = DTMLFile('dtml/addRRDDataPoint',globals())

SEPARATOR = '_'

def convertMethodParameter(value, type):
    if type == "integer":
        return int(value)
    elif type == "string":
        return str(value)
    elif type == "float":
        return float(value)
    else:
        raise TypeError('Unsupported method parameter type: %s' % type)

class RRDDataPointError(Exception): pass

class RRDDataPoint(ZenModelRM, ZenPackable):

    meta_type = 'RRDDataPoint'
  
    rrdtypes = ('COUNTER', 'GAUGE', 'DERIVE', 'ABSOLUTE')
    
    createCmd = ""
    rrdtype = 'GAUGE'
    isrow = True
    rrdmin = None
    rrdmax = None
    
    ## These attributes can be removed post 2.1
    ## They should remain in 2.1 so the migrate script works correctly
    linetypes = ('', 'AREA', 'LINE')
    rpn = ""
    color = ""
    linetype = ''
    limit = -1
    format = '%5.2lf%s'
    

    _properties = (
        {'id':'rrdtype', 'type':'selection',
        'select_variable' : 'rrdtypes', 'mode':'w'},
        {'id':'createCmd', 'type':'text', 'mode':'w'},
        {'id':'isrow', 'type':'boolean', 'mode':'w'},
        {'id':'rrdmin', 'type':'string', 'mode':'w'},
        {'id':'rrdmax', 'type':'string', 'mode':'w'},
        )


    _relations = ZenPackable._relations + (
        ("datasource", ToOne(ToManyCont,"Products.ZenModel.RRDDataSource","datapoints")),
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataPoint',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Point'
            , 'action'        : 'editRRDDataPoint'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDDataPoint, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -3)



    security.declareProtected('View', 'getPrimaryUrlPath')
    def getPrimaryUrlPath(self):
        """get the physicalpath as a url"""
        return self.absolute_url_path()

    def name(self):
        """Include the data source name in our name,
        useful for lists of DataPoints"""
        return '%s%c%s' % (self.datasource().id, SEPARATOR, self.id)

    security.declareProtected('Manage DMD', 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        """Edit a ZenModel object and return its proper page template
        """
        if REQUEST:
            msgs = []
            for optional in 'rrdmin', 'rrdmax':
                v = REQUEST.form.get(optional, None)
                if v:
                    try:
                        REQUEST.form[optional] = long(v)
                    except ValueError:
                        msgs.append('Unable to convert "%s" to a number' % v)
            msgs = ', '.join(msgs)
            if msgs:
                REQUEST['message'] = msgs[0].capitalize() + msgs[1:] + ", at Time:"
                return self.callZenScreen(REQUEST, False)
        
        return ZenModelRM.zmanage_editProperties(self, REQUEST)

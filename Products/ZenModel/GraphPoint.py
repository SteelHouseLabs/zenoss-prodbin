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

__doc__="""GraphPoint

Defines attributes for how a data source will be graphed
and builds the nessesary rrd commands.
"""

import os

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

                                     
def manage_addGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    if REQUEST:
        REQUEST['message'] = 'That operation is not supported.'
        self.callZenScreen(REQUEST)


class GraphPoint(ZenModelRM, ZenPackable):
    '''
    '''
    
    isThreshold = False

    DEFAULT_FORMAT = '%5.2lf%s'

    sequence = 0
    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("graphDef", ToOne(ToManyCont,"Products.ZenModel.GraphDefinition","graphPoints")),
        )
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'editGraphPoint',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Graph Point'
                , 'action'        : 'editGraphPoint'
                , 'permissions'   : ( Permissions.view, )
                },
            )
        },
    )

    colors = (
        '#00cc00', '#0000ff', '#00ffff', '#ff0000', 
        '#ffff00', '#cc0000', '#0000cc', '#0080c0',
        '#8080c0', '#ff0080', '#800080', '#0000a0',
        '#408080', '#808000', '#000000', '#00ff00',
        '#fb31fb', '#0080ff', '#ff8000', '#800000', 
        )

    ## Interface


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        if self.graphDef.rrdTemplate():
            from RRDTemplate import crumbspath
            crumbs = super(GraphPoint, self).breadCrumbs(terminator)
            return crumbspath(self.graphDef(), crumbs, -3)
        return ZenModelRM.breadCrumbs(self, terminator)
        
        
    def manage_editProperties(self, REQUEST):
        '''
        '''
        if REQUEST.get('color', ''):
            REQUEST.color = '#%s' % REQUEST.color.lstrip('#')
        return self.zmanage_editProperties(REQUEST)


    def getDescription(self):
        ''' Return a description
        '''
        return self.id


    def getTalesContext(self):
        ''' Standard stuff to add to context for tales expressions
        '''
        d = self.graphDef.getTalesContext()
        d['graphPoint'] = self
        return d


    ## Graphing Support
    
    def getColor(self, index):
        color = self.color or self.colors[index]
        color = '#%s' % color.lstrip('#')
        return color


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, multiid=-1):
        ''' Build the graphing commands for this graphpoint
        '''
        return cmds
        

    def getDsName(self, base, multiid=-1):
        if multiid > -1:
            return '%s_%s' % (base, multiid)
        return base

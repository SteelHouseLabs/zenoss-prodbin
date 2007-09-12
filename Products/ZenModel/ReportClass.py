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

__doc__="""ReportClass

ReportClass groups different types of reports together

$Id: ReportClass.py,v 1.3 2004/04/22 15:33:44 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Organizer import Organizer
from Report import Report
from ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *

def manage_addReportClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ReportClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addReportClass = DTMLFile('dtml/addReportClass',globals())

class ReportClass(Organizer, ZenPackable):
    dmdRootName = "Reports"
    portal_type = meta_type = "ReportClass"

    sub_meta_types = ("ReportClass", "Report", 'DeviceReport', 'GraphReport',
                        'FancyReport')

    _relations = Organizer._relations + ZenPackable._relations + (
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'reportClass')),
        )

    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewReportClass',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'Status'
                , 'action'        : 'viewReportClass'
                , 'permissions'   : ( "View",)
                , 'visible'       : 1
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    def manage_addReportClass(self, id, title = None, REQUEST = None):
        """make a device class"""
        dc = ReportClass(id, title)
        self._setObject(id, dc)
        if REQUEST:
            REQUEST['message'] = "Report organizer created"
            return self.callZenScreen(REQUEST)


    def reports(self):
        """Return list of report instances.
        """
        return [ r for r in self.objectValues(
                 spec=('Report','DeviceReport','GraphReport','FancyReport')) ]

        
    def countReports(self):
        """Return a count of all our contained children."""
        count = len(self.reports())
        for child in self.children():
            count += child.countReports()
        return count
        

    security.declareProtected('Manage DMD', 'manage_addDeviceReport')
    def manage_addDeviceReport(self, id, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            from Products.ZenModel.DeviceReport import DeviceReport
            dr = DeviceReport(id)
            self._setObject(id, dr)
        if REQUEST:
            REQUEST['message'] = "Device report created"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add an graph report to this object.
        """
        if id:
            from Products.ZenModel.GraphReport import GraphReport
            gr = GraphReport(id)
            self._setObject(id, gr)
        if REQUEST:
            REQUEST['message'] = "Graph report created"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_addFancyReport')
    def manage_addFancyReport(self, id, REQUEST=None):
        """Add an fancy report to this object.
        """
        from Products.ZenModel.FancyReport import FancyReport
        fr = FancyReport(id)
        self._setObject(id, fr)
        if REQUEST:
            url = '%s/%s' % (self.getPrimaryUrlPath(), id)
            REQUEST['RESPONSE'].redirect(url)
        return fr

    
    def moveReports(self, moveTarget, ids=None, REQUEST=None):
        """Move a report from here organizer to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) in types.StringTypes: ids = (ids,)
        target = self.getOrganizer(moveTarget)
        for rptname in ids:
            rpt = self._getOb(rptname)
            rpt._operation = 1 # moving object state
            self._delObject(rptname)
            target._setObject(rptname, rpt)
        if REQUEST:
            REQUEST['message'] = "Device reports moved"
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
    

    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        from Acquisition import aq_base
        for o in self.reports():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)
     
    ### Graph Definitions
         
    security.declareProtected('Manage DMD', 'getGraphDefs')
    def getGraphDefs(self):
        ''' Return an ordered list of the graph definitions
        '''
        def cmpGraphDefs(a, b):
            try: a = int(a.sequence)
            except ValueError: a = sys.maxint
            try: b = int(b.sequence)
            except ValueError: b = sys.maxint
            return cmp(a, b)
        graphDefs =  self.graphDefs()[:]
        graphDefs.sort(cmpGraphDefs)
        return graphDefs


    security.declareProtected('Manage DMD', 'manage_addGraphDefinition')
    def manage_addGraphDefinition(self, new_id, REQUEST=None):
        """Add a GraphDefinition 
        """
        from GraphDefinition import GraphDefinition
        graph = GraphDefinition(new_id)
        self.graphDefs._setObject(graph.id, graph)
        if REQUEST:
            url = '%s/graphDefs/%s' % (self.getPrimaryUrlPath(), graph.id)
            REQUEST['RESPONSE'].redirect(url)
        return graph
        

    security.declareProtected('Manage DMD', 'manage_deleteGraphDefinitions')
    def manage_deleteGraphDefinitions(self, ids=(), REQUEST=None):
        """Remove GraphDefinitions 
        """
        for id in ids:
            self.graphDefs._delObject(id)
            self.manage_resequenceGraphDefs()
        if REQUEST:
            if len(ids) == 1:
                REQUEST['message'] = 'Graph %s deleted.' % ids[0]
            elif len(ids) > 1:
                REQUEST['message'] = 'Graphs %s deleted.' % ', '.join(ids)
            return self.callZenScreen(REQUEST)


InitializeClass(ReportClass)

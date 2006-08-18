#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.

$Id: RRDDataSource.py,v 1.6 2003/06/03 18:47:49 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import os

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Acquisition import aq_parent

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


def manage_addRRDDataSource(context, id, REQUEST = None):
    """make a RRDDataSource"""
    ds = RRDDataSource(id)
    context._setObject(ds.id, ds)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDDataSource = DTMLFile('dtml/addRRDDataSource',globals())


class RRDDataSourceError(Exception): pass

class RRDDataSource(ZenModelRM):

    meta_type = 'RRDDataSource'
  
    rrdtypes = ('', 'COUNTER', 'GAUGE', 'DERIVE')
    linetypes = ('', 'AREA', 'LINE')
    sourcetypes = ('SNMP', 'XMLRPC')
    
    sourcetype = 'SNMP'
    oid = ''
    xmlrpcURL = ''
    xmlrpcMethodName = ''
    createCmd = ""
    rrdtype = 'COUNTER'
    isrow = True
    rpn = ""
    rrdmax = -1
    color = ""
    linetype = ''
    limit = -1
    format = '%0.2lf%s'

    _properties = (
        {'id':'sourcetype', 'type':'selection',
        'select_variable' : 'sourcetypes', 'mode':'w'},
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcURL', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcMethodName', 'type':'string', 'mode':'w'},
        {'id':'rrdtype', 'type':'selection',
        'select_variable' : 'rrdtypes', 'mode':'w'},
        {'id':'createCmd', 'type':'text', 'mode':'w'},
        {'id':'isrow', 'type':'boolean', 'mode':'w'},
        {'id':'rpn', 'type':'string', 'mode':'w'},
        {'id':'rrdmax', 'type':'long', 'mode':'w'},
        {'id':'limit', 'type':'long', 'mode':'w'},
        {'id':'linetype', 'type':'selection', 
        'select_variable' : 'linetypes', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        )


    _relations = (
        ("rrdTemplate", ToOne(ToManyCont,"RRDTemplate","datasources")),
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'RRD Data Source'
            , 'action'        : 'editRRDDataSource'
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
        crumbs = super(RRDDataSource, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def graphOpts(self, file, defaultcolor, defaulttype, summary, multiid=-1):
        """build graph options for this datasource"""
        
        graph = []
        src = "ds%d" % self.getIndex()
        dest = src
        if multiid != -1: dest += str(multiid)
        file = os.path.join(file, self.getId()) + ".rrd"
        graph.append("DEF:%s=%s:%s:AVERAGE" % (dest, file, 'ds0'))
        src = dest

        if self.rpn: 
            dest = "rpn%d" % self.getIndex()
            if multiid != -1: dest += str(multiid)
            graph.append("CDEF:%s=%s,%s" % (dest, src, self.rpn))
            src = dest

        if self.limit > 0:
            dest = "limit%d" % self.getIndex()
            if multiid != -1: dest += str(multiid)
            graph.append("CDEF:%s=%s,%s,GT,UNKN,%s,IF"%
                        (dest,src,self.limit,src))
            src = dest

        if not self.color: src += defaultcolor
        else: src += self.color
        
        if not self.linetype: type = defaulttype
        else: type = self.linetype

        if multiid != -1:
            fname = os.path.basename(file)
            if fname.find('.rrd') > -1: fname = fname[:-4]
            name = "%s-%s" % (self.getId(), fname)
        else: name = self.getId()

        graph.append(":".join((type, src, name,)))

        if summary:
            src,color=src.split('#')
            graph.extend(self._summary(src, self.format, ongraph=1))
        return graph

   
    def summary(self, file, format="%0.2lf%s"):
        """return only arguments to generate summary"""
        if self.getIndex() == -1: 
            raise "DataSourceError", "Not part of a TargetType"
        graph = []
        src = "ds%d" % self.getIndex()
        dest = src
        graph.append("DEF:%s=%s:%s:AVERAGE" % (dest, file, src))
        src = dest

        if self.rpn: 
            dest = "rpn%d" % self.getIndex()
            graph.append("CDEF:%s=%s,%s" % (dest, src, self.rpn))
            src = dest

        graph.extend(self._summary(src, self.format, ongraph=1))
        return graph

    
    def _summary(self, src, format="%0.2lf%s", ongraph=1):
        """Add the standard summary opts to a graph"""
        gopts = []
        funcs = ("LAST", "AVERAGE", "MAX")
        tags = ("cur\:", "avg\:", "max\:")
        for i in range(len(funcs)):
            label = "%s%s" % (tags[i], format)
            gopts.append(self.summElement(src, funcs[i], label, ongraph))
        gopts[-1] += "\j"
        return gopts

    
    def summElement(self, src, function, format="%0.2lf%s", ongraph=1):
        """Make a single summary element"""
        if ongraph: opt = "GPRINT"
        else: opt = "PRINT"
        return ":".join((opt, src, function, format))
        

    def setIndex(self, index):
        self._v_index = index


    def getIndex(self):
        if not hasattr(self, '_v_index'):
            self._v_index = -1
        return self._v_index


    def getOidOrUrl(self):
        if self.sourcetype == "SNMP":
            return self.oid
        if self.sourcetype == "XMLRPC":
            return self.xmlrpcURL+" ("+self.xmlrpcMethodName+")"
        return None

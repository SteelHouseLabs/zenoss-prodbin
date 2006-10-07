#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

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


# addRRDDataPoint = DTMLFile('dtml/addRRDDataPoint',globals())

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

class RRDDataPoint(ZenModelRM):

    meta_type = 'RRDDataPoint'
  
    rrdtypes = ('', 'COUNTER', 'GAUGE', 'DERIVE')
    linetypes = ('', 'AREA', 'LINE')
    
    createCmd = ""
    rrdtype = 'GAUGE'
    isrow = True
    rpn = ""
    rrdmax = -1
    color = ""
    linetype = ''
    limit = -1
    format = '%0.2lf%s'

    _properties = (
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
        ("datasource", ToOne(ToManyCont,"RRDDataSource","datapoints")),
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
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def graphOpts(self, file, defaultcolor, defaulttype, summary, multiid=-1):
        """build graph options for this datasource"""
        graph = []
        src = "ds%d" % self.getIndex()
        dest = src
        if multiid != -1: dest += str(multiid)
        file = os.path.join(file, self.name()) + ".rrd"
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
            name = "%s-%s" % (self.id, fname)
        else: name = self.id

        graph.append(":".join((type, src, name,)))

        if summary:
            src,color=src.split('#')
            graph.extend(self._summary(src, self.format, ongraph=1))
        return graph

   
    def summary(self, file, format="%0.2lf%s"):
        """return only arguments to generate summary"""
        if self.getIndex() == -1: 
            raise "DataPointError", "Not part of a TargetType"
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

    security.declareProtected('View', 'getPrimaryUrlPath')
    def getPrimaryUrlPath(self):
        """get the physicalpath as a url"""
        return self.absolute_url_path()

    def name(self):
        """Include the data source name in our name,
        useful for lists of DataPoints"""
        return '%s%c%s' % (self.datasource().id, SEPARATOR, self.id)

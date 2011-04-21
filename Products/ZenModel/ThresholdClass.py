###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from AccessControl import ClassSecurityInfo

import Globals
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *

class BadInstance(Exception): pass

class ThresholdClass(ZenModelRM, ZenPackable):
    """A ThresholdClass is a threshold description stored in a
    Template.  The ThresholdClass will create ThresholdInstance
    objects when provided with a context, such as a device.  Lists of
    ThresholdInstances will be sent to collectors for evaluation.
    """

    meta_type = 'ThresholdClass'
    security = ClassSecurityInfo()
    dsnames = []
    enabled = True

    def __init__(self, id, buildRelations=True):
        self.id = id
        if buildRelations:
            self.buildRelations()

    _properties = (
        {'id':'dsnames', 'type':'lines', 'mode':'w', 'label': 'DataPoints'},
        {'id':'enabled', 'type':'boolean', 'mode':'w', 'label': 'Enabled'},
        )

    _relations =  ZenPackable._relations + (
        ("rrdTemplate", ToOne(ToManyCont,"Products.ZenModel.RRDTemplate", "thresholds")),
        )

    def getTypeName(self):
        return self.__class__.__name__


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(ThresholdClass, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def createThresholdInstance(self, context):
        """Return a sub-class of ThresholdInstance.  May raise a
        BadInstance exception if the type of the context does not
        match this type of threshold.
        """

        
    def canGraph(self, graph):
        """Returns true if instances of this ThresholdClass can be
        placed on a users' graph"""
        return True


    def sync(self, eventManager, instances):
        "update instances with state from the event manager"


    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


    def getDataPointNamesString(self):
        """
        Return a string that lists the datapoints used in this threshold.
        Indicate missing datapoints with (missing) after the name.
        """
        names = []
        availableDPNames = self.rrdTemplate.getRRDDataPointNames()
        for dsName in self.dsnames:
            if dsName in availableDPNames:
                names.append(dsName)
            else:
                names.append('%s(<span style="color: red">missing</span>)' % dsName)
        return ','.join(names)

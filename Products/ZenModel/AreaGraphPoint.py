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

__doc__="""AreaGraphPoint

Handles GraphPoints that define an rrd AREA
"""

from GraphPoint import GraphPoint
from Globals import InitializeClass

from Products.ZenUtils.Utils import unused

def manage_addAreaGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = AreaGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class AreaGraphPoint(GraphPoint):

    meta_type = 'AreaGraphPoint'

    value = ''
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND
    stacked = False

    _properties = GraphPoint._properties + (
        {'id':'value', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        )


    def getDescription(self):
        return '%s %s' % (self.value, self.legend)


    def getType(self):
        return 'AREA'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        unused(multiid, rrdDir)
        gopts = 'AREA:%s%s' % (
            self.addPrefix(prefix, self.value), self.getColor(idx))

        if self.legend or self.stacked:
            legend = self.talesEval(self.legend, context)
            legend = self.escapeForRRD(legend)
            gopts += ':%s' % legend
        if self.stacked:
            gopts += ':STACK'
        return cmds + [gopts]


InitializeClass(AreaGraphPoint)

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

__doc__="""ShiftGraphPoint

Handles GraphPoints that define an rrd SHIFT
"""

from GraphPoint import GraphPoint
from Globals import InitializeClass
from Products.ZenUtils.deprecated import deprecated


@deprecated
def manage_addShiftGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = ShiftGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class ShiftGraphPoint(GraphPoint):

    meta_type = 'ShiftGraphPoint'
    rrdFile = None
    vname = ''
    offset = 0

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'offset', 'type':'long', 'mode':'w'},
        )

    def getDescription(self):
        return '%s' % self.offset


    def getType(self):
        return 'SHIFT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        if not (self.rrdFile and self.dsName and self.cFunc):
            return cmds
        
        offset = self.talesEval(self.offset, context)

        return cmds + ['SHIFT:%s:%s' % (
                            self.addPrefix(prefix, self.vname), offset or 0)]


InitializeClass(ShiftGraphPoint)

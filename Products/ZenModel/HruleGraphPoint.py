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

__doc__=""" 

Handles GraphPoints that define an rrd Line
"""

import os
from GraphPoint import GraphPoint


def manage_addHruleGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    if REQUEST:
        REQUEST['message'] = 'That operation is not supported.'
        context.callZenScreen(REQUEST)


class HruleGraphPoint(GraphPoint):

    meta_type = 'HruleGraphPoint'

    value = ''
    color = ''
    legend = ''

    _properties = GraphPoint._properties + (
        {'id':'value', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    

    def getDescription(self):
        return '%s %s' % (self.value, self.color)


    def getType(self):
        return 'HRULE'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        legend = self.addPrefix(prefix, self.legend)
        return cmds + ['HRULE:%s%s%s' % (
                    self.value or 0,
                    self.getColor(idx),
                    legend and ':%s' % legend or '')]

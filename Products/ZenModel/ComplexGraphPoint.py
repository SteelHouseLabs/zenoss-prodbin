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

__doc__="""ComplexGraphPoint
"""

from GraphPoint import GraphPoint                                     
from Globals import InitializeClass


class ComplexGraphPoint(GraphPoint):

    LINETYPE_DONTDRAW = 'DONTDRAW'
    LINETYPE_LINE = 'LINE'
    LINETYPE_AREA = 'AREA'

    lineTypeOptions = (
        ('Not Drawn', LINETYPE_DONTDRAW),
        ('Line', LINETYPE_LINE),
        ('Area', LINETYPE_AREA),
        )

    color = ''
    lineType = LINETYPE_LINE
    lineWidth = 1
    stacked = False
    format = GraphPoint.DEFAULT_FORMAT
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'lineType', 'type':'selection', 
        'select_variable' : 'lineTypes', 'mode':'w'},
        {'id':'lineWidth', 'type':'long', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )


InitializeClass(ComplexGraphPoint)

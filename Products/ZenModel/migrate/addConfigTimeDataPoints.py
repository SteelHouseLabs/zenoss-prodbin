###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Add data points for configTime to zeneventlog and zenwin's data sources and the
Config Time graph.

'''
import Migrate
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint


class AddConfigTimeDataPoints(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        # get the PerformanceConf template
        template = dmd.Monitors.rrdTemplates._getOb('PerformanceConf', None)
        if not template:
            # No collector performance template exists.
            return

        # add configTime to the zeneventlog and zenwin data sources
        dpNames = []
        for ds in template.datasources():
            if ds.id not in ('zeneventlog', 'zenwin'):
                continue

            # don't try and add configTime if it already exists
            if 'configTime' in ds.datapoints.objectIds():
                continue

            newDp = ds.manage_addRRDDataPoint('configTime')
            newDp.rrdtype = 'GAUGE'
            newDp.rrdmin = 0

            dpNames.append("%s_configTime" % ds.id)

        # add the new datapoints to the config time graph
        graph = template.graphDefs._getOb("Config Time")
        if not graph:
            # No Graph Definition in the template
            return

        graph.manage_addDataPointGraphPoints(dpNames)

        # Fix up all of the graph points we just added.
        for gp in graph.graphPoints():
            if isinstance(gp, DataPointGraphPoint):
                collectorName = gp.dpName.split('_', 1)[0]
                gp.legend = collectorName

AddConfigTimeDataPoints()


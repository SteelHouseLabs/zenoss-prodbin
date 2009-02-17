###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate

def attachCpuAliases( dmd, aliasMap ):
    for template in [ t.getObject() for t in dmd.searchRRDTemplates()]:
        for ds in template.datasources():
            for dp in ds.datapoints():
                if aliasMap.has_key( dp.id ):
                    if not dp.hasAlias( aliasMap[dp.id][0] ):
                        dp.addAlias( *aliasMap[dp.id] )

class addCpuDataPointAliases(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        attachCpuAliases( dmd, 
          {'cpu5min' : ('cpu__pct',),
           'ssCpuRawIdle' : ('cpu__pct', "__EVAL:str(len(here.hw.cpus())) " + \
                                         "+ ',/,100,EXC,-,0,MAX'"),
           'laLoadInt5' : ('loadAverage5min', '100,/'),
           'cpuPercentProcessorTime' : ('cpu__pct',) }
           )

            
addCpuDataPointAliases()
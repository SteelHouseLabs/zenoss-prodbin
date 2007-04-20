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

TARGET=0
GATEWAY=1
NETMASK=2
FLAGS=3
INTERFACE=7

from CollectorPlugin import CommandPlugin

class netstat_rn(CommandPlugin):
    
    maptype = "RouteMap" 
    command = 'netstat -rn'
    compname = "os"
    relname = "routes"
    modname = "Products.ZenModel.IpRouteEntry"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting routes for device %s' % device.id)
        indirectOnly = getattr(device, 'zRouteMapCollectOnlyIndirect', False)
        rm = self.relMap()
        rlines = results.split("\n")
        for line in rlines:
            aline = line.split()
            if len(aline) != 8 or not self.isip(aline[0]): continue
            route = self.objectMap()

            route.routemask = self.maskToBits(aline[NETMASK])
            if route.routemask == 32: continue

            if "G" in aline[FLAGS]:
                route.routetype = 'indirect'
            else:
                route.routetype = 'direct'
            if indirectOnly and route.routetype != 'indirect':
                continue

            route.id = aline[TARGET]
            route.setTarget = route.id + "/" + str(route.routemask)
            route.id = route.id + "_" + str(route.routemask)
            route.setInterfaceName = aline[INTERFACE]
            route.setNextHopIp = aline[GATEWAY]
            rm.append(route)
        return rm

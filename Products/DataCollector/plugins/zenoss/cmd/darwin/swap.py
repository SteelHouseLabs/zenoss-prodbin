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

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap

MULTIPLIERS = {
    'M' : 1024 * 1024,
    'K' : 1024,
    'B' : 1
    }

class swap(CommandPlugin):
    """
    reads from sysctl and puts the swap total into the swap field
    """
    maptype = "FileSystemMap" 
    command = '/usr/sbin/sysctl vm.swapusage'
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting swap for device %s' % device.id)

        rm = self.relMap()
        maps = []

        results = results.split()
        total = results[3]
        multiplier = MULTIPLIERS[total[-1]]

        total = float(total[:-1]) * multiplier
        maps.append(ObjectMap({"totalSwap": total}, compname="os"))
                
        return maps

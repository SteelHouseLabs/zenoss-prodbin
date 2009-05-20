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

import Globals
import re
from Products.ZenReports import Utils, Utilization
from Products.ZenReports.AliasPlugin import AliasPlugin, RRDColumn, Column, TalesColumnHandler

class interface( AliasPlugin ):
    "The interface usage report"

    def getComponentPath(self):
        return 'os/interfaces'
    
    def _getComponents(self, device, componentPath):
        components=[]
        isLocal = re.compile(device.zLocalInterfaceNames)
        for i in device.os.interfaces():
            if isLocal.match(i.name()): continue
            if not i.monitored(): continue
            if i.snmpIgnore(): continue
            if not i.speed: continue
            components.append(i)
        return components
    
    def getColumns(self):
        return [
                Column('speed', TalesColumnHandler('component.speed')),
                RRDColumn('input', 'inputOctets__bytes'),
                RRDColumn('output', 'outputOctets__bytes'),
                ]
    
    def getCompositeColumns(self):
        return [
                Column('total',TalesColumnHandler('input+output')),
                Column('percentUsed',TalesColumnHandler('(long(total)*8)/speed'))
                ]

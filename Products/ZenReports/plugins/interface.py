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

import re

import Globals
from Products.ZenReports.AliasPlugin import \
        AliasPlugin, Column, PythonColumnHandler, RRDColumnHandler


class interface(AliasPlugin):
    "The interface usage report"

    def getComponentPath(self):
        return 'os/interfaces'

    def _getComponents(self, device, componentPath):
        components = []
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
                Column(
                    'deviceName', PythonColumnHandler('device.titleOrId()')
                ),
                Column('interface', PythonColumnHandler('component.name()')),
                Column('speed', PythonColumnHandler('component.speed')),
                Column('input', RRDColumnHandler('inputOctets__bytes')),
                Column('output', RRDColumnHandler('outputOctets__bytes')),
            ]

    def getCompositeColumns(self):
        return [
                Column('inputBits', PythonColumnHandler('input * 8')),
                Column('outputBits', PythonColumnHandler('output * 8')),
                Column('total', PythonColumnHandler('input + output')),
                Column(
                    'totalBits', PythonColumnHandler('(input + output) * 8')
                ),
                Column(
                    'percentUsed',
                    PythonColumnHandler(
                        # total == total is False if total is NaN
                        '((long(total) if total == total else total) * 8) '
                        '* 100.0 / speed'
                   )
               )
            ]

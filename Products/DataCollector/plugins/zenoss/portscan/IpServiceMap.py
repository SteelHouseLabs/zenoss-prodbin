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

__doc__ = """IpServiceMap

IpServiceMap maps the interface and ip tables to interface objects

"""

from Products.DataCollector.plugins.CollectorPlugin import CollectorPlugin

class IpServiceMap(CollectorPlugin):

    transport = "portscan"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = CollectorPlugin.deviceProperties + (
        'zIpServiceMapMaxPort',
        )

    def condition(self, device, log):
        """
        Default condition for portscan is True.
        """
        return True

    def preprocess(self, results, log):
        """
        Make sure the ports are integers.
        """
        addr = results.keys()[0]
        ports = [ int(port) for port in results[addr] ]
        return (addr, ports)

    def process(self, device, results, log):
        """
        Collect open port information from this device.
        """
        log.info('processing Ip Services for device %s' % device.id)
        addr, ports = results
        rm = self.relMap()
        for port in ports:
            om = self.objectMap()
            om.id = 'tcp_%05d' % port
            om.ipaddresses = [addr]
            om.protocol = 'tcp'
            om.port = port
            om.setServiceClass = {'protocol': 'tcp', 'port':port}
            om.discoveryAgent = self.name()
            rm.append(om)
        return rm


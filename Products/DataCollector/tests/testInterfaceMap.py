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

import logging

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.plugins.zenoss.snmp.InterfaceMap import InterfaceMap

log = logging.getLogger("zen.testcases")

class FakeDevice:
    def __init__(self, id):
        self.id = id

def dumpRelMap(relmap):
    """
    Display the contents returned from a modeler
    """
    for om in relmap:
        dumpObjectMapData(om)

def dumpObjectMapData(om):
    """
    I'm sure that 'Om' is not a reference to Terry Pratchet and
    the god of the same name.  Really.
    Anyway, this is a chance to view the mind of a small god.... :)
    """
    for attr in dir(om):
        obj = getattr(om, attr)
        if not attr.startswith('_') and not hasattr(obj, "__call__"):
            print "%s = %s" % (attr, obj)



class TestInterfaceMap(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)

        self.imap = InterfaceMap()
        self.device = FakeDevice('testdevice')


    def testGoodResults(self):
        tabledata = {
           'ifalias': {'1': {'highSpeed': 0, 'description': ''}, '3': {'highSpeed': 0, 'description': ''}, '5': {'highSpeed': 0, 'description': ''}},
           'iftable': {'1': {'adminStatus': 1, 'macaddress': '', 'operStatus': 1, 'speed': 10000000, 'mtu': 16436, 'ifindex': 1, 'type': 24, 'id': 'lo'},
                       '3': {'adminStatus': 2, 'macaddress': '', 'operStatus': 2, 'speed': 0, 'mtu': 1480, 'ifindex': 3, 'type': 131, 'id': 'sit0'},
                       '5': {'adminStatus': 1, 'macaddress': '\x00\x0c\x8d\xfd\x22\xd3', 'operStatus': 1, 'speed': 10000000, 'mtu': 1500, 'ifindex': 5, 'type': 6, 'id': 'eth0'}},
           'ipAddrTable': {'10.175.211.118': {'ifindex': 5, 'netmask': '255.255.255.0', 'ipAddress': '10.175.211.118'}, '127.0.0.1': {'ifindex': 1, 'netmask': '255.0.0.0', 'ipAddress': '127.0.0.1'}},
           'ipNetToMediaTable': {
               '5.10.175.211.117': {'ifindex': 5, 'ipaddress': '10.175.211.117', 'iptype': 3},
               '5.10.175.211.116': {'ifindex': 5, 'ipaddress': '10.175.211.116', 'iptype': 3},
               '5.10.175.211.115': {'ifindex': 5, 'ipaddress': '10.175.211.115', 'iptype': 3},
               '5.10.175.211.121': {'ifindex': 5, 'ipaddress': '10.175.211.121', 'iptype': 3},
               '5.10.175.211.179': {'ifindex': 5, 'ipaddress': '10.175.211.179', 'iptype': 3},
               '5.10.175.211.34': {'ifindex': 5, 'ipaddress': '10.175.211.34', 'iptype': 3},
               '5.10.175.211.1': {'ifindex': 5, 'ipaddress': '10.175.211.1', 'iptype': 3},
               '5.10.175.211.10': {'ifindex': 5, 'ipaddress': '10.175.211.10', 'iptype': 3}}
        }

        results = ('ignored', tabledata)
        relmap = InterfaceMap().process(self.device, results, log)
        parsed_data = {
              5: { 
                   'id':'eth0',
                   'macaddress':'00:0C:8D:FD:22:D3',
                   'speed':10000000,
                   'mtu':1500,
                   'interfaceName':'eth0',
                   'type':'ethernetCsmacd',
                   'setIpAddresses':['10.175.211.118/24'],
              },

              1: {
                   'id':'lo', 
                   'speed':10000000,
                   'mtu':16436,
                   'interfaceName':'lo',
                   'type':'softwareLoopback',
              }, 

              3: { 
                   'id':'sit0',
                   'speed':0,
                   'mtu':1480,
                   'interfaceName':'sit0',
                   'type':'Encapsulation Interface',
              },

        }

        for om in relmap:
            index = om.ifindex
            for attr in parsed_data[index].keys():
                self.assertEquals( getattr(om, attr), parsed_data[index][attr] )



    def testNon24Netmask(self):
        tabledata = {
           'ifalias': {'1': {'highSpeed': 0, 'description': ''}, '3': {'highSpeed': 0, 'description': ''}, '2': {'highSpeed': 0, 'description': ''}},
           'iftable': {'1': {'adminStatus': 1, 'macaddress': '', 'operStatus': 1, 'speed': 10000000, 'mtu': 16436, 'ifindex': 1, 'type': 24, 'id': 'lo'},
                       '3': {'adminStatus': 2, 'macaddress': '', 'operStatus': 2, 'speed': 0, 'mtu': 1480, 'ifindex': 3, 'type': 131, 'id': 'sit0'},
                       '2': {'adminStatus': 1, 'macaddress': '\x00\x0c\x8d\xfd\x22\xd3', 'operStatus': 1, 'speed': 10000000, 'mtu': 1500, 'ifindex': 2, 'type': 6, 'id': 'eth0'}},
           'ipAddrTable': {'10.1.254.8': {'ifindex': 2, 'netmask': '255.255.128.0', 'ipAddress': '10.1.254.8'}, '127.0.0.1': {'ifindex': 1, 'netmask': '255.0.0.0', 'ipAddress': '127.0.0.1'}},
           'ipNetToMediaTable': {
               '2.10.1.254.107': {'ifindex': 2, 'ipaddress': '10.1.254.107', 'iptype': 3},
               '2.10.1.254.254': {'ifindex': 2, 'ipaddress': '10.1.254.254', 'iptype': 3},
               '2.10.1.252.54': {'ifindex': 2, 'ipaddress': '10.1.252.54', 'iptype': 3},
               '2.10.1.246.11': {'ifindex': 2, 'ipaddress': '10.1.246.11', 'iptype': 3},
               '2.10.1.254.61': {'ifindex': 2, 'ipaddress': '10.1.254.61', 'iptype': 3},
               '2.10.1.254.170': {'ifindex': 2, 'ipaddress': '10.1.254.170', 'iptype': 3}}
        }

        results = ('ignored', tabledata)
        relmap = InterfaceMap().process(self.device, results, log)

        parsed_data = {
              2: {
                   'id':'eth0',
                   'macaddress':'00:0C:8D:FD:22:D3',
                   'speed':10000000,
                   'mtu':1500,
                   'interfaceName':'eth0',
                   'type':'ethernetCsmacd',              },
                   'setIpAddresses':['10.1.254.8/17'],
              1: { 
                   'id':'lo',
                   'speed':10000000,
                   'mtu':16436,
                   'interfaceName':'lo',
                   'setIpAddresses':['127.0.0.1/8'],

                   'type':'softwareLoopback',              },
              3: { 
                   'id':'sit0',
                   'speed':0,
                   'mtu':1480,
                   'interfaceName':'sit0',
                   'type':'Encapsulation Interface',              },
        }

        for om in relmap:
            index = om.ifindex
            for attr in parsed_data[index].keys():
                self.assertEquals( getattr(om, attr), parsed_data[index][attr] )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestInterfaceMap))
    return suite


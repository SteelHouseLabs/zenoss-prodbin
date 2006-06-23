#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenModel.IpInterface import IpInterface
from Products.ZenUtils.ZeoConn import ZeoConn

zeoconn = ZeoConn()

class TestIpAddress(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpIface = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpIface)
        self.iface = self.dev.getDeviceComponents()[0]
        tmpAddr = IpAddress('1.2.3.4')
        self.iface.ipaddresses._setObject('1.2.3.4',tmpAddr)
        self.addr = self.iface.getIpAddressObj()


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testGetIp(self):
        self.assert_(self.addr.getIp() == '1.2.3.4')
        self.assert_(self.addr.getIpAddress() == '1.2.3.4/24')


    def testGets(self):#most/all of the get method tests
       #self.assert_(self.addr.getInterfaceName() == self.addr.interface.interface().name)
        self.assert_(self.addr.getDeviceUrl() == '/zport/dmd/Devices/devices/testdev')
        self.assert_(self.addr.device() == self.dev)
    

def main():

       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()

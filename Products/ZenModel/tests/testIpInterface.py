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
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import logging

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpInterface import IpInterface

from ZenModelBaseTest import ZenModelBaseTest

log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None

class TestIpInterface(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        tmpo = IpInterface('test')
        self.dev = self.dmd.Devices.createInstance('testdev')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[0]
        self.iface.interfaceName = 'test'
        self.iface.macaddress = '00:00:00:00:00:00'


    def testAddIpAddress(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#2 birds...
        self.assert_(self.iface.getIp() == '1.2.3.4')#and 3
        
        self.iface.addIpAddress('2.3.4.5')
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#it's primary
        self.assert_(self.iface.getIp() == '1.2.3.4')#ditto
        
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' not in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '2.3.4.5/24')#primary changed
        self.assert_(self.iface.getIp() == '2.3.4.5')#ditto

    def testGetInterfaceMacaddress(self):
        self.assert_(self.iface.getInterfaceMacaddress() == '00:00:00:00:00:00')
        

    def testViewName(self):
        self.assert_(self.iface.viewName() == 'test')
        self.assert_(self.iface.getInterfaceName() == 'test')


    def testGetIpAddressObjs(self):
        from Products.ZenModel.IpAddress import IpAddress
        add = IpAddress('1.2.3.4')
        self.iface.ipaddresses._setObject('1.2.3.4',add)
        self.assert_(self.iface.getIpAddressObj().getIp() == add.getIp())
        self.assert_(add in self.iface.getIpAddressObjs())
        add2 = IpAddress('2.3.4.5')
        self.iface.ipaddresses._setObject('2.3.4.5',add2)
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj().getIp() == add.getIp())
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(add not in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj().getIp() == add2.getIp())


    def testAddIpaddress(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        

    def testAddLocalIpAddresses(self):
        self.iface.addLocalIpAddress('127.0.0.2')
        self.assert_(self.dmd.Networks.findIp('127.0.0.2') is None)
        self.assert_('127.0.0.2/24' in self.iface._ipAddresses)

    def testGetNetworkName(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_(self.iface.getNetworkName() == '1.2.3.0/24')
        

    def testSetIpAddresses(self):
        self.iface.setIpAddresses('1.2.3.4/24')
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')
        
    def testSetIpAddresses2(self):
        self.iface.setIpAddresses(['1.2.3.4/24', '2.3.4.5/24'])
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        self.assert_(self.dmd.Networks.findIp('2.3.4.5'))
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')
        
        self.iface.setIpAddresses(['2.3.4.5/24', '3.4.5.6/24'])
        self.assert_('1.2.3.4/24' not in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_('3.4.5.6/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '2.3.4.5/24')
        
        self.iface.setIpAddresses(['4.5.6.7/24'])
        self.assert_('2.3.4.5/24' not in self.iface.getIpAddresses())
        self.assert_('3.4.5.6/24' not in self.iface.getIpAddresses())
        self.assert_('4.5.6.7/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '4.5.6.7/24')

        self.iface.setIpAddresses([])
        self.assert_(self.iface.getIpAddresses() == [])
        self.assert_(self.iface.getIpAddress() == None)

        self.iface.setIpAddresses('127.0.0.1/8')
        self.assert_(self.iface.getIpAddress() == '127.0.0.1/8')
        self.assert_('127.0.0.1/8' in self.iface.getIpAddressObjs())


    def testGetParentInfo(self):
        self.assert_(self.iface.getParentDeviceName()==self.dev.getDeviceName())
        self.assert_(self.iface.getParentDeviceUrl() == self.dev.absolute_url())


    def testClearIps(self):
        self.iface.clearIps(None)
        self.assert_(not self.iface.getIpAddresses())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpInterface))
    return suite

if __name__=="__main__":
    framework()

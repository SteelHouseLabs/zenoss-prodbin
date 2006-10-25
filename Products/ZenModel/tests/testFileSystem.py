#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest

from Products.ZenModel.Exceptions import *
from Products.ZenModel.FileSystem import FileSystem

from ZenModelBaseTest import ZenModelBaseTest

class TestFileSystem(ZenModelBaseTest):


    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance('testdev')
        tmpo = FileSystem('fs')
        self.dev.os.filesystems._setObject('fs',tmpo)
        self.fs = self.dev.os.filesystems()[0]


    def testSetManageIp(self):
        self.fs.setManageIp('1.2.3.4/24')
        self.assert_(self.fs.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.fs.getManageIp() == '2.3.4.5/24')


    def testGets(self):
        import pdb;pdb.set_trace()
        self.assert_(self.fs.getInstDescription() == 'fs')
        self.assert_(self.fs.name() == 'fs')
        self.assert_(self.fs.hostname() == 'testdev')
        self.assert_(self.fs.getParentDeviceName() == 'testdev')
        self.assert_(self.fs.getParentDeviceUrl() == 'zport/dmd/Devices/devices/testdev')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFileSystem))
    return suite

if __name__=="__main__":
    framework()

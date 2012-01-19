###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import os.path
import logging

from DateTime import DateTime
from StringIO import StringIO
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.BatchDeviceLoader import BatchDeviceLoader
from Products.ZenModel.BatchDeviceDumper import BatchDeviceDumper

class FakeConfigs: pass

class FakeOptions:
    def __init__(self):
        self.nocommit = True

class Testzenbatchdumper(BaseTestCase):

    def afterSetUp(self):
        super(Testzenbatchdumper, self).afterSetUp()

        self.zdumper = BatchDeviceDumper(noopts=1)
        self.zdumper.options = FakeOptions()
        self.zdumper.options.regex = '.*'
        self.zdumper.options.prune = False
        self.zdumper.options.root = 'Devices/TestZenBatchDumper'

        self.zloader = BatchDeviceLoader(noopts=1)
        self.zloader.options = FakeOptions()
        self.zloader.options.nomodel = True
        self.zloader.options.nocommit = False

        # WARNING: burtal nasty hack to get around wierdness in TestSuite
        # otherwise only last instantiated object gets a real database connection
        self.zdumper.dmd = self.zloader.dmd

        self.log = logging.getLogger("zen.BatchDeviceDumper")
        self.zdumper.log = self.log
        self.zloader.log = logging.getLogger("zen.BatchDeviceLoader")

    def testDump(self):
        self.zdumper.options.root = 'Devices'
        olympics = DateTime("2010/02/28")
        configs = ["device1 cDateTest=%s" % repr(olympics)]
        device_list = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)
        self.log.debug(self.zloader.dmd.Devices.getSubDevices())
        self.log.debug(self.zdumper.dmd.Devices.getSubDevices())

        outFile = StringIO()
        numLoc = self.zdumper.listLSGOTree(outFile, self.zdumper.dmd.Locations)
        numSys = self.zdumper.listLSGOTree(outFile, self.zdumper.dmd.Systems)
        numGrp = self.zdumper.listLSGOTree(outFile, self.zdumper.dmd.Groups)
        numDevs = self.zdumper.listDeviceTree(outFile)
        self.log.info("dumped %d of %d devices" % (numDevs['Devices'], len([d for d in self.zdumper.root.getSubDevices() if not 'ZenPack' in d.zPythonClass])))
        self.assert_(numDevs['Devices'] == len([d for d in self.zdumper.root.getSubDevices() if not 'ZenPack' in d.zPythonClass]))
        self.log.info(numLoc, numSys, numGrp, numDevs)
        outText = outFile.getvalue()
        outFile.close()
        self.log.info(outText)
        outConfigs = outText.split('\n')
        out_device_list = self.zloader.parseDevices(outConfigs)
        self.log.info(out_device_list)
        self.assert_(numDevs['Devices'] == len(out_device_list))
        dev = self.zloader.dmd.Devices.findDevice('device1')
        self.assert_(dev.cDateTest == olympics)

        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(Testzenbatchdumper))
    return suite


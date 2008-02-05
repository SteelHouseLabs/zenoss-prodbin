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

from twisted.python.runtime import platform
platform.supportsThreads = lambda : False

import unittest
import Globals

from Products.ZenUtils.Driver import drive

from twisted.internet import reactor
from twisted.cred import credentials
from twisted.spread import pb
import sys

count = 0

def stop(ignored=None):
    if isinstance(ignored, Exception):
        raise ignored
    if reactor.running:
        reactor.crash()

from Products.ZenHub.zenhub import ZenHub

class TestClient(pb.Referenceable):

    success = False
    svc = 'Products.ZenHub.tests.TestService'
    
    def __init__(self, tester, port):
        self.tester = tester
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", port, factory)
        d = factory.login(credentials.UsernamePassword("admin", "zenoss"),
                          client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)

    def connected(self, perspective):
        d = perspective.callRemote('getService', self.svc, 'localhost', self)
        d.addCallback(self.test)
        d.addErrback(self.bad)

    def bad(self, reason):
        stop()
        self.tester.fail('error: '+str(reason.value))

    def test(self, service):
        def Test(driver):
            data = ('Some Data', 17)
            yield service.callRemote('echo', data)
            self.tester.assertEqual(driver.next(), data)
            self.success = True
        drive(Test).addBoth(stop)

class SendEventClient(TestClient):
    svc = 'EventService'

    def test(self, service):
        def Test(driver):
            evt = dict(device='localhost',
                       severity='5',
                       summary='This is a test message')
            yield service.callRemote('sendEvents', [evt])
            self.tester.assertEqual(driver.next(), 1)
            self.success = True
        drive(Test).addBoth(stop)

class TestZenHub(unittest.TestCase):

    base = 7000
    xbase = 8000

    def setUp(self):
        global count
        count += 1
        base = self.base + count
        xbase = self.xbase + count
        self.before, sys.argv = sys.argv, ['run',
                                           '--pbport=%d' % base,
                                           '--xmlrpcport=%d' % xbase]
        self.zenhub = ZenHub()
        reactor.callLater(5, stop)

    def tearDown(self):
        sys.argv = self.before

    def testGetService(self):
        client = TestClient(self, self.base + count)
        self.zenhub.main()
        self.assertTrue(client.success)

    def testSendEvent(self):
        client = SendEventClient(self, self.base + count)
        self.zenhub.main()
        self.assertTrue(client.success)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZenHub))
    return suite

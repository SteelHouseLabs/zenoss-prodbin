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

import operator
import simplejson
from itertools import count, islice

#af = lambda x:x>1 and reduce(operator.add, xrange(1, x+1)) or x
#numpairs = lambda x: ((x*(x-1))*0.5) - (af(x%10)) - (af(10)*((x/10)-1))

numpairs = lambda x: (x*(x-1))*0.5

from Products.ZenModel.IpInterface import manage_addIpInterface
from ZenModelBaseTest import ZenModelBaseTest


class TestLinking(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.globalInt = count()
        self.devices = {}

    def assertSameObs(self, *stuff):
        idsort = lambda a,b:cmp(a.id, b.id)
        for l in stuff:
            l.sort(idsort)
        return self.assertEqual(*stuff)

    def _getSubnet(self, base=None, netmask=24):
        if not base: base = self.globalInt.next()
        return ('10.0.%d.%d' % (base, ip) for ip in count())

    def _makeDevices(self, num):
        devgen = ((i, self.dmd.Devices.createInstance("dev%d" % i)) 
                  for i in self.globalInt)
        self.devices.update(dict((i, dev) for (i, dev) in islice(devgen, num)))
        return self.devices

    def _linkDevices(self, devs):
        subnet = self._getSubnet()
        for i in devs:
            dev = devs[i]
            iid = self.globalInt.next()
            manage_addIpInterface(dev.os.interfaces, 'eth%d'%iid, True)
            iface = dev.os.interfaces._getOb('eth%d'%iid)
            iface.addIpAddress(subnet.next())

    def testSlash30Nets(self):
        devs = self._makeDevices(6)

        devs[0].setLocation('/A')
        devs[1].setLocation('/A')
        devs[2].setLocation('/B')
        devs[3].setLocation('/C')
        devs[4].setLocation('/D')
        devs[5].setLocation('/A')

        manage_addIpInterface(devs[0].os.interfaces, 'eth0', True)
        iface0 = devs[0].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[1].os.interfaces, 'eth0', True)
        iface1 = devs[1].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[2].os.interfaces, 'eth0', True)
        iface2 = devs[2].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[3].os.interfaces, 'eth0', True)
        iface3 = devs[3].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[4].os.interfaces, 'eth0', True)
        iface4 = devs[4].os.interfaces._getOb('eth0')
        manage_addIpInterface(devs[5].os.interfaces, 'eth0', True)
        iface5 = devs[5].os.interfaces._getOb('eth0')

        iface0.addIpAddress('192.168.254.9/30')
        iface2.addIpAddress('192.168.254.10/30')

        iface1.addIpAddress('192.168.254.5/30')
        iface3.addIpAddress('192.168.254.6/30')

        iface4.addIpAddress('192.168.254.1/30')
        iface5.addIpAddress('192.168.254.2/30')

        links = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        links = simplejson.loads(links)
        self.assertEqual(len(links), 3)


    def testGetLinkedNodes(self):
        devs = self._makeDevices(3)
        ateam = {0:devs[0], 1:devs[1]}
        bteam = {2:devs[2], 1:devs[1]}
        self._linkDevices(ateam)
        self._linkDevices(bteam)

        def getLinkDevs(start):
            brains, been_there = self.dmd.ZenLinkManager.getLinkedNodes(
                'Device', start.id)
            devbrains = self.dmd.Devices.deviceSearch(
                id=[x.deviceId for x in brains])
            devobs = [x.getObject() for x in devbrains]
            return devobs

        self.assertSameObs(getLinkDevs(devs[0]), ateam.values())
        self.assertSameObs(getLinkDevs(devs[1]), [devs[0], devs[1], devs[2]])
        self.assertSameObs(getLinkDevs(devs[2]), bteam.values())

    def testGetChildLinks(self):
        numDevices = 36
        devs = self._makeDevices(numDevices)
        self._linkDevices(devs)
        devs = devs.values()
        while devs:
            these, devs = devs[:6], devs[6:]
            for this in these:
                this.setLocation("/loc_%d" % len(devs))
        locs = self.dmd.ZenLinkManager.getChildLinks(self.dmd.Locations)
        locs = simplejson.loads(locs)
        self.assertEqual(len(locs), 15) # (n!)/(k!(n-k)!), n=6, k=2

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestLinking))
    return suite

if __name__=="__main__":
    framework()

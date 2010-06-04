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

import unittest
import zope.component
from Products.Zuul.catalog.interfaces import IIndexingEvent
from zope.interface.verify import verifyClass
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.interfaces import IDeviceInfo
from Products.Zuul.infos.device import DeviceInfo

class DeviceFacadeTest(ZuulFacadeTestCase):

    def setUp(self):
        super(DeviceFacadeTest, self).setUp()
        self.facade = Zuul.getFacade('device', self.dmd)

    def test_interfaces(self):
        verifyClass(IDeviceInfo, DeviceInfo)

    def testDeleteOrganizerRemovesDevices(self):
        """When we delete an organizer all the devices assigned to it should not
        still have a relationship to it in the catalog
        """
        # Create Organizer
        organizer = self.facade.addOrganizer("/zport/dmd/Groups", 'testOrganizer')
        organizer_path = organizer.uid

        catalog = self.dmd.zport.global_catalog

        # Add some devices to it (use createInstance to create a device)
        devices = self.dmd.Devices
        test_device = devices.createInstance('testDevice')
        self.facade.moveDevices(['/'.join(test_device.getPhysicalPath())], organizer_path)
        organizer = self.dmd.unrestrictedTraverse(organizer_path)

        # test we have added the device
        self.assertEqual(len(organizer.getDevices()), 1, "make sure we saved our device")
        deviceBrains = catalog(path='/'.join(organizer.getPhysicalPath()))
        self.assertTrue(len(deviceBrains) > 1, " At this point we should have the organizer and the device")

        # Delete the Organizer
        self.facade.deleteNode(organizer_path)

        # Get the devices directly from the path
        deviceBrains = catalog(path='/'.join(organizer.getPhysicalPath()))
        self.assertEqual(len(deviceBrains), 0, " we should not have any devices at this point")

    def test_setProductionState(self):
        notified = []
        @zope.component.adapter(IIndexingEvent)
        def _indexed(event):
            self.assertEqual(event.idxs, ('productionState',))
            self.assertEqual(event.update_metadata, True)
            notified.append(event)

        dev = self.dmd.Devices.createInstance('dev')
        dev2 = self.dmd.Devices.createInstance('dev2')

        self.assertEqual(dev.productionState, 1000)
        self.assertEqual(dev2.productionState, 1000)

        zope.component.provideHandler(_indexed)

        self.facade.setProductionState((dev.getPrimaryUrlPath(),
                                        dev2.getPrimaryUrlPath()), 500)

        self.assertEqual(dev.productionState, 500)
        self.assertEqual(dev2.productionState, 500)

        self.assertEqual(len(notified), 2)

        zope.component.getGlobalSiteManager().unregisterHandler(_indexed)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DeviceFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')


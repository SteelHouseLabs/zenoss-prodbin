###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
from random import shuffle
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.utils import LazySortableList, getZProperties

class Item(object):
    def __init__(self, num):
        self.num = num
    def __repr__(self):
        return '<%s>' % self.num


class UtilsTest(BaseTestCase):
    
    def test_laziness(self):
        s = range(100)
        shuffle(s)
        l = LazySortableList(s)
        self.assertEqual(len(l), 0)

        sslice = s[:10]
        lslice = l[:10]
        self.assertEqual(sslice, lslice)
        # We've only loaded that slice so far
        self.assertEqual(sslice, l.seen)

        sslice = s[5:20]
        lslice = l[5:20]
        self.assertEqual(sslice, lslice)
        self.assertEqual(s[:20], l.seen)

        # Can't do negative
        self.assertRaises(ValueError,lambda:l[-3])

    def test_sorting(self):
        # Not much to test, since it's all default, but we do have
        # the 'orderby' argument.
        from operator import attrgetter
        s = range(100)
        shuffle(s)
        l = LazySortableList(s, cmp=cmp)
        self.assertEqual(l[:], sorted(s, cmp=cmp))

        items = [Item(num=i) for i in s]
        getnum = attrgetter('num')

        l = LazySortableList(items, key=getnum)
        self.assertEqual(l[:], sorted(items, key=getnum))

        l = LazySortableList(items, orderby='num')
        self.assertEqual(l[:], sorted(items, key=getnum))

        l = LazySortableList(items, key=getnum, reverse=True)
        self.assertEqual(l[:], sorted(items, key=getnum, reverse=True))
        
    def test_canGetAllZProperties(self):
        """Makes sure we are only getting the properties that are defined
        on our object
        """
        testPropertyId = self.dmd.Devices.zenPropertyIds()[0]
        properties = getZProperties(self.dmd.Devices)
        
        # test the results
        self.assertTrue(isinstance(properties, dict))
        self.assertTrue(testPropertyId in properties,
                        'testPropertyId should be a key in the returned dictionary')

    def test_canGetGroupSpecificZProperties(self):
        """Makes sure if we override a zproperty at a level that we
        only return that specific zProperty
        """
        devices = self.dmd.Devices
        (testProperty, invariant) = getZProperties(devices).keys()[0:2]
        
        organizer = devices.createOrganizer('TestOrganizer')
        organizer._setProperty(testProperty, 'testChangedProperty')

        properties = getZProperties(organizer)
        self.assertTrue(testProperty in properties.keys() ,
                        "testProperty should be in the list because we changed it")
                
        self.assertFalse(invariant in properties.keys(),
                         "invariant should NOT be in the properties because we did not change it")
        self.assertNotEqual(devices.getProperty(testProperty), organizer.getProperty(testProperty),
                            "Organizers property should have changed")

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(UtilsTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')

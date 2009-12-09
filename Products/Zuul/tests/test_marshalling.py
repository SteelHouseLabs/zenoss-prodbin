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
from zope.interface.verify import verifyClass
from zope.interface import implements
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products import Zuul
from Products.Zuul.marshalling import InfoMarshaller
from Products.Zuul.marshalling import TreeNodeMarshaller
from Products.Zuul.marshalling import DefaultUnmarshaller
from Products.Zuul.marshalling import ProcessUnmarshaller
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.interfaces import IUnmarshaller
from Products.Zuul.interfaces import IInfo

class TestClass(object):
    implements(IInfo)

    foo = 1
    _bar = 2
    quux = 3

    def __init__(self):
        self.quux = 4

    def myMethod(self):
        pass
        
    @property
    def myProperty(self):
        return 5


class MarshalTest(BaseTestCase):

    def setUp(self):
        super(MarshalTest, self).setUp()

    def match(self, dct, keys=None):
        if keys is None:
            # Implicit marshalling
            self.assert_('foo' in dct, 'no foo in %s' % dct)
            self.assertEqual(1, dct['foo'])
            self.failIf('_bar' in dct, 'private vars should not be in dct')
            self.failIf('myMethod' in dct, 'methods should not be in dct')
            self.assert_('quux' in dct, 'no quux in %s' % dct)
            self.assertEqual(4, dct['quux']) # should have instance value
            self.assert_('myProperty' in dct, 'no myProperty in %s' % dct)
            self.assertEqual(5, dct['myProperty'])
        else:
            # Explicit marshalling
            for key in keys:
                self.assertEqual(sorted(keys), sorted(dct.keys()))

    def test_interfaces(self):
        verifyClass(IMarshaller, InfoMarshaller)
        verifyClass(IMarshaller, TreeNodeMarshaller)
        verifyClass(IUnmarshaller, DefaultUnmarshaller)
        verifyClass(IUnmarshaller, ProcessUnmarshaller)
        
    def test_marshal_implicit(self):
        dct = Zuul.marshal(TestClass())
        self.match(dct)

    def test_marshal_explicit(self):
        keys = ('foo', '_bar')
        dct = Zuul.marshal(TestClass(), keys=keys)
        self.match(dct, keys)
        
    def test_unmarshal(self):
        data = {'foo': 42}
        obj = TestClass()
        Zuul.unmarshal(data, obj)
        self.assertEqual(42, obj.foo)
    
    def test_recursion(self):
        data = [TestClass(), TestClass()]
        result = Zuul.marshal(data)
        self.assert_(isinstance(result, list))
        for o in result:
            self.match(o)
        
        data = {'a':TestClass(), 'b':TestClass()}
        result = Zuul.marshal(data)
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['a', 'b'])
        for v in result.values():
            self.match(v)
    
    def test_recursion_with_keys(self):
        keys = ['foo', '_bar']
        data = [TestClass(), TestClass()]
        result = Zuul.marshal(data, keys=keys)
        self.assert_(isinstance(result, list))
        for o in result:
            self.match(o, keys=keys)
        
        data = {'a':TestClass(), 'b':TestClass()}
        result = Zuul.marshal(data, keys=keys)
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['a', 'b'])
        for v in result.values():
            self.match(v, keys=keys)
    
    def test_recursion_with_callables(self):
        class TestThing(object):
            implements(IInfo)
            foo = 5
            def children(self):
                return [TestClass()]
        result = Zuul.marshal(TestThing(), keys=('children', 'foo'))
        self.assert_(isinstance(result['children'], list))
        self.assertEqual(result['children'], [{'foo':1}])


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(MarshalTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    

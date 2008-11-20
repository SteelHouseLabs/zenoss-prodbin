###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.testing.doctestunit import DocTestSuite
import unittest

def test_suite():
    suite = DocTestSuite('Products.ZenUtils.Utils')
    jsonsuite = DocTestSuite('Products.ZenUtils.json')
    return unittest.TestSuite([suite, jsonsuite])

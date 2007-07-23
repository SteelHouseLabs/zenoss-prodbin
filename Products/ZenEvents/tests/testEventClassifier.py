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

import unittest
from os import path
from pprint import pprint

from Products.ZenEvents.EventClassifier import EventClassifier
from Products.ZenEvents.Event import EventFromDict

class testEventClassifier(unittest.TestCase):
    
    tempfile = "tests/eventtemplates.txt"

    def setUp(self):
        self.ec = EventClassifier(self.tempfile)

    def tearDown(self):
        self.ec = None

    def testReadTemplates(self):
        self.failUnless(path.exists(self.tempfile))
        templates = self.ec.readTemplates()
        #pprint(templates)
        self.failUnless(templates[0][0]=="named")
        self.failUnless(templates[0][2]==1)

    def testBuildIndex(self):
        self.failUnless(path.exists(self.tempfile))
        self.ec.buildIndex()
        pprint(self.ec.positionIndex)
    
    def testIndexMatch(self):
        self.ec.buildIndex()
        self.loadLogEvents()
        for i in range(len(self.logevents)):
            ev = self.logevents[i]
            print "testing event %s" % ev.summary
            self.failUnless(self.ec.classify(ev) == (i+1))
    
    def loadLogEvents(self):
        self.failUnless(path.exists(self.tempfile))
        self.logevents = []
        file = open(self.tempfile,"r")
        for line in file.readlines():
            if line.find("#") == 0:
                process, summary = line[1:].split("||")
                ev = EventFromDict({"device":"conrad",
                        "process":process, "summary": summary})
                self.logevents.append(ev)

        
        
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( testEventClassifier ) )
    return suite


if __name__ == "__main__":
    unittest.main()

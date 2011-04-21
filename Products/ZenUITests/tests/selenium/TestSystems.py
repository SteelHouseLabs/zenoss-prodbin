###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#
# Contained below is the class that tests elements located under
# the "Systems" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase

class TestSystems(SelTestBase):
    """Defines a class that runs tests under the Systems heading"""

    def testSystemOrganizer(self):
        """Run tests on the Systems page"""
        
        self.waitForElement("link=Systems")
        self.selenium.click("link=Systems")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog(new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()

##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from ZenModelBaseTest import ZenModelBaseTest

class DummyRequest(object):
    def __init__(self, dataz):
        from cStringIO import StringIO
        self._file = StringIO()
        self._file.write(dataz)
        self._file.seek(0)

class TestGoogleMaps(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestGoogleMaps, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance('testdev')
        self.loc = self.dmd.Locations.createOrganizer('annapolis')
        self.loc.address = 'Annapolis, MD'
        self.geocodedata = """
            {"Z":{"annapolis md":{"name":"Annapolis, MD",
            "Status":{"code":610, "request":"geocode"}}}}
        """.strip()

    def testSetGeocodeCache(self):
        request = DummyRequest(self.geocodedata)
        self.dmd.setGeocodeCache(request)
        self.assert_(self.dmd.geocache == self.geocodedata)

    def testGetGeoCache(self):
        self.dmd.geocache = self.geocodedata
        testdata = self.dmd.getGeoCache()
        self.assert_(r'\\r' not in testdata)
        self.assert_(r'\\n' not in testdata)

    def testClearGeocodeCache(self):
        self.dmd.geocache = self.geocodedata
        self.dmd.clearGeocodeCache()
        self.assert_(not self.dmd.geocache)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestGoogleMaps))
    return suite

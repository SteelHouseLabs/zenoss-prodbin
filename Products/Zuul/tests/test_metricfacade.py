##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from zenoss.protocols.services import JsonRestServiceClient

class MockRestServiceClient(JsonRestServiceClient):

    def _executeRequest(self, request):
        return 200, '[2]'

class MetricFacadeTest(ZuulFacadeTestCase):

    def afterSetUp(self):
        super(MetricFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('metric', self.dmd)
        self.facade._client = MockRestServiceClient('http://localhost:8888')

    def testTagBuilder(self):
        dev = self.dmd.Devices.createInstance('device1')
        self.assertTrue(dev.getUUID())
        tags = self.facade._buildTagsFromContext([dev])
        self.assertEquals(tags.keys()[0], 'uuid')
        self.assertEquals(tags.values()[0][0], dev.getUUID())

    def testMetricBuilder(self):
        metric = ["laLoadInt1_laLoadInt1"]
        cf = "avg"
        metric = self.facade._buildMetrics(metric, cf)[0]
        self.assertEquals(metric['tags'][0], 'laLoadInt1')

    def testRequestBuilder(self):
        metric = ["laLoadInt1_laLoadInt1"]
        dev = self.dmd.Devices.createInstance('device1')
        request = self.facade._buildRequest(dev, metric, cf="AVERAGE")
        self.assertEquals(request['metrics'][0]['aggregator'], 'avg')
        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(MetricFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')


import pdb
import unittest
import Globals
import transaction

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenEvents.Event import Event
from Products.ZenEvents.Exceptions import *

zodb = ZCmdBase(noopts=True)

class MySqlEventMangerTest(unittest.TestCase):
    """
    To run these tests zport.dmd.ZenEventManager must exist and must be setup
    with a proper config to access the mysql backend.  MySQL must also have
    an events database created with bin/zeneventbuild.
    Zeo must be running.
    """

    def setUp(self):
        zodb.getDataRoot()
        self.dmd = zodb.dmd
        self.zem = self.dmd.ZenEventManager
        self.evt = Event()
        self.evt.device = "dev.test.com"
        self.evt.eventClass = "TestEvent"
        self.evt.summary = "this is a test event"
        self.evt.severity = 3

    def tearDown(self):
        transaction.abort()
        db = self.zem.connect()
        curs = db.cursor()
        curs.execute("truncate status")
        curs.execute("truncate detail")
        curs.execute("truncate log")
        curs.execute("truncate history")
        db.close()
        zodb.closedb()
        self.dmd = None
        self.zem = None

    
    def testSendEvent(self):
        self.zem.sendEvent(self.evt) 
        evts = self.zem.getEventList(where="device='dev.test.com'")
        self.assert_(len(evts) == 1)
        self.assert_(evts[0].summary == self.evt.summary)


    def testSendEventDup(self):
        self.zem.sendEvent(self.evt) 
        self.zem.sendEvent(self.evt) 
        evts = self.zem.getEventList(where="device='dev.test.com'")
        self.assert_(len(evts) == 1)
        self.assert_(evts[0].count == 2)


    def testEventMissingRequired(self):
        delattr(self.evt, "eventClass")
        self.assertRaises(ZenEventError, self.zem.sendEvent, self.evt) 


    def testEventDetailField(self):
        self.evt.ntseverity = "Error"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        self.assert_(("ntseverity", self.evt.ntseverity) in evdetail.details)

    
    def testEventDetailFields(self):
        self.evt.ntseverity = "Error"
        self.evt.ntsource = "Zope"
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        self.assert_(("ntseverity", self.evt.ntseverity) in evdetail.details)
        self.assert_(("ntsource", self.evt.ntsource) in evdetail.details)
    
    
    def testEventDetailgetEventFields(self):
        pdb.set_trace()
        evt = self.zem.sendEvent(self.evt)
        evdetail = self.zem.getEventDetail(dedupid=evt.dedupid)
        feilds = evdetail.getEventFields()

    

if __name__ == "__main__":
    unittest.main()



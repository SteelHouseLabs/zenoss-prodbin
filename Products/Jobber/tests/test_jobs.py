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

from twisted.internet import reactor, defer

from Products.Jobber.jobs import Job
from Products.Jobber.manager import JobManager
from Products.Jobber.status import JobStatus, SUCCESS, FAILURE
from Products.Jobber.logfile import LogFile
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class SucceedingJob(Job):
    def run(self, r):
        d = defer.Deferred()
        d.addBoth(self.finished, SUCCESS)
        return d

class FailingJob(Job):
    def run(self, r):
        d = defer.Deferred()
        d.addBoth(self.finished, FAILURE)
        return d

class NotAJob(object):
    def run(self):
        pass

class OneSecondJob(Job):
    def run(self, r):
        def done():
            self.finished(SUCCESS)
        reactor.callLater(1, done)


class TestJob(BaseTestCase):

    def test_id_required(self):
        self.assertRaises(TypeError, Job)

    def test_step_workflow(self):
        """
        Make sure that if start() is called, it makes its way through run() and
        finished() with the proper result at the end.
        """
        def test_success(result): self.assertEqual(result, SUCCESS)
        def test_failure(result): self.assertEqual(result, FAILURE)

        good = SucceedingJob('good')
        bad = FailingJob('bad')

        d = good.start()
        d.addCallback(test_success)

        d = bad.start()
        d.addCallback(test_failure)


class TestJobStatus(BaseTestCase):
    def afterSetUp(self):
        super(TestJobStatus, self).afterSetUp()
        self.j = JobStatus(Job('ajob'))

    def test_isFinished(self):
        self.assertEqual(self.j.isFinished(), False)

        self.j.jobStarted()
        self.assertEqual(self.j.isFinished(), False)

        self.j.jobFinished(None)
        self.assertEqual(self.j.isFinished(), True)

    def test_waitUntilFinished(self):
        self.j.jobStarted()
        def hasFinished(jobstatus):
            self.assert_(jobstatus.isFinished())
        d = self.j.waitUntilFinished()
        d.addCallback(hasFinished)
        self.j.jobFinished(SUCCESS)

    def test_properties(self):
        props = {'a':1, 'b':2}
        self.j.setProperties(**props)
        self.assert_(self.j.getProperties() == props)
        # Make sure it's a copy, not same ob
        self.assert_(self.j.getProperties() is not props)
        self.j.setProperties(b=3)
        self.assert_(self.j.getProperties()['b']==3)


class TestJobManager(BaseTestCase):
    def afterSetUp(self):
        super(TestJobManager, self).afterSetUp()
        self.m = JobManager('jobmgr')

    def test_add_job_jobs_only(self):
        self.assertRaises(AssertionError, self.m.addJob, NotAJob)

    def test_add_job(self):
        stat = self.m.addJob(SucceedingJob)
        self.assert_(isinstance(stat, JobStatus))
        self.assert_(isinstance(stat.getJob(), Job))
        self.assert_(stat in self.m.jobs())

    def test_getJob(self):
        stat = self.m.addJob(SucceedingJob)
        stat2 = self.m.addJob(SucceedingJob)
        self.assertEqual(self.m.getJob(stat.id), stat)
        self.assertEqual(self.m.getJob(stat2.id), stat2)
        self.assertEqual(self.m.getJob(stat.id.split('_')[-1]), stat)
        self.assert_(self.m.getJob('NotAnId') is None)



class TestLogFile(BaseTestCase):
    def afterSetUp(self):
        super(TestLogFile, self).afterSetUp()
        self.stat = JobStatus(Job('ajob'))
        self.log = self.stat.getLog()

    def test_create(self):
        self.assert_(isinstance(self.log, LogFile))
        self.assert_(self.log.getStatus() is self.stat)
        log2 = self.stat.getLog()
        self.assertEqual(self.log.getFilename(),
                         log2.getFilename())

    def test_write(self):
        data = ['foo', 'bar', 'spam', 'eggs']
        self.log.write(data[0])
        self.assertEqual(self.log.getText(), data[0])
        self.log.write(data[1])
        self.assertEqual(self.log.readlines(), ["".join(data[:2])])
        self.log.write("".join(data[2:]))
        self.assertEqual(self.log.readlines(), ["".join(data)])

class TestLogStream(BaseTestCase):
    def afterSetUp(self):
        super(TestLogStream, self).afterSetUp()
        self.stat = JobStatus(Job('ajob'))
        self.log = self.stat.getLog()
        self.stream = self.stat.getLog()

    def test_create(self):
        self.assertEqual(
            self.log.getFilename(),
            self.stream.getFilename()
        )
        self.assert_(self.stream.getFilename() is not None)

    def test_read(self):
        self.log.write('blah')
        data = self.stream.getText()
        self.assertEqual(data, 'blah')
        self.log.write('blah is a thingy')
        data = self.stream.getText()
        self.assertEqual(data, 'blahblah is a thingy')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestJob))
    suite.addTest(makeSuite(TestJobStatus))
    suite.addTest(makeSuite(TestJobManager))
    suite.addTest(makeSuite(TestLogFile))
    suite.addTest(makeSuite(TestLogStream))
    return suite

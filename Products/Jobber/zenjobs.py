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

import logging
from Globals import *
from ZODB.transact import transact
from Products.ZenEvents.Schedule import Schedule
from twisted.internet import reactor, defer
from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop
from Products.ZenCallHome.transport.cycler import CallHomeCycler
from Products.ZenUtils.CyclingDaemon import CyclingDaemon
import transaction
from status import FAILURE

logger = logging.getLogger('zen.Jobs')

class ZenJobs(CyclingDaemon):
    """
    Daemon to run jobs.
    """
    name = 'zenjobs'

    def __init__(self, *args, **kwargs):
        CyclingDaemon.__init__(self, *args, **kwargs)
        self.jm = self.dmd.JobManager
        self.runningjobs = []

        self.schedule = Schedule(self.options, self.dmd)
        self.schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
        self.schedule.monitor = self.options.monitor

        # Send startup event
        if self.options.cycle:
            event = Event(device=self.options.monitor,
                      eventClass=App_Start,
                      summary="zenjobs started",
                      severity=0, component="zenjobs")
            self.sendEvent(event)

    @defer.inlineCallbacks
    def run_job(self, job):
        self.syncdb()
        logger.info("Starting %s %s" % (
            job.getJobType(),
            job.getDescription()))
        d = job.getStatus().waitUntilFinished()
        d.addCallback(self.job_done)
        jobd = job.start()
        # the Job.start method will persist the "started"
        # flag on the status object, but leaving this commit
        # here in case other jobs were depending on it
        transaction.commit()
        self.runningjobs.append(jobd)
        yield jobd

    def job_done(self, jobstatus):
        logger.info('%s %s completed in %s seconds.' % (
            jobstatus.getJob().getJobType(),
            jobstatus.getJob().getDescription(),
            jobstatus.getDuration()))
        # Zope will want to know the job has finished
        transaction.commit()

    def waitUntilRunningJobsFinish(self):
        return defer.DeferredList(self.runningjobs)

    @defer.inlineCallbacks
    def main_loop(self):
        for job in self.get_new_jobs():
            yield self.run_job(job)
        yield self.finish_loop()

    def finish_loop(self):
        if not self.options.cycle:
            # Can't stop the reactor until jobs are done
            whenDone = self.waitUntilRunningJobsFinish()
            whenDone.addBoth(self.finish)

    def get_new_jobs(self):
        return [s.getJob() for s in self.jm.getPendingJobs()]

    def finish(self, r=None):
        for d in self.runningjobs:
            try:
                d.callback(FAILURE)
            except defer.AlreadyCalledError:
                pass
        CyclingDaemon.finish(self, r)

    def run(self):
        def startup():
            chc = CallHomeCycler(self.dmd)
            chc.start()
            self.schedule.start()
            self.runCycle()
        reactor.callWhenRunning(startup)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        reactor.run()

    def stop(self):
        self.running = False
        self.log.info("stopping")
        if self.options.cycle:
            self.sendEvent(Event(device=self.options.monitor,
                             eventClass=App_Stop,
                             summary="zenjobs stopped",
                             severity=3, component="zenjobs"))



from Products.ZenUtils.celeryintegration import ZenossCelery
from celery.bin.celeryd import main as run_celery
from Products.ZenUtils.ZenDaemon import ZenDaemon

try:
    from celery.concurrency.processes.forking import freeze_support
except ImportError:
    freeze_support = lambda: True


class CeleryZenJobs(ZenDaemon):

    def __init__(self, *args, **kwargs):
        ZenDaemon.__init__(self, *args, **kwargs)
        self.setup_celery()

    def setup_celery(self):
        self.celery = ZenossCelery(
           loader="Products.ZenUtils.celeryintegration.ZenossLoader",
           options=self.options)

    def run(self):
        freeze_support()
        from celery import concurrency
        kwargs = {}
        kwargs["pool_cls"] = concurrency.get_implementation(
                    kwargs.get("pool_cls") or self.celery.conf.CELERYD_POOL)
        return self.celery.Worker(**kwargs).run()


if __name__ == "__main__":
    zj = ZenJobs()
    zj.run()


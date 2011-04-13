###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging

from zope.component import getUtility

from twisted.internet import defer, reactor
from twisted.python.failure import Failure
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from zenoss.protocols.protobufs.zep_pb2 import DaemonHeartbeat

log = logging.getLogger("zen.maintenance")


def maintenanceBuildOptions(parser, defaultCycle=60):
    """
    Adds option for maintence cycle interval
    """
    parser.add_option('--maintenancecycle',
                      dest='maintenancecycle',
                      default=defaultCycle,
                      type='int',
                      help='Cycle, in seconds, for maintenance tasks.'
                           ' Default is %s.' % defaultCycle)


class QueueHeartbeatSender(object):
    """
    class for sending heartbeats over amqp
    """
    def __init__(self, monitor, daemon, timeout):
        self._monitor = monitor
        self._daemon = daemon
        self._timeout = timeout

    def heartbeat(self):
        """
        publish the heartbeat
        """
        heartbeat = DaemonHeartbeat(monitor=self._monitor,
                                    daemon=self._daemon,
                                    timeout_seconds=self._timeout)
        log.debug('sending heartbeat %s' % heartbeat)
        publisher = getUtility(IQueuePublisher)
        publisher.publish('$Heartbeats', 'zenoss.heartbeat.%s' % heartbeat.monitor, heartbeat)

class MaintenanceCycle(object):
    def __init__(self, cycleInterval, heartbeatSender=None, maintenanceCallback=None):
        self._cycleInterval = cycleInterval
        self._heartbeatSender = heartbeatSender
        self._callback = maintenanceCallback
        self._stop = False

    def start(self):
        reactor.callWhenRunning(self._doMaintenance)

    def stop(self):
        log.debug("Maintenance stopped")
        self._stop
        
    def _doMaintenance(self):
        """
        Perform daemon maintenance processing on a periodic schedule. Initially
        called after the daemon configuration loader task is added, but afterward
        will self-schedule each run.
        """
        if self._stop:
            log.debug("Skipping, maintenance stopped")
            return
        
        log.info("Performing periodic maintenance")
        interval = self._cycleInterval

        def _maintenance():
            log.debug("calling hearbeat sender")
            d = defer.maybeDeferred(self._heartbeatSender.heartbeat)
            d.addCallback(self._additionalMaintenance)
            return d

        def _reschedule(result):
            if isinstance(result, Failure):
                log.error("Maintenance failed: %s",
                               result.getErrorMessage())

            if interval > 0:
                log.debug("Rescheduling maintenance in %ds", interval)
                reactor.callLater(interval, self._doMaintenance)

        d = _maintenance()
        d.addBoth(_reschedule)

        return d

    def _additionalMaintenance(self, result):
        if self._callback:
            log.debug("calling additional maintenance")
            d = defer.maybeDeferred(self._callback, result)
            return d
#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################
__doc__ = """zenstatus

Check the TCP/IP connectivity of IP services.
UDP is specifically not supported.
"""

import logging

from twisted.internet import defer

import Globals
import zope.component
import zope.interface
from Products.ZenStatus.ZenTcpClient import ZenTcpClient
from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SubConfigurationTaskSplitter,\
                                        TaskStates

from Products.ZenUtils.observable import ObservableMixin

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.ZenStatusConfig import ServiceProxy
unused(ServiceProxy)
unused(DeviceProxy)

#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.zenstatus")


class ServiceTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = 'components'
    def makeConfigKey(self, config, subconfig):
        return (config.id, config.configCycleInterval, subconfig.component)


# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
class ZenStatusPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Construct a new ZenStatusPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = "zenstatus"
        self.defaultRRDCreateCommand = None
        self.cycleInterval = 60  # seconds
        self.configCycleInterval = 20  # minutes
        self.statusCycleInterval = 60
        self.options = None

        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.ZenStatusConfig'

    def buildOptions(self, parser):
        """
        add any zenstatus specific command line options here
        TODO: add parallel option (in the collector framework)
        """
        pass

    def postStartup(self):
        """
        process any zenstatus specific command line options here
        """
        pass


class ZenStatusTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    def __init__(self,
                 name,
                 configId,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        Construct a new task for checking the status

        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(ZenStatusTask, self).__init__()
        self.name = name
        self.configId = configId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE
        self.log = log
        self.cfg = taskConfig.components[0]
        self._devId = self.cfg.device
        self._manageIp = self.cfg.ip
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        "zenstatus")

    def doTask(self):
        log.debug("Scanning device %s (%s) port %s",
                  self._devId, self._manageIp, self.cfg.port)
        job = ZenTcpClient(self.cfg, self.cfg.status)
        d = job.start()
        d.addCallback(self.processTest)
        d.addErrback(self.handleExceptions)
        return d

    def processTest(self, result):
        """
        Test a connection to a device.

        @parameter result: device and TCP service to test
        @type result: ZenTcpClient object
        """
        evt = result.getEvent()
        if evt:
            self._eventService.sendEvent(evt)
            if evt['severity'] != 0:
                return defer.succeed("Failed")

        return defer.succeed("Connected")

    def handleExceptions(self, reason):
        """
        Log internal exceptions that have occurred
        from testing TCP services

        @param reason: error message
        @type reason: Twisted error instance
        """
        msg = reason.getErrorMessage()
        evt = dict(device=self._preferences.options.monitor,
                   summary=msg,
                   severity=4,  # error
                   component='zenstatus',
                   traceback=reason.getTraceback())
        self._eventService.sendEvent(evt)
        return defer.succeed("Failed due to internal error")

    def cleanup(self):
        pass


#
# Collector Daemon Main entry point
#
if __name__ == '__main__':
    myPreferences = ZenStatusPreferences()
    myTaskFactory = SimpleTaskFactory(ZenStatusTask)
    myTaskSplitter = ServiceTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()

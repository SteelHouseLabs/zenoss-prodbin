###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """PingTask

Determines the availability of a IP addresses using ping (ICMP).

"""

import re
import time
import logging
log = logging.getLogger("zen.zenping")

import Globals
import zope.interface
import zope.component

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR

from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import TaskStates, BaseTask

from Products.ZenStatus.PingJob import PingJob
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenEvents import Event

from Products.ZenUtils.IpUtil import ipunwrap

# Temporarily run ping6 from a command-line
from Products.ZenRRD.zencommand import Cmd, ProcessRunner, TimeoutError


# Try a circular import?
COLLECTOR_NAME = "zenping"
TOPOLOGY_MODELER_NAME = "topology_modeler"
MAX_BACK_OFF_MINUTES = 20
MAX_IFACE_PING_JOBS = 10

STATUS_EVENT = { 
                'eventClass' : Status_Ping,
                'component' : 'zenping',
                'eventGroup' : 'Ping' }

class PingCollectionTask(BaseTask):
    zope.interface.implements(IScheduledTask)

    STATE_PING_START = 'PING_START'
    STATE_PING_STOP  = 'PING_STOP'
    STATE_STORE_PERF = 'STORE_PERF_DATA'
    STATE_UPDATE_TOPOLOGY = 'UPDATE_TOPOLOGY'

    def __init__(self,
                 taskName,
                 deviceId,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(PingCollectionTask, self).__init__()

        # Needed for interface
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = deviceId
        self._manageIp = ipunwrap(self._device.manageIp)
        self.interval = scheduleIntervalSeconds

        self._daemon = zope.component.queryUtility(ICollector)
        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        COLLECTOR_NAME)
        self._maxbackoffseconds = self._preferences.options.maxbackoffminutes * 60

        self._pinger = self._preferences.pinger
        self.startTime = None

        # Split up so that every interface's IP gets its own ping job
        self.config = self._device.monitoredIps[0]
        self._iface = self.config.iface
        self.pingjob = PingJob(ipunwrap(self.config.ip), self._devId,
                                maxtries=self.config.tries,
                                sampleSize=self.config.sampleSize,
                                iface=self._iface)
        self.pingjob.points = self.config.points

        if self.config.ipVersion == 6:
            self._network = self._daemon.ipv6network
        else:
            self._network = self._daemon.network

        self._addToTopology()

        self._lastErrorMsg = ''

    def _addToTopology(self):
        """
        Update the topology with our local knowledge of how we're connected.
        """
        ip = self.config.ip
        if ip not in self._network.topology:
            self._network.topology.add_node(ip)
        self._network.topology.node[ip]['task'] = self

        internalEdge = (self._manageIp, ip)
        if ip != self._manageIp and \
           not self._network.topology.has_edge(*internalEdge):
            self._network.topology.add_edge(*internalEdge)

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single IP.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        # Decode the exception
        msg = reason.getErrorMessage()
        if not msg: # Sometimes we get blank error messages
            msg = reason.__class__

        msg = '%s %s' % (self._devId, msg)

        # Leave 'reason' alone to generate a traceback
        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)
        self._eventService.sendEvent(STATUS_EVENT,
                                     device=self._devId,
                                     summary=msg,
                                     severity=Event.Error)
        self._delayNextCheck()

        return reason

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to ping the device and any of its interfaces.
        @rtype: Twisted deferred object
        """
        # Reset statistics for this run of data collection
        self.pingjob.reset()

        # Start the ping job
        self.state = PingCollectionTask.STATE_PING_START
        if self.config.ipVersion == 6:
            d = self._ping6()
        else:
            self._pinger.sendPacket(self.pingjob)
            d = self.pingjob.deferred

        d.addCallback(self._storeResults)
        d.addCallback(self._updateStatus)
        d.addErrback(self._failure)

        # Wait until the Deferred actually completes
        return d

    def _ping6(self):
       """
       Temporary hack to be able to veriy IPv6 ping functionality end-to-end
       """
       # FIXME: use a Python-level library rather than spawning a process
       cmd = Cmd()
       cmd.ds = "PING6"
       cmd.ip = ipunwrap(self.config.ip)
       cmd.command = "ping6 -n -c %d %s" % (self.config.tries, cmd.ip)
       cmd.name = cmd.command
       class DevProxy(object):
           zCommandCommandTimeout = self._preferences.options.tracetimeoutseconds
       cmd.deviceConfig = DevProxy()

       runner = ProcessRunner()
       d = runner.start(cmd)
       cmd.lastStart = time.time()
       d.addBoth(cmd.processCompleted)
       d.addCallback(self._updatePingJob6)
       return d

    def _updatePingJob6(self, result):
        self.pingjob.sent = self.config.tries
        if result.result.exitCode != 0:
            self.pingjob.rtt = -1
            return result.result.output
        else:
            output = result.result.output.strip().split('\n')

            # rtt min/avg/max/mdev = 1.211/2.322/3.434/1.112 ms, pipe 2'
            statsLine = output[-1]
            stats = statsLine.rsplit('=',1)[1].split()[0]
            rttMin, rttAvg, rttMax, rttStdDev = map(float, stats.split('/'))
            self.pingjob.rtt = rttAvg
            self.pingjob.rtt_avg = rttAvg
            self.pingjob.rtt_min = rttMin
            self.pingjob.rtt_max = rttMax
            self.pingjob.rtt_stddev = rttStdDev

            # 2 packets transmitted, 2 received, 0% packet loss, time 1000ms
            lossLine = output[-2]
            lossPct = lossLine.split()[5][:-1]
            self.pingjob.rtt_losspct = int(lossPct)

        return result.result.output

    def _storeResults(self, result):
        """
        Store the datapoint results asked for by the RRD template.
        """
        self.state = PingCollectionTask.STATE_STORE_PERF
        if self.pingjob.rtt >= 0 and self.pingjob.points:
            if self.config.ipVersion == 4:
                self.pingjob.calculateStatistics()
            for rrdMeta in self.pingjob.points:
                name, path, rrdType, rrdCommand, rrdMin, rrdMax = rrdMeta
                value = getattr(self.pingjob, name, None)
                if value is None:
                    log.debug("No datapoint '%s' found on the %s pingjob",
                              name, self.pingjob.ipaddr)
                    continue
                self._dataService.writeRRD(path, value, rrdType,
                                           rrdCommand=rrdCommand,
                                           min=rrdMin, max=rrdMax)

        return result

    def _updateStatus(self, result):
        """
        Update the modeler and handle issues

        @parameter result: results of Ping or a failure
        @type result: array of (boolean, dictionaries)
        """
        self.state = PingCollectionTask.STATE_UPDATE_TOPOLOGY
        ip = self.pingjob.ipaddr
        if self.pingjob.rtt >= 0:
            success = 'Success'
            self._network.downDevices.discard(ip)
            self.sendPingClearEvent(self.pingjob)
        else:
            success = 'Failed'
            self._network.downDevices.add(ip)
            log.warning("No ping response for %s in %d tries",
                        self.pingjob.ipaddr, self.pingjob.sent)
        resultMsg = "%s RTT = %s sec (%s)" % (
                        ip, self.pingjob.rtt, success)

        return resultMsg

    def sendPingClearEvent(self, pj):
        """
        Send an event based on a ping job to the event backend.
        """
        msg = "%s is UP!" % self._devId
        evt = dict(device=self._devId,
                   ipAddress=pj.ipaddr,
                   summary=msg,
                   severity=SEVERITY_CLEAR,
                   eventClass=Status_Ping,
                   eventGroup='Ping',
                   component=self._iface)
        evstate = getattr(pj, 'eventState', None)
        if evstate is not None:
            evt['eventState'] = evstate
        self._eventService.sendEvent(evt)

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = self.name
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


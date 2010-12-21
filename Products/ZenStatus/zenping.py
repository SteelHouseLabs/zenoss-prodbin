#! /usr/bin/env python
# -*- coding: utf-8 -*-
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

__doc__ = """zenping

Determines the availability of a IP addresses using ping (ICMP).

"""

import os
import os.path
import sys
import re
from socket import gethostbyname, getfqdn, gaierror
import time
import logging
log = logging.getLogger("zen.zenping")

import Globals
import zope.interface
import zope.component

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences,\
                                             IConfigurationListener
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SubConfigurationTaskSplitter

from Products.ZenStatus.AsyncPing import Ping
from Products.ZenStatus.TestPing import Ping as TestPing
from Products.ZenStatus.TracerouteTask import TracerouteTask
from Products.ZenStatus.PingTask import PingCollectionTask
from Products.ZenStatus.CorrelatorTask import TopologyCorrelatorTask
from Products.ZenStatus.NetworkModel import NetworkModel

from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)
from Products.ZenHub.services.PingPerformanceConfig import PingPerformanceConfig
unused(PingPerformanceConfig)


COLLECTOR_NAME = "zenping"
TOPOLOGY_MODELER_NAME = "topology_modeler"
TOPOLOGY_CORRELATOR_NAME = "topology_correlator"
MAX_BACK_OFF_MINUTES = 20
MAX_IFACE_PING_JOBS = 10


class PingCollectionPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new PingCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.PingPerformanceConfig'

        # Will be filled in based on buildOptions
        self.options = None

        self.pingTimeOut = 1.5
        self.pingTries = 2
        self.pingChunk = 75
        self.pingCycleInterval = 60
        self.configCycleInterval = 20*60
        self.maxPingFailures = 2
        self.pinger = None

        self.topologySaveTime = time.time()

    def buildOptions(self, parser):
        parser.add_option('--showrawresults',
                          dest='showrawresults',
                          action="store_true",
                          default=False,
                          help="Show the raw RRD values. For debugging purposes only.")
        parser.add_option('--name',
                          dest='name',
                          default=findIp(),
                          help=("Host that roots the ping dependency "
                                "tree: typically the collecting hosts' "
                                "name; defaults to our fully qualified "
                                "domain name (%default)"))
        parser.add_option('--test',
                          dest='test',
                          default=False,
                          action="store_true",
                          help="Run in test mode: doesn't really ping,"
                               " but reads the list of IP Addresses that "
                               " are up from /tmp/testping")
        parser.add_option('--useFileDescriptor',
                          dest='useFileDescriptor',
                          default=None,
                          help="Use the given (privileged) file descriptor")
        parser.add_option('--maxbackoffminutes',
                          dest='maxbackoffminutes',
                          default=MAX_BACK_OFF_MINUTES,
                          type='int',
                          help="When a device fails to respond, increase the time to" \
                               " check on the device until this limit.")
        parser.add_option('--tracetimeoutseconds',
                          dest='tracetimeoutseconds',
                          default=40,
                          type='int',
                          help="Wait for a maximum of this time before stopping"
                               " the traceroute")
        parser.add_option('--tracechunk',
                          dest='tracechunk',
                          default=5,
                          type='int',
                          help="Number of devices to traceroute at once.")
        parser.add_option('--topofile',
                          dest='topofile',
                          default='',
                          help="Use this file rather than the default.")
        parser.add_option('--savetopominutes',
                          dest='savetopominutes',
                          default=45,
                          type='int',
                          help="When cycling, save the topology this number of minutes.")
        parser.add_option('--showroute',
                          dest='showroute',
                          default='',
                          help="Show the route from the collector to the end point.")

    def postStartup(self):
        daemon = zope.component.getUtility(ICollector)

        if not self.options.useFileDescriptor:
            daemon.openPrivilegedPort('--ping')

        daemon.network = NetworkModel()
        if self.options.showroute:
            daemon.network.showRoute(self.options.showroute)
            sys.exit(0)

        # Initialize our connection to the ping socket
        self._getPinger()

        # Start modeling network topology
        task = TracerouteTask(TOPOLOGY_MODELER_NAME,
                                   taskConfig=daemon._prefs)
        daemon._scheduler.addTask(task, now=True)

        # Start the event correlator
        task = TopologyCorrelatorTask(TOPOLOGY_CORRELATOR_NAME,
                                   taskConfig=daemon._prefs)
        daemon._scheduler.addTask(task, now=True)

    def preShutdown(self):
        daemon = zope.component.getUtility(ICollector)

        # Run the correlator one last time
        tasks = daemon._scheduler.getTasksForConfig(TOPOLOGY_CORRELATOR_NAME)
        if tasks:
            tasks[0].doTask()
        else:
            log.warn("Unable to run correlator as the task has been removed")

        # If we're running as a daemon, save the topology
        daemon.network._saveTopology()

    def _getPinger(self):
        if self.pinger:
            self.pinger.reconfigure(self.pingTimeOut)
        else:
            if self.options.test:
                self.pinger = TestPing(self.pingTimeOut)
            else:
                fd = None
                if self.options.useFileDescriptor is not None:
                    fd = int(self.options.useFileDescriptor)
                self.pinger = Ping(self.pingTimeOut, fd)


class PerIpAddressTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = 'monitoredIps'

    def makeConfigKey(self, config, subconfig):
        return (config.id, subconfig.cycleTime, subconfig.ip)


class TopologyUpdater(object):
    """
    This updates the link between a device and the topology.
    """
    zope.interface.implements(IConfigurationListener)
      
    def deleted(self, configurationId):
        """
        Called when a configuration is deleted from the collector
        """
        # Note: having the node in the topology doesn't bother us,
        #       so don't worry about it
        pass

    def added(self, configuration):
        """
        Called when a configuration is added to the collector.
        This links the schedulable tasks to the topology so that we can
        check on the status of the network devices.
        """
        daemon = zope.component.getUtility(ICollector)
        if daemon.network.topology is None:
            return

        ipAddress = configuration.manageIp
        if ipAddress not in daemon.network.topology:
            daemon.network.notModeled.add(ipAddress)
            log.debug("zenhub asked us to add new device: %s (%s)",
                      configuration.id, ipAddress)
            daemon.network.topology.add_node(ipAddress)
        #daemon.network.topology.node[ipAddress]['task'] = configuration

    def updated(self, newConfiguration):
        """
        Called when a configuration is updated in collector
        """
        log.debug("zenhub asked us to update device: %s (%s)",
                      newConfiguration.id, newConfiguration.manageIp)
        pass


def findIp():
    try:
        return gethostbyname(getfqdn())
    except gaierror:
        # find the first non-loopback interface address
        ifconfigs = ['/sbin/ifconfig',
                     '/usr/sbin/ifconfig',
                     '/usr/bin/ifconfig',
                     '/bin/ifconfig']
        ifconfig = filter(os.path.exists, ifconfigs)[0]
        fp = os.popen(ifconfig + ' -a')
        config = fp.read().split('\n\n')
        fp.close()
        digits = r'[0-9]{1,3}'
        pat = r'(addr:|inet) *(%s\.%s\.%s\.%s)[^0-9]' % ((digits,)*4)
        parse = re.compile(pat)
        results = []
        for c in config:
            addr = parse.search(c)
            if addr:
                results.append(addr.group(2))
        try:
            results.remove('127.0.0.1')
        except ValueError:
            pass
        if results:
            return results[0]
    return '127.0.0.1'


if __name__=='__main__':
    myPreferences = PingCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(PingCollectionTask)
    myTaskSplitter = PerIpAddressTaskSplitter(myTaskFactory)
    myListener = TopologyUpdater()
    daemon = CollectorDaemon(myPreferences, myTaskSplitter,
                            configurationLister=myListener,
                            stoppingCallback=myPreferences.preShutdown)
    daemon.run()


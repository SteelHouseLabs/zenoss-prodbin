##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.zenping.pingcollectionprefs")

import Globals
import zope.interface
import zope.component

from Products.ZenCollector import daemon 
from Products.ZenCollector import interfaces 
from Products.ZenCollector import tasks 
from Products.ZenUtils import IpUtil
import Products.ZenStatus.interfaces

# perform some imports to allow twisted's PB to serialize these objects
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.PingPerformanceConfig import PingPerformanceConfig
unused(DeviceProxy)
unused(PingPerformanceConfig)

# define some constants strings
COLLECTOR_NAME = "zenping"
CONFIG_SERVICE = 'Products.ZenHub.services.PingPerformanceConfig'


class PingCollectionPreferences(object):
    zope.interface.implements(interfaces.ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new PingCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 60 * 5 # seconds
        
        # do not pause our tasks, when devices are determined down
        self.pauseUnreachableDevices = False

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = CONFIG_SERVICE

        # Will be filled in based on buildOptions
        self.options = None

        self.pingTimeOut = 1.5
        self.pingTries = 2
        self.pingChunk = 75
        self.pingCycleInterval = 60
        
    def buildOptions(self, parser):
        parser.add_option('--disable-correlator',
            dest='correlator',
            default=True,
            action="store_false",
            help="Disable the correlator.")

        parser.add_option('--traceroute-interval',
            dest='tracerouteInterval',
            default=5,
            type='int',
            help="Traceroute every N ping intervals; default is 5, traceroute every time" \
                " a ping is performed.")

        # look up possible ping backends
        pingBackends = []
        for pingBackend, _ in zope.component.getUtilitiesFor(
                Products.ZenStatus.interfaces.IPingTaskFactory):
            pingBackends.append(pingBackend)
        backendsHelp = "ping backend to use (%s)" % ", ".join(pingBackends)
        parser.add_option('--ping-backend',
            dest='pingBackend',
            default='nmap',
            help=backendsHelp + " default: %default")

    def postStartup(self):
        pass

    def preShutdown(self):
        pass

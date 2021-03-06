##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """CmdPingTask

Determines the availability of a IP addresses using command line ping.

"""

import logging
log = logging.getLogger("zen.zenping.cmdping")

from twisted.python.failure import Failure
from twisted.internet import defer, utils
import time

import Globals
from zope import interface
from zope import component

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR

from Products.ZenCollector import interfaces 
from Products.ZenCollector.tasks import TaskStates, BaseTask

from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenEvents import Event
from Products import ZenStatus

from PingResult import PingResult
_PING = None
_PING6 = None
_PING_ARG_TEMPLATE = None
_OK = 0

def _detectPing():
    import subprocess
    global _PING, _PING6, _PING_ARG_TEMPLATE
    try:
        _PING = subprocess.check_output(['which', 'ping']).strip()
    except subprocess.CalledProcessError:
        log.error('no command line ping detected')
        import sys
        sys.exit(1)
    try:
        _PING6 = subprocess.check_output(['which', 'ping6']).strip()
    except subprocess.CalledProcessError:
       log.info('ping6 not found in path')

    _PING_ARG_TEMPLATE = '%(ping)s -n -s %(datalength)d -c 1 -t %(ttl)d -w %(timeout)f %(ip)s'
    import platform
    system = platform.system() 
    if system in ('Mac OS X', 'Darwin'):
       log.info('Mac OS X detected; adjusting ping args.')
       _PING_ARG_TEMPLATE = '%(ping)s -n -s %(datalength)d -c 1 -m %(ttl)d -t %(timeout)f %(ip)s'
    elif system != 'Linux':
       log.info('CmdPing has not been tested on %r; assuming that Linux ping args work.')

_detectPing()

def _getPingCmd(version=6, **kwargs):
    args = kwargs.copy()
    if version == 6:
        args['ping'] = _PING6
    else:
        args['ping'] = _PING
    
    cmd_str = _PING_ARG_TEMPLATE % args
    cmd_list = cmd_str.split(' ')
    return (cmd_list[0], cmd_list[1:])
    

class CmdPingCollectionPreferences(ZenStatus.PingCollectionPreferences):
    """
    This required to be a ping backend; use default implementation.
    """
    pass

class CmdPingTaskFactory(object):
    """
    A Factory to create command line PingTasks.
    """
    interface.implements(ZenStatus.interfaces.IPingTaskFactory)

    def __init__(self):
        self.reset()

    def build(self):
        task = CmdPingTask(
            self.name,
            self.configId,
            self.interval,
            self.config,
        )
        return task

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None    

class CmdPingTask(ZenStatus.PingTask):
    interface.implements(ZenStatus.interfaces.IPingTask)

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to ping the device and any of its interfaces.
        @rtype: Twisted deferred object
        """
        self.resetPingResult()
        return self._pingIp()

    @defer.inlineCallbacks
    def _pingIp(self):
 
        maxTries = self.config.tries
        attempts = 0
        exitCode = -1
        timestamp = None
        while attempts < maxTries:
            attempts += 1
            cmd, args = _getPingCmd(ip=self.config.ip, version=self.config.ipVersion, 
                ttl=64, timeout=float(self._preferences.pingTimeOut), 
		datalength=self._daemon.options.dataLength)
            log.debug("%s %s", cmd, " ".join(args))
            timestamp = time.time()
            out, err, exitCode = yield utils.getProcessOutputAndValue(cmd, args)
            pingResult = PingResult(self.config.ip, exitCode, out, timestamp)
            self.logPingResult(pingResult)
            if not self.config.points and exitCode == 0:
                # if there are no datapoints to store
                # and there is at least 1 ping up, then go on
                break

        if self.isUp:
            log.debug("%s is up!", self.config.ip)
            self.sendPingUp()
        else:
            log.debug("%s is down", self.config.ip)
            self.sendPingDown()
        self.storeResults()

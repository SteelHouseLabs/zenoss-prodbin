#!/usr/bin/env python2.1

#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__=''' ZenPing

Determines the availability of an IP address using ping.

$Id$'''

__version__ = "$Revision$"[11:-2]

from socket import gethostbyname, getfqdn, gaierror

import time
import sys

import Globals # make zope imports work

from AsyncPing import Ping
import pingtree

from Products.ZenEvents.ZenEventClasses import AppStart, AppStop, DNSFail
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenUtils.ZCmdBase import ZCmdBase

from twisted.internet import reactor, defer

class ZenPing(ZCmdBase):

    agent = "ZenPing"
    eventGroup = "Ping"

    pathcheckthresh = 10
    timeOut = 1.5
    tries = 2
    chunk = 75
    cycleInterval = 60
    configCycleInterval = 20*60
    maxFailures = 2
    pinger = None
    pingTreeIter = None
    startTime = None
    jobs = 0
    reconfigured = True

    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        self.failed = {}
        self.hostname = getfqdn()
        self.configpath = self.options.configpath
        if self.configpath.startswith("/"):
            self.configpath = self.configpath[1:]
        self.configCycleInterval = 0

        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=getfqdn(), 
                               eventClass=AppStart, 
                               summary="zenping started",
                               severity=0,
                               component="zenping"))
        self.log.info("started")

    def sendEvent(self, evt):
        "wrapper for sending an event"
        self.zem.sendEvent(evt)

    def sendPingEvent(self, pj):
        "Send an event based on a ping job to the event backend."
        evt = Event(device=pj.hostname, 
                    component="icmp", 
                    ipAddress=pj.ipaddr, 
                    summary=pj.message, 
                    severity=pj.severity,
                    eventClass=PingStatus,
                    eventGroup=self.eventGroup, 
                    agent=self.agent, 
                    manager=self.hostname)
        evstate = getattr(pj, 'eventState', None)
        if evstate is not None: evt.eventState = evstate
        self.sendEvent(evt)

    def loadConfig(self):
        "get the config data"
        reactor.callLater(self.configCycleInterval, self.loadConfig)

        self.dmd._p_jar.sync()
        changed = False
        smc = self.dmd.unrestrictedTraverse(self.configpath)
        for att in ("timeOut", "tries", "chunk",
                    "cycleInterval", "configCycleInterval",
                    "maxFailures",):
            before = getattr(self, att)
            after = getattr(smc, att)
            setattr(self, att, after)
            if not changed:
                changed = before != after
        self.configCycleInterval *= 60
        me = None
        if self.options.name:
            me = self.dmd.Devices.findDevice(self.options.name)
            self.log.info("device %s not found trying %s", 
                          self.options.name, self.hostname)
        else:
            me = self.dmd.Devices.findDevice(self.hostname)
        if me: 
            self.log.info("building pingtree from %s", me.id)
            self.pingtree = pingtree.buildTree(me)
        else:
            self.log.critical("ZenPing '%s' not found,"
                              "ignoring network topology.",self.hostname)
            self.pingtree = pingtree.Rnode(findIp(), self.hostname, 0)
        devices = smc.getPingDevices()
        self.prepDevices(devices)


    def prepDevices(self, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            status = device.getStatus(PingStatus, state=2)
            self.failed[device.getManageIp()] = status
            if device.monitorDevice() and not device.zPingMonitorIgnore:
                self.pingtree.addDevice(device)
        reconfigured = True


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--configpath',
                               dest='configpath',
                               default="Monitors/StatusMonitors/localhost",
                               help="path to our monitor config ie: "
                               "/Monitors/StatusMonitors/localhost")
        self.parser.add_option('--name',
                               dest='name',
                               help=("name to use when looking up our "
                                     "record in the dmd "
                                     "defaults to our fqdn as returned "
                                     "by getfqdn"))


    def pingCycle(self):
        "Start a new run against the ping job tree"
        reactor.callLater(self.cycleInterval, self.pingCycle)

        if self.pingTreeIter == None:
            self.start = time.time()
            self.jobs = 0
            self.pingTreeIter = self.pingtree.pjgen()
        while self.pinger.jobCount() < self.chunk and self.startOne():
            pass


    def startOne(self):
        "Initiate the next ping job"
        if not self.pingTreeIter:
            return False
        while 1:
            try:
                pj = self.pingTreeIter.next()
                failures = self.failed.get(pj.ipaddr, 0)
                if failures < self.maxFailures or self.reconfigured:
                    self.ping(pj)
                    return True
            except StopIteration:
                self.pingTreeIter = None
                return False

    def ping(self, pj):
        "Perform a ping"
        self.log.debug("starting %s", pj.ipaddr)
        pj.reset()
        self.pinger.sendPacket(pj)
        pj.deferred.addCallbacks(self.pingSuccess, self.pingFailed)
        
    def next(self):
        "Pull up the next ping job, which may throw StopIteration"
        self.jobs += 1
        self.startOne()
        if self.pinger.jobCount() == 0:
            self.endCycle()

    
    def endCycle(self, *unused):
        "Note the end of the ping list with a successful status message"
        self.sendHeartbeat()
        runtime = time.time() - self.start
        self.log.info("Finished pinging %d jobs in %.2f seconds",
                      self.jobs, runtime)
        self.reconfigured = False
        if not self.options.cycle:
            self.stop()

    def sendHeartbeat(self):
        'Send a heartbeat event for this monitor.'
        timeout = self.cycleInterval*3
        evt = EventHeartbeat(getfqdn(), "zenping", timeout)
        self.sendEvent(evt)

    def pingSuccess(self, pj):
        "Callback for a good ping response"
        if self.failed.get(pj.ipaddr, 0) > 1:
            pj.severity = 0
            self.sendPingEvent(pj)
        self.log.debug('success %s', pj.ipaddr)
        self.failed[pj.ipaddr] = 0
        self.log.debug("Success %s %s", pj.ipaddr, self.failed[pj.ipaddr])
        self.next()

    def pingFailed(self, err):
        "Callback for a bad (no) ping response"
        pj = err.value
        self.log.debug('failure %s', pj.ipaddr)
        self.failed.setdefault(pj.ipaddr, 0)
        self.log.debug("Failed %s %s", pj.ipaddr, self.failed[pj.ipaddr])
        self.failed[pj.ipaddr] += 1
        status = self.failed[pj.ipaddr]
        if status == 1:         
            self.log.debug("first failure '%s'", pj.hostname)
            # if our path back is currently clear add our parent
            # to the ping list again to see if path is really clear
            # and then re-ping ourself.
            if not pj.checkpath():
                routerpj = pj.routerpj()
                if routerpj:
                    self.ping(routerpj)
                self.ping(pj)
        else:
            failname = pj.checkpath()
            if failname:
                pj.eventState = 2 # suppressed FIXME
                pj.message += (", failed at %s" % failname)
            self.log.warn(pj.message)
            self.sendPingEvent(pj)
            self.markChildrenDown(pj)
        
        self.next()

    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

    def start(self):
        "Get things going"
        self.loadConfig()
        self.pinger = Ping(self.tries, self.timeOut)
        self.pingCycle()

    def stop(self):
        "Support keyboard interrupt "
        self.log.info("stopping...")
        self.sendEvent(Event(device=getfqdn(), 
                               eventClass=AppStop, 
                               summary="zenping stopped",
                               severity=4, component="zenping"))
        reactor.stop()

    def markChildrenDown(self, pj):
        """If this is a router PingJob, mark all Nodes
        away from the ping monitor as down"""

        # unfortunately there's no mapping from pj to router, so find it
        routers = []
        def recurse(node):
            if routers: return
            if node.pj == pj:
                routers.append(pj)
            for c in node.children:
                recurse(c)
        recurse(self.pingtree)
        if not routers: return
        assert len(routers) == 1
        children = routers[0].pjgen()
        children.next()                 # skip self
        for pj in children:
            pj.eventState = 2           # suppress
            self.sendPingEvent(pj)


        

def findIp():
    try:
        return gethostbyname(getfqdn())
    except gaierror:
        # find the first non-loopback interface address
        import os
        import re
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
    if sys.platform == 'win32':
        time.time = time.clock
    pm = ZenPing()
    pm.start()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    reactor.run(installSignalHandlers=False)
    pm.log.info("stopped")

#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''ZenPerformanceFetcher

Gets snmp performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import socket
import time
import pprint

from sets import Set

import Globals

from twisted.internet import reactor, defer

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol

DEFAULT_URL = 'http://localhost:8080/zport/dmd/Monitors/Cricket/localhost'
EVENT_URL = 'http://localhost:8080/zport/dmd/ZenEventManager'
SAMPLE_CYCLE_TIME = 5*60
CONFIG_CYCLE_TIME = 20*60
MAX_OIDS_PER_REQUEST = 200
MAX_SNMP_REQUESTS = 100

COMMON_EVENT_INFO = {
    'device':socket.getfqdn(),
    'component':'zenperfsnmp',
    }

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def rrdPath(branch):
    'compute where the RDD perf files should go'
    root = os.path.join(os.getenv('ZENHOME'), 'perf')
    r = os.path.join(root, branch[1:] + '.rrd')
    return r

class ZenPerformanceFetcher(ZenDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    startevt = {'eventClass':'/App/Start', 'summary': 'started', 'severity': 0}
    stopevt = {'eventClass':'/App/Stop', 'summary': 'stopped', 'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat'}
    for event in [startevt, stopevt, heartbeat]:
        event.update(COMMON_EVENT_INFO)


    def __init__(self):
        ZenDaemon.__init__(self)
        self.model = self.buildProxy(self.options.zopeurl)
        self.proxies = {}
        self.snmpPort = snmpprotocol.port()
        self.queryWorkList = Set()
        self.zem = self.buildProxy(self.options.zem)
        self.configLoaded = defer.Deferred()
        self.configLoaded.addCallbacks(self.readDevices, self.quit)
        self.unresponsiveDevices = Set()
        self.devicesRead = None

    def buildOptions(self):
        ZenDaemon.buildOptions(self)

        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server",
            default=DEFAULT_URL)
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("-p", "--zopepassword", dest="zopepassword")
        self.parser.add_option("--debug", dest="debug", action='store_true')
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance",
            default=EVENT_URL)

    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        url = basicAuthUrl(self.options.zopeusername,
                           self.options.zopepassword,
                           url)
        return AuthProxy(url)


    def sendEvent(self, event):
        'convenience function for pushing events to the Zope server'
        self.zem.callRemote('sendEvent', event).addErrback(self.log.debug)


    def startFetchUnresponsiveDevices(self, devices):
        "start fetching the devices that are unresponsive"
        proxy = self.buildProxy(self.options.zem)
        d = proxy.callRemote('getWmiConnIssues')
        d.addCallbacks(self.setUnresponsiveDevices, self.log.error)
        return d


    def setUnresponsiveDevices(self, deviceList):
        "remember all the unresponsive devices"
        self.log.debug('Unresponsive devices: %r' % deviceList)
        self.unresponsiveDevices = Set([d[0] for d in deviceList])

    def cycle(self, seconds, callable):
        "callLater if we should be cycling"
        if self.options.daemon or self.options.cycle:
            return reactor.callLater(seconds, callable)
        reactor.stop()


    def startUpdateConfig(self):
        'Periodically ask the Zope server for the device list.'
        deferred = self.model.callRemote('cricketDeviceList', True)
        deferred.addCallbacks(self.updateConfig, self.log.debug)
        self.cycle(CONFIG_CYCLE_TIME, self.startUpdateConfig)


    def updateConfig(self, deviceList):
        '''Update the list of devices, and initiate a request
        to get the device configuration'''
        self.log.debug('Configured %d devices' % len(deviceList))
        lst = []
        for device in deviceList:
            self.log.debug("load config for %s", device)
            lst.append(self.startDeviceConfig(device))
        lst.append(self.startFetchUnresponsiveDevices(deviceList))
        if not self.configLoaded.called:
            defer.DeferredList(lst).chainDeferred(self.configLoaded)
            
        if not deviceList: self.log.warn("no devices found")
        # stop collecting those no longer in the list
        for device in self.proxies.values():
            if device.url not in deviceList:
                self.log.debug('removing device %s' % device)
                del self.proxies[device]
                # we could delete the RRD files, too


    def startDeviceConfig(self, deviceUrl):
        'Kick off a request to get the configuration of a device'
        proxy = self.buildProxy(deviceUrl)
        d = proxy.callRemote('getSnmpOidTargets')
        d.addCallbacks(self.updateDeviceConfig, self.log.error, (deviceUrl,) )
        return d


    def updateDeviceConfig(self, snmpTargets, url):
        'Save the device configuration and create an SNMP proxy to talk to it'
        deviceName, ip, port, community, oidData = snmpTargets
        self.log.debug("received config for %s", deviceName)
        p = self.proxies.get(deviceName, None)
        if p is None:
            p = AgentProxy(ip=ip, port=port, community=community,
                           protocol=self.snmpPort.protocol, allowCache=True)
            p.url = url
        p.badOidMode = False
        p.oidMap = {}
        for oid, path, dsType in oidData:
            p.oidMap[oid] = path, dsType
        self.proxies[deviceName] = p


    def readDevices(self, ignored=None):
        'Periodically fetch the performance values from all known devices'
        self.log.debug('readingDevices')
        # limit the number of devices we query at once to avoid
        # a UDP packet storm
        if self.queryWorkList:
            self.log.warning("There are still %d devices to query, "
                             "waiting for them to finish" %
                             len(self.queryWorkList))
        else:
            self.queryWorkList =  Set(self.proxies.keys())
            self.queryWorkList -= self.unresponsiveDevices
            self.startTime = time.time()
            self.devcount = len(self.queryWorkList)
            lst = []
            for i in range(MAX_SNMP_REQUESTS):
                if not self.queryWorkList: break
                lst.append(self.startReadDevice(self.queryWorkList.pop()))
            self.devicesRead = defer.DeferredList(lst, consumeErrors=1)
            self.devicesRead.addCallback(self.reportRate)
        self.cycle(SAMPLE_CYCLE_TIME, self.readDevices)

    def reportRate(self, *ignored):
        self.sendEvent(self.heartbeat)
        runtime = time.time() - self.startTime
        self.log.info("collected %d devices in %.2f", 
                      self.devcount, runtime)

    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        lst = []
        if proxy.badOidMode:
            # creep through oids to find the bad oid
            for oid in proxy.oidMap.keys():
                d = proxy.get([oid])
                d.addCallback(self.noticeBadOid, deviceName, oid)
                lst.append(d)
        else:
            # ensure that the request will fit in a packet
            for part in chunk(proxy.oidMap.keys(), MAX_OIDS_PER_REQUEST):
                lst.append(proxy.get(part))
        d = defer.DeferredList(lst, consumeErrors=1)
        d.addCallbacks(self.storeValues,
                       self.finishDevices,
                       (deviceName,))
        return d

    def noticeBadOid(self, result, deviceName, oid):
        'Remove Oids that return empty responses'
        proxy = self.proxies.get(deviceName, None)
        if proxy is None: return
        if not result:
            self.log.error('Bad oid %s found for device %s' % (oid, deviceName))
            del proxy.oidMap[oid]
            return (False, result)
        return (True, result)


    def finishDevices(self, error=None):
        'work down the list of devices'
        if error:
            self.log.error(error)
        if self.queryWorkList:
            self.devicesRead.addDeferred(
                self.startReadDevice(self.queryWorkList.pop())
                )

    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'
        self.log.debug('storeValues %r' % deviceName)
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # bad oid in request
        if proxy.badOidMode:
            # bad scan complete, clear the flag
            proxy.badOidMode = False
            return
        for success, update in updates:
            if success:
                if not update:
                    proxy.badOidMode = True
                for oid, value in update.items():
                    # oids start with '.' coming back from the client
                    path, dsType = proxy.oidMap[oid.strip('.')]
                    self.storeRRD(path, dsType, value)
        if proxy.badOidMode:
            self.queryWorkList.add(deviceName)
        self.finishDevices()


    def storeRRD(self, path, type, value):
        'store a value into an RRD file'
        import rrdtool
        filename = rrdPath(path)
        if not os.path.exists(filename):
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            dataSource = 'DS:%s:%s:%d:0:U' % ('ds0',type,3*SAMPLE_CYCLE_TIME)
            rrdtool.create(filename,
                           "--step",  str(SAMPLE_CYCLE_TIME),
                           dataSource,
                           'RRA:AVERAGE:0.5:1:600',
                           'RRA:AVERAGE:0.5:6:600',
                           'RRA:AVERAGE:0.5:24:600',
                           'RRA:AVERAGE:0.5:288:600',
                           'RRA:MAX:0.5:288:600')
        try:
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            self.log.error('rrd error %s' % err)


    def quit(self, error):
        'stop the reactor if an error occured on the first config load'
        print >>sys.stderr, error
        reactor.stop()


    def main(self):
        global SAMPLE_CYCLE_TIME, CONFIG_CYCLE_TIME
        "Run forever, fetching and storing"

        if self.options.debug:
            SAMPLE_CYCLE_TIME /= 60
            CONFIG_CYCLE_TIME /= 60

        self.heartbeat['timeout'] = SAMPLE_CYCLE_TIME * 3
        self.sendEvent(self.startevt)
        
        zpf.startUpdateConfig()
        reactor.run()
        
        self.sendEvent(self.stopevt)

if __name__ == '__main__':
    zpf = ZenPerformanceFetcher()
    zpf.main()

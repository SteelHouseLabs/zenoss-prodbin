#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""DataCollector

Collects data from devices and puts it into objects in the DMD
data is passed through 3 queues in this system:

self.devices -> self.clients -> self.deviceMaps

self.devices is a list of DMD devices on which we will collect
self.clients is the list of active CollectorClients
self.deviceMaps is the list of results received from remote devices

$Id: DataCollector.py,v 1.8 2003/12/18 23:07:44 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

import sys
import os
import time
import types
import Queue
import re

import Globals
import transaction
import DateTime
from twisted.internet import reactor
from pysnmp.error import PySnmpError

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import importClass

from SnmpSession import SnmpSession, ZenSnmpError
from ApplyDataMap import ApplyDataMap, ApplyDataMapThread
import SshClient
import TelnetClient
import SnmpClient

from Exceptions import *

defaultParallel = 10
defaultProtocol = "ssh"
defaultPort = 22


pluginskip = ("CollectorPlugin.py", "DataMaps.py")
def plfilter(f):
    return f.endswith(".py") and not (f.startswith("_") or f in pluginskip)

class DataCollector(ZCmdBase):
    
    def __init__(self, noopts=0,app=None,single=False,threaded=True):
        ZCmdBase.__init__(self,noopts,app)
        
        self.single = single
        self.threaded = threaded
        self.cycletime = self.options.cycletime*60
        self.collage = self.options.collage / 1440.0
        self.clients = 0
        self.collectorPlugins = {} 
        self.deviceMaps = {}
        self.devicegen = None
        self.running=False
        self.loadPlugins()
        if self.threaded and not self.single:
            self.log.info("starting apply in separate thread.")
            self.applyData = ApplyDataMapThread(self, self.getConnection())
            self.applyData.start()
        else:
            self.log.debug("in debug mode starting apply in main thread.")
            self.applyData = ApplyDataMap(self)
 

    def loadPlugins(self):
        """Load plugins from the plugin directory.
        """
        for key in filter(lambda x: x.startswith("plugins"), sys.modules):
            self.log.debug("clearing plugin %s", key)
            del sys.modules[key]
        pdir = os.path.join(os.path.dirname(__file__),"plugins")
        sys.path.append(pdir)
        lpdir = len(pdir)+1
        self.log.info("loading collector plugins from:%s", pdir)
        for path, dirname, filenames in os.walk(pdir):
            path = path[lpdir:]
            for filename in filter(plfilter, filenames):
                modpath = os.path.join(path,filename[:-3]).replace("/",".")
                self.log.debug("loading:%s", modpath)
                try:
                    const = importClass(modpath)
                    plugin = const()
                    if plugin.transport == "command":
                        self.collectorPlugins[plugin.command] = plugin
                    elif plugin.transport == "snmp":
                        self.collectorPlugins[plugin.name()] = plugin
                    else:
                        self.log.warn("skipped:%s unknown transport:%s", 
                                       plugin.name(), plugin.transport)
                except ImportError, e:
                    self.log.exception("problem loading plugin:%s",modpath)

    
    def selectPlugins(self, device, transport):
        """Build a list of active plugins for a device.  
        """
        tpref = getattr(device,'zTransportPreference', 'snmp')
        aqignore = getattr(device, 'zCollectorIgnorePlugins', "")
        aqcollect = getattr(device, 'zCollectorCollectPlugins', "")
        plugins = {}
        for plugin in self.collectorPlugins.values():
            pname = plugin.name()
            try:
                if not plugin.condition(device, self.log):
                    self.log.debug("condition failed %s on %s",pname,device.id)
                elif ((self.options.ignorePlugins 
                    and re.search(self.options.ignorePlugins, pname))
                    or (aqignore and re.search(aqignore, pname))):
                    self.log.debug("ignore %s on %s",pname, device.id)
                elif self.options.collectPlugins:
                    if (re.search(self.options.collectPlugins, pname) and
                        (not plugins.has_key(plugin.maptype) 
                        or plugins[plugin.maptype].transport != tpref)):
                        self.log.debug("--collect %s on %s", pname, device.id)
                        plugins[plugin.maptype] = plugin
                elif aqcollect and re.search(aqcollect, pname): 
                    if (not plugins.has_key(plugin.maptype) 
                        or plugins[plugin.maptype].transport != tpref):
                        self.log.debug("zCollect %s on %s", pname, device.id)
                        plugins[plugin.maptype] = plugin
                elif not (self.options.collectPlugins or aqcollect):
                    if (not plugins.has_key(plugin.maptype) 
                        or plugins[plugin.maptype].transport != tpref):
                        self.log.debug("collect %s on %s", pname, device.id)
                        plugins[plugin.maptype] = plugin
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("failed to select plugin %s", pname)
        return [ p for p in plugins.values() if p.transport == transport ]
             
   
    
    def collectDevices(self, deviceroot):
        """Main processing loop collecting command data from devices.
        """
        if type(deviceroot) == types.StringType:
            deviceroot = self.dmd.Devices.getOrganizer(deviceroot)
        self.devicegen = deviceroot.getSubDevicesGen()
        for i, device in enumerate(self.devicegen):
            if i >= self.options.parallel: break
            client = self.collectDevice(device)
        if i > 0: 
            self.log.debug("reactor start multi-device")
            #self.reactorLoop()
            reactor.run(False)
        else: self.log.warn("no valid clients found")
            
  
    def resolveDevice(self, device):
        """If device is a string look it up in the dmd.
        """
        if type(device) == types.StringType:
            dname = device
            device = self.dmd.Devices.findDevice(device)
            if not device: 
                raise DataCollectorError("device %s not found" % dname)
        return device


    def collectDevice(self, device):
        """Collect data from a single device.
        """
        device = self.resolveDevice(device)
        cmdclient = self.cmdCollect(device)
        snmpclient = self.snmpCollect(device)
        if cmdclient: 
            cmdclient.run()
            self.clients += 1
        if snmpclient: 
            snmpclient.run()
            self.clients += 1
        if self.single and (cmdclient or snmpclient):
            self.log.debug("reactor start single-device")
            #self.reactorLoop(timeout=120)
            reactor.run(False)


    def cmdCollect(self, device):
        """Start command collection client.
        """
        client = None
        hostname = device.id
        plugins = self.selectPlugins(device,"command")
        commands = map(lambda x: x.command, plugins)
        if not commands:
            self.log.warn("no cmd plugins found for %s" % hostname)
            return 
        protocol = getattr(device, 'zCommandProtocol', defaultProtocol)
        commandPort = getattr(device, 'zCommandPort', defaultPort)
        if protocol == "ssh": 
            client = SshClient.SshClient(hostname, commandPort, 
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self)
            self.log.info('ssh collection device %s' % hostname)
        elif protocol == 'telnet':
            if commandPort == 22: commandPort = 23 #set default telnet
            client = TelnetClient.TelnetClient(hostname, commandPort,
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self)
            self.log.info('telnet collection device %s' % hostname)
        else:
            self.log.warn("unknown protocol %s for device %s",protocol,hostname)
        if not client: 
            self.log.warn("cmd client creation failed")
        else:
            self.log.info("plugins: %s", 
                ", ".join(map(lambda p: p.name(), plugins)))
        return client

    
    def snmpCollect(self, device):
        """Start snmp collection client.
        """
        client = None
        plugins = []
        hostname = device.id
        plugins = self.selectPlugins(device,"snmp")
        if not plugins:
            self.log.warn("no snmp plugins found for %s" % hostname)
            return 
        #if (self.checkCollection(device) or 
        #    self.checkCiscoChange(device, community, port)):
        if self.checkCollection(device):
            self.log.info('snmp collection device %s' % hostname)
            self.log.info("plugins: %s", 
                ", ".join(map(lambda p: p.name(), plugins)))
            client = SnmpClient.SnmpClient(device.id, self.options, 
                                            device, self, plugins)
                                        
        if not client or not plugins: 
            self.log.warn("snmp client creation failed")
            return
        return client


    def checkCollection(self, device):
        age = device.getSnmpLastCollection()+self.collage
        if device.getSnmpStatusNumber() > 0 and age >= DateTime.DateTime():
            self.log.info("skipped collection of %s" % device.getId())
            return False
        return True


    def checkCiscoChange(self, device, community, port):
        """Check to see if a cisco box has changed.
        """
        if self.options.force: return True
        snmpsess = SnmpSession(device.id, community=community, port=port)
        if not device.snmpOid.startswith(".1.3.6.1.4.1.9"): return True
        lastpolluptime = device.getLastPollSnmpUpTime()
        self.log.debug("lastpolluptime = %s", lastpolluptime)
        try:
            lastchange = snmpsess.get('.1.3.6.1.4.1.9.9.43.1.1.1.0').values()[0]
            self.log.debug("lastchange = %s", lastchange)
            if lastchange == lastpolluptime: 
                self.log.info(
                    "skipping cisco device %s no change detected", device.id)
                return False
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except (ZenSnmpError, PySnmpError): pass
        return True


    def clientFinished(self, collectorClient):
        """Callback that processes the return values from a device. 
        """
        try:
            nodevices = False
            self.log.debug("client for %s finished collecting",
                            collectorClient.hostname)
            device = collectorClient.device
            self.applyData.processClient(device, collectorClient)
            try:
                if not self.devicegen: raise StopIteration
                device = self.devicegen.next()
                self.collectDevice(device)
            except StopIteration:
                nodevices = True
        finally:
            self.clients -= 1
            self.log.debug("clients=%s nodevices=%s",self.clients,nodevices)
            if self.clients <= 0 and nodevices: 
                self.log.debug("reactor stop")
                #self.running = False
                reactor.stop()


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--debug',
                dest='debug', action="store_true",
                help="don't fork threads for processing")
        self.parser.add_option('--parallel', dest='parallel', 
                type='int', default=defaultParallel,
                help="number of devices to collect from in parallel")
        self.parser.add_option('--cycletime',
                dest='cycletime',default=60,type='int',
                help="run collection every x minutes")
        self.parser.add_option('--ignore',
                dest='ignorePlugins',default="",
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('--collect',
                dest='collectPlugins',default="",
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path', dest='path',
                help="start path for collection ie /NetworkDevices")
        self.parser.add_option('-d', '--device', dest='device',
                help="fully qualified device name ie www.confmon.com")
        self.parser.add_option('-a', '--collage',
                dest='collage', default=0, type='int',
                help="don't collect from devices whos collect date " +
                        "is with in this many minutes")
        self.parser.add_option('--writetries',
                dest='writetries',default=2,type='int',
                help="number of times to try to write if a "
                     "readconflict is found")
        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true',
                    help="force collection of config data " 
                         "(even without change to the device)")
        TelnetClient.buildOptions(self.parser, self.usage)
    

    
    def processOptions(self):
        if not self.options.path and not self.options.device:
            raise SystemExit("no device or path specified must have one!")
        if self.options.ignorePlugins and self.options.collectPlugins:
            raise SystemExit("--ignore and --collect are mutually exclusive")


    def reactorLoop(self, timeout=0, seltime=1):
        """Our own reactor loop so we can control timeout.
        """
        start = time.time()
        self.log.debug("starting reactor loop timeout=%s", timeout)
        reactor.startRunning(installSignalHandlers=False)
        self.running=True
        while self.running:
            try:
                if timeout and start + timeout < time.time(): 
                    self.log.error("reactor loop timeout")
                    break
                reactor.runUntilCurrent()
                t2 = reactor.timeout()
                t = reactor.running and t2
                reactor.doIteration(seltime)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected error in reactorLoop")
        #import pdb
        #pdb.set_trace()
        reactor.stop()
        self.log.debug("ended reactor loop runtime=%s", time.time()-start)

    
    def mainLoop(self):
        while 1:
            startLoop = time.time()
            runTime = 0
            try:
                try:
                    self.log.info("starting collector loop")
                    self.app._p_jar.sync()
                    self.collectDevices(self.options.path)
                    self.log.info("ending collector loop")
                finally:
                    transaction.abort()
                runTime = time.time()-startLoop
                self.log.info("loop time = %0.2f seconds",runTime)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("problem in main loop")
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)


    def sigTerm(self, signum, frame):
        self.stop()
        ZCmdBase.sigTerm(self, signum, frame)


    def stop(self):
        """Stop DataCollector make sure reactor is stopped, join with 
        applyData thread and close the zeo connection.
        """
        self.log.info("stopping...")
        self.running = False
        self.applyData.stop()
        self.closedb()


    def main(self):
        if self.options.device:
            self.single = True
            self.collectDevice(self.options.device)
        elif not self.options.cycle:
            self.collectDevices(self.options.path)
        else:
            self.mainLoop()
        self.stop()
                    

if __name__ == '__main__':
    dc = DataCollector()
    dc.processOptions()
    dc.main()

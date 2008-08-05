###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import types
import pywintypes

import Globals
from Products.ZenWin.WinCollector import WinCollector
from Products.ZenEvents.ZenEventClasses import \
     Status_WinService, Status_Wmi

from Products.ZenEvents import Event

from Products.ZenUtils.Driver import drive
from Products.ZenHub.PBDaemon import FakeRemote

from twisted.internet import reactor
from twisted.internet.defer import DeferredList

from Products.ZenWin.WMIClient import WMIClient

class Client:

    def __init__(self, proxy, device, plugins):
        self.proxy = proxy
        self.plugins = plugins
        self.results = []
        
    def query(self, queries):
        return self.proxy.query(queries)

    def getResults(self):
        return self.results


class zenwinmodeler(WinCollector):
    
    evtClass = Status_WinService
    name = agent = "zenwinmodeler"
    evtAlertGroup = "ServiceTest"
    winmodelerCycleInterval = 20*60
    attributes = WinCollector.attributes + ('winmodelerCycleInterval',)
    initialServices = WinCollector.initialServices + ['ModelerService',]


    def __init__(self):
        WinCollector.__init__(self)
        self.lastRead = {}
        self.client = None
        self.collectorPlugins = {}


    def selectPlugins(self, device, transport):
        """Build a list of active plugins for a device.  
        """
        plugins = [loader.create() for loader in device.plugins]
        result = []
        for plugin in plugins:
            if plugin.transport != transport:
                continue
            pname = plugin.name()
            self.log.debug("using %s on %s",pname, device.getId())
            result.append(plugin)
            self.collectorPlugins[pname] = plugin
        return result


    def config(self):
        "Get the ModelerService"
        return self.services.get('ModelerService', FakeRemote())


    def fetchDevices(self, driver):
        if self.options.device:
            self.log.info("Fetching a single device config for %s" % \
                self.options.device)
            yield self.configService().callRemote(
                'getDeviceConfigAndWinServices', [self.options.device])
        else:
            self.log.info("Fetching device configs for %s" % \
                self.options.monitor)
            yield self.config().callRemote('getDeviceListByMonitor',
                                       self.options.monitor)
            yield self.configService().callRemote(
                'getDeviceConfigAndWinServices', driver.next())
        
        self.updateDevices(driver.next())


    def collectDevice(self, device):
        """Collect the service info and build datamap using WMI.
        """
        if device.zWinUser == '':
            self.sendEvent(dict(eventClass=Status_Wmi,
                                device=device.id,
                                agent=self.agent,
                                component=self.name,
                                severity=Event.Warning,
                                summary=
                                "You must set the zProperties "
                                "zWinPassword and zWinUser "))
            return
        hostname = device.getId()
        self.client = None
        try:
            plugins = []
            plugins = self.selectPlugins(device, "wmi")
            if not plugins:
                self.log.info("No WMI plugins found for %s" % hostname)
                return 
            if self.checkCollection(device):
                self.log.info('Device: %s' % hostname)
                self.log.info('User: %s' % device.zWinUser)
                self.log.info("Plugins: %s", 
                              ", ".join(map(lambda p: p.name(), plugins)))
                wmic = WMIClient(device)
                wmic.connect()
                self.client = Client(wmic, device, plugins)
            if not self.client or not plugins:
                self.log.warn("WMIClient creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except pywintypes.com_error, e:
            code,txt,info,param = e
            msg = self.printComErrorMessage(e)
            if msg:
                self.log.warning("WMI Com error: %s", msg)
            if info:
                wcode, source, descr, hfile, hcont, scode = info
            return
        except:
            self.log.exception("Error opening WMIClient")
            return
        try:
            for plugin in self.client.plugins:
                pluginName = plugin.name()
                self.log.debug("Sending queries for plugin: %s", pluginName)
                self.log.debug("Queries: %s" % str(plugin.queries().values()))

                try:
                    result = self.client.query(plugin.queries())
                    self.client.results.append((plugin, result))
                except pywintypes.com_error, e:
                    msg = self.printComErrorMessage(e)
                    self.log.warning("WMI Comm Error for plugin '%s': %s", pluginName, msg)
                    if not plugin.handleException(e, device, self.log):
                        raise

        finally:
            self.niceDoggie(self.cycleInterval())

    def checkCollection(self, device):
        if self.options.device and device.getId() != self.options.device:
            return False
        if self.lastRead.get(device.getId(), 0) > device.lastChange:
            self.log.info('Skipping collection of %s' % device.getId())
            return False
        return True
        

    def processClient(self, device):
        def doProcessClient(driver):
            self.log.debug("processing data for device %s", device.getId())
            devchanged = False
            maps = []
            for plugin, results in self.client.getResults():
                self.log.debug("processing plugin %s on device %s",
                               plugin.name(), device.getId())
                if not results: 
                    self.log.warn("plugin %s no results returned",
                                  plugin.name())
                    continue
                
                results = plugin.preprocess(results, self.log)
                datamaps = plugin.process(device, results, self.log)

                # allow multiple maps to be returned from a plugin
                if type(datamaps) not in \
                (types.ListType, types.TupleType):
                    datamaps = [datamaps,]
                if datamaps:
                    maps += [m for m in datamaps if m]

            if maps:
                self.log.info("ApplyDataMaps to %s" % device.getId())
                yield self.config().callRemote('applyDataMaps',device.getId(),maps)
                if driver.next():
                    devchanged = True

            if devchanged:
                self.log.info("Changes applied to %s" % device.getId())
            else:
                self.log.info("No changes detected on %s" % device.getId())

        return drive(doProcessClient)
    
    def processLoop(self):
        """For each device collect service info and send to server.
        """
        if not self.devices: return
        deferreds = []
        for device in self.devices:
            reactor.runUntilCurrent()
            try:
                if device.getId() in self.wmiprobs:
                    self.log.warn("skipping %s has bad wmi state",
                        device.getId())
                    continue
                self.collectDevice(device)
                if self.client:
                    d = self.processClient(device)
                    d.addErrback(self.error)
                    deferreds.append(d)
            except pywintypes.com_error, e:
                msg = self.printComErrorMessage(e)
                if not msg:
                    msg = "WMI connect error on %s" % (device.getId())
                    code, txt, info, param = e
                    wmsg = "%s: %s" % (abs(code), txt)
                    if info:
                        wcode, source, descr, hfile, hcont, scode = info
                        scode = abs(scode)
                        if descr: wmsg = descr.strip()
                    msg += " %d: %s" % (scode, wmsg)
                if msg.find('RPC_S_CALL_FAILED') >= 0:
                    # transient error, log it but don't create an event
                    self.log.exception('Ignoring: %s' % msg)
                else:
                    self.sendFail(device.getId(), msg)
            except:
                self.sendFail(device.getId())
        return DeferredList(deferreds)


    def error(self, why):
        self.log.error(why.getErrorMessage())

    def sendFail(self, name, msg=""):
        evtclass = Status_Wmi
        sev = Event.Warning
        if not msg:
            msg = "WMI connection failed %s" % name
            sev = Event.Error
        evt = dict(summary=msg,
                   eventClass=evtclass, 
                   device=name,
                   severity=sev,
                   agent=self.agent,
                   component=self.name)
        self.sendEvent(evt)
        self.log.exception(msg)
        self.failed = True

    def cycleInterval(self):
        return self.winmodelerCycleInterval


if __name__=='__main__':
    zw = zenwinmodeler()
    zw.run()

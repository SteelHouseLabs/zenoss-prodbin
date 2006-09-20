import socket
import logging
log = logging.getLogger("zen.SnmpClient")

from twisted.internet import reactor, error, defer
from twisted.python import failure
from twistedsnmp import snmpprotocol, agentproxy

import Globals

from Products.ZenUtils.IpUtil import isip
from Products.ZenUtils.Driver import drive

global defaultTries, defaultTimeout
defaultTries = 2
defaultTimeout = 1

DEFAULT_MAX_OIDS_BACK = 40

class SnmpClient(object):

    def __init__(self, hostname, ipaddr, options=None, device=None, 
                 datacollector=None, plugins=[]):
        global defaultTries, defaultTimeout
        self.hostname = hostname
        self.device = device
        self.options = options
        self.datacollector = datacollector
        self.plugins = plugins

        self._getdata = {}
        self._tabledata = {}

        community = getattr(device, 'zSnmpCommunity', "public")
        port = int(getattr(device, 'zSnmpPort', 161))
        snmpver = getattr(device, 'zSnmpVer', "v1")
        self.tries = int(getattr(device,'zSnmpTries', defaultTries))
        self.timeout = float(getattr(device,'zSnmpTimeout', defaultTimeout))

        srcport = snmpprotocol.port()
        self.proxy = agentproxy.AgentProxy(ipaddr, port, community, snmpver,
                                           protocol=srcport.protocol)


    def run(self):
        """Start snmp collection.
        """
        log.debug("timeout=%s, tries=%s", self.timeout, self.tries)
        drive(self.doRun).addBoth(self.clientFinished)


    def checkCiscoChange(self, driver):
        """Check to see if a cisco box has changed.
        """
        yield self.proxy.get(['.1.3.6.1.4.1.9.9.43.1.1.1.0'],
                             timeout=self.timeout,
                             retryCount=self.tries)
        lastpolluptime = device.getLastPollSnmpUpTime()
        self.log.debug("lastpolluptime = %s", lastpolluptime)
        try:
            lastchange = driver.next().values()[0]
            self.log.debug("lastchange = %s", lastchange)
            if lastchange == lastpolluptime: 
                self.log.info("skipping cisco device %s no change detected",
                              device.id)
                yield defer.success(False)
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except (ZenSnmpError, PySnmpError): pass
        yield defer.success(False)


    def doRun(self, driver):
        changed = True
        if not self.options.force and self.device.snmpOid.startswith(".1.3.6.1.4.1.9"):
            yield drive(self.checkCiscoChange)
            changed = driver.next()
        if changed:
            yield drive(self.collect)


    def collect(self, driver):
        for plugin in self.plugins:
            try:
                log.debug('running %s', plugin)
                pname = plugin.name()
                self._tabledata[pname] = {}
                log.debug("sending queries for plugin %s", pname)
                if plugin.snmpGetMap:
                    yield self.proxy.get(plugin.snmpGetMap.getoids(),
                                       timeout=self.timeout,
                                       retryCount=self.tries)
                    self._getdata[pname] = driver.next()
                for tmap in plugin.snmpGetTableMaps:
                    rowSize = len(tmap.getoids())
                    maxRepetitions = max(DEFAULT_MAX_OIDS_BACK / rowSize, 1)
                    yield self.proxy.getTable(tmap.getoids(),
                                              timeout=self.timeout,
                                              retryCount=self.tries,
                                              maxRepetitions=maxRepetitions)
                    self._tabledata[pname][tmap] = driver.next()
            except Exception, ex:
                trace = log.getException(ex)
                if not isinstance( ex, error.TimeoutError ):
                    log.error("""device %s plugin %s unexpected error: %s""",
                              self.hostname, pname, trace)


    def getResults(self):
        """Return data for this client in the form
        ((pname, (getdata, tabledata),)
        getdata = {'.1.2.4.5':"value",}
        tabledata = {tableMap : {'.1.2.3.4' : {'.1.2.3.4.1': "value",...}}} 
        """
        data = []
        for plugin in self.plugins:
            pname = plugin.name()
            getdata = self._getdata.get(pname,{})
            tabledata = self._tabledata.get(pname,{})
            if getdata or tabledata:
                data.append((pname, (getdata, tabledata)))
        return data 

    def clientFinished(self, *ignored):
        """tell the datacollector that we are all done"""
        log.info("snmp client finished collection for %s" % self.hostname)
        if self.datacollector:
            self.datacollector.clientFinished(self)
        else:
            reactor.stop()



def buildOptions(parser=None, usage=None):
    "build options list that both telnet and ssh use"
   
    if not usage:
        usage = "%prog [options] hostname[:port] oids"

    if not parser:
        from optparse import OptionParser
        parser = OptionParser(usage=usage, 
                                   version="%prog " + __version__)
  
    parser.add_option('--snmpCommunity',
                dest='snmpCommunity',
                default=defaultSnmpCommunity,
                help='Snmp Community string')


if __name__ == "__main__":
    import pprint
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(20)
    import sys
    sys.path.append("plugins")
    from plugins.zenoss.snmp.InterfaceMap import InterfaceMap
    ifmap = InterfaceMap()
    sc = SnmpClient("gate.confmon.loc", community="zentinel", plugins=[ifmap,])
    reactor.run()
    pprint.pprint(sc.getResults())

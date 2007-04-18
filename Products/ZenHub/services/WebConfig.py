#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''WebConfig

ZenHub service for handling zenweb configuration
'''

from PerformanceConfig import PerformanceConfig
import transaction
import logging
log = logging.getLogger("zenhub")

class WebConfig(PerformanceConfig):


    def __init__(self, dmd, instance):
        PerformanceConfig.__init__(self, dmd, instance)


    def remote_getPageChecks(self):
        pageChecks = []
        for dev in self.config.devices():
            dev = dev.primaryAq()
            pageChecks += self.getDevicePageChecks(dev)
        return pageChecks


    def getDevicePageChecks(self, dev):
        result = []
        log.debug('Getting pagechecks for %s' % dev.id)
        if not dev.monitorDevice():
            log.warn('Not monitoring %' % dev.id)
            return result
        for templ in dev.getRRDTemplates():
            dataSources = templ.getRRDDataSources('PAGECHECK')
            for ds in [d for d in dataSources if d.enabled]:
                points = [{'id': dp.id, 
                            #'path': '/'.join((dev.rrdPath(), dp.name())),
                            #'rrdType': dp.rrdtype,
                            #'rrdCmd': dp.createCmd,
                            #'minv': dp.rrdmin,
                            #'maxv': dp.rrdmax,
                            #'thesholds': threshs.get(dp.name(), []),
                            }
                            for dp in ds.getRRDDataPoints()]
                result.append({
                                'devId': dev.id,
                                'manageIp': dev.manageIp,
                                'timeout': dp.pagecheckTimeout,
                                'datasource': ds.id,
                                'datapoints': points,
                                'cycletime': ds.cycletime or '',
                                'compId': ds.component or '',
                                'eventClass': ds.eventClass or '',
                                'eventKey': ds.eventKey or ds.id,
                                'severity': ds.severity or 0,
                                'userAgent': ds.userAgent or '',
                                'initialUrl': ds.initialURL or '',
                                'command': ds.getCommand(dev) or '',
                                })
        log.debug('%s pagechecks for %s', len(result), dev.id)
        return result


    def getDeviceConfig(self, device):
        "How to get the config for a device"
        return self.getDevicePageChecks(device)


    def sendDeviceConfig(self, listener, config):
        "How to send the config to a device, probably via callRemote"
        return listener.callRemote('updateDeviceConfig', config)


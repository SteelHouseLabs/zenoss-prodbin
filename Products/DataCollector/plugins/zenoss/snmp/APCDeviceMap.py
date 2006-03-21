#################################################################
#
#   Copyright (c) 2006 Confmon Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetMap

class DellDeviceMap(SnmpPlugin):
    """Map mib elements from Dell Open Manage mib to get hw and os products.
    """

    maptype = "APCDeviceMap" 

    snmpGetMap = GetMap({ 
        '.1.3.6.1.4.1.318.1.1.1.1.1.1.0': 'setHWProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.3.0': 'setHWSerialNumber',
         })


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing dell device info on device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om

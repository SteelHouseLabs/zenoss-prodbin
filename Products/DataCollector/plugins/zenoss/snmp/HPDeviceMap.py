#################################################################
#
#   Copyright (c) 2006 Confmon Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetMap

class HPDeviceMap(SnmpPlugin):
    """Map mib elements from HP Insight Manager mib to get hw and os products.
    """

    maptype = "HPDeviceMap" 

    snmpGetMap = GetMap({ 
        '.1.3.6.1.4.1.232.2.2.4.2.0' : 'setHWProductKey',
        '.1.3.6.1.4.1.232.11.2.2.1.0': 'setOSProductKey',
         })



    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing HP device info on device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        if om.setOSProductKey and om.setOSProductKey.find("NetWare") > -1:
            delattr(om, 'setOSProductKey')
        return om

#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""InterfaceMap

InterfaceMap maps the interface and ip tables to interface objects

$Id: InterfaceMap.py,v 1.24 2003/10/30 18:42:19 edahl Exp $"""

__version__ = '$Revision: 1.24 $'[11:-2]

import transaction

from Products.ZenUtils.Utils import cleanstring

from CollectorPlugin import SnmpPlugin, GetTableMap

class CiscoHSRP(SnmpPlugin):

    maptype = "CiscoHSRP" 

    snmpGetTableMaps = (
        # HSRP Table
        GetTableMap('hsrpTable', '.1.3.6.1.4.1.9.9.106.1.2.1.1', 
                {
                '.11': 'vip',  # virtual ip ifindex is second to last id
                '.13': 'actip', # ip of active router
                #'.16': 'vmacaddress'
                 }
        ),
    )

    def condition(self, device, log):
        return device.getManufacturerName() == "Cisco"
        
   
    def process(self, device, results, log):
        """collect snmp information from this device
        """
        changed = False
        getdata, tabledata = results
        log.info('processing hsrp for device %s' % device.id)
        hsrptable = tabledata.get("hsrpTable")
        if not hsrptable: return
        nets = device.getDmdRoot("Networks")
        transaction.begin()
        for hsrp in hsrptable.values():
            actip = self.asip(hsrp['actip'])
            vip = self.asip(hsrp['vip'])
            actip = nets.findIp(actip)
            if not actip: 
                log.warn("active ip %s on device %s not found",actip,device.id)
                continue
            intr = actip.interface()
            if not intr:
                log.warn("active ip %s on device %s no interface", 
                          actip, device.id)
                continue
            intr = intr.primaryAq()
            vip = "%s/%s" % (vip, intr.netmask) 
            if vip not in intr.getIpAddresses():
                log.info("adding vip %s to device %s interface %s", 
                        vip, intr.getDeviceName(), intr.id)
                intr.addIpAddress(vip)
                changed = True
        if changed: transaction.commit()      
        else: transaction.abort()

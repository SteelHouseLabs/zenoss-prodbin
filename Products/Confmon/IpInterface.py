#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""IpInterface

IpInterface is a collection of devices and subsystems that make
up a business function

$Id: IpInterface.py,v 1.59 2004/04/23 03:01:02 edahl Exp $"""

__version__ = "$Revision: 1.59 $"[11:-2]

import re
import copy

from Globals import Persistent
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_parent
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship
from IpAddress import IpAddress, findIpAddress
from IpNetwork import addIpAddressToNetworks 
from Products.ZenUtils.IpUtil import *

from DeviceResultInt import DeviceResultInt
from ConfmonPropManager import ConfmonPropManager
from DeviceComponent import DeviceComponent
from PingStatusInt import PingStatusInt
from Products.Confmon.Exceptions import *

def manage_addIpInterface(context, id, REQUEST = None):
    """make a device"""
    d = IpInterface(id)
    context._setObject(id, d)
    d = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpInterface = DTMLFile('dtml/addIpInterface',globals())


class IpInterface(DeviceComponent, DeviceResultInt, PingStatusInt):
    """IpInterface object"""

    portal_type = meta_type = 'IpInterface'

    manage_editIpInterfaceForm = DTMLFile('dtml/manageEditIpInterface',
                                                        globals())
   
    # catalog to find interfaces that should be pinged
    # indexes are id and description
    default_catalog = 'interfaceSearch'
    
    _properties = (
                 {'id':'ips', 'type':'lines', 
                    'mode':'w', 'setter':'setIpAddresses'},
                 {'id':'name', 'type':'string', 'mode':'w'},
                 {'id':'ifindex', 'type':'string', 'mode':'w'},
                 {'id':'macaddress', 'type':'string', 'mode':'w'},
                 {'id':'type', 'type':'string', 'mode':'w'},
                 {'id':'description', 'type':'string', 'mode':'w'},
                 {'id':'mtu', 'type':'int', 'mode':'w'},
                 {'id':'speed', 'type':'long', 'mode':'w'},
                 {'id':'adminStatus', 'type':'int', 'mode':'w'},
                 {'id':'operStatus', 'type':'int', 'mode':'w'},
                )
   
    noPropertiesCopy = ('ips','macaddress')
   
    localipcheck = re.compile(r'^127.|^0.').search
    localintcheck = re.compile(r'^lo0').search
    
    factory_type_information = ( 
        { 
            'id'             : 'IpInterface',
            'meta_type'      : 'IpInterface',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpInterface_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addIpInterface',
            'immediate_view' : 'viewIpInterface',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewIpInterface'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ('View',)
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, title = None):
        DeviceComponent.__init__(self, id, title)
        self.ifindex = 0 
        self.name = ''
        self.macaddress = ""
        self.type = ""
        self.description = ""
        self.mtu = 0
        self.speed = 0
        self.adminStatus = 0
        self.operStatus = 0
        self._ipAddresses = []


    security.declareProtected('View', 'viewName')
    def viewName(self):
        """Use the unmagled interface name for display"""
        return self.name

    def primarySortKey(self):
        return self.name

    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'ips':
            self.setIpAddresses(value)
        else:    
            setattr(self,id,value)
            #if id == 'macaddress': self.index_object()
   

    def manage_editProperties(self, REQUEST):
        """override from propertiyManager so we can trap errors"""
        try:
            return ConfmonPropManager.manage_editProperties(self, REQUEST)
        except IpAddressError, e:
            return   MessageDialog(
                title = "Input Error",
                message = e.args[0],
                action = "manage_main")
 

    def __getattr__(self, name):
        if name == 'ip':
            return self.getIpAddress()
        if name == 'ips':
            return self.getIpAddresses()
        elif name == 'network':
            return self.getNetwork()
        elif name == 'networkName':
            n = self.getNetwork()
            if n:
                return n.id
            return None
        else:
            raise AttributeError, name

  
    def _prepIp(self, ip, netmask=24):
        """break ips in the format 1.1.1.1/24 into ip and netmask"""
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            checkip(ip)
            netmask = maskToBits(iparray[1])
        return ip, netmask
  

    def addIpAddress(self, ip, netmask=24):
        """add an ip to the ipaddresses relationship"""
        (ip, netmask) = self._prepIp(ip, netmask)

        #see if ip exists already and link it to interface
        ipobj = findIpAddress(self, ip)
        if ipobj:
            if hasattr(ipobj, 'interface'):
                dev = ipobj.getDevice()
                if dev and dev != self.device():
                    raise IpAddressConflict, \
                        "IP Address %s exists on device %s" % (ip, dev.getId())
                                
            self.addRelation('ipaddresses', ipobj)
        #never seen this ip make a new one in correct subnet
        else:  
            ipobj = addIpAddressToNetworks(self, ip, netmask)
            self.addRelation('ipaddresses', ipobj)
        ipobj = ipobj.primaryAq()
        ipobj.index_object()
  

    def addLocalIpAddress(self, ip, netmask=24):
        """store some ips locally (like loopback)"""
        (ip, netmask) = self._prepIp(ip, netmask)
        ip = ip + '/' + str(netmask)
        if not hasattr(self,'_ipAddresses'):
            self._ipAddresses = []
        if not ip in self._ipAddresses:
            self._ipAddresses.append(ip)


    def setIpAddresses(self, ips):
        """set the relationship with ipaddress must have aq to call this"""
        if type(ips) == type(''): ips = [ips,]
        if not ips:
            self.removeRelation('ipaddresses')
        else:
            ipids = self.ipaddresses.objectIdsAll()
            localips = copy.copy(self._ipAddresses)
            for ip in ips:
                if self.localipcheck(ip) or self.localintcheck(self.id):
                    if not ip in localips:
                        self.addLocalIpAddress(ip)
                    else:
                        localips.remove(ip)
                else:
                    #if not ipFromIpMask(ip) in ipids:
                    rawip = ipFromIpMask(ip)
                    ipmatch = filter(lambda x: x.find(rawip) > -1, ipids)
                    if not ipmatch:
                        self.addIpAddress(ip)
                    elif len(ipmatch) == 1:
                        ipids.remove(ipmatch[0])
                    else:
                        pass # THIS WOULD BE BAD!! -EAD

            #delete ips that are no longer in use
            for ip in ipids:
                ipobj = getattr(self.ipaddresses, ip)
                self.removeRelation('ipaddresses', ipobj)
            for ip in localips:
                self._ipAddresses.remove(ip)
   

    def removeIpAddress(self, ip):
        ipobj = getattr(self.ipaddresses, ip, None)
        self.removeRelation('ipaddresses', ipobj)

    
    def getIp(self):
        """return only the ip ie: 1.1.1.1"""
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIp()
        elif len(self._ipAddresses):
            return self._ipAddresses[0].split('/')[0]
        
   
    def getIpSortKey(self):
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].primarySortKey()
        elif len(self._ipAddresses):
            return numbip(self._ipAddresses[0].split('/')[0])


    def getIpAddress(self):
        """return the ipaddress with its netmask ie: 1.1.1.1/24"""
        if len(self.ipaddresses()):
            return self.ipaddresses()[0].getIpAddress()
        elif len(self._ipAddresses):
            return self._ipAddresses[0]


    def getIpAddresses(self):
        """get a list of the ips on this interface in the format 1.1.1.1/24"""
        retval=[]
        for ip in self.ipaddresses.objectValuesAll():
            retval.append(ip)
        if not hasattr(self,'_ipAddresses'):
            self._ipAddresses = []
        for ip in self._ipAddresses:
            retval.append(ip)
        return retval


    def getNetwork(self):
        """get the network for the first ip on this interface"""
        if self.ipaddress():
            return self.ipaddresses()[0].network()


    def getNetworkLink(self, target=None):
        """get the network link for the first ip on this interface"""
        if len(self.ipaddresses()):
            addr = self.ipaddresses.objectValuesAll()[0]
            if addr:
                if hasattr(aq_base(addr), 'network'):
                    return addr.network.getPrimaryLink(target)
        else:
            return ""
   

    def getNetworkLinks(self, target=None):
        """retun a list of network links for each ip in this interface"""
        if not hasattr(self,'_ipAddresses'):
            self._ipAddresses = []
        addrs = self.ipaddresses() + self._ipAddresses
        if addrs:
            links = []
            for addr in addrs: 
                if hasattr(aq_base(addr), 'network'):
                    links.append(addr.network.getPrimaryLink(target))
                else:
                    links.append("")
            return "<br/>".join(links)
        else:
            return ""


    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """return the name of this interface"""
        return self.name


    security.declareProtected('View', 'getInterfaceMacaddress')
    def getInterfaceMacaddress(self):
        """return the mac address of this interface"""
        return self.macaddress


    def getDevice(self):
        """support DeviceResultInt mixin class"""
        return self.device()

    
    def _getPingStatus(self):
        """get the first IpAddress on this interface for PingStatusInt"""
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0]._getPingStatus()


InitializeClass(IpInterface)

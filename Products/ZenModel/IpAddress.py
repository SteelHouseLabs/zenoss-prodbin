#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""IpAddress

IpAddress represents a device residing on an IP network.

$Id: IpAddress.py,v 1.42 2004/04/15 00:54:14 edahl Exp $"""

__version__ = "$Revision: 1.42 $"[11:-2]

import socket
import logging
log = logging.getLogger("zen.IpAddress")

#base classes for IpAddress
from ManagedEntity import ManagedEntity


from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.FindSupport import FindSupport
from Acquisition import aq_parent    

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.IpUtil import *
from Products.ZenUtils.Utils import getObjByPath

from Products.ZenModel.Exceptions import * 

def manage_addIpAddress(context, id, netmask=24, REQUEST = None):
    """make a IpAddress"""
    ip = IpAddress(id, netmask)
    context._setObject(ip.id, ip)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


def findIpAddress(context, ip):
    """find an ip from base. base should be Networks root found through aq"""
    searchCatalog = context.Networks.ipSearch
    ret = searchCatalog({'id':ip})
    if len(ret) > 1: 
        raise IpAddressConflict, "IP address conflict for IP: %s" % ip
    if ret:
        ipobj = getObjByPath(searchCatalog.getPhysicalRoot(), 
                            ret[0].getPrimaryId) 
        return ipobj


addIpAddress = DTMLFile('dtml/addIpAddress',globals())


class IpAddress(ManagedEntity):
    """IpAddress object"""
    event_key = portal_type = meta_type = 'IpAddress'

    default_catalog = 'ipSearch'

    _properties = (
        {'id':'netmask', 'type':'string', 'mode':'w', 'setter':'setNetmask'},
        {'id':'ptrName', 'type':'string', 'mode':'w'},
        )
    _relations = ManagedEntity._relations + (
        ("network", ToOne(ToManyCont,"IpNetwork","ipaddresses")),
        ("interface", ToOne(ToMany,"IpInterface","ipaddresses")),
        ("clientroutes", ToMany(ToOne,"IpRouteEntry","nexthop")),
        )

    factory_type_information = ( 
        { 
            'id'             : 'IpAddress',
            'meta_type'      : 'IpAddress',
            'description'    : """Ip Address Class""",
            'icon'           : 'IpAddress_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpAddress',
            'immediate_view' : 'viewIpAddressOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewIpAddressOverview'
                , 'permissions'   : ( "View", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, netmask=24):
        checkip(id)
        ManagedEntity.__init__(self, id)
        self._netmask = maskToBits(netmask)
        self.ptrName = None
        try:
            data = socket.gethostbyaddr(id)
            if data: self.ptrName = data[0]
        except socket.error, e:
            log.warn("%s: %s", id, e)


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """make sure that networks sort correctly"""
        return numbip(self.id)


    def setNetmask(self, value):
        self._netmask = maskToBits(value)


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'netmask':
            self.setNetmask(value)
        else:    
            setattr(self,id,value)


    def __getattr__(self, name):
        if name == 'netmask':
            return self._netmask
        else:
            raise AttributeError, name


    security.declareProtected('Change Device', 'setIpAddress')
    def setIpAddress(self, ip):
        """set the ipaddress can be in the form 1.1.1.1/24 to also set mask"""
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            self._netmask = maskToBits(iparray[1])
        checkip(ip)
        aqself = self.aq_primary() #set aq path
        network = aqself.aq_parent
        netip = getnetstr(ip, network.netmask)
        if netip == network.id:
            aqs.aq_parent._renameObject(aqs.id, ip)
        else:
            raise WrongSubNetError, \
                    "Ip %s is in a different subnet than %s" % (ip, self.id)
                    


    security.declareProtected('View', 'getIp')
    def getIp(self):
        """return only the ip"""
        return self.id


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self):
        """return the ip with its netmask in the form 1.1.1.1/24"""
        return self.id + "/" + str(self._netmask)


    def __str__(self):
        return self.getIpAddress()


    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        if self.interface():
            return self.interface().name
        return "No Interface"


    security.declareProtected('View', 'getNetworkName')
    def getNetworkName(self):
        if self.network():
            return self.network().getNetworkName()
        return "No Network"


    security.declareProtected('View', 'getNetworkUrl')
    def getNetworkUrl(self):
        if self.network():
            return self.network().absolute_url()
        return ""

    
    security.declareProtected('View', 'getDeviceUrl')
    def getDeviceUrl(self):
        """Get the primary url path of the device in which this ip
        is associated with.  If no device return url to the ip itself.
        """
        d = self.device()
        if d:
            return d.getPrimaryUrlPath()
        else:
            return self.getPrimaryUrlPath()


    def device(self):
        """Reuturn the device for this ip for DeviceResultInt"""
        int = self.interface()
        if int: return int.device()
        return None


    def manage_afterAdd(self, item, container):
        """setup relationshipmanager add object to index and build relations """
        if item == self: 
            self.index_object()


    def manage_afterClone(self, item):
        self.index_object()


    def manage_beforeDelete(self, item, container):
        if item == self or getattr(item, "_operation", -1) < 1: 
            ManagedEntity.manage_beforeDelete(self, item, container)
            self.unindex_object()


    def index_object(self):
        """interfaces use hostname + interface name as uid"""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.getId())
            
                                                
    def unindex_object(self):
        """interfaces use hostname + interface name as uid"""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.getId())


InitializeClass(IpAddress)

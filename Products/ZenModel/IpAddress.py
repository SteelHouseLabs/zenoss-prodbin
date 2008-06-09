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

from Products.ZenModel.Linkable import Layer3Linkable

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.IpUtil import *

from Products.ZenModel.Exceptions import *

def manage_addIpAddress(context, id, netmask=24, REQUEST = None):
    """make a IpAddress"""
    ip = IpAddress(id, netmask)
    context._setObject(ip.id, ip)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


addIpAddress = DTMLFile('dtml/addIpAddress',globals())


class IpAddress(ManagedEntity, Layer3Linkable):
    """IpAddress object"""
    event_key = portal_type = meta_type = 'IpAddress'

    default_catalog = 'ipSearch'

    _properties = (
        {'id':'netmask', 'type':'string', 'mode':'w', 'setter':'setNetmask'},
        {'id':'ptrName', 'type':'string', 'mode':'w'},
        )
    _relations = ManagedEntity._relations + (
        ("network", ToOne(ToManyCont,"Products.ZenModel.IpNetwork","ipaddresses")),
        ("interface", ToOne(ToMany,"Products.ZenModel.IpInterface","ipaddresses")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","nexthop")),
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
        #self.setPtrName()


    def setPtrName(self):
        try:
            data = socket.gethostbyaddr(self.id)
            if data: self.ptrName = data[0]
        except socket.error, e:
            self.ptrName = ""
            log.warn("%s: %s", self.id, e)


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
        aqself = self.primaryAq() #set aq path
        network = aqself.aq_parent
        netip = getnetstr(ip, network.netmask)
        if netip == network.id:
            network._renameObject(aqself.id, ip)
        else:
            raise WrongSubnetError, \
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
            return self.interface().name()
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
        """
        Device only propagates afterAdd if it is the added object.
        """
        super(IpAddress,self).manage_afterAdd(item, container)
        self.index_object()


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        super(IpAddress,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(IpAddress,self).manage_beforeDelete(item, container)
        self.unindex_object()

    def index_object(self):
        super(IpAddress, self).index_object()
        self.index_links()

    def deviceId(self):
        """
        The device id, for indexing purposes.
        """
        d = self.device()
        if d: return d.id
        else: return None

    def interfaceId(self):
        """
        The interface id, for indexing purposes.
        """
        i = self.interface()
        if i: return i.id
        else: return None

    def ipAddressId(self):
        """
        The ipAddress id, for indexing purposes.
        """
        return self.getPrimaryId()

    def networkId(self):
        """
        The network id, for indexing purposes.
        """
        n = self.network()
        if n: return n.getPrimaryId()
        else: return None

InitializeClass(IpAddress)

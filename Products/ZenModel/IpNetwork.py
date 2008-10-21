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

__doc__="""IpNetwork

IpNetwork represents an IP network which contains
many IP addresses.

$Id: IpNetwork.py,v 1.22 2004/04/12 16:21:25 edahl Exp $"""

__version__ = "$Revision: 1.22 $"[11:-2]

import math
import transaction
import logging
log = logging.getLogger('zen')

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import *

from Products.ZenUtils.IpUtil import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

from IpAddress import IpAddress
from DeviceOrganizer import DeviceOrganizer

from Products.ZenModel.Exceptions import *

from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader, executeCommand
from Products.ZenUtils.Utils import binPath, clearWebLoggingStream
from Products.ZenUtils import NetworkTree
from Products.ZenUtils.Utils import edgesToXML
from Products.ZenUtils.Utils import unused

def manage_addIpNetwork(context, id, netmask=24, REQUEST = None):
    """make a IpNetwork"""
    net = IpNetwork(id, netmask=netmask)
    context._setObject(net.id, net)
    if id == "Networks":
        net = context._getOb(net.id)
        net.buildZProperties()
        net.createCatalog()
        #manage_addZDeviceDiscoverer(context)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addIpNetwork = DTMLFile('dtml/addIpNetwork',globals())


# when an ip is added the defaul location will be
# into class A->B->C network tree
defaultNetworkTree = (32,)

class IpNetwork(DeviceOrganizer):
    """IpNetwork object"""
    
    isInTree = True

    buildLinks = True
    
    # Organizer configuration
    dmdRootName = "Networks"

    # Index name for IP addresses
    default_catalog = 'ipSearch'

    portal_type = meta_type = 'IpNetwork'

    _properties = (
        {'id':'netmask', 'type':'int', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        )
    
    _relations = DeviceOrganizer._relations + (
        ("ipaddresses", ToManyCont(ToOne, "Products.ZenModel.IpAddress", "network")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","target")),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "networks")),
        )
                   
    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'IpNetwork',
            'meta_type'      : 'IpNetwork',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpNetwork_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpNetwork',
            'immediate_view' : 'viewNetworkOverview',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewNetworkOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
          },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, netmask=24, description=''):
        if id.find("/") > -1: id, netmask = id.split("/",1)
        DeviceOrganizer.__init__(self, id, description)
        if id != "Networks":
            checkip(id)
        self.netmask = maskToBits(netmask)
        self.description = description

    
    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        if id.find("/") > -1: id, netmask = id.split("/",1)
        return super(IpNetwork, self).checkValidId(id, prep_id)
    
    
    def createNet(self, netip, netmask=24):
        """
        Return and create if necessary network.  netip is in the form
        1.1.1.0/24 or with netmask passed as parameter.  Subnetworks created
        based on the zParameter zDefaulNetworkTree.
        Called by IpNetwork.createIp and IpRouteEntry.setTarget
        """
        if netip.find("/") > -1: netip, netmask = netip.split("/",1)
        netmask = int(netmask)
        netroot = self.dmd.getDmdRoot("Networks")
        netobj = netroot.getNet(netip)
        if netobj and netobj.netmask == netmask: # Network already exists.
            return netobj
        if netmask == 0:
            raise ValueError("netip '%s' without netmask", netip)
        netip = getnetstr(netip,netmask)
        netTree = getattr(self, 'zDefaultNetworkTree', defaultNetworkTree)
        netTree = map(int, netTree)
        if netobj:
            # strip irrelevant values from netTree if we're not starting at /0
            netTree = [ m for m in netTree if m > netobj.netmask ]
        else:
            # start at /Networks if no containing network was found
            netobj = netroot

        for treemask in netTree:
            if treemask >= netmask:
                netobj = netobj.addSubNetwork(netip, netmask)
                break
            else:
                supnetip = getnetstr(netip, treemask)
                netobj = netobj.addSubNetwork(supnetip, treemask)
        return netobj


    def findNet(self, netip, netmask=0):
        """
        Find and return the subnet of this IpNetwork that matches the requested
        netip and netmask.
        """
        if netip.find("/") >= 0:
            netip, netmask = netip.split("/", 1)
            netmask = int(netmask)
        for subnet in [self] + self.getSubNetworks():
            if netmask == 0 and subnet.id == netip:
                return subnet
            if subnet.id == netip and subnet.netmask == netmask:
                return subnet
        return None


    def getNet(self, ip):
        """Return the net starting form the Networks root for ip.
        """
        return self._getNet(ip)


    def _getNet(self, ip):
        """Recurse down the network tree to find the net of ip.
        """
        for net in self.children():
            if net.hasIp(ip):
                if len(net.children()):
                    subnet = net._getNet(ip)
                    if subnet:
                        return subnet
                    else:
                        return net
                else:
                    return net


    def createIp(self, ip, netmask=24):
        """Return an ip and create if nessesary in a hierarchy of 
        subnetworks based on the zParameter zDefaulNetworkTree.
        """
        ipobj = self.findIp(ip)
        if ipobj: return ipobj
        netobj = self.createNet(ip, netmask)
        ipobj = netobj.addIpAddress(ip,netmask)
        return ipobj


    def freeIps(self):
        """Number of free Ips left in this network.
        """
        freeips = int(math.pow(2,32-self.netmask)-(self.countIpAddresses()))
        if self.netmask >= 31:
            return freeips 
        return freeips - 2


    def hasIp(self, ip):
        """Does network have (contain) this ip.
        """
        start = numbip(self.id)
        end = start + math.pow(2,32-self.netmask)
        return start <= numbip(ip) < end

        
    def fullIpList(self):
        """Return a list of all ips in this network.
        """
        if (self.netmask == 32): return [self.id]
        ipnumb = numbip(self.id)
        maxip = math.pow(2,32-self.netmask)
        start = int(ipnumb+1)
        end = int(ipnumb+maxip-1)
        return map(strip, range(start,end))
        

    def deleteUnusedIps(self):
        """Delete ips that are unused in this network.
        """
        for ip in self.ipaddresses():
            if ip.device(): continue
            self.ipaddresses.removeRelation(ip)


    def defaultRouterIp(self):
        """Return the ip of the default router for this network.
        It is based on zDefaultRouterNumber which specifies the sequence
        number that locates the router in this network.  If:
        zDefaultRouterNumber==1 for 10.2.1.0/24 -> 10.2.1.1
        zDefaultRouterNumber==254 for 10.2.1.0/24 -> 10.2.1.254
        zDefaultRouterNumber==1 for 10.2.2.128/25 -> 10.2.2.129
        zDefaultRouterNumber==126 for 10.2.2.128/25 -> 10.2.2.254
        """
        roffset = getattr(self, "zDefaultRouterNumber", 1)
        return strip((numbip(self.id) + roffset))


    def getNetworkName(self):
        """return the full network name of this network"""
        return "%s/%d" % (self.id, self.netmask)


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """make sure that networks sort correctly"""
        return numbip(self.id)


    security.declareProtected('Change Network', 'addSubNetwork')
    def addSubNetwork(self, ip, netmask=24):
        """Return and add if nessesary subnetwork to this network.
        """
        netobj = self.getSubNetwork(ip)
        if not netobj:
            net = IpNetwork(ip, netmask)
            self._setObject(ip, net)
        return self.getSubNetwork(ip)


    security.declareProtected('View', 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self._getOb(ip, None)

    
    def getSubNetworks(self):
        """Return all network objects below this one.
        """
        nets = self.children()
        for subgroup in self.children():
            nets.extend(subgroup.getSubNetworks())
        return nets

    security.declareProtected('Change Network', 'addIpAddress')
    def addIpAddress(self, ip, netmask=24):
        """add ip to this network and return it"""
        ipobj = IpAddress(ip,netmask)
        self.ipaddresses._setObject(ip, ipobj)
        return self.getIpAddress(ip)


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self, ip):
        """get an ip on this network"""
        return self.ipaddresses._getOb(ip, None)

    security.declareProtected('Change Network', 'manage_deleteIpAddresses')
    def manage_deleteIpAddresses(self, ipaddresses=(), REQUEST=None):
        """Delete ipaddresses by id from this network.
        """
        for ipaddress in ipaddresses:  
            ip = self.getIpAddress(ipaddress)
            self.ipaddresses.removeRelation(ip)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'countIpAddresses')
    def countIpAddresses(self, inuse=False):
        """get an ip on this network"""
        if inuse:
            # When there are a large number of IPs this code is too slow
            # we either need to cache all /Status/Ping events before hand
            # and then integrate them with the list of IPs
            # or blow off the whole feature.  For now we just set the
            # default to not use this code.  -EAD
            count = len(filter(lambda x: x.getStatus() == 0,self.ipaddresses()))
        else:
            count = self.ipaddresses.countObjects()
        for net in self.children():
            count += net.countIpAddresses(inuse)
        return count

    security.declareProtected('View', 'countDevices')
    countDevices = countIpAddresses
   

    def getAllCounts(self, devrel=None):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        unused(devrel)
        counts = [
            self.ipaddresses.countObjects(),
            self._status("Ping", "ipaddresses"),
            self._status("Snmp", "ipaddresses"),
        ]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts

    
    def pingStatus(self, devrel=None):
        """aggregate ping status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.pingStatus(self, "ipaddresses")

    
    def snmpStatus(self, devrel=None):
        """aggregate snmp status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.snmpStatus(self, "ipaddresses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "ipaddresses")


    def findIp(self, ip):
        """Find an ipAddress.
        """
        searchCatalog = self.getDmdRoot("Networks").ipSearch
        ret = searchCatalog(dict(id=ip))
        if not ret: return None
        if len(ret) > 1:
            raise IpAddressConflict, "IP address conflict for IP: %s" % ip
        return ret[0].getObject()

    
    def buildZProperties(self):
        nets = self.getDmdRoot("Networks")
        if getattr(aq_base(nets), "zDefaultNetworkTree", False):
            return
        nets._setProperty("zDefaultNetworkTree", (24,32), type="lines")
        nets._setProperty("zDrawMapLinks", True, type="boolean")
        nets._setProperty("zAutoDiscover", True, type="boolean")
        nets._setProperty("zPingFailThresh", 168, type="int")
        nets._setProperty("zIcon", "/zport/dmd/img/icons/network.png")


    def reIndex(self):
        """Go through all ips in this tree and reindex them."""
        zcat = self._getCatalog()
        zcat.manage_catalogClear()
        transaction.savepoint()
        for net in self.getSubNetworks():
            for ip in net.ipaddresses():
                ip.index_object()
            transaction.savepoint()


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX convert to ManagableIndex
        manage_addZCatalog(self, self.default_catalog,
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('id', makeCaseInsensitiveFieldIndex('id'))
        zcat.addColumn('getPrimaryId')


    def discoverNetwork(self, REQUEST=None):
        """
        """
        path = '/'.join(self.getPrimaryPath()[4:])
        return self.discoverDevices([path], REQUEST=REQUEST)

    def discoverDevices(self, organizerPaths=None, REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration. 
        """
        xmlrpc = isXmlRpc(REQUEST)
                  
        if not organizerPaths: 
            if xmlrpc: return 1
            return self.callZenScreen(REQUEST)
        
        if REQUEST and not xmlrpc:
            handler = setupLoggingHeader(self, REQUEST)
        zDiscCommand = "empty"
        
        from Products.ZenUtils.ZenTales import talesEval

        orgroot = self.getDmdRoot(self.dmdRootName)
        for organizerName in organizerPaths:
            organizer = orgroot._getNet(organizerName)
            zDiscCommand = getattr(organizer, "zZenDiscCommand", None)
            if zDiscCommand:
                cmd = talesEval('string:' + zDiscCommand, organizer).split(" ")
            else:
                cmd = ["zendisc", "run", "--weblog", "--net", organizer.id]
            zd = binPath('zendisc')
            zendiscCmd = [zd] + cmd[1:]
            result = executeCommand(zendiscCmd, REQUEST)
            if result and xmlrpc: return result

        log.info('Done')

        if REQUEST and not xmlrpc:
            self.loaderFooter(REQUEST.RESPONSE)
            clearWebLoggingStream(handler)

        if xmlrpc: return 0


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        alog = logging.getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)


    def loaderFooter(self, response):
        """add navigation links to the end of the loader output"""
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to network <a href=%s>%s</a></td></tr>""" 
            % (self.absolute_url(), self.id))
        response.write("</table></body></html>")

    security.declareProtected('View', 'getXMLEdges')
    def getXMLEdges(self, depth=1, filter='/', start=()):
        """ Gets XML """
        if not start: start=self.id
        edges = NetworkTree.get_edges(self, depth, 
                                      withIcons=True, filter=filter)
        return edgesToXML(edges, start)

    def getIconPath(self):
        """ gets icon """
        try:
            return self.primaryAq().zIcon
        except AttributeError:
            return '/zport/dmd/img/icons/noicon.png'


    def urlLink(self, text=None, url=None, attrs={}):
        """
        Return an anchor tag if the user has access to the remote object.
        @param text: the text to place within the anchor tag or string.
                     Defaults to the id of this object.
        @param url: url for the href. Default is getPrimaryUrlPath
        @type attrs: dict
        @param attrs: any other attributes to be place in the in the tag.
        @return: An HTML link to this object
        @rtype: string 
        """
        if not text:
            text = "%s/%d" % (self.id, self.netmask)
        if not self.checkRemotePerm("View", self):
            return text
        if not url:
            url = self.getPrimaryUrlPath()
        if len(attrs):
            return '<a href="%s" %s>%s</a>' % (url,
                ' '.join(['%s="%s"' % (x,y) for x,y in attrs.items()]),
                text)
        else:
            return '<a href="%s">%s</a>' % (url, text)

InitializeClass(IpNetwork)


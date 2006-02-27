#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""IpService.py

IpService is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: IpService.py,v 1.10 2004/04/22 22:04:14 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from Products.ZenRelations.RelSchema import *

from Service import Service
from Products.ZenModel.IpServiceClass import IpServiceClass

def manage_addIpService(context, id, title = None, REQUEST = None):
    """make a device"""
    d = IpService(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addIpService = DTMLFile('dtml/addIpService',globals())

class IpService(Service):
    """
    IpService object
    """

    portal_type = meta_type = 'IpService'

    protocols = ('tcp', 'udp')

    ipaddresses = []
    discoveryAgent = ""
    port = 0 
    protocol = ""

    _properties = (
        {'id':'port', 'type':'int', 'mode':'', 'setter': 'setPort'},
        {'id':'protocol', 'type':'string', 'mode':'', 'setter': 'setProtocol'},
        {'id':'ipaddresses', 'type':'lines', 'mode':''},
        {'id':'discoveryAgent', 'type':'string', 'mode':''},
        ) 
    _relations = Service._relations + (
        ("os", ToOne(ToManyCont,"OperatingSystem","ipservices")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'ipServiceDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceDetail'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def monitored(self):
        """Return monitored state of ipservice.  
        If service only listens on 127.0.0.1 return false.
        """
        if len(self.ipaddresses) == 1 and "127.0.0.1" in self.ipaddresses:
            return -1
        return super(IpService, self).monitored()
            

    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "%s-%d ips:%s" % (self.protocol, self.port, 
                                 ", ".join(self.ipaddresses))

        
    def setServiceClass(self, kwargs):
        """Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(factory=IpServiceClass, **kwargs)
        self.serviceclass.addRelation(srvclass)


    def getSendString(self):
        return self._aqprop("sendString")


    def getExpectRegex(self):
        return self._aqprop("expectRegex")


    def getServiceClass(self):
        """Return a dict like one set by IpServiceMap for services.
        """
        svc = self.serviceclass()
        if svc:
            return {'protocol': self.protocol, 'port': svc.port }
        return {}


    def primarySortKey(self):
        return "%s-%05d" % (self.protocol, self.port)
    
    def getProtocol(self):
        return self.protocol

    def getPort(self):
        return self.port
        
    def getKeyword(self):
        sc = self.serviceclass()
        if sc: return sc.name

    def getDescription(self):
        sc = self.serviceclass()
        if sc: return sc.description

    def ipServiceClassUrl(self):
        sc = self.serviceclass()
        if sc: return sc.getPrimaryUrlPath()
    
    
    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, monitor=False, severity=5, sendString="",
                            expectRegex="", REQUEST=None):
        """Edit a Service from a web page.
        """
        msg = []
        msg.append(self._aqsetprop("sendString", sendString, "string"))
        msg.append(self._aqsetprop("expectRegex", expectRegex, "string"))
        return super(IpService, self).manage_editService(monitor, severity, 
                                        msg=msg,REQUEST=REQUEST)


InitializeClass(IpService)

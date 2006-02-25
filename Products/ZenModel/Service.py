#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Service.py

Service is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: Service.py,v 1.15 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

class Service(OSComponent):
    portal_type = meta_type = 'Service'
   
    _relations = OSComponent._relations + (
        ("serviceclass", ToOne(ToMany,"ServiceClass","instances")),
        )

    security = ClassSecurityInfo()

    def key(self):
        """Return tuple (manageIp, name) for this service to uniquely id it.
        """
        return (self.getManageIp(), self.name())


    def name(self):
        """Return the name of this service. (short name for net stop/start).
        """
        svccl = self.serviceclass()
        if svccl: return svccl.name
        return ""

    
    def monitored(self):
        """Should this service be monitored or not. Use ServiceClass aq path. 
        """
        return self._aqprop("zMonitor")


    def getSendString(self):
        return self._aqprop("sendString")


    def getExpectRegex(self):
        return self._aqprop("expectRegex")


    def getSeverity(self):
        """Return the severity for this service when it fails.
        """
        #FIXME!!!
        return 5


    def _aqprop(self, prop):
        """get a property from ourself if it exsits then try serviceclass path.
        """
        if getattr(aq_base(self), prop, None) is not None:
            return getattr(self, prop)
        svccl = self.serviceclass()
        if svccl: 
            svccl = svccl.primaryAq()
            return getattr(svccl, prop)


    def getStatus(self):
        """Return the status of this service as a number.
        """
        if not self.monitored(): return -1
        statusClass = "/Status/%s" % self.meta_type
        return OSComponent.getStatus(self, statusClass)

   
    def setServiceClass(self, kwargs):
        """Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(**kwargs)
        self.serviceclass.addRelation(srvclass)


    def getServiceClassLink(self):
        """Return an a link to the service class.
        """
        svccl = self.serviceclass()
        if svccl: return "<a href='%s'>%s</a>" % (svccl.getPrimaryUrlPath(),
                                                svccl.getServiceClassName())
        return ""


    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, monitor=False, REQUEST=None):
        """
        Edit a Service from a web page.
        """
        msg = "No action needed:"
        svccl = self.serviceclass()
        if not svccl: return
        svccl = svccl.primaryAq()
        if svccl.zMonitor != monitor:
            self._setProperty("zMonitor", monitor, type="boolean")
            msg = "Set local zMonitor property:"
        elif getattr(aq_base(self), "zMonitor", None) is not None:
            self._delProperty("zMonitor")
            msg = "Removed local zMonitor property:"
        if REQUEST:
            REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)



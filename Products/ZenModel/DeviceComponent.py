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

__doc__="""DeviceComponent

All device components inherit from this class

$Id: DeviceComponent.py,v 1.1 2004/04/06 21:05:03 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

import zope.interface
from Products.ZenModel.interfaces import IIndexed

from Lockable import Lockable

class DeviceComponent(Lockable):
    """
    DeviceComponent is a mix-in class for all components of a device.
    These include LogicalComponent, Software, and Hardware.
    """
    zope.interface.implements(IIndexed)
    __pychecker__='no-override'
    event_key = "Component"

    default_catalog = "componentSearch"

    collectors = ('zenperfsnmp', 'zencommand', 'zenwinperf')

    security = ClassSecurityInfo()

    perfmonInstance = None

    def getParentDeviceName(self):
        """
        Return the name of this component's device
        """
        name = ""
        dev = self.device()
        if dev: name = dev.getDeviceName()
        return name
    hostname = getParentDeviceName


    def getParentDeviceUrl(self):
        """
        Return the url of this component's device
        """
        url = ""
        dev = self.device()
        if dev: url = dev.absolute_url()
        return url
    
   
    def name(self):
        """
        Return the name of this component.  Default is id.
        """
        return self.id


    def monitored(self):
        """
        Return the monitored status of this component. Default is False.
        """
        return self.monitor


    def getCollectors(self):
        """
        Return list of collectors that want to monitor this component
        """
        return self.collectors


    def getInstDescription(self):
        """
        Return some text that describes this component.  Default is name.
        """
        return self.name()

        
    def getStatus(self, statClass=None):
        """
        Return the status number for this component of class statClass.
        """
        if not self.monitored() \
            or not self.device() \
            or not self.device().monitorDevice(): return -1
        if not statClass: statClass = "/Status/%s" % self.meta_type
        return self.getEventManager().getComponentStatus(
                self.getParentDeviceName(), self.name(), statclass=statClass)

  
    def getStatusString(self, statClass=None):
        """
        Return a text representation of this component's status
        """
        return self.convertStatus(self.getStatus(statClass))


    def getManageIp(self):
        """
        Return the manageIP of the device of this component.
        """
        dev = self.device()
        if dev: return dev.getManageIp()
        return ""


    def getNagiosTemplate(self, unused=None):
        import warnings
        warnings.warn('anything named nagios is deprecated', DeprecationWarning)


    def getAqProperty(self, prop):
        """
        Get a property from ourself if it exsits then try serviceclass path.
        """
        if getattr(aq_base(self), prop, None) is not None:
            return getattr(self, prop)
        classObj = self.getClassObject()
        if classObj: 
            classObj = classObj.primaryAq()
            return getattr(classObj, prop)


    def setAqProperty(self, prop, value, type):
        """
        Set a local prop if nessesaary on this service.
        """
        classObj = self.getClassObject()
        if not classObj: return
        classObj = classObj.primaryAq()
        svcval = getattr(classObj, prop)
        locval = getattr(aq_base(self),prop,None)
        msg = ""
        if svcval == value and locval is not None:
            self._delProperty(prop)
            msg = "Removed local %s" % prop
        elif svcval != value and locval is None:
            self._setProperty(prop, value, type=type)
            msg = "Set local %s" % prop
        elif locval is not None and locval != value:
            self._updateProperty(prop, value)
            msg = "Update local %s" % prop
        return msg

    
    def getClassObject(self):
        """
        If you are going to use acquisition up different class path
        override this.
        """
        return self.device()


    def getRRDContextData(self, context):
        context['comp'] = self
        context['compId'] = self.id
        context['compName'] = self.name()
        if self.device():
            context['dev'] = self.device()
            context['devId'] = self.device().id


    def filterAutomaticCreation(self):
        """Test if automatic creation (and anchoring into a model) is
        appropriate for this object.  Lets us ignore detectable gunk
        that's not very interesting to model, like most processes, and
        loopback network devices, CDROM file systems, etc.
        
        Returns False if the object should not be added.

        The object will have its full acquisition path, but will not
        have been added to the database.
        """
        return True
   
InitializeClass(DeviceComponent)

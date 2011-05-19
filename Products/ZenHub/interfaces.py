###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.component.interfaces import Interface, IObjectEvent
from zope.interface import Attribute


class IInvalidationEvent(IObjectEvent):
    """
    ZenHub has noticed an invalidation.
    """
    oid = Attribute("OID of the changed object")


class IUpdateEvent(IInvalidationEvent):
    """
    An object has been updated.
    """


class IDeletionEvent(IInvalidationEvent):
    """
    An object has been deleted.
    """

class IBatchNotifier(Interface):
    """
    Processes subdevices in batches.
    """
    
    def notify_subdevices(device_class, service_uid, callback):
        """
        Process subdevices of device class in batches calling callback with
        each device. The service UID uniquely identifies the service, so the
        processing of the same device_class-service pair is not duplicated.
        """

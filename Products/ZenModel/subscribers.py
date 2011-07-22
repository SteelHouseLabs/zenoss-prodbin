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
from Products.ZenModel.IpInterface import IpInterface, beforeDeleteIpInterface
from OFS.interfaces import IObjectWillBeAddedEvent
from zope.container.interfaces import IObjectRemovedEvent

def unindexBeforeDelete(ob, event):
    """
    Multisubscriber for IIndexed + IObjectWillBeMovedEvent
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        if isinstance(ob, IpInterface):
            beforeDeleteIpInterface(ob, event)
        else:
            ob.unindex_object()

def indexAfterAddOrMove(ob, event):
    """
    Multisubscriber for IIndexed + IObjectMovedEvent.
    """
    if not IObjectRemovedEvent.providedBy(event):
        ob.index_object()

###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedOutEvent
from Products.PluggableAuthService.events import PASEvent
from zope.interface import implements, Interface, Attribute
from zope.event import notify
from ZODB.transact import transact

class UserLoggedInEvent(PASEvent):
    """
    Login notification event.

    Subscribe to this to run code when a user logs in.
    The username can be obtained in the handler via: evt.object.id

    WARNING: Currently it doesn't notify when switching directly from
             a non-admin user to the admin user without logging out,
             because we're unable to determine whether the login succeeded.
    """
    implements(IUserLoggedInEvent)


class UserLoggedOutEvent(PASEvent):
    """
    Manual logout notification event.

    This does not fire for session timeouts.
    """
    implements(IUserLoggedOutEvent)

class IZopeApplicationOpenedEvent(Interface):
    """
    Returns the Zope application.
    """
    app = Attribute("The Zope Application")

class ZopeApplicationOpenedEvent(object):
    implements(IZopeApplicationOpenedEvent)

    def __init__(self, app):
        self.app = app

def notifyZopeApplicationOpenedSubscribers(event):
    """
    Re-fires the IDatabaseOpenedWithRoot notification to subscribers with an
    open handle to the application defined in the database.
    """
    db = event.database
    conn = db.open()
    try:
        app = conn.root()['Application']
        transact(notify)(ZopeApplicationOpenedEvent(app))
    finally:
        conn.close()


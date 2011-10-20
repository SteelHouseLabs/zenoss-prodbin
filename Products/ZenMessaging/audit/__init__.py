###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Announces messages so they can be tracked or handled.

Messages have a category hierarchy, a target, and various passed data.
Values that evaluate to False are never shown, so pass str(value) if needed.
If old values are passed it only shows the new/changed/deleted values.
If old values are passed and nothing changed at all, there's no announcement.

Examples:
    from Products.ZenMessaging.audit import audit

    audit('UI.Widget.Add',                     #category string or list
          widgetObjectOrUid,                   #object or UID
          name='Widget', count=10, ...)        #pass data via kwargs

    category = ['UI', 'Widget', 'Edit']        #[source, objType, action]
    audit(category,
          widget,
          skipFields_=('Referrer','REQUEST'),  #ignore these keys if found
          maskFields_=('passwd','password'),   #hide the values of these keys
          oldData_={'x': oldX, 'count': 10} ,  #old values for comparison
          data_={dynamicName: value},          #pass data dynamically {X:Y}
          count=25, ...)                       #pass data via kwargs (X=Y)

    # 'Same' will not be announced since its value didn't change.
    category = [sourceType, objectType, actionType, ...]
    oldData = {'Same': 123, 'Up': oldUp, 'Down': oldDown}
    data    = {'Same': 123, 'Up': newUp, 'Upp': newUpp, 'Away': newAway}
    audit(category, uid, oldData_=oldData, data_=dyanmicData)
"""

from zope.component import getUtility, ComponentLookupError
from .interfaces import IAuditManager


def getAuditManager():
    """Convenience method."""
    try:
        return getUtility(IAuditManager)
    except ComponentLookupError:
        return None


def audit(*args, **kwargs):
    """Convenience method."""
    util = getAuditManager()
    if util:
        util.audit(*args, **kwargs)

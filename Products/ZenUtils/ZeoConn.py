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

from zope.component import getUtility
from Products.ZenUtils.Utils import set_context
from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup

class ZeoConn(object):

    def __init__(self, **kwargs):
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        self.db, self.storage = connectionFactory.getConnection(**kwargs)

        self.app = None
        self.dmd = None
        self.opendb()


    def opendb(self):
        if self.app: return
        self.connection=self.db.open()
        root=self.connection.root()
        app = root['Application']
        self.app = set_context(app)
        self.dmd = self.app.zport.dmd


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        self.db.close()
        self.app = None
        self.dmd = None


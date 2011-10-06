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

__doc__="""ZenScriptBase
"""

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from transaction import commit
from Utils import getObjByPath, zenPath, set_context
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.ZCmdBase import ZCmdBase

from Products.Five import zcml

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Exceptions import ZentinelException

defaultCacheDir = zenPath('var')

class DataRootError(Exception):pass

class ZenScriptBase(CmdBase):

    def __init__(self, noopts=0, app=None, connect=False):
        import Products.ZenossStartup
        zcml.load_site()
        CmdBase.__init__(self, noopts)
        self.dataroot = None
        self.app = app
        self.db = None
        if connect:
            self.connect()

    def connect(self):
        if not self.app:
            from zope.component import getUtility
            from ZodbFactory import IZodbFactory
            connectionFactory = getUtility(IZodbFactory)()
            self.db, self.storage = connectionFactory.getConnection(**self.options.__dict__)
        self.getDataRoot()
        self.login()
        if getattr(self.dmd, 'propertyTransformers', None) is None:
            self.dmd.propertyTransformers = {}
            commit()
        setDescriptors(self.dmd.propertyTransformers)


    def login(self, name='admin', userfolder=None):
        '''Logs in.'''
        if userfolder is None:
            userfolder = self.app.acl_users
        user = userfolder.getUserById(name)
        if user is None: return
        if not hasattr(user, 'aq_base'):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)


    def logout(self):
        '''Logs out.'''
        noSecurityManager()


    def getConnection(self):
        """Return a wrapped app connection from the connection pool.
        """
        if not self.db:
            raise ZentinelException(
                "running inside zope can't open connections.")
        with self.poollock:
            connection=self.db.open()
            root=connection.root()
            app=root['Application']
            app = set_context(app)
            app._p_jar.sync()
            return app


    def closeAll(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()


    def opendb(self):
        if self.app: return 
        self.connection=self.db.open()
        root=self.connection.root()
        app = root['Application']
        self.app = set_context(app)
        self.app._p_jar.sync()


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        #self.db.close()
        self.app = None
        self.dataroot = None
        self.dmd = None


    def getDataRoot(self):
        if not self.app: self.opendb()
        if not self.dataroot:
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return getObjByPath(self.app, self.options.dataroot+path)


    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)

        from zope.component import getUtility
        from ZodbFactory import IZodbFactory
        connectionFactory = getUtility(IZodbFactory)()
        connectionFactory.buildOptions(self.parser)


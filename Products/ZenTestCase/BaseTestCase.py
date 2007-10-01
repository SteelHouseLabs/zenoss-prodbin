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
import os
import unittest

from Testing import ZopeTestCase
from Testing.ZopeTestCase.ZopeTestCase import standard_permissions

from Products import ZenModel
from Products.ZenModel.DmdBuilder import DmdBuilder
from Products.ZenModel.ZentinelPortal import PortalGenerator
from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenEvents.MySqlSendEvent import MySqlSendEventMixin
from Products.ZenEvents.MySqlEventManager import log
from Products.ZenEvents import MySqlEventManager
from Products.ZenRelations.ImportRM import ImportRM

log.warn = lambda *args, **kwds: None

# setup the Products needed for the Zenoss test instance
ZopeTestCase.installProduct('ZenRelations', 1)
ZopeTestCase.installProduct('ZenModel', 1)
ZopeTestCase.installProduct('ZCatalog', 1)
ZopeTestCase.installProduct('OFolder', 1)
ZopeTestCase.installProduct('ManagableIndex', 1)
ZopeTestCase.installProduct('AdvancedQuery', 1)
ZopeTestCase.installProduct('ZCTextIndex', 1)
ZopeTestCase.installProduct('CMFCore', 1)
ZopeTestCase.installProduct('CMFDefault', 1)
ZopeTestCase.installProduct('MailHost', 1)
ZopeTestCase.installProduct('Transience', 1)


def manage_addDummyManager(context, id):
    context._delObject(id)
    context._setObject(id, DummyManager(id))
    evtmgr = context._getOb(id)
    evtmgr.installIntoPortal()


class DummyCursor(object):
    def __init__(self, *args, **kwds): pass
    def execute(self, *args, **kwds): pass


class DummyConnection(object):
    def __init__(self, *args, **kwds): pass
    def cursor(self):
        return DummyCursor()
    def close(self): pass


class DummyManager(MySqlSendEventMixin, EventManagerBase):
    def __init__(self, *args, **kwds):
        EventManagerBase.__init__(self, *args, **kwds)
    def connect(self, *args, **kwds): return DummyConnection()
    def sendEvent(self, *args, **kwds): pass
    def sendEvents(self, *args, **kwds): pass
    def doSendEvent(self, *args, **kwds): pass
    def getEventSummary(self, *args, **kwds): pass
    def getEventDetail(self, *args, **kwds): pass
    def getGenericStatus(self, *args, **kwds): pass
    def getOrganizerStatus(self, *args, **kwds): pass
    def getOrganizerStatusIssues(self, *args, **kwds): pass
    def getDeviceIssues(self, *args, **kwds): pass
    def getDeviceStatus(self, *args, **kwds): pass
    def getHeartbeat(self, *args, **kwds): pass
    def getComponentStatus(self, *args, **kwds): pass
    def getEventList(self, *args, **kwds): return []
    def applyEventContext(self, evt): return evt
    def applyDeviceContext(self, dev, evt): return evt


class Builder(DmdBuilder):

    def build(self):
        DmdBuilder.build(self)
        manage_addDummyManager(self.dmd, 'ZenEventManager')
        manage_addDummyManager(self.dmd, 'ZenEventHistory')


class BaseTestCase(ZopeTestCase.ZopeTestCase):


    def afterSetUp(self):
        gen = PortalGenerator()
        gen.create(self.app, 'zport', True)
        # builder params:
        # portal, cvthost, evtuser, evtpass, evtdb,
        #    smtphost, smtpport, snpphost, snppport
        builder = Builder(self.app.zport, 'localhost', 'dbuser', 'dbpass',
                            'dbtable', 'localhost', '25', 'localhost', '0')
        builder.build()
        self.dmd = builder.dmd

        self.dmd.ZenUsers.manage_addUser('tester', roles=('Manager',))
        user = self.app.zport.acl_users.getUserById('tester')
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, user)


    def tearDown(self):
        self.app = None
        self.dmd = None
        ZopeTestCase.ZopeTestCase.tearDown(self)


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst


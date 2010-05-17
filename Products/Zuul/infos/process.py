###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import imap, chain
from zope.component import adapts
from zope.interface import implements
from Products.ZenModel.OSProcess import OSProcess
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul import getFacade
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.interfaces import IProcessEntity
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo

class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    @property
    def _evsummary(self):
        return getFacade('process', self._object).getEventSummary(self.uid)

    @property
    def text(self):
        text = super(ProcessNode, self).text
        numInstances = ICatalogTool(self._object).count(OSProcess, self.uid)
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(OSProcessOrganizer, paths=(self.uid,), depth=1)
        # Must search at depth+1 to account for relationship
        cls = cat.search(OSProcessClass, paths=(self.uid,), depth=2)
        return imap(ProcessNode, chain(orgs, cls))

    @property
    def leaf(self):
        return 'osProcessClasses' in self.uid


class ProcessInfo(InfoBase):
    implements(IProcessInfo)
    adapts(IProcessEntity)

    def getDescription(self):
        return self._object.description

    def setDescription(self, description):
        self._object.description = description

    description = property(getDescription, setDescription)

    def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)

    def setZMonitor(self, data):
        setZPropertyInfo(self._object, 'zMonitor', **data)

    zMonitor = property(getZMonitor, setZMonitor)

    def getZAlertOnRestart(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAlertOnRestart', True, translate)

    def setZAlertOnRestart(self, data):
        setZPropertyInfo(self._object, 'zAlertOnRestart', **data)

    zAlertOnRestart = property(getZAlertOnRestart, setZAlertOnRestart)

    def getZFailSeverity(self):
        def translate(rawValue):
            return {5: 'Critical',
                    4: 'Error',
                    3: 'Warning',
                    2: 'Info',
                    1: 'Debug'}[rawValue]
        return getZPropertyInfo(self._object, 'zFailSeverity', 4, translate)

    def setZFailSeverity(self, data):
        setZPropertyInfo(self._object, 'zFailSeverity', **data)

    zFailSeverity = property(getZFailSeverity, setZFailSeverity)

    def getHasRegex(self):
        return isinstance(self._object, OSProcessClass)

    def setHasRegex(self, hasRegex):
        pass

    hasRegex = property(getHasRegex, setHasRegex)

    def getRegex(self):
        return getattr(self._object, 'regex', None)

    def setRegex(self, regex):
        if self.hasRegex:
            self._object.regex = regex

    regex = property(getRegex, setRegex)

    def getIgnoreParameters(self):
        return getattr(self._object, 'ignoreParameters', None)

    def setIgnoreParameters(self, ignoreParameters):
        if self.hasRegex:
            self._object.ignoreParameters = ignoreParameters

    ignoreParameters = property(getIgnoreParameters, setIgnoreParameters)

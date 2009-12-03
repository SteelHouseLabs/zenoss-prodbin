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

from itertools import imap
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IProcessFacade, IProcessEntity
from Products.Zuul.interfaces import ITreeFacade
from Products.Zuul.interfaces import IProcessInfo, IInfo, IMonitoringInfo
from Products.Zuul.interfaces import ISerializableFactory
from Products.Zuul.interfaces import IProcessNode, ITreeNode
from Products.Zuul.interfaces import IDeviceInfo
from Products.Zuul.interfaces import IEventInfo
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer


class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    uiProvider = 'hierarchy'

    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object

    @property
    def iconCls(self):
        sev = 'clear' # FIXME: Get this somehow
        return 'severity-icon-small %s' % sev

    @property
    def text(self):
        text = super(ProcessNode, self).text
        numInstances = 3 # FIXME: Get this somehow
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }

    @property
    def id(self):
        path = list(self._object.getPrimaryPath()[3:])
        if 'osProcessClasses' in path:
            path.remove('osProcessClasses')
        return '/'.join(path)

    @property
    def children(self):
        managers = []
        if not self.leaf:
            obj = self._object
            managers.extend(obj.objectValues(spec='OSProcessOrganizer'))
            rel = obj._getOb('osProcessClasses')
            managers.extend(rel.objectValues(spec='OSProcessClass'))
        return imap(ITreeNode, managers)

    @property
    def leaf(self):
        return isinstance(self._object, OSProcessClass)

    def __repr__(self):
        return "<ProcessTree(id=%s)>" % (self.id)


class ProcessInfo(object):
    implements(IProcessInfo)
    adapts(IProcessEntity)

    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object

    @property
    def name(self):
        return self._object.titleOrId()

    @property
    def description(self):
        return self._object.description

    @property
    def isMonitoringAcquired(self):
        return not self._object.hasProperty('zMonitor') \
                and not self._object.hasProperty('zFailSeverity')

    @property
    def monitor(self):
        return self._object.zMonitor

    @property
    def eventSeverity(self):
        return self._object.zFailSeverity

    @property
    def hasRegex(self):
        return isinstance(self._object, OSProcessClass)

    @property
    def regex(self):
        return getattr(self._object, 'regex', None)

    @property
    def ignoreParameters(self):
        return getattr(self._object, 'ignoreParameters', None)

    def __repr__(self):
        return "<ProcessInfo(name=%s)>" % (self.name)


class SerializableProcessInfoFactory(object):
    implements(ISerializableFactory)
    adapts(ProcessInfo)

    def __init__(self, processInfo):
        self._processInfo = processInfo

    def __call__(self):
        return {'name': self._processInfo.name,
                'description': self._processInfo.description,
                'isMonitoringAcquired': self._processInfo.isMonitoringAcquired,
                'monitor': self._processInfo.monitor,
                'eventSeverity': self._processInfo.eventSeverity,
                'hasRegex': self._processInfo.hasRegex,
                'regex': self._processInfo.regex,
                'ignoreParameters': self._processInfo.ignoreParameters
                }


class MonitoringInfo(object):
    implements(IMonitoringInfo)
    adapts(IProcessEntity)

    def __init__(self, object):
        self._object = object

    @property
    def enabled(self):
        return self._object.zMonitor

    @property
    def eventSeverity(self):
        return self._object.zFailSeverity


class SerializableMonitoringInfoFactory(object):
    implements(ISerializableFactory)
    adapts(IMonitoringInfo)

    def __init__(self, monitoringInfo):
        self._monitoringInfo = monitoringInfo

    def __call__(self):
        return {'enabled': self._monitoringInfo.enabled,
                'eventSeverity': self._monitoringInfo.eventSeverity
                }


class ProcessFacade(ZuulFacade):
    implements(IProcessFacade, ITreeFacade)

    def getTree(self, id):
        obj = self._findObject(id)
        return ITreeNode(obj)

    def getInfo(self, id):
        obj = self._findObject(id)
        return IInfo(obj)

    def getMonitoringInfo(self, id):
        obj = self._findObject(id)
        return IMonitoringInfo(obj)

    def getDevices(self, id):
        processClasses = self._getProcessClasses(id)
        deviceInfos = []
        infoClass = None
        for processClass in processClasses:
            for instance in processClass.instances():
                newDeviceInfo = IDeviceInfo(instance.device())
                if infoClass is None:
                    infoClass = newDeviceInfo.__class__
                for existingDeviceInfo in deviceInfos:
                    if existingDeviceInfo.device == newDeviceInfo.device:
                        break
                else:
                    deviceInfos.append(newDeviceInfo)
        if infoClass is not None:
            deviceInfos.sort(key=infoClass.getDevice)
        return deviceInfos

    def getEvents(self, id):
        processClasses = self._getProcessClasses(id)
        zem = self._dmd.ZenEventManager
        eventInfos = []
        for processClass in processClasses:
            for instance in processClass.instances():
                for event in zem.getEventListME(instance):
                    if not getattr(event, 'device', None):
                        event.device = instance.device().id
                    if not getattr(event, 'component', None):
                        event.component = instance.name()
                    eventInfos.append(IEventInfo(event))
        return eventInfos

    def _findObject(self, id):
        parts = id.split('/')
        objectId = parts[-1]
        if len(parts) == 1:
            manager = self._dmd
        else:
            parentPath = '/'.join(parts[:-1])
            parent = self._dmd.findChild(parentPath)
            if objectId in parent.objectIds():
                manager = parent
            else:
                manager = parent._getOb('osProcessClasses')
        return manager._getOb(objectId)

    def _getProcessClasses(self, id):
        processObj = self._findObject(id)
        if isinstance(processObj, OSProcessOrganizer):
            processClasses = processObj.getSubOSProcessClassesSorted()
        else:
            processClasses = [processObj]
        return processClasses

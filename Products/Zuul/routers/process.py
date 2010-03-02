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

from Products import Zuul
from Products.Zuul.decorators import require
from Products.Zuul.routers import TreeRouter

class ProcessRouter(TreeRouter):

    def _getFacade(self):
        return Zuul.getFacade('process')

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return data['children']

    def moveProcess(self, uid, targetUid):
        facade = self._getFacade()
        primaryPath = facade.moveProcess(uid, targetUid)
        id = '.'.join(primaryPath)
        uid = '/'.join(primaryPath)
        return {'success': True, 'uid': uid, 'id': id}

    def getInfo(self, uid, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        return {'data': data, 'success': True}

    @require('Manage DMD')
    def setInfo(self, **data):
        facade = self._getFacade()
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return {'success': True}

    def getDevices(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        facade = self._getFacade()
        devices = facade.getDevices(uid)
        data = Zuul.marshal(devices)
        return {'data': data, 'success': True}

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return {'data': data, 'success': True}

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                     dir='ASC'):
        facade = self._getFacade()
        instances = facade.getInstances(uid, start, limit, sort, dir, params)
        data = Zuul.marshal(instances)
        return {'data': data, 'success': True, 'total': instances.total}

    def getSequence(self):
        facade = self._getFacade()
        sequence = facade.getSequence()
        data = Zuul.marshal(sequence)
        return {'data': data, 'success': True}

    def setSequence(self, uids):
        facade = self._getFacade()
        facade.setSequence(uids)
        return {'success': True}

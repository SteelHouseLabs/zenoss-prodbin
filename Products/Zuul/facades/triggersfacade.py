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

from Products.ZenUtils.PkgResources import pkg_resources
import logging
import uuid
from Acquisition import aq_parent
from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IInfo
from Products.ZenModel.NotificationSubscription import NotificationSubscription
from Products.ZenModel.NotificationSubscriptionWindow import NotificationSubscriptionWindow
import zenoss.protocols.protobufs.zep_pb2 as zep
from zenoss.protocols.jsonformat import to_dict, from_dict
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from zenoss.protocols.services.triggers import TriggerServiceClient

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):
    
    def __init__(self, context):
        super(TriggersFacade, self).__init__(context)
        
        config = getGlobalConfiguration()
        self.triggers_service = TriggerServiceClient(config.get('zep_uri', 'http://localhost:8084'))
    
    def removeNode(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        return context._delObject(obj.id)
        
    def getTriggers(self):
        response, trigger_set = self.triggers_service.getTriggers()
        if trigger_set:
            trigger_set = to_dict(trigger_set)
        return trigger_set['triggers']
    
    def parseFilter(self, source):
        """
        Parse a filter to make sure it's sane.
        
        @param source: The python expression to test.
        @type source: string
        @todo: make this not allow nasty python.
        """
        if isinstance(source, basestring):
            if source:
                tree = parser.expr(source)
                if parser.isexpr(tree):
                    return source
                else:
                    raise Exception('Invalid filter expression.')
            else:
                return True # source is empty string
        

    def addTrigger(self, newId):
        trigger = zep.EventTrigger()
        trigger.uuid = str(uuid.uuid4())
        trigger.name = newId
        trigger.rule.api_version = 1
        trigger.rule.type = zep.RULE_TYPE_JYTHON
        trigger.rule.source = ''
        response, content = self.triggers_service.addTrigger(trigger)
        return content

    def removeTrigger(self, uuid):
        response, content = self.triggers_service.removeTrigger(uuid)
        return content

    def getTrigger(self, uuid):
        response, trigger = self.triggers_service.getTrigger(uuid)
        return to_dict(trigger)
    
    def updateTrigger(self, **kwargs):
        trigger = from_dict(zep.EventTrigger, kwargs)
        response, content = self.triggers_service.updateTrigger(trigger)
        return content
    
    
    def _getManager(self):
        return self._dmd.findChild('NotificationSubscriptions')
        
    def getNotifications(self):
        # don't think I'm doing this correctly, don't know yet how to manage
        # ownership and what not.
        for notification in self._getManager().getChildNodes():
            yield IInfo(notification)
    
    def addNotification(self, newId):
        notification = NotificationSubscription(newId)
        self._getManager()._setObject(newId, notification)
        return IInfo(self._getManager().findChild(newId))
    
    def removeNotification(self, uid):
        return self.removeNode(uid)
    
    def getNotification(self, uid):
        notification = self._getObject(uid)
        if notification:
            return IInfo(notification)
        
    def updateNotification(self, **data):
        log.debug(data)
        try:
            uid = data['uid']
            del data['uid']
            notification = self._getObject(uid)
            if not notification:
                log.info('Could not find notification to update: %s' % uid)
                return
                
            for field in notification._properties:
                log.debug('setting: %s: %s' % (field['id'], data.get(field['id'])))
                setattr(notification, field['id'], data.get(field['id']))
            
            # editing as a text field, but storing as a list for now.
            notification.subscriptions = [data.get('subscriptions')]
            
            log.debug('updated notification: %s' % notification)
        except KeyError, e:
            log.error('Could not update notification:')
            log.exception(e)
            raise Exception('There was an error updating the notificaton: missing required field.')
    
    def getWindows(self, uid):
        notification = self._getObject(uid)
        for window in notification.windows():
            yield IInfo(window)
    
    def addWindow(self, contextUid, newId):
        notification = self._getObject(contextUid)
        window = NotificationSubscriptionWindow(newId)
        notification.windows._setObject(newId, window)
        new_window = notification.windows._getOb(newId)
        return IInfo(new_window)
    
    def removeWindow(self, uid):
        return self.removeNode(uid)
    
    def getWindow(self, uid):
        window = self._getObject(uid)
        return IInfo(window)
    
    def updateWindow(self, data):
        try:
            uid = data['uid']
            del data['uid']
            window = self._getObject(uid)
            if not window:
                log.info('could not find schedule window to update: %s' % uid)
                return
            
            for field in window._properties:
                log.debug('setting: %s: %s' % (field['id'], data.get(field['id'])))
                setattr(window, field['id'], data.get(field['id']))
            log.debug('updated window')
            
        except KeyError, e:
            log.error('Could not update schedule window:')
            log.exception(e)
            raise Exception('There was an error updating the schedule window: missing required field.')
    
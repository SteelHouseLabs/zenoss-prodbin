###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from operator import itemgetter
from Products import Zuul
from zope.component import getUtilitiesFor
from Products.ZenModel.interfaces import IAction
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import serviceConnectionError
from zenoss.protocols.protobufs.zep_pb2 import RULE_TYPE_JYTHON
from Products.ZenMessaging.actions import sendUserAction
from Products.ZenMessaging.actions.constants import ActionTargetType, ActionName

import logging

log = logging.getLogger('zen.triggers');

class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """

    def _getFacade(self):
        return Zuul.getFacade('triggers', self)

    @serviceConnectionError
    def getTriggers(self, **kwargs):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())

    @serviceConnectionError
    def getTriggerList(self, **unused):
        return DirectResponse.succeed(data=self._getFacade().getTriggerList())

    @serviceConnectionError
    def addTrigger(self, newId):
        data = self._getFacade().addTrigger(newId)
        if sendUserAction:
            sendUserAction(ActionTargetType.Trigger, ActionName.Add,
                           trigger=newId)
        return DirectResponse.succeed(data=data)

    @serviceConnectionError
    def removeTrigger(self, uuid):

        updated_count = self._getFacade().removeTrigger(uuid)

        msg = "Trigger removed successfully. {count} {noun} {verb} updated.".format(
            count = updated_count,
            noun = 'notification' if updated_count == 1 else 'notifications',
            verb = 'was' if updated_count == 1 else 'were'
        )

        if sendUserAction:
            sendUserAction(ActionTargetType.Trigger, ActionName.Remove,
                           trigger=uuid)
        return DirectResponse.succeed(msg=msg, data=None)

    @serviceConnectionError
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))

    @serviceConnectionError
    def updateTrigger(self, **data):
        data['rule']['api_version'] = 1
        data['rule']['type'] = RULE_TYPE_JYTHON
        response = self._getFacade().updateTrigger(**data)
        if sendUserAction:
            sendUserAction(ActionTargetType.Trigger, ActionName.Edit,
                           trigger=data['uuid'], **data)
        return DirectResponse.succeed(msg="Trigger updated successfully.", data=response)

    @serviceConnectionError
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e,
                'Error parsing filter source. Please check your syntax.')


    # notification subscriptions
    @serviceConnectionError
    def getNotifications(self):
        response = self._getFacade().getNotifications()
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addNotification(self, newId, action):
        response = self._getFacade().addNotification(newId, action)
        if sendUserAction:
            sendUserAction(ActionTargetType.Notification, ActionName.Add,
                           notification=newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeNotification(self, uid):
        response = self._getFacade().removeNotification(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.Notification, ActionName.Remove,
                           notification=uid)
        return DirectResponse.succeed(msg="Notification removed successfully.", data=response)

    @serviceConnectionError
    def getNotificationTypes(self):
        utils = getUtilitiesFor(IAction)
        actionTypes = sorted((dict(id=id, name=util.name) for id, util in utils), key=itemgetter('id'))
        log.debug('notification action types are: %s' % actionTypes)
        return DirectResponse.succeed(data=actionTypes)

    @serviceConnectionError
    def getNotification(self, uid):
        response = self._getFacade().getNotification(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateNotification(self, **data):
        response = self._getFacade().updateNotification(**data)
        if sendUserAction:
            sendUserAction(ActionTargetType.Notification, ActionName.Edit,
                           notification=data['uid'], **data)
        return DirectResponse.succeed(msg="Notification updated successfully.", data=Zuul.marshal(response))

    @serviceConnectionError
    def getRecipientOptions(self):
        data = self._getFacade().getRecipientOptions()
        return DirectResponse.succeed(data=data);

    # subscription windows
    @serviceConnectionError
    def getWindows(self, uid):
        response = self._getFacade().getWindows(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addWindow(self, contextUid, newId):
        response = self._getFacade().addWindow(contextUid, newId)
        if sendUserAction:
            sendUserAction(ActionTargetType.NotificationWindow, ActionName.Add,
                           notificationwindow=newId, notification=contextUid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeWindow(self, uid):
        response = self._getFacade().removeWindow(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.NotificationWindow, ActionName.Remove,
                           notificationwindow=uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def getWindow(self, uid):
        response = self._getFacade().getWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateWindow(self, **data):
        response = self._getFacade().updateWindow(data)
        if sendUserAction:
            sendUserAction(ActionTargetType.NotificationWindow, ActionName.Edit,
                           notificationwindow=data['uid'], **data)
        return DirectResponse.succeed(data=Zuul.marshal(response))

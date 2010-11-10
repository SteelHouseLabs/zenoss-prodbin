###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse

import logging

log = logging.getLogger('zen.triggers');

class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """
    
    def _getFacade(self):
        return Zuul.getFacade('triggers', self)
    
    def getTriggers(self, **kwargs):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())
    
    def addTrigger(self, newId):
        return DirectResponse.succeed(data=self._getFacade().addTrigger(newId))
        
    def removeTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().removeTrigger(uuid))
        
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))
        
    def updateTrigger(self, **data):
        response = self._getFacade().updateTrigger(**data)
        return DirectResponse.succeed(data=response)
    
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail(
                'Error parsing filter source. Please check your syntax.')
    
    
    # notification subscriptions
    def getNotifications(self):
        response = self._getFacade().getNotifications()
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def addNotification(self, newId):
        response = self._getFacade().addNotification(newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def removeNotification(self, uid):
        response = self._getFacade().removeNotification(uid)
        return DirectResponse.succeed(data=response)
    
    def getNotification(self, uid):
        response = self._getFacade().getNotification(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))
        
    def updateNotification(self, **data):
        response = self._getFacade().updateNotification(**data)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    
    # subscription windows
    def getWindows(self, uid):
        response = self._getFacade().getWindows(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def addWindow(self, contextUid, newId):
        response = self._getFacade().addWindow(contextUid, newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def removeWindow(self, uid):
        response = self._getFacade().removeWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def getWindow(self, uid):
        response = self._getFacade().getWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))
    
    def updateWindow(self, **data):
        response = self._getFacade().updateWindow(data)
        return DirectResponse.succeed(data=Zuul.marshal(response))

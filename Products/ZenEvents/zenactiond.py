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

import Globals
import os
import re
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

# set up the zope environment
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

from Products.ZenUtils import Utils
from zenoss.protocols.protobufs.zep_pb2 import Signal
from Products.ZenModel.interfaces import IAction, IProvidesEmailAddresses, IProvidesPagerAddresses
from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumerProcess
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask

from zenoss.protocols.amqpconfig import getAMQPConfiguration
from zope.interface import implements

import logging
log = logging.getLogger("zen.zenactiond")


class NotificationDao(object):
    def __init__(self):
        self.app = Zope2.app()
        self.dmd = self.app.zport.dmd
        self.notification_manager = self.dmd.getDmdRoot(NotificationSubscriptionManager.root)
    
    def getNotifications(self):
        return self.notification_manager.getChildNodes()
    
    def getSignalNotifications(self, signal):
        """
        Given a signal, find which notifications match this signal. In order to
        match, a notification must be active (enabled and if has maintenance
        windows, at least one must be active) and must be subscribed to the 
        signal.
        
        @param signal: The signal for which to get subscribers.
        @type signal: protobuf zep.Signal
        """
        active_matching_notifications = []
        for notification in self.getNotifications():
            # if notification.isActive() and self.notificationSubscribesToSignal(notification, signal):
            
            # @TODO: This condition is temporary; exists only to start QA.
            # if notification.isActive() and self.notificationSubscribesToSignal(notification, signal):
            if notification.isActive():
                active_matching_notifications.append(notification)
                log.info('Found matching notification: %s' % notification)
            else:
                log.info('Notification "%s" is not active.' % notification)
        return active_matching_notifications
    
    def notificationSubscribesToSignal(self, notification, signal):
        """
        Determine if the notification matches the specified signal.
        
        @param notification: The notification to check
        @type notification: NotificationSubscription
        @param signal: The signal to match.
        @type signal: zenoss.protocols.protbufs.zep_pb2.Signal
        
        @rtype boolean
        """
        return signal.trigger.uuid in notification.subscriptions
    

class EmailAction(object):
    implements(IAction)
    
    def __init__(self, email_from, host, port, useTls, user, password):
        self.email_from = email_from
        self.host = host
        self.port = port
        self.useTls = useTls
        self.user = user
        self.password = password
    
    def execute(self, target, notification, signal):
        """
        """
        log.debug('Executing action: Email')
        
        subject = notification.getSubject(signal)
        body = notification.getBody(signal)
        
        log.debug('Sending this subject: %s' % subject)
        log.debug('Sending this body: %s' % body)
        
        plain_body = MIMEText(self._stripTags(body))
        email_message = plain_body
        
        if notification.body_content_type == 'html':
            log.debug('Sending HTML email.')
            email_message = MIMEMultipart('related')
            
            email_message_alternateive = MIMEMultipart('alternative')
            
            email_message_alternateive.attach(plain_body)
            
            html_body = MIMEText(body.replace('\n', '<br />\n'))
            html_body.set_type('text/html')
            email_message_alternateive.attach(html_body)
            
            email_message.attach(email_message_alternateive)
            
        email_message['Subject'] = subject
        email_message['From'] = self.email_from
        email_message['To'] = target
        email_message['Date'] = formatdate(None, True)
        
        result, errorMsg = Utils.sendEmail(
            email_message,
            self.host,
            self.port,
            self.useTls,
            self.user,
            self.password
        )
        
        if result:
            log.info("Notification '%s' sent email to:%s",
                notification.id, target)
        else:
            log.info("Notification '%s' failed to send email to %s: %s",
                notification.id, target, errorMsg)
    
    def getActionableTargets(self, target):
        if IProvidesEmailAddresses.providedBy(target):
            return target.getEmailAddresses()
    
    def _stripTags(self, data):
        """A quick html => plaintext converter
           that retains and displays anchor hrefs
           
           stolen from the old zenactions.
           @todo: needs to be updated for the new data structure?
        """
        tags = re.compile(r'<(.|\n)+?>', re.I|re.M)
        aattrs = re.compile(r'<a(.|\n)+?href=["\']([^"\']*)[^>]*?>([^<>]*?)</a>', re.I|re.M)
        anchors = re.finditer(aattrs, data)
        for x in anchors: data = data.replace(x.group(), "%s: %s" % (x.groups()[2], x.groups()[1]))
        data = re.sub(tags, '', data)
        return data

class PageAction(object):
    implements(IAction)
    
    def __init__(self, page_command=None):
        self.page_command = page_command
    
    def execute(self, target, notification, signal):
        """
        @TODO: handle the deferred parameter on the sendPage call.
        """
        log.debug('Executing action: Page')
        
        subject = self._parseFormat(notification.subject_format, signal)
        
        success, errorMsg = Utils.sendPage(
            target, subject, self.page_command,
            #deferred=self.options.cycle)
            deferred=False)
            
        if success:
            log.info('Success sending page to %s: %s' % (target, subject))
        else:
            log.info('Failed to send page to %s: %s %s' % (target, subject, errorMsg))
    
    def getActionableTargets(self, target):
        if IProvidesPagerAddresses.providedBy(target):
            return target.getPagerAddresses()


class ProcessSignalTask(object):
    implements(IQueueConsumerTask)

    def __init__(self, notificationDao):
        super(ProcessSignalTask, self).__init__()
        self.notificationDao = notificationDao
        
        # set by the constructor of queueConsumer
        self.queueConsumer = None
        
        config = getAMQPConfiguration()
        queue = config.getQueue("$Signals")
        binding = queue.getBinding("$Signals")
        self.exchange = binding.exchange.name
        self.routing_key = binding.routing_key
        self.exchange_type = binding.exchange.type
        self.queue_name = queue.name
        
        self.action_registry = {}
        
    def registerAction(self, action, actor):
        """
        Map an action to an IAction object.
        
        @TODO: Check that actor implements IAction
        """
        self.action_registry[action] = actor
    
    def getAction(self, action):
        if action in self.action_registry:
            return self.action_registry[action]
        else:
            raise Exception('Cannot perform unregistered action: "%s"' % action)
    
    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        
        if message.content.body == self.queueConsumer.MARKER:
            log.info("Received MARKER sentinel, exiting message loop")
            self.queueConsumer.acknowledge(message)
            return
        
        try:
            signal = Signal()
            signal.ParseFromString(message.content.body)
            self.processSignal(signal)
            
        except Exception, e:
            # Do not acknowledge the message, let it go and try again.
            # @TODO: make this submit this error to some sort of queue.
            log.exception(e)
            log.error('Acknowledging broken message.')
            self.queueConsumer.acknowledge(message)
            
        else:
            # ack only if no errors
            self.queueConsumer.acknowledge(message)
        
    def processSignal(self, signal):
        matches = self.notificationDao.getSignalNotifications(signal)
        log.debug('Found these matching notifications: %s' % matches)
        
        for notification in matches:
            # this getAction maps an instance of each action (when registered 
            # via registerAction())
            action = self.getAction(notification.action)
            
            # For User/Group/Role targets, figure out their end-targets and 
            # add them to this list. After we figure out all the end-targets
            # we will parse the excplicit recipients as well. After we do that
            # we can create a set from this list and end up with a unique list
            # so we don't inadvertantly send out multiple emails to multiple
            # peple.
            targets = []
            
            # recipients are objects like Users, Groups, Roles
            for recipient in notification.getRecipients():
                
                for target in action.getActionableTargets(recipient):
                    targets.append(target)
            
            # these derived targets handle anything the user has manually
            # input as a target. We have to assume that the derived targets
            # make sense for this notification's action.
            for derived_target in notification.getExplicitRecipients():
                targets.append(derived_target)
            
            for target in set(targets):
                log.debug('executing action for target: %s' % target)
                action.execute(target, notification, signal)
                

if __name__ == '__main__':
    
    task = ProcessSignalTask(NotificationDao())
    
    dmd = Zope2.app().zport.dmd
    email_action = EmailAction(
        email_from = dmd.getEmailFrom(),
        host = dmd.smtpHost,
        port = dmd.smtpPort,
        useTls = dmd.smtpUseTLS,
        user = dmd.smtpUser,
        password = dmd.smtpPass
    )
    task.registerAction('email', email_action)
    task.registerAction('page', PageAction(page_command=dmd.pageCommand))
    
    consumer = QueueConsumerProcess(task)
    options, args = consumer.server.parser.parse_args()
    logging.basicConfig(level=options.logseverity)
    
    consumer.run()

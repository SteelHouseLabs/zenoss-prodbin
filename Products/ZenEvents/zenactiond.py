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
import socket
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

# set up the zope environment
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

from Products.ZenUtils import Utils
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.guid.guid import GUIDManager
from Products.ZenUtils.ProcessQueue import ProcessQueue
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from zenoss.protocols.protobufs.zep_pb2 import Signal
from zenoss.protocols.jsonformat import to_dict
from Products.ZenModel.interfaces import IAction, IProvidesEmailAddresses, IProvidesPagerAddresses
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenModel.NotificationSubscription import NotificationSubscriptionManager
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumerProcess
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ReactorNotRunning

from zenoss.protocols.amqpconfig import getAMQPConfiguration
from zope.interface import implements

import logging
log = logging.getLogger("zen.zenactiond")

class ActionExecutionException(Exception): pass

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
            if notification.isActive():
                if self.notificationSubscribesToSignal(notification, signal):
                    active_matching_notifications.append(notification)
                    log.info('Found matching notification: %s' % notification)
                else:
                    log.debug('Notification "%s" does not subscribe to this signal.' % notification)
            else:
                log.debug('Notification "%s" is not active.' % notification)
                
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
        return signal.subscriber_uuid == IGlobalIdentifier(notification).getGUID()
    
def _signalToContextDict(signal):
    """
    Returns a dict that looks something like:
    
    {
        'signal': {
            'uuid': u '0e25a363-47c9-4535-a981-ae2149c279af',
            'clear': False,
            'trigger_uuid': u 'ccd90790-53c7-4970-a1c4-585c77c3bdca',
            'created_time': 1290666301343L,
            'message': u 'Example test message.',
            'subscriber_uuid': u 'ef089864-7008-412f-9db4-d717ac53c16e'
        },
        'eventSummary': {
            'status': 1,
            'count': 47,
            'status_change_time': 1290638268357L,
            'first_seen_time': 1290638268357L,
            'last_seen_time': 1290666301246L,
            'uuid': u '1c3f8493-6eb9-4ba8-9260-9e33abd8e390'
        },
        'event': {
            'severity': 2,
            'actor': {
                'element_identifier': u 'local vm',
                'element_sub_identifier': u '',
                'element_uuid': u '0f7c9fce-8417-46b2-90f9-f9a132a2490a',
                'element_type_id': 1
            },
            'summary': u 'Example test message.',
            'fingerprint': u 'localhost||/Unknown||6|Example test message.',
            'created_time': 1290666301246L,
            'message': u 'Example test message.',
            'event_key': u '',
            'event_class': u '/Unknown',
            'monitor': u 'localhost'
        }
    }
    """
    
    data = {}
    signal = to_dict(signal)
    summary = signal['event']
    del signal['event']
    
    data['signal'] = signal
    
    if 'occurrence' in summary and summary['occurrence']:
        event = summary['occurrence'][0]
        del summary['occurrence']
        
        # TODO: pass in device obj
        event['eventUrl'] = getEventUrl(summary['uuid'])
        event['ackUrl'] = getAckUrl(summary['uuid'])
        event['deleteUrl'] = getDeleteUrl(summary['uuid'])
        event['eventsUrl'] = getEventsUrl(summary['uuid'])
        event['undeleteUrl'] = getUndeleteUrl(summary['uuid'])
        
        data['event'] = event
        
    data['eventSummary'] = summary
    return data
        
def getBaseUrl(device=None):
    url = 'http://%s:%d' % (socket.getfqdn(), 8080)
    if device:
        return "%s%s" % (url, device.getPrimaryUrlPath())
    else:
        return "%s/zport/dmd/Events" % (url)
        
def getEventUrl(evid, device=None):
    return "%s/viewDetail?evid=%s" % (getBaseUrl(device), evid)
    
def getEventsUrl(device=None):
    return "%s/viewEvents" % getBaseUrl(device)
    
def getAckUrl(evid, device=None):
    return "%s/manage_ackEvents?evids=%s&zenScreenName=viewEvents" % (
        getBaseUrl(device), evid)
        
def getDeleteUrl(evid, device=None):
    return "%s/manage_deleteEvents?evids=%s" % (
        getBaseUrl(device), evid) + \
        "&zenScreenName=viewHistoryEvents"
        
def getUndeleteUrl(evid, device=None):
    return "%s/manage_undeleteEvents?evids=%s" % (
        getBaseUrl(device), evid) + \
        "&zenScreenName=viewEvents"
            
    
class TargetableAction(object):
    implements(IAction)
    
    def __init__(self):
        self.guidManager = GUIDManager(Zope2.app().zport.dmd)    
    
    def getTargets(self, notification):
        targets = set([])
        for recipient in notification.recipients:
            if recipient['type'] in ['group', 'user']:
                guid = recipient['value']
                target_obj = self.guidManager.getObject(guid)
                for target in self.getActionableTargets(target_obj):
                    targets.add(target)
            else:
                targets.add(recipient['value'])
        return targets
                
    def getActionableTargets(self, target_obj):
        raise NotImplementedError()
    
    def execute(self, notification, signal):
        for target in self.getTargets(notification):
            try:
                self.executeOnTarget(notification, signal, target)
                log.debug('Done executing action for target: %s' % target)
            except ActionExecutionException, e:
                # If there is an error executing this action on a target, 
                # we need to handle it, but we don't want to prevent other
                # actions from executing on any other targets that may be
                # about to be acted on.
                # @FIXME: Make this do something better for failed execution
                # per target.
                log.error(e)
                log.error('Error executing action for target: {target}, {notification} with signal: {signal}'.format(
                    target = target,
                    notification = notification,
                    signal = signal,
                ))
        
    def executeOnTarget(self):
        raise NotImplementedError()


class EmailAction(TargetableAction):
    
    def __init__(self, email_from, host, port, useTls, user, password):
        self.email_from = email_from
        self.host = host
        self.port = port
        self.useTls = useTls
        self.user = user
        self.password = password
        super(EmailAction, self).__init__()
    
    def executeOnTarget(self, notification, signal, target):
        log.debug('Executing action: Email')
        
        
        data = _signalToContextDict(signal)
        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = notification.getClearSubject(**data)
            body = notification.getClearBody(**data)
        else:
            subject = notification.getSubject(**data)
            body = notification.getBody(**data)
        
        log.debug('Sending this subject: %s' % subject)
        log.debug('Sending this body: %s' % body)
        
        plain_body = MIMEText(self._stripTags(body))
        email_message = plain_body
        
        if notification.body_content_type == 'html':
            email_message = MIMEMultipart('related')
            email_message_alternative = MIMEMultipart('alternative')
            email_message_alternative.attach(plain_body)
            
            html_body = MIMEText(body.replace('\n', '<br />\n'))
            html_body.set_type('text/html')
            email_message_alternative.attach(html_body)
            
            email_message.attach(email_message_alternative)
            
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
            log.info("Notification '%s' sent email to: %s",
                notification.id, target)
        else:
            raise ActionExecutionException(
                "Notification '%s' failed to send email to %s: %s" % 
                (notification.id, target, errorMsg)
            )
    
    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesEmailAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
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


class PageAction(TargetableAction):
    
    def __init__(self, page_command=None):
        self.page_command = page_command
        super(PageAction, self).__init__()
    
    def executeOnTarget(self, notification, signal, target):
        """
        @TODO: handle the deferred parameter on the sendPage call.
        """
        log.debug('Executing action: Page')
        
        
        data = _signalToContextDict(signal)
        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = notification.getClearSubject(**data)
        else:
            subject = notification.getSubject(**data)
            
        success, errorMsg = Utils.sendPage(
            target, subject, self.page_command,
            #deferred=self.options.cycle)
            deferred=False)
            
        if success:
            log.info("Notification '%s' sent page to %s." % (notification, target))
        else:
            raise ActionExecutionException("Notification '%s' failed to send page to %s. (%s)" % (notification, target, errorMsg))
    
    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesPagerAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
        if IProvidesPagerAddresses.providedBy(target):
            return target.getPagerAddresses()


class EventCommandProtocol(ProcessProtocol):
    
    def __init__(self, cmd):
        self.cmd = cmd
        self.data = ''
        self.error = ''

    def timedOut(self, value):
        log.error("Command '%s' timed out" % self.cmd.id)
        # FIXME: send an event or something?
        return value

    def processEnded(self, reason):
        log.debug("Command finished: '%s'" % reason.getErrorMessage())
        code = 1
        try:
            code = reason.value.exitCode
        except AttributeError:
            pass

        if code == 0:
            cmdData = self.data or "<command produced no output>"
            # FIXME: send an event or something?
        else:
            cmdError = self.error or "<command produced no output>"
            # FIXME: send an event or something?

    def outReceived(self, text):
        self.data += text

    def errReceived(self, text):
        self.error += text

class CommandAction(object):
    implements(IAction)
    
    def __init__(self, processQueue):
        self.processQueue = processQueue
    
    def execute(self, notification, signal):
        log.debug('Executing action: Command')
        
        
        data = _signalToContextDict(signal)
        if signal.clear:
            command = notification.getClearBody(**data)
        else:
            command = notification.getBody(**data)
        
        log.debug('Executing this command: %s' % command)
        
        
        # FIXME: Construct the context for this command before parsing with TAL
        device = None
        component = None
        data = {}
        
        compiled = talesCompile('string:' + command)
        environ = {'dev':device, 'component':component, 'evt':data }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
            
        _protocol = EventCommandProtocol(command)
        
        log.info('Queueing up command action process.')
        self.processQueue.queueProcess(
            '/bin/sh', 
            ('/bin/sh', '-c', res),
            env=None, 
            processProtocol=_protocol,
            timeout=int(notification.action_timeout),
            timeout_callback=_protocol.timedOut
        )
    
    def getActionableTargets(self, target):
        """
        Commands do not act _on_ targets, they are only executed.
        """
        pass

class ProcessSignalTask(object):
    implements(IQueueConsumerTask)

    def __init__(self, notificationDao, dmd):
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
        log.debug('processing message.')
        
        if message.content.body == self.queueConsumer.MARKER:
            log.info("Received MARKER sentinel, exiting message loop")
            self.queueConsumer.acknowledge(message)
            return
        
        try:
            signal = Signal()
            signal.ParseFromString(message.content.body)
            self.processSignal(signal)
            log.info('Done processing signal.')
        except Exception, e:
            log.exception(e)
            # FIXME: Send to an error queue instead of acknowledge.
            log.error('Acknowledging broken message.')
            self.queueConsumer.acknowledge(message)
            
        else:
            log.info('Acknowledging message. (%s)' % signal.message)
            self.queueConsumer.acknowledge(message)
        
    def processSignal(self, signal):
        matches = self.notificationDao.getSignalNotifications(signal)
        log.debug('Found these matching notifications: %s' % matches)
        
        for notification in matches:
            action = self.getAction(notification.action)
            
            try:
                action.execute(notification, signal)
            except ActionExecutionException, e:
                log.error(e)
                log.error('Error executing action: {notification} with signal: {signal}'.format(
                    notification = notification,
                    signal = signal,
                ))
                    
        log.debug('Done processing signal. (%s)' % signal.message)

class ZenActionD(ZCmdBase):
    def run(self):
        
        dmd = Zope2.app().zport.dmd
        task = ProcessSignalTask(NotificationDao(), dmd)
          
        # FIXME: Make this parameter an option on the daemon.
        # 10 is the number of parallel processes to use.
        self._processQueue = ProcessQueue(10)
        self._processQueue.start()
        
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
        task.registerAction('command', CommandAction(self._processQueue))
        
        self._consumer = QueueConsumerProcess(task)
        
        log.debug('starting zenactiond consumer.')
        self._consumer.run()

    def shutdown(self, *ignored):
        log.debug('Shutting down zenactiond consumer.')
        self._processQueue.stop()

    def _start(self):
        log.info('starting queue consumer task')
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()


    @defer.inlineCallbacks
    def _shutdown(self, *ignored):
        if self._consumer:
            yield self._consumer.shutdown()
        try:
            reactor.stop()
        except ReactorNotRunning:
            pass

if __name__ == '__main__':
    zad = ZenActionD()
    zad.run()
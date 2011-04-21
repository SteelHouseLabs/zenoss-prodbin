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

import re
import socket

from zope.interface import implements
from zope.component import getUtilitiesFor

from twisted.internet.protocol import ProcessProtocol

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

from Products.ZenModel.interfaces import IAction
from Products.Zuul.interfaces.actions import IEmailActionContentInfo, IPageActionContentInfo, ICommandActionContentInfo, ISnmpTrapActionContentInfo
from Products.Zuul.form.interfaces import IFormBuilder

from Products.ZenModel.interfaces import IAction, IProvidesEmailAddresses, IProvidesPagerAddresses, IProcessSignal
from Products.ZenModel.NotificationSubscription import NotificationEventContextWrapper

from Products.ZenUtils.ZenTales import talesCompile, getEngine
from Products.ZenUtils import Utils
from Products.ZenUtils.guid.guid import GUIDManager
from Products.ZenUtils.ProcessQueue import ProcessQueue

from Products.ZenUtils.ZenTales import talEval

import logging
log = logging.getLogger("zen.actions")



class ActionExecutionException(Exception): pass
class ActionMissingException(Exception): pass

def processTalSource(source, **kwargs):
    """
    This function is used to parse fields made available to actions that allow
    for TAL expressions.
    """
    sourceStr = source
    context = kwargs.get('here', {})
    context.update(kwargs)
    return talEval(sourceStr, context, kwargs)

def _signalToContextDict(signal):
    summary = signal.event
    # build basic event context wrapper for notifications
    if signal.clear:
        data = NotificationEventContextWrapper(summary, signal.clear_event)
    else:
        data = NotificationEventContextWrapper(summary)

    # add urls to event context
    data['urls']['eventUrl'] = getEventUrl(summary.uuid)
    data['urls']['ackUrl'] = getAckUrl(summary.uuid)
    data['urls']['closeUrl'] = getCloseUrl(summary.uuid)
    # TODO: pass in device obj
    data['urls']['eventsUrl'] = getEventsUrl()
    data['urls']['reopenUrl'] = getReopenUrl(summary.uuid)

    # now process all custom processors that might be registered to enhance
    # the event context
    for key, processor in getUtilitiesFor(IProcessSignal):
        data[key] = processor.process(signal)

    return data

def getBaseUrl(device=None):
    url = 'http://%s:%d' % (socket.getfqdn(), 8080)
    if device:
        return "%s%s" % (url, device)#.getPrimaryUrlPath())
    else:
        return "%s/zport/dmd/Events" % (url)

def getEventUrl(evid, device=None):
    return "%s/viewDetail?evid=%s" % (getBaseUrl(device), evid)

def getEventsUrl(device=None):
    return "%s/viewEvents" % getBaseUrl(device)

def getAckUrl(evid, device=None):
    return "%s/manage_ackEvents?evids=%s&zenScreenName=viewEvents" % (
        getBaseUrl(device), evid)

def getCloseUrl(evid, device=None):
    return "%s/manage_deleteEvents?evids=%s" % (
        getBaseUrl(device), evid) + \
        "&zenScreenName=viewHistoryEvents"

def getReopenUrl(evid, device=None):
    return "%s/manage_undeleteEvents?evids=%s" % (
        getBaseUrl(device), evid) + \
        "&zenScreenName=viewEvents"



class IActionBase(object):
    """
    Mixin class for provided some common, necessary, methods.
    """

    def getInfo(self, notification):
        return self.actionContentInfo(notification)
    
    def generateJavascriptContent(self, notification):
        content = self.getInfo(notification)
        return IFormBuilder(content).render(fieldsets=False)


class TargetableAction(object):

    def setupAction(self, dmd):
        """
        Some actions need to configure themselves with properties from the dmd.
        This is their opportunity to do so.
        """
        pass
    
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

    def execute(self, notification, signal):
        self.setupAction(notification.dmd)

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



class EmailAction(IActionBase, TargetableAction):
    implements(IAction)
    id = 'email'
    name = 'Email'
    actionContentInfo = IEmailActionContentInfo

    def __init__(self):
        super(EmailAction, self).__init__()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.email_from = dmd.getEmailFrom()
        self.host = dmd.smtpHost
        self.port = dmd.smtpPort
        self.useTls = dmd.smtpUseTLS
        self.user = dmd.smtpUser
        self.password = dmd.smtpPass

    def executeOnTarget(self, notification, signal, target):
        log.debug('Executing action: Email')

        data = _signalToContextDict(signal)
        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = processTalSource(notification.content['clear_subject_format'], **data)
            body = processTalSource(notification.content['clear_body_format'], **data)
        else:
            subject = processTalSource(notification.content['subject_format'], **data)
            body = processTalSource(notification.content['body_format'], **data)

        log.debug('Sending this subject: %s' % subject)
        log.debug('Sending this body: %s' % body)

        plain_body = MIMEText(self._stripTags(body))
        email_message = plain_body

        if notification.content['body_content_type'] == 'html':
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

    def updateContent(self, content=None, data=None):
        updates = dict()
        updates['body_content_type'] = data.get('body_content_type', 'html')

        properties = ['subject_format', 'body_format', 'clear_subject_format', 'clear_body_format',]
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)


class PageAction(IActionBase, TargetableAction):
    implements(IAction)

    id = 'page'
    name = 'Page'
    actionContentInfo = IPageActionContentInfo

    def __init__(self):
        super(PageAction, self).__init__()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.page_command = dmd.pageCommand

    def executeOnTarget(self, notification, signal, target):
        """
        @TODO: handle the deferred parameter on the sendPage call.
        """
        log.debug('Executing action: Page')

        data = _signalToContextDict(signal)
        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = processTalSource(notification.content['clear_subject_format'], **data)
        else:
            subject = processTalSource(notification.content['subject_format'], **data)

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

    def updateContent(self, content=None, data=None):
        updates = dict()

        properties = ['subject_format', 'clear_subject_format',]
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)




def commandFactory():
    # not sure how we're going to make this configurable.
    defaultMaxCommands = 10
    processQueue = ProcessQueue(defaultMaxCommands)
    processQueue.start()
    return CommandAction(processQueue)

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

class CommandAction(IActionBase):
    implements(IAction)

    id = 'command'
    name = 'Command'
    actionContentInfo = ICommandActionContentInfo

    def __init__(self, processQueue):
        self.processQueue = processQueue

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)

    def execute(self, notification, signal):
        self.setupAction(notification.dmd)
        
        log.debug('Executing action: Command')

        if signal.clear:
            command = notification.content['clear_body_format']
        else:
            command = notification.content['body_format']
        
        log.debug('Executing this command: %s' % command)


        actor = signal.event.occurrence[0].actor
        device = None
        if actor.element_uuid:
            device = self.guidManager.getObject(actor.element_uuid)

        component = None
        if actor.element_sub_uuid:
            component = self.guidManager.getObject(actor.element_sub_uuid)

        
        environ = {'dev':device, 'component':component }
        data = _signalToContextDict(signal)
        environ.update(data)

        command = processTalSource(command, **environ)
        log.debug('Executing this compiled command: "%s"' % command)

        _protocol = EventCommandProtocol(command)

        log.info('Queueing up command action process.')
        self.processQueue.queueProcess(
            '/bin/sh',
            ('/bin/sh', '-c', command),
            env=None,
            processProtocol=_protocol,
            timeout=int(notification.content['action_timeout']),
            timeout_callback=_protocol.timedOut
        )

    def getActionableTargets(self, target):
        """
        Commands do not act _on_ targets, they are only executed.
        """
        pass

    def updateContent(self, content=None, data=None):
        updates = dict()

        properties = ['body_format', 'clear_body_format', 'action_timeout']
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)


class SNMPTrapAction(IActionBase):
    implements(IAction)

    id = 'trap'
    name = 'SNMP Trap'
    actionContentInfo = ISnmpTrapActionContentInfo

    _sessions = {}

    def _getSession(self, destination):
        if destination not in self._sessions:
            log.debug("Creating SNMP trap session to %s", destination)
            self._sessions[destination] = netsnmp.Session((
                '-v2c', '-c', 'public', '%s:162' % destination))
            self._sessions[destination].open()

        return self._sessions.get(destination)

    def execute(self, notification, signal):
        """
        Send out an SNMP trap according to the definition in ZENOSS-MIB.
        """
        log.debug('Processing SNMP Trap action.')

        data = _signalToContextDict(signal)
        eventSummary = data['eventSummary']
        event = eventSummary
        actor = event.get['actor']

        baseOID = '1.3.6.1.4.1.14296.1.100'

        fields = {
           'uuid' :                   ( 1, eventSummary),
           'fingerprint' :            ( 2, event),
           'element_identifier' :     ( 3, actor),
           'element_sub_identifier' : ( 4, actor),
           'event_class' :            ( 5, event),
           'event_key' :              ( 6, event),
           'summary' :                ( 7, event),
           'severity' :               ( 9, event),
           'status' :                 (10, eventSummary),
           'event_class_key' :        (11, event),
           'event_group' :            (12, event),
           'state_change_time' :      (13, eventSummary),
           'first_seen_time' :        (14, eventSummary),
           'last_seen_time' :         (14, eventSummary),
           }

        varbinds = []

        for field, oidspec in sorted(fields.items(), key=lambda x : x[1][0]):
            i, source = oidspec
            val = source.get(field, None)
            if val is not None:
                varbinds.append(("%s.%d.0" % (baseOID,i), 's', str(val)))

        self._getSession(notification.content['action_destination']).sendTrap(
            baseOID + '.0.0.1', varbinds=varbinds)

    def updateContent(self, content=None, data=None):
        content['action_destination'] = data.get('action_destination')

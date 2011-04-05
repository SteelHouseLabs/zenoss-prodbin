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
import re
import Migrate
import logging
from Products.ZenModel.ZenossSecurity import *
from Products.ZenEvents.WhereClause import toPython

from Products import Zuul
from Products.ZenModel.NotificationSubscriptionWindow import NotificationSubscriptionWindow

log = logging.getLogger( 'zen.migrate' )


def talesifyLegacyFormatString(s, refRe = re.compile(r"%\((?P<attr>[^)]+)\)s")):
   return refRe.sub(lambda m : '${' + m.group('attr') + '}',s)

class TriggerRuleSourceError(Exception): pass

class AddTriggersAndNotifications(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def __init__(self):
        Migrate.Step.__init__(self)
        import addTriggers
        self.dependencies = [ addTriggers.triggers ]

    def _parseRule(self, rule):
        python_statement = toPython(rule.genMeta(), rule.where)

        # if the parser failed to parse the where clause, the python statement
        # will be empty.
        if not python_statement:
            raise TriggerRuleSourceError(rule.where)

        log.debug('Parsing From: "%s"' % rule.where)
        log.debug('        To  : "%s"' % python_statement)
        return python_statement

    def _parseContent(self, content):
        return talesifyLegacyFormatString(content)
    
    def _createTrigger(self, rule):
        log.debug('Creating trigger for: %s' % rule.id)

        new_rule_source = self._parseRule(rule)
        
        # make the rules unique - per user
        trigger_name = '%s - %s' % (rule.id, rule.getUser().getId())

        for t in self.existing_triggers:
            if trigger_name == t['name']:
                log.debug('Trigger already exists, not creating.')
                return self.triggers_facade.getTrigger(t['uuid'])
        
        trigger_uuid = self.triggers_facade.addTrigger(trigger_name)
            
        trigger = self.triggers_facade.getTrigger(trigger_uuid)
        trigger['enabled'] = rule.enabled
        trigger['rule']['source'] = new_rule_source


        trigger_obj = self.dmd.Triggers.findChild(trigger_name)

        # Just add the user of the alert rule as an owner on this trigger,
        # don't worry about moving ownership off admin or anything like that.
        trigger_obj.manage_addLocalRoles(rule.getUser().getId(), [OWNER_ROLE])

        self.triggers_facade.updateTrigger(**trigger)

        return trigger


    def _createNotification(self, rule, trigger):
        log.debug('Creating notification for: %s (%s)' % (rule.id, rule.action))

        notification_name = '%s - %s' % (rule.id, rule.getUser().getId())

        for n in self.existing_notifications:
            if notification_name == n.name:
                log.debug('Notification already exists, not creating.')
                return

        self.triggers_facade.addNotification(notification_name, rule.action)

        notification_obj = self.dmd.NotificationSubscriptions.findChild(notification_name)

        # make the rule owner also an owner of this notification object.
        notification_obj.manage_addLocalRoles(rule.getUser().getId(), [OWNER_ROLE])

        notification_obj.enabled = rule.enabled
        notification_obj.send_clear = rule.sendClear
        notification_obj.send_initial_occurrence = True
        notification_obj.delay_seconds = rule.delay
        notification_obj.repeat_seconds = rule.repeatTime

        notification_obj.subscriptions = [trigger['uuid']]

        notification_obj.body_content_type = 'text' if rule.plainText else 'html'

        notification_obj.body_format = self._parseContent(rule.body)
        notification_obj.subject_format = self._parseContent(rule.format)
        notification_obj.clear_body_format = self._parseContent(rule.clearBody)
        notification_obj.clear_subject_format = self._parseContent(rule.clearFormat)

        # add the rule owner as a recipient of this notification, with full
        # permissions.
        recipient = self.triggers_facade.fetchRecipientOption(rule.getUser())
        recipient.update(dict(write=True, manage=True))
        recipients = [recipient]

        if rule.targetAddr:
            recipients.append(dict(
                type = 'manual',
                label = rule.targetAddr,
                value = rule.targetAddr
            ))

        notification_obj.recipients = recipients
        
        log.debug('Creating new windows for this notification...')
        for window in rule.windows.objectValues():
            log.debug('Copying window: %s' % window.id)
            nsw = NotificationSubscriptionWindow(window.id)

            window_props = ['name', 'start', 'started', 'duration', 'repeat',
                         'startProductionState','stopProductionState',
                         'enabled', 'skip']

            for prop in window_props:
                log.debug('Setting property on new window: %s = %s' % (prop, getattr(window, prop)))
                setattr(nsw, prop, getattr(window, prop))

            # set window properties
            notification_obj.windows.addRelation(nsw)

        log.debug('Have these windows: %r' % notification_obj.windows.objectValues())

        self.triggers_facade.updateNotificationSubscriptions(notification_obj)

    def cutover(self, dmd):

        self.dmd = dmd
        self.triggers_facade = Zuul.getFacade('triggers', dmd)

        self.existing_triggers = self.triggers_facade.getTriggers()
        self.existing_notifications = self.triggers_facade.getNotifications()
        
        # action rules are being removed, make sure they haven't been yet.
        rules = []
        if hasattr(dmd.ZenUsers, 'getAllActionRules'):
            rules = dmd.ZenUsers.getAllActionRules()

        failed = False
        for rule in rules:
            try:
                trigger = self._createTrigger(rule)
                self._createNotification(rule, trigger)
                log.info('Done processing rule: %s.' % rule.id)
            except TriggerRuleSourceError, e:
                failed = True
                log.warn('Unable to parse existing rule: %s' % rule.id)

        if failed:
            log.info('If any rules were unable to be migrated, they will need to'
            ' be manually migrated to triggers and notifications. You can access'
            ' the old Alerting Rules through the ZMI.')

addTriggersAndNotifications = AddTriggersAndNotifications()

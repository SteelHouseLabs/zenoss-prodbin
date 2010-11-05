###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger("zen.notifications")
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import * 
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM

NotificationSubscriptionsId = 'NotificationSubscriptions'

def manage_addNotificationSubscriptionManager(context, REQUEST=None):
    """Create the notification subscription manager."""
    nsm = NotificationSubscriptionManager(NotificationSubscriptionsId)
    context._setObject(NotificationSubscriptionsId, nsm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

class NotificationSubscriptionManager(ZenModelRM):
    """Manage notification subscriptions.
    
    @todo: change the icon parameter in factory_type_information.
    """
    
    security = ClassSecurityInfo()

    _id = "NotificationSubscriptionManager"
    root = 'NotificationSubscriptions'
    meta_type = _id

    sub_meta_types = ("NotificationSubscription",)

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Management of notification subscriptions""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addNotificationSubscriptionManager',
            'immediate_view' : 'editSettings',
            'actions'        : (
                { 
                    'id'            : 'settings',
                    'name'          : 'Settings',
                    'action'        : '../editSettings',
                    'permissions'   : ( ZEN_MANAGE_DMD, )
                })
         },
    )
    
    
addNotificationSubscription = DTMLFile('dtml/addNotificationSubscription',globals())

def manage_addNotificationSubscription(context, id, title = None, REQUEST = None):
    """Create a notification subscription"""
    ns = NotificationSubscription(id, title)
    context._setObject(id, ns)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

class NotificationSubscription(ZenModelRM):
    """
    A subscription to a signal that produces notifications in the form of
    actions.
    """
    _id = "NotificationSubscription"
    meta_type = _id
    
    enabled = False
    action_types = ('email', 'page')
    action = 'email'
    content_types = ('text', 'html')
    body_content_type = 'html'
    
    subject_format = "[zenoss] %(device)s %(summary)s"
    body_format =  "Device: %(device)s\n" \
        "Component: %(component)s\n" \
        "Severity: %(severityString)s\n" \
        "Time: %(firstTime)s\n" \
        "Message:\n%(message)s\n" \
        "<a href=\"%(eventUrl)s\">Event Detail</a>\n" \
        "<a href=\"%(ackUrl)s\">Acknowledge</a>\n" \
        "<a href=\"%(deleteUrl)s\">Delete</a>\n" \
        "<a href=\"%(eventsUrl)s\">Device Events</a>\n"
    
    clear_subject_format = "[zenoss] CLEAR: %(device)s %(clearOrEventSummary)s"
    clear_body_format =  "Event: '%(summary)s'\n" \
        "Cleared by: '%(clearSummary)s'\n" \
        "At: %(clearFirstTime)s\n" \
        "Device: %(device)s\n" \
        "Component: %(component)s\n" \
        "Severity: %(severityString)s\n" \
        "Message:\n%(message)s\n" \
        "<a href=\"%(undeleteUrl)s\">Undelete</a>\n"
        
    # targets may be: page numbers, email addresses, users, groups, roles, or urls.
    # this list should be all the same type.
    targets = []
    
    # the targets_source property will hold whatever the user types in, such
    # as a list of emails or whatever else they put in. For each action this
    # will be combined with the targets - the result will filter duplicates out.
    targets_source = ''

    # a list of triggers that this notification is subscribed to.
    subscription_uuids = []

    _properties = ZenModelRM._properties + (
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'action', 'type':'text', 'mode':'w'},
        {'id':'body_content_type', 'type':'text', 'mode':'w'},
        {'id':'subject_format', 'type':'text', 'mode':'w'},
        {'id':'body_format', 'type':'text', 'mode':'w'},
        {'id':'clear_subject_format', 'type':'text', 'mode':'w'},
        {'id':'clear_body_format', 'type':'text', 'mode':'w'},
        {'id':'targets_source', 'type':'text', 'mode':'w'},
    )

    _relations = (
        ("windows", 
        ToManyCont(
            ToOne, 
            "Products.ZenModel.NotificationSubscriptionWindow", 
            "notificationSubscription"
        )),
    )

    factory_type_information = ( 
        { 
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Define the notification and the signals to
                which it is subscribed.""",
            # @todo: fix this icon
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addNotificationSubscription',
            'immediate_view' : 'editNotificationSubscription',
            'actions'        :( 
                {
                    'id'            : 'edit',
                    'name'          : 'Edit',
                    'action'        : 'editNotificationSubscription',
                    'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                }
            )
         },
    )

    security = ClassSecurityInfo()
    
    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editNotificationSubscription')
    def manage_editNotificationSubscription(self, REQUEST=None):
        """Update notification subscription properties"""
        return self.zmanage_editProperties(REQUEST)
    
    def getTargets(self):
        """
        Return the list of all of the 'targets' for this subscription. If 
        groups, roles or zenoss users are subscribing, this will determine
        the actual targets for the notifications (if a group is subscribed, 
        the emails for all of the group members will become targets).
        
        @todo implement
        """
        return self.targets_source.split(',')
    
    def isActive(self):
        """
        Using maintenance windows and `enabled`, determine if this notification
        is active for right now.
        """
        if self.enabled:
            log.debug('Notification is enabled: %s' %  self.id)
            windows = self.windows()
            if windows:
                log.debug('Notification has (%s) windows.' % len(windows))
                for window in windows:
                    if window.isActive():
                        log.debug('Notification has active window: %s' % window.id)
                        return True
            else:
                log.debug('Notification is enabled, but has no windows, it is active.')
                return True
        else:
            log.debug('Notification NOT enabled: %s' %  self.id)
            return False
    
    def matchesSignal(self, signal):
        """
        Determine if this notification subscription matches the specified signal.
        
        @param trigger: The signal to match.
        @type trigger: zenoss.protocols.protbufs.zep_pb2.Signal
        
        @rtype boolean
        """
        log.debug('Trying to match uuid to subscriptions.')
        return signal.trigger.uuid in self.subscription_uuids

InitializeClass(NotificationSubscriptionManager)
InitializeClass(NotificationSubscription)
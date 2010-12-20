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
"""
Operations for Events.

Available at:  /zport/dmd/evconsole_router
"""

import time
import logging
import DateTime # Zope DateTime, not python datetime
from uuid import uuid4
from zope.component import getUtility
from Products.ZenUtils.Ext import DirectRouter
from AccessControl import getSecurityManager
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenUtils.Time import isoDateTimeFromMilli
from Products.Zuul import getFacade
from Products.Zuul.decorators import require
from Products.ZenEvents.Event import Event as ZenEvent
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenEvents.EventClass import EventClass
from zenoss.protocols.services.zep import EventStatus, EventSeverity
from json import loads
from Products.Zuul.utils import resolve_context
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.ZenUI3.browser.eventconsole.grid import column_config

log = logging.getLogger('zen.%s' % __name__)

class EventsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """


    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.zep = getFacade('zep', context)
        self.api = getFacade('event', context)

    def _mapToOldEvent(self, event_summary):
        eventOccurrence = event_summary['occurrence'][0]

        eventClass = eventOccurrence['event_class']

        event = {
            'id' : event_summary['uuid'],
            'evid' : event_summary['uuid'],
            'device' : {
                'text': eventOccurrence['actor'].get('element_identifier', None),
                'uid': None,
                'url' : self._uuidUrl(eventOccurrence['actor'].get('element_uuid', None)),
                'uuid' : eventOccurrence['actor'].get('element_uuid', None)
            },
            'component' : {
                'text': eventOccurrence['actor'].get('element_sub_identifier', None),
                'uid': None,
                'url' : self._uuidUrl(eventOccurrence['actor'].get('element_sub_uuid', None)),
                'uuid' : eventOccurrence['actor'].get('element_sub_uuid', None)
            },
            'firstTime' : isoDateTimeFromMilli(event_summary['first_seen_time']),
            'lastTime' : isoDateTimeFromMilli(event_summary['last_seen_time'] ),
            'eventClass' : {"text": eventClass, "uid": "/zport/dmd/Events%s" % eventClass},
            'eventKey' : eventOccurrence.get('event_key', None),
            'summary' : eventOccurrence['summary'],
            'severity' : eventOccurrence['severity'],
            'eventState' : EventStatus.getPrettyName(event_summary['status']),
            'count' : event_summary['count'],
        }

        return event

    def _timeRange(self, value):
        values = []
        for t in value.split('/'):
            values.append(DateTime.DateTime(t, datefmt='us').millis())
        return values

    @require('ZenCommon')
    def queryArchive(self, limit=0, start=0, sort='lastTime', dir='desc', params=None, uid=None):
        filter = self._buildFilter(uid, params)

        events = self.zep.getEventSummariesFromArchive(limit=limit, offset=start, sort=(sort, dir), filter=filter)

        return DirectResponse.succeed(
            events = [self._mapToOldEvent(e) for e in events['events']],
            totalCount = events['total'],
            asof = time.time()
        )

    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='desc', params=None,
              archive=False, uid=None):
        """
        Query for events.

        @type  limit: integer
        @param limit: (optional) Max index of events to retrieve (default: 0)
        @type  start: integer
        @param start: (optional) Min index of events to retrieve (default: 0)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        if archive:
            return self.queryArchive(limit=limit, start=start, sort=sort, dir=dir, params=params, uid=uid)

        filter = self._buildFilter(uid, params)

        events = self.zep.getEventSummaries(limit=limit, offset=start, sort=(sort, dir), filter=filter)

        return DirectResponse.succeed(
            events = [self._mapToOldEvent(e) for e in events['events']],
            totalCount = events['total'],
            asof = time.time()
        )

    def _buildFilter(self, uid, params):
        """
        Query for events.
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        """
        if params:
            params = loads(params)
            filter = self.zep.createFilter(
                uuid = params.get('evid'),
                fingerprint = params.get('dedupid'),
                summary = params.get('summary'),
                event_class = params.get('eventClass'),
                status = [i for i in params.get('eventState', [])],
                severity = params.get('severity'),
                tags = params.get('tags'),
                count = params.get('count'),
                element_identifier = params.get('device'),
                element_sub_identifier = params.get('component'),
                first_seen = params.get('firstTime') and self._timeRange(params.get('firstTime')),
                last_seen = params.get('lastTime') and self._timeRange(params.get('lastTime')),
            )
        else:
            filter = {}

        if uid is None:
            uid = self.context

        context = resolve_context(uid)

        if context and context.id != 'Events':
            tags = filter.setdefault('tag_uuids', [])

            try:
                tags.append(IGlobalIdentifier(context).getGUID())
            except TypeError:
                if isinstance(context, EventClass):
                    filter['event_class'] = context.getDmdKey()
                else:
                    raise Exception('Unknown context %s' % context)

        return filter

    def _uuidUrl(self, uuid):
        if uuid:
            return '/zport/dmd/goto?guid=%s' % uuid;

    @require('ZenCommon')
    def detail(self, evid):
        """
        Get event details.

        @type  evid: string
        @param evid: Event ID to get details
        @type  history: boolean
        @param history: Deprecated
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - event: ([dictionary]) List containing a dictionary representing
                    event details
        """
        event_summary = self.zep.getEventSummary(evid)
        if event_summary:
            eventOccurrence = event_summary['occurrence'][0]

            eventClass = eventOccurrence['event_class']
            eventData = {
                'evid' : event_summary['uuid'],
                'device' : eventOccurrence['actor'].get('element_identifier', None),
                'device_title' : eventOccurrence['actor'].get('element_identifier', None),
                'device_url' : self._uuidUrl(eventOccurrence['actor'].get('element_uuid', None)),
                'device_uuid' : eventOccurrence['actor'].get('element_uuid', None),
                'component' : eventOccurrence['actor'].get('element_sub_identifier', None),
                'component_title' : eventOccurrence['actor'].get('element_sub_identifier', None),
                'component_url' : self._uuidUrl(eventOccurrence['actor'].get('element_sub_uuid', None)),
                'component_uuid' : eventOccurrence['actor'].get('element_sub_uuid', None),
                'firstTime' : isoDateTimeFromMilli(event_summary['first_seen_time']),
                'lastTime' : isoDateTimeFromMilli(event_summary['last_seen_time']),
                'eventClass' : eventClass,
                'eventClass_url' : "/zport/dmd/Events%s" % eventClass,
                'severity' : eventOccurrence['severity'],
                'eventState' : EventStatus.getPrettyName(event_summary['status']),
                'count' : event_summary['count'],
                'summary' : eventOccurrence.get('summary'),
                'message' : eventOccurrence.get('message'),
                'properties' : [
                    dict(key=k, value=v) for (k, v) in {
                        'evid' : event_summary['uuid'],
                        'device' : eventOccurrence['actor'].get('element_identifier', None),
                        'component' : eventOccurrence['actor'].get('element_sub_identifier', None),
                        'firstTime' : isoDateTimeFromMilli(event_summary['first_seen_time']),
                        'lastTime' : isoDateTimeFromMilli(event_summary['last_seen_time']),
                        'stateChange' : isoDateTimeFromMilli(event_summary['status_change_time']),
                        'dedupid' : eventOccurrence['fingerprint'],
                        'eventClass' : eventClass,
                        'eventClassKey' :  eventOccurrence['event_class'],
                        'eventClassMapping_uuid' : self._uuidUrl(eventOccurrence.get('event_class_mapping_uuid')),
                        'eventKey' : eventOccurrence.get('event_key', None),
                        'summary' : eventOccurrence.get('summary'),
                        'severity' : eventOccurrence.get('severity'),
                        'eventState' : EventStatus.getPrettyName(event_summary['status']),
                        'count' : event_summary['count'],
                        'monitor' : eventOccurrence.get('monitor'),
                        'agent' : eventOccurrence.get('agent'),
                        'message' : eventOccurrence.get('message'),
                    }.iteritems() if v
                ],
                'log' : []
            }

            if 'notes' in event_summary:
                for note in event_summary['notes']:
                    eventData['log'].append((note['user_name'], isoDateTimeFromMilli(note['created_time']), note['message']))

            if 'details' in eventOccurrence:
                for detail in eventOccurrence['details']:
                    values = detail['value']
                    if not isinstance(values, list):
                        values = list(values)

                    for value in (v for v in values if v):
                        eventData['properties'].append(dict(key=detail['name'], value=value))

            return DirectResponse.succeed(event=[eventData])
        else:
            raise Exception('Could not find event %s' % evid)

    @require('Manage Events')
    def write_log(self, evid=None, message=None, history=False):
        """
        Write a message to an event's log.

        @type  evid: string
        @param evid: Event ID to log to
        @type  message: string
        @param message: Message to log
        @type  history: Deprecated
        @rtype:   DirectResponse
        @return:  Success message
        """

        userName = getSecurityManager().getUser().getId()

        self.zep.addNote(uuid=evid, message=message, userName=userName)

        return DirectResponse.succeed()

    @require('Manage Events')
    def close(self, evids=None, excludeIds=None, selectState=None, field=None,
              direction=None, params=None, history=False, uid=None, asof=None):
        """
        Close event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to close (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           close (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only close if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.zep.closeEventSummary(evids[0])
        return DirectResponse.succeed()

    @require('Manage Events')
    def acknowledge(self, evids=None, excludeIds=None, selectState=None,
                    field=None, direction=None, params=None, history=False,
                    uid=None, asof=None):
        """
        Acknowledge event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to acknowledge (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           acknowledgment (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only acknowledge if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context

        userName = getSecurityManager().getUser().getId()
        self.zep.acknowledgeEventSummary(evids[0], userName=userName)
        return DirectResponse.succeed()

    @require('Manage Events')
    def unacknowledge(self, *args, **kwargs):
        """
        @Deprecated Use reopen
        """
        return self.reopen(*args, **kwargs)

    @require('Manage Events')
    def reopen(self, evids=None, excludeIds=None, selectState=None, field=None,
               direction=None, params=None, history=False, uid=None, asof=None):
        """
        Reopen event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to reopen (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           reopen (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only reopen if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.zep.reopenEventSummary(evids[0])
        return DirectResponse.succeed()

    @require('Manage Events')
    def add_event(self, summary, device, component, severity, evclasskey, evclass):
        """
        Create a new event.

        @type  summary: string
        @param summary: New event's summary
        @type  device: string
        @param device: Device uid to use for new event
        @type  component: string
        @param component: Component uid to use for new event
        @type  severity: string
        @param severity: Severity of new event. Can be one of the following:
                         Critical, Error, Warning, Info, Debug, or Clear
        @type  evclasskey: string
        @param evclasskey: The Event Class Key to assign to this event
        @type  evclass: string
        @param evclass: Event class for the new event
        @rtype:   DirectResponse
        """

        event = ZenEvent(
            evid=str(uuid4()),
            summary=summary,
            device=device,
            component=component,
            severity=severity,
            eventClassKey=evclasskey,
            eventClass=evclass,
        )

        publisher = getUtility(IEventPublisher)
        publisher.publish(event, mandatory=True)

        return DirectResponse.succeed(evid=event.evid)

    def _convertSeverityToNumber(self, sev):
        return EventSeverity.getNumber(sev)

    def _convertSeverityToName(self, sevId):
        return EventSeverity.getName(sevId)

    @property
    def configSchema(self):
        configSchema =[{
                'id': 'event_age_disable_severity',
                'name': _t("Don't Age This Severity and Above"),
                'xtype': 'severity',
                'fromZep': self._convertSeverityToNumber,
                'toZep': self._convertSeverityToName,
                },{
                'id': 'event_age_interval_minutes',
                'name': _t('Event Aging Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 60,
                'allowNegative': False,
                },{
                'id': 'event_archive_interval_days',
                'name': _t('Event Archive Interval (days)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'maxValue': 30,
                'allowNegative': False,
                },{
                'id': 'event_archive_purge_interval_days',
                'maxValue': 90,
                'name': _t('Delete Historical Events Older Than (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'event_occurrence_purge_interval_days',
                'maxValue': 30,
                'name': _t('Event Occurrence Purge Interval (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'default_syslog_priority',
                'name': _t('Default Syslog Priority'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'value': self.context.dmd.ZenEventManager.defaultPriority
                }]
        return configSchema

    def _mergeSchemaAndZepConfig(self, data, config):
        """
        Copy the values and defaults from ZEP to our schema
        """
        for conf in config:
            if not data.get(conf['id']):
                continue
            prop = data[conf['id']]
            for key in prop.keys():
                conf[key] = prop[key]
            # our drop down expects severity to be the number constant
            if conf.get('fromZep'):
                conf['defaultValue'] = conf['fromZep']((prop['defaultValue']))
                if prop['value']:
                    conf['value'] = conf['fromZep']((prop['value']))
                del conf['fromZep']
            if conf.get('toZep'):
                del conf['toZep']
        return config

    @require('ZenCommon')
    def getConfig(self):
        data = self.zep.getConfig()
        config = self._mergeSchemaAndZepConfig(data, self.configSchema)
        return DirectResponse.succeed(data=config)

    @require('Manage DMD')
    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        for config in self.configSchema:
            id = config['id']
            if config.get('toZep'):
                values[id] = config['toZep'](values[id])

        # we store default syslog priority on the event manager
        if values.get('default_syslog_priority'):
            pri = values.get('default_syslog_priority')
            self.context.dmd.ZenEventManager.defaultPriority = pri
            del values['default_syslog_priority']
        self.zep.setConfigValues(values)
        return DirectResponse.succeed()

    def column_config(self, uid=None, archive=False):
        """
        Get the current event console field column configuration.

        @type  uid: string
        @param uid: (optional) UID context to use (default: None)
        @type  archive: boolean
        @param archive: (optional) True to use the event archive instead
                        of active events (default: False)
        @rtype:   [dictionary]
        @return:  A list of objects representing field columns
        """
        return column_config(self.request, archive)

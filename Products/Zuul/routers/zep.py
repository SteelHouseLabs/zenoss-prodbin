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

from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul import getFacade
from Products.Zuul.decorators import require
from Products.Zuul.routers.events import EventsRouter
from datetime import datetime
from zenoss.protocols.protobufs.zep_pb2 import EventSummary, Event

log = logging.getLogger(__name__)

# TODO Temporarily extend EventsRouter till all methods are implemented
class ZepRouter(EventsRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """

    def __init__(self, context, request):
        super(ZepRouter, self).__init__(context, request)
        self.zep = getFacade('zep', context)
        self.api = getFacade('event', context)

    def _mapToOldEvent(self, event_summary):
        def statusToName(status):
            enum = EventSummary.DESCRIPTOR.fields_by_name['status'].enum_type
            return enum.values_by_number[status].name.replace('STATUS_', '').lower().title()

        def severityToName(severity):
            enum = Event.DESCRIPTOR.fields_by_name['severity'].enum_type
            map = {
                'SEVERITY_CLEAR' : 0,
                'SEVERITY_DEBUG' : 1,
                'SEVERITY_INFO' : 2,
                'SEVERITY_WARNING' : 3,
                'SEVERITY_ERROR' :  4,
                'SEVERITY_CRITICAL' : 5,
            }

            return map[enum.values_by_number[severity].name]

        eventClass = event_summary['occurrence'][0]['event_class']
        event = {
            'id' : event_summary['uuid'],
            'evid' : event_summary['uuid'],
            'device' : {'text': event_summary['occurrence'][0]['actor'].get('element_identifier', None), 'uid': None},
            'component' : {'text': event_summary['occurrence'][0]['actor'].get('element_sub_identifier', None), 'uid': None},
            'created' : str(datetime.utcfromtimestamp(event_summary['occurrence'][0]['created_time'] / 1000)),
            'firstTime' : str(datetime.utcfromtimestamp(event_summary['first_seen_time'] / 1000)),
            'lastTime' : str(datetime.utcfromtimestamp(event_summary['last_seen_time'] / 1000)),
            'eventClass' : {"text": eventClass, "uid": "/zport/dmd/Events%s" % eventClass},
            'dedupid' : event_summary['occurrence'][0]['fingerprint'],
            'eventKey' : event_summary['occurrence'][0]['event_class_key'],
            'summary' : event_summary['occurrence'][0]['summary'],
            'severity' : severityToName(event_summary['occurrence'][0]['severity']),
            'eventState' : statusToName(event_summary['status']),
            'count' : event_summary['count'],

            #IGuidManager(dmd).getObject(uuid)

        }

        return event

    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='DESC', params=None,
              history=False, uid=None, criteria=()):
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
        @type  criteria: [dictionary]
        @param criteria: (optional) A list of key-value pairs to to build query's
                         where clause (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        if uid is None:
            uid = self.context

        events = self.zep.getEventSummaries(limit, start, sort)

        return DirectResponse.succeed(
            events = [self._mapToOldEvent(e) for e in events['events']],
            totalCount = events['total'],
            asof = time.time()
        )

    @require('ZenCommon')
    def detail(self, evid, history=False):
        """
        Get event details.

        @type  evid: string
        @param evid: Event ID to get details
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - event: ([dictionary]) List containing a dictionary representing
                    event details
        """
        event = self.zep.getEventSummary(evid)
        if event:
            return DirectResponse.succeed(event=[self._mapToOldEvent(event)])
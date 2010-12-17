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

import logging
import re
import random
from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
from Products.Zuul.utils import resolve_context

import pkg_resources
from zenoss.protocols.services.zep import ZepServiceClient, EventSeverity, EventStatus, ZepConfigClient
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSummaryFilter, NumberCondition, EventSort
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_INFO, SEVERITY_DEBUG

log = logging.getLogger(__name__)

class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    _opMap = {
        '<' : NumberCondition.LT,
        '>' : NumberCondition.GT,
        '>=' : NumberCondition.GTEQ,
        '<=' : NumberCondition.LTEQ,
        '=' : NumberCondition.EQ,
        None : NumberCondition.EQ,
    }

    _sortMap = {
        'eventstate' : EventSort.STATUS,
        'severity' : EventSort.SEVERITY,
        'firsttime' : EventSort.FIRST_SEEN,
        'lasttime' : EventSort.LAST_SEEN,
        'eventclass' : EventSort.EVENT_CLASS,
        'device' : EventSort.ELEMENT_IDENTIFIER,
        'component' : EventSort.ELEMENT_SUB_IDENTIFIER,
        'count' : EventSort.COUNT,
        'summary' : EventSort.EVENT_SUMMARY,
    }

    _sortDirectionMap  = {
        'asc' : EventSort.ASCENDING,
        'desc' : EventSort.DESCENDING,
    }

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)

        config = getGlobalConfiguration()
        zep_url = config.get('zep_uri', 'http://localhost:8084')
        self.client = ZepServiceClient(zep_url)
        self.configClient = ZepConfigClient(zep_url)

    def createFilter(self,
        uuid=[],
        summary=None,
        event_class=None,
        status=[],
        severity=[],
        first_seen=None,
        last_seen=None,
        status_change=None,
        tags=[],
        count=None,
        element_identifier=None,
        element_sub_identifier=None,
        fingerprint=None):
        filter = {}

        if uuid:
            filter['uuid'] = [uuid]

        if summary:
            filter['event_summary'] = str(summary).strip()

        if event_class:
            filter['event_class'] = str(event_class).strip()

        if status:
            filter['status'] = status

        if severity:
            filter['severity'] = severity

        if first_seen:
            filter['first_seen'] = first_seen

        if last_seen:
            filter['last_seen'] = last_seen

        if status_change:
            filter['status_change'] = status_change

        if tags:
            filter['tag_uuids'] = tags

        if count:
            filter['count'] = count

        if fingerprint:
            filter['fingerprint'] = fingerprint

        if element_identifier:
            filter['element_identifier'] = str(element_identifier).strip()

        if element_sub_identifier:
            filter['element_sub_identifier'] = str(element_sub_identifier).strip()

        return filter

    def _timeRange(self, timeRange):
        d = {
            'start_time' : timeRange[0],
        }

        if len(timeRange) == 2:
            d['end_time'] = timeRange[1]

        return d

    def getEventSummariesFromArchive(self, offset, limit=100, keys=None, sort=None, filter={}):
        return self._getEventSummaries(self.client.getEventSummariesFromArchive, offset=offset, limit=limit, keys=keys, sort=sort, filter=filter)

    def getEventSummaries(self, offset, limit=100, keys=None, sort=None, filter={}):
        return self._getEventSummaries(self.client.getEventSummaries, offset=offset, limit=limit, keys=keys, sort=sort, filter=filter)

    def _getEventSummaries(self, source, offset, limit=100, keys=None, sort=None, filter={}):
        filterBuf = None
        if filter:
            filterBuf = self._buildFilterProtobuf(filter)

        eventSort = None
        if sort:
            eventSort = self._buildSortProtobuf(sort)

        response, content = source(offset=offset, limit=limit, keys=keys, sort=eventSort, filter=filterBuf)
        return {
            'total' : content.total,
            'limit' : content.limit,
            'next_offset' : content.next_offset,
            'events' : (to_dict(event) for event in content.events),
        }

    def _buildSortProtobuf(self, sort):
        if isinstance(sort, (list, tuple)):
            eventSort = from_dict(EventSort, {
                'field' : self._sortMap[sort[0].lower()],
                'direction' : self._sortDirectionMap[sort[1].lower()]
            })
        else:
            eventSort = from_dict(EventSort, { 'field' : self._sortMap[sort.lower()] })
        return eventSort

    def _buildFilterProtobuf(self, filter):
        # Build protobuf filter
        if 'count' in filter:
            m = re.match(r'^(?P<op>>|<|=|>=|<=)?(?P<num>[0-9]+)$', filter['count'])
            if m:
                filter['count'] = {
                    'op' : self._opMap[m.groupdict()['op']],
                    'value' : int(m.groupdict()['num']),
                }
            else:
                raise Exception('Invalid count filter %s' % filter['count'])

        if 'first_seen' in filter:
            filter['first_seen'] = self._timeRange(filter['first_seen'])

        if 'last_seen' in filter:
            filter['last_seen'] = self._timeRange(filter['last_seen'])

        return from_dict(EventSummaryFilter, filter)

    def _getUserUuid(self, userName):
        # Lookup the user uuid
        user = self._dmd.ZenUsers.getUserSettings(userName)
        if user:
            return IGlobalIdentifier(user).getGUID()

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)

    def addNote(self, uuid, message, userName, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)
            if not userUuid:
                raise Exception('Could not find user "%s"' % userName)

        self.client.addNote(uuid, message, userUuid, userName)

    def closeEventSummary(self, uuid):
        return self.client.closeEventSummary(uuid)

    def acknowledgeEventSummary(self, uuid, userName=None, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)
            if not userUuid:
                raise Exception('Could not find user "%s"' % userName)

        return self.client.acknowledgeEventSummary(uuid, userUuid)

    def reopenEventSummary(self, uuid):
        return self.client.reopenEventSummary(uuid)

    def getConfig(self):
        config = self.configClient.getConfig()
        return config

    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        self.configClient.setConfigValues(values)

    def setConfigValue(self, name, value):
        self.configClient.setConfigValue(name, value)

    def removeConfigValue(self, name):
        self.configClient.removeConfigValue(name)

    def getEventSeveritiesByUuid(self, tagUuid):
        return self.getEventSeverities([tagUuid])[tagUuid]

    def getEventSeverities(self, tagUuids):
        """
        Get a dictionary of the event severity counds for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @rtype: dict
        @return: A dictionary of UUID -> { C{EventSeverity} -> count }
        """
        response, content = self.client.getEventSeverities(tagUuids)
        if content:
            # Pre-populate the list with count = 0 to make sure all tags request exist in the result
            severities = dict.fromkeys(tagUuids, dict.fromkeys(EventSeverity.numbers, 0))
            for tag in content.severities:
                # Since every element is using a shared default dict we can't just updated it, we
                # have to create a new copy, otherwise we are just updating the same dict.
                severities[tag.tag_uuid] = dict.fromkeys(EventSeverity.numbers, 0)
                severities[tag.tag_uuid].update((sev.severity, sev.count) for sev in tag.severities)

            return severities

    def getWorstSeverityByUuid(self, tagUuid, default=SEVERITY_CLEAR, ignore=None):
        return self.getWorstSeverity([tagUuid], default=default, ignore=ignore)[tagUuid]

    def getWorstSeverity(self, tagUuids, default=SEVERITY_CLEAR, ignore=None):
        """
        Get a dictionary of the worst event severity for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @param default: The default severity to use if there are no results or if a severity is ignored
        @type default: An C{EventSeverity} enum value
        @param ignore: Severities to not include as worst, use the default instead.
        @type ignore: A list of C{EventSeverity} enum values
        @rtype: dict
        @return: A dictionary of UUID -> C{EventSeverity}
        """

        # Prepopulate the list with defaults
        severities = dict.fromkeys(tagUuids, default)
        response, content = self.client.getWorstSeverity(tagUuids)
        if content:
            for tag in content.severities:
                sev = tag.severities[0].severity
                severities[tag.tag_uuid] = default if ignore and sev in ignore else sev

            return severities

    def getSeverityName(self, severity):
        return EventSeverity.getPrettyName(severity)

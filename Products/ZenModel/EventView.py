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
log = logging.getLogger("zen.EventView")

from _mysql_exceptions import MySQLError

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from zope.interface import Interface, implements

from Products.ZenUtils.FakeRequest import FakeRequest
from Products.ZenUtils.Utils import unused
from Products.Zuul import getFacade
from Products.Zuul.decorators import deprecated
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier


class IEventView(Interface):
    """
    Marker interface for objects which have event views.
    """

class EventView(object):
    """
    This class provides convenience methods for retrieving events to any subclass. Note that
    this class is currently transitioning between the old event system and ZEP. Most of the methods
    are marked as deprecated except those that go through ZEP.

    """
    implements(IEventView)

    security = ClassSecurityInfo()

    @deprecated
    def getEventManager(self, table='status'):
        """Return the current event manager for this object.
        """
        if table=='history':
            return self.ZenEventHistory
        return self.ZenEventManager

    @deprecated
    def getEventHistory(self):
        """Return the current event history for this object.
        """
        return self.ZenEventHistory

    def getStatusString(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        # used to avoid pychecker complaint about wrong # of args to getStatus
        f = self.getStatus
        return self.convertStatus(f(statclass, **kwargs))

    @deprecated
    def getEventSummary(self, severity=1, state=1, prodState=None):
        """Return an event summary list for this managed entity.
        """
        return self.getEventManager().getEventSummaryME(self, severity, state, prodState)

    def getEventOwnerList(self, severity=0, state=1):
        """Return list of event owners for this mangaed entity.
        """
        return self.getEventManager().getEventOwnerListME(self, severity, state)

    def getStatusImgSrc(self, status):
        ''' Return the image source for a status number
        '''
        return self.getEventManager().getStatusImgSrc(status)

    def getStatusCssClass(self, status):
        """Return the css class for a status number.
        """
        return self.getEventManager().getStatusCssClass(status)

    @deprecated
    def getEventDetail(self, evid=None, dedupid=None, better=False):
        """
        Return an EventDetail for an event on this object.
        """
        evt = self.getEventManager().getEventDetail(evid, dedupid, better)
        return evt.__of__(self)

    @deprecated
    def getEventDetailFromStatusOrHistory(self, evid=None,
                                            dedupid=None, better=False):
        """
        Return the event detail for an event within the context of a device
        or other device organizer
        """
        evt = self.getEventManager().getEventDetailFromStatusOrHistory(
                                        evid, dedupid, better)
        return evt.__of__(self)

    @deprecated
    def convertEventField(self, field, value, default=""):
        return self.getEventManager().convertEventField(field, value, default)


    security.declareProtected('Manage Events','manage_addLogMessage')
    @deprecated
    def manage_addLogMessage(self, evid=None, message='', REQUEST=None):
        """
        Add a log message to an event
        """
        self.getEventManager().manage_addLogMessage(evid, message)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage Events','manage_deleteEvents')
    @deprecated
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        # If we pass REQUEST in to the getEventManager().manage_deleteEvents()
        # call we don't get a proper refresh of the event console.  It only
        # works if self.callZenScreen() is called from here rather than down
        # in the event manager.  I'm not sure why.  Using FakeResult to fetch
        # the message seems like best workaround for now.
        request = FakeRequest()
        self.getEventManager().manage_deleteEvents(evids, request)
        if REQUEST:
            request.setMessage(REQUEST)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteBatchEvents')
    @deprecated
    def manage_deleteBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        """
        unused(count)
        evids = self.getEventManager().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_deleteEvents(evids, request)
        return request.get('message', '')


    security.declareProtected('Manage Events','manage_undeleteEvents')
    @deprecated
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        request = FakeRequest()
        self.getEventManager().manage_undeleteEvents(evids, request)
        if REQUEST:
            request.setMessage(REQUEST)
            return self.callZenScreen(REQUEST)


    #security.declareProtected('Manage Events','manage_undeleteBatchEvents')
    @deprecated
    def manage_undeleteBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        Only called from event console, so uses FakeRequest to avoid
        page rendering.
        """
        unused(count)
        evids = self.getEventHistory().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_undeleteEvents(evids, request)
        return request.get('message', '')


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, REQUEST=None):
        """Delete events form this managed entity.
        """
        dev = self.device()
        if dev:
            return self.getEventManager().manage_deleteHeartbeat(dev.id, REQUEST)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    @deprecated
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        return self.getEventManager().manage_ackEvents(evids, REQUEST)


    security.declareProtected('Manage Events','manage_ackBatchEvents')
    @deprecated
    def manage_ackBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        Only called from event console, so uses FakeRequest to avoid
        page rendering.
        """
        unused(count)
        evids = self.getEventManager().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_ackEvents(evids, request)
        return request.get('message', '')


    security.declareProtected('Manage Events','manage_setEventStates')
    @deprecated
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        return self.getEventManager().manage_setEventStates(
                                                eventState, evids, REQUEST)


    security.declareProtected('Manage Events','manage_createEventMap')
    @deprecated
    def manage_createEventMap(self, eventClass=None, evids=(),
                              table='status', REQUEST=None):
        """Create an event map from an event or list of events.
        """
        screen = self.getEventManager(table).manage_createEventMap(
                                      eventClass, evids, REQUEST)
        if REQUEST:
            if screen: return screen
            return self.callZenScreen(REQUEST)

    def getStatus(self, statusclass=None, **kwargs):
        """
        Return the status number for this device of class statClass.
        """
        zep = getFacade('zep')
        filter = {
            'tag_uuids': [self.getUUID()],
            'severity': [3,4,5],
            'status': [1, 2]
            }
        if statusclass:
            filter['event_class'] = statusclass
        events = zep.getEventSummaries(0, filter=filter)
        count = len(list(events['events']))
        return count

    def getUUID(self):
        return IGlobalIdentifier(self).getGUID()

    def getEventSeveritiesCount(self):
        """
        Uses the zep facade to return a list of
        event summaries for this entity
        """
        zep = getFacade('zep')
        severities = zep.getEventSeveritiesByUuid(self.getUUID())
        results = dict((zep.getSeverityName(sev).lower(), count) for (sev, count) in severities.iteritems())
        return results

    def getWorstEventSeverity(self):
        """
        Uses Zep to return the worst severity for this object
        """
        zep = getFacade('zep')
        result =  zep.getWorstSeverityByUuid(self.getUUID())
        return result

InitializeClass(EventView)

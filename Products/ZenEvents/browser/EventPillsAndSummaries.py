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

import re

from Products.Five.browser import BrowserView
from Products.ZenUtils.jsonutils import json
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer

class SinglePill(BrowserView):
    def __call__(self):
        """
        Gets event pill for worst severity.

        @return: HTML that will render the event pill.
        @rtype: str
        """
        zem = self.context.dmd.ZenEventManager
        pill = getEventPillME(zem, self.context)
        if type(pill)==type([]) and len(pill)==1: return pill[0]
        return pill


class ObjectsEventSummary(BrowserView):
    """
    Return an HTML link and event pill for each object passed as a JSON
    object ready for inclusion in a YUI data table.

    @param objects: The objects for which to create links and pills.
    @type objects: list
    @return: A JSON-formatted string representation of the columns and rows
        of the table
    @rtype: string
    """
    @json
    def __call__(self):
        zem = self.context.dmd.ZenEventManager
        obs = self._getObs()
        return getDashboardObjectsEventSummary(zem, obs)

    def _getObs(self):
        raise NotImplementedError


class SubOrganizersEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return self.context.children()


class SubDevicesEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return self.context.devices()


class SingleObjectEventSummary(ObjectsEventSummary):
    def _getObs(self):
        return [self]


def getObjectsEventSummary(zem, objects, prodState=None, REQUEST=None):
    """
    Return an HTML link and event pill for each object passed as a JSON
    object ready for inclusion in a YUI data table.

    @param objects: The objects for which to create links and pills.
    @type objects: list
    @return: A JSON-formatted string representation of the columns and rows
        of the table
    @rtype: string
    """ 
    mydict = {'columns':[], 'data':[]}
    mydict['columns'] = ['Object', 'Events']
    getcolor = re.compile(r'class=\"evpill-(.*?)\"', re.S|re.I|re.M).search
    colors = "red orange yellow blue grey green".split()
    def pillcompare(a,b):
        a, b = map(lambda x:getcolor(x[1]), (a, b))
        def getindex(x):
            try: 
                color = x.groups()[0]
                smallcolor = x.groups()[0].replace('-acked','')
                isacked = 'acked' in color
                index = colors.index(x.groups()[0].replace('-acked',''))
                if isacked: index += .5
                return index
            except: return 5
        a, b = map(getindex, (a, b))
        return cmp(a, b)
    devdata = []
    for obj in objects:
        alink = obj.getPrettyLink()
        pill = getEventPillME(zem, obj, showGreen=True, prodState=prodState)
        if type(pill)==type([]): pill = pill[0]
        devdata.append([alink, pill])
    devdata.sort(pillcompare)
    mydict['data'] = [{'Object':x[0],'Events':x[1]} for x in devdata]
    return mydict


def getDashboardObjectsEventSummary(zem, objects, REQUEST=None):
    """
    Event summary that takes dashboard production state threshold into account.
    """
    thold = zem.dmd.prodStateDashboardThresh
    return getObjectsEventSummary(zem, objects, thold, REQUEST)


def _getPill(summary, url=None, number=3):
    iconTemplate = """
        <td class="severity-icon-small 
            %(severity)s %(noevents)s">
            %(count)s
        </td>
    """
    rainbowTemplate = """
    <table onclick="location.href='%(url)s';"
        class="eventrainbow eventrainbow_cols_%(number)s">
        <tr>%(cells)s</tr>
    </table>
    """
    stati = "critical error warning info debug".split()
    summary =[x[2] for x in summary]

    cells = []
    for i, count in enumerate(summary[:number]):
        cells.append(iconTemplate % {
            'noevents': '' if count else 'no-events',
            'severity': stati[i],
            'count':count
        })
    return rainbowTemplate % {
        'url': url,
        'cells': ''.join(cells),
        'number': number
    }

def getEventPill(zem, where, number=3, minSeverity=0, showGreen=True,
                 prodState=None, url=None):
    summary = zem.getEventSummary(where, minSeverity, prodState)
    return _getPill(summary, url, number)

def getEventPillME(zem, me, number=3, minSeverity=0, showGreen=True,
                   prodState=None):
    """
    Get HTML code displaying the maximum event severity and the number of
    events of that severity on a particular L{ManagedEntity} in a pleasing
    pill-shaped container. Optionally return pills for lesser severities as
    well. Optionally return a green pill if there are no events (normally no
    events in a severity will not yield a result).

    @param zem: A reference to ZenEventManager
    @type zem: L{Products.ZenEvents.EventManagerBase.EventManagerBase}
    @param me: The object regarding which event data should be queried.
    @type me: L{ManagedEntity}
    @param number: The number of pills to return
    @type number: int
    @param showGreen: Whether to return an empty green pill if all is well
    @type showGreen: bool
    @return: HTML strings ready for template inclusion
    @rtype: list
    """
    evsum = zem.getEventSummaryME(me, minSeverity, prodState=prodState)
    url = getEventsURL(me)
    return _getPill(evsum, url, number)


organizerTypes = {
    'Devices': 'devices',
    'Groups': 'groups',
    'Locations': 'locs',
    'Systems': 'systems'
}


def getEventsURL(me) :
    from Products.ZenModel.Device import Device
    if isinstance(me, DeviceOrganizer) :
        path = me.getPrimaryPath()
        url = ('/zport/dmd/itinfrastructure?filter=default#'
               '%s:%s:events_grid' % (
                   organizerTypes[path[3]], '.'.join(path)))
    elif isinstance(me, Device) :
        url = (me.getPrimaryUrlPath() +
               '/devicedetail?filter=default#'
               'deviceDetailNav:device_events')
    else:
        url = me.getPrimaryUrlPath()+'/viewEvents?filter=default'
    return url


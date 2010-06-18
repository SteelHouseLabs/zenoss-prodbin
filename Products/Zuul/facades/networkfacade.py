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

import logging
from itertools import imap

from Acquisition import aq_parent
from zope.interface import implements

from Products.Jobber.jobs import ShellCommandJob
from Products.ZenUtils.Utils import binPath
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade, INetworkFacade
from Products.Zuul.interfaces import IInfo, ICatalogTool
from Products.Zuul.tree import SearchResults

log = logging.getLogger('zen.NetworkFacade')


class NetworkFacade(TreeFacade):
    implements(INetworkFacade, ITreeFacade)

    def addSubnet(self, newSubnet, contextUid):
        return self._root.restrictedTraverse(contextUid).createNet(newSubnet)

    def deleteSubnet(self, uid):
        toDel = self._dmd.restrictedTraverse(uid)
        aq_parent(toDel)._delObject(toDel.id)
        return True

    def getIpAddresses(self, limit=0, start=0, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):

        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'

        brains = cat.search("Products.ZenModel.IpAddress.IpAddress",
                            start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        objs = imap(unbrain, brains)
        infos = imap(IInfo, objs)
        # convert to info objects
        return SearchResults(infos, brains.total, brains.hash_)

    def discoverDevices(self, uid):
        """
        Discover devices on input subnetwork
        """
        ip = '/'.join(self._dmd.restrictedTraverse(uid).getPrimaryPath()[4:])
        orgroot = self._root.restrictedTraverse(uid).getNetworkRoot()

        organizer = orgroot.getOrganizer(ip)
        if organizer is None:
            log.error("Couldn't obtain a network entry for '%s' "
                        "-- does it exist?" % ip)
            return False

        zDiscCommand = getattr(organizer, "zZenDiscCommand", None)
        if zDiscCommand:
            from Products.ZenUtils.ZenTales import talesEval
            cmd = talesEval('string:' + zDiscCommand, organizer).split(" ")
        else:
            cmd = ["zendisc", "run", "--net", organizer.getNetworkName()]
            if getattr(organizer, "zSnmpStrictDiscovery", False):
                cmd += ["--snmp-strict-discovery"]
            if getattr(organizer, "zPreferSnmpNaming", False):
                cmd += ["--prefer-snmp-naming"]
        zd = binPath('zendisc')
        zendiscCmd = [zd] + cmd[1:]
        return self._dmd.JobManager.addJob(ShellCommandJob, zendiscCmd)

    @property
    def _root(self):
        return self._dmd.Networks

    @property
    def _instanceClass(self):
        return "Products.ZenModel.IpAddress.IpAddress"

    def _getSecondaryParent(self, obj):
        return obj


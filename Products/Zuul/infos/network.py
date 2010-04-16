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

from zope.interface import implements
from Products.Zuul.interfaces import IIpNetworkInfo, IIpAddressInfo
from Products.Zuul.infos import InfoBase, ConfigProperty
from Products.Zuul.decorators import info

class IpNetworkInfo(InfoBase):
    implements(IIpNetworkInfo)

    @property
    def name(self):
        return self._object.getNetworkName()

    @property
    def ipcount(self):
        return str(self._object.countIpAddresses()) + '/' + \
               str(self._object.freeIps())

    # zProperties
    def inheritConfigProperty(configProp):
        def getICP(self):
            return not self._object.hasProperty(configProp)

        def setICP(self, isInherited):
            if isInherited:
                if self._object.hasProperty(configProp):
                    self._object.deleteZenProperty(configProp)

        return property(getICP, setICP)

    isInheritAutoDiscover = inheritConfigProperty('zAutoDiscover')
    autoDiscover = ConfigProperty('zAutoDiscover', 'boolean')

    isInheritDefaultNetworkTree = inheritConfigProperty('zDefaultNetworkTree')
    defaultNetworkTree = ConfigProperty('zDefaultNetworkTree', 'lines')

    isInheritDrawMapLinks = inheritConfigProperty('zDrawMapLinks')
    drawMapLinks = ConfigProperty('zDrawMapLinks', 'boolean')

    isInheritIcon = inheritConfigProperty('zIcon')
    icon = ConfigProperty('zIcon', 'string')
    
    isInheritPingFailThresh = inheritConfigProperty('zPingFailThresh')
    pingFailThresh = ConfigProperty('zPingFailThresh', 'int')


class IpAddressInfo(InfoBase):
    implements(IIpAddressInfo)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def pingstatus(self):
        if not self._object.interface():
            return 5
        return self._object.getPingStatus()

    @property
    def snmpstatus(self):
        if not self._object.interface():
            return 5
        return self._object.getSnmpStatus()

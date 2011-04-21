###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import zope.component
from Products.Five.browser import BrowserView
from Products.ZenModel.interfaces import IZenDocProvider

class EditZendoc(BrowserView):
    """
    Populates the component table that appears on the device status page.
    """
    def _getZendocProvider(self):
        return zope.component.queryAdapter( self.context,
                                            IZenDocProvider )

    def getZendoc(self):
        zendocProvider = self._getZendocProvider()
        return zendocProvider.getZendoc()

    def saveZendoc(self, zendocText):
        zendocProvider = self._getZendocProvider()
        zendocProvider.setZendoc( zendocText )



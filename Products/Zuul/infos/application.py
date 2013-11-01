##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implementer
from Products.Zuul.interfaces import IApplicationInfo


@implementer(IApplicationInfo)
class ApplicationInfo(object):
    """
    """

    def __init__(self, facade):
        """
        Initialize an instance of ApplicationInfo.

        :param IApplicationFacade application: The facade.
        """
        self._object = facade

    @property
    def id(self):
        return self._object.id

    @property
    def name(self):
        return self._object.name

    @property
    def text(self):
        return self._object.name

    @property
    def uid(self):
        return self._object.id

    @property
    def description(self):
        return self._object.description

    @property
    def qtip(self):
        return self._object.description

    @property
    def autostart(self):
        return self._object.autostart

    @property
    def isRestarting(self):
        return self._object.state == "STARTING"

    @property
    def state(self):
        return self._object.state

    @property
    def leaf(self):
        return True

    @property
    def children(self):
        return []

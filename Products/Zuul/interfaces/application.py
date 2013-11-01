##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Attribute
from Products.Zuul.interfaces import IFacade, IInfo


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    description = Attribute("Brief description of the application's function")
    autostart = Attribute("True if the application will run on startup")
    state = Attribute("Current running state of the application")


class IApplicationFacade(IFacade):
    """
    Interface for controlling and inspecting Zenoss applications.
    """

    name = Attribute("Name of the application")
    description = Attribute("Brief description of the application's function")
    autostart = Attribute("True if the application will run on startup")
    config = Attribute("The application configuration object")

    def getLog(lastCount):
        """
        Returns the given last count of lines of the log (as a string).
        """

    def start():
        """
        Starts the named application.
        """

    def stop():
        """
        Stops the named application.
        """

    def restart(name):
        """
        Restarts the named application.
        """


class IApplicationManagerFacade(IFacade):
    """
    Interface for locating Zenoss applications.
    """

    def query(name=None):
        """
        Returns a sequence of IApplication objects.
        """

    def get(id, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """

__all__ = (
    "IApplicationManagerFacade", "IApplicationFacade", "IApplicationInfo"
)

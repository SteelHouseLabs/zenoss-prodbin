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
from ..form.schema import TextLine
from . import IInfo, ITreeNode, IFacade
from Products.Zuul.utils import ZuulMessageFactory as _t


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """
    id = TextLine(title=_t("ID"),
        description=_t("Identifier of the running service"), readonly=True)
    
    description = TextLine(title=_t("Description"),
                           description=_t("Brief description of the application's function"),
                           readonly=True)
    autostart = TextLine(title=_t("AutoStart"),
                         description=_t("True if the application will run on startup"), readonly=True)
    
    state = TextLine(title=_t("State"),
                     description=_t("Current running state of the application"),
                     readonly=True)

    startup = TextLine(title=_t("Startup"),
                      description=_t("The command that this deamon runs when starting up"),
                      readonly=True)

    imageId = TextLine(title=_t("Image ID"),
                      description=_t("Image ID for this daemon."),
                      readonly=True)

    poolId = TextLine(title=_t("Pool ID"),
                      description=_t("The resource pool this daemon is running under."),
                      readonly=True)

    createdAt = TextLine(title=_t("Created At"),
                      description=_t("The time this deamon was created at."),
                      readonly=True)

    instances = TextLine(title=_t("Running Instances"),
                      description=_t("How many instances of this deamon are running."),
                      readonly=True)
    

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

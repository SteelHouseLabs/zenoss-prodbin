#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""MonitorClass

The service classification class.  default identifiers, screens,
and data collectors live here.

$Id: MonitorClass.py,v 1.11 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addMonitorClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = MonitorClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMonitorClass = DTMLFile('dtml/addMonitorClass',globals())

class MonitorClass(Classification, Folder):
    meta_type = "MonitorClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options


    def getStatusMonitor(self, monitorName):
        """get or create the status monitor name"""
        from Products.Confmon.StatusMonitorConf \
            import manage_addStatusMonitorConf
        statusMonitorObj = self.getOrganizer("Monitors").StatusMonitors
        if not hasattr(statusMonitorObj, monitorName):
            manage_addStatusMonitorConf(statusMonitorObj, monitorName)
        return statusMonitorObj._getOb(monitorName)


    def getStatusMonitorNames(self):
        """return a list of all status monitor names"""
        status = self.getOrganizer("Monitors").StatusMonitors
        return status.objectIds()
            

    def getCricketMonitor(self, monitorName):
        """get or create the cricket monitor name"""
        from Products.Confmon.CricketConf \
            import manage_addCricketConf
        cricketObj = self.getOrganizer("Monitors").Cricket
        if not hasattr(cricketObj, monitorName):
            manage_addCricketConf(cricketObj, monitorName)
        return cricketObj._getOb(monitorName)


    def getCricketMonitorNames(self):
        """return a list of all cricket monitor names"""
        cricket = self.getOrganizer("Monitors").Cricket
        return cricket.objectIds()
            


InitializeClass(MonitorClass)

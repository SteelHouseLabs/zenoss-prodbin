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

from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.Commandable import Commandable
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *
from Globals import InitializeClass
from EventFilter import EventFilter

class EventCommand(ZenModelRM, Commandable, EventFilter, ZenPackable):

    where = ''
    command = ''
    clearCommand = ''
    enabled = False
    delay = 0
    
    _properties = ZenModelRM._properties + (
        {'id':'command', 'type':'string', 'mode':'w'},
        {'id':'clearCommand', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'string', 'mode':'w'},
        {'id':'defaultTimeout', 'type':'int', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
    )
    
    _relations =  ZenPackable._relations + (
        ("eventManager", ToOne(ToManyCont, "Products.ZenEvents.EventManagerBase", "commands")),
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'editEventCommand',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editEventCommand'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def getEventFields(self):
        return self.eventManager.getFieldList()

    def getUserid(self):
        return ''

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(EventCommand, self).breadCrumbs(terminator)
        url = aq_parent(self).absolute_url_path() + "/listEventCommands"
        crumbs.insert(-1,(url,'Event Commands'))
        return crumbs

    
    def manage_beforeDelete(self, item, container):
        """Clear state in alert_state before we are deleted.
        """
        self._clearAlertState()


    def sqlwhere(self):
        """Return sql where to select alert_state data for this event.
        """
        return "userid = '' and rule = '%s'" % (self.id)

    def _clearAlertState(self):
        """Clear state in alert_state before we are deleted.
        """
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            delcmd = "delete from alert_state where %s" % self.sqlwhere()
            curs = self.dmd.ZenEventManager.cursor()
            curs.execute(delcmd)
        finally: zem.close(conn)


    security.declareProtected('Manage EventManager', 'manage_editEventCommand')
    def manage_editEventCommand(self, REQUEST=None):
        "edit the commands run when events match"
        import WhereClause
        if REQUEST and not REQUEST.form.has_key('where'):
            clause = WhereClause.fromFormVariables(self.genMeta(), REQUEST.form)
            if clause:
                REQUEST.form['where'] = clause
        return self.zmanage_editProperties(REQUEST)
        
    
InitializeClass(EventCommand)

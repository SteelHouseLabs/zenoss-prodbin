import logging
log = logging.getLogger("zen.EventView")

from _mysql_exceptions import MySQLError

from Globals import DTMLFile, InitializeClass
from AccessControl import Permissions, ClassSecurityInfo
from Acquisition import aq_parent

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenEvents.EventFilter import EventFilter

def manage_addCustomEventView(context, id, REQUEST=None):
    """Create an aciton rule"""
    ed = CustomEventView(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addCustomEventView = DTMLFile('dtml/addCustomEventView',globals())


class CustomEventView(ZenModelRM, EventFilter):
    
    meta_type = "CustomEventView"

    type = "status"
    evtypes = ("status", "history")
    orderby = ""
    where = ""
    resultFields = ()
    
    _properties = ZenModelRM._properties + (
        {'id':'type', 'type':'selection', 
            'select_variable':'evtypes', 'mode':'w'},
        {'id':'orderby', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'resultFields', 'type':'lines', 'mode':'w'},
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'getEventView',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'getEventView'
                , 'permissions'   : ("View",)
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editEventView'
                , 'permissions'   : ("Change Settings",)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    security.declareProtected('View', 'zentinelTabs')
    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = super(CustomEventView, self).zentinelTabs(templateName)
        if templateName.endswith("Events"): tabs[0]['selected']=True
        return tabs


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add CustomViews list.
        [('url','id'), ...]
        """
        crumbs = super(CustomEventView, self).breadCrumbs(terminator)
        url = aq_parent(self).absolute_url_path() + "/editEventViews"
        crumbs.insert(-1,(url,'Event Views'))
        return crumbs


    def getEventView(self):
        """Return the default screen for this custom view.
        """
        if self.type == "status":
            return self.viewEvents()
        else:    
            return self.viewHistoryEvents()
        
   
    def getEventManager(self):
        """Return the current event manager for this object.
        """
        if self.type == "status":
            return self.ZenEventManager
        else:
            return self.ZenEventHistory


    def getResultFields(self):
        if self.resultFields:
            return self.resultFields
        return self.getEventManager().defaultResultFields


    def getWhere(self):
        if self.where:
            return self.where
        return self.getEventManager.defaultWhere


    def getOrderBy(self):
        if self.orderby:
            return self.orderby
        return self.getEventManager().defaultOrderby


    def getEventSummary(self, severity=1, state=1):
        """Return the current event summary for this custom view.
        """
        zem = self.getEventManager()
        return zem.getEventSummary(self.getWhere(),severity,state)


    def getEventList(self, **kwargs):
        """Return the current event list for this custom view.
        """
        zem = self.getEventManager()
        return zem.getEventList(self.getResultFields(),
                                self.getWhere(),
                                self.getOrderBy(),
                                **kwargs)
    getEventHistoryList = getEventList
        

    security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        self.getEventManager().manage_deleteEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage Events','manage_undeleteEvents')
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        self.getEventManager().manage_undeleteEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, REQUEST=None):
        """Delete events form this managed entity.
        """
        dev = self.device()
        if dev: 
            self.getEventManager().manage_deleteHeartbeat(dev.id)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        self.getEventManager().manage_ackEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        self.getEventManager().manage_setEventStates(eventState, evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_createEventMap(self, eventClass=None, evids=(), REQUEST=None):
        """Create an event map from an event or list of events.
        """
        screen = self.getEventManager().manage_createEventMap(
                                      eventClass, evids, REQUEST)
        if REQUEST:
            if screen: return screen
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Settings', 'manage_editEventView')
    def manage_editEventView(self, REQUEST=None):
        """Update user settings.
        """
        import WhereClause
        if REQUEST and not REQUEST.form.has_key('where'):
            clause = WhereClause.fromFormVariables(self.genMeta(), REQUEST.form)
            if clause:
                REQUEST.form['where'] = clause
        return self.zmanage_editProperties(REQUEST)



InitializeClass(CustomEventView)

###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

__doc__="""ZenTableManager

ZenTableManager is a Zope Product that helps manage and display
large sets of tabular data.  It allows for column sorting,
break down of the set into pages, and filtering of elements
in the table.  It also allows users to store their own default
page size (but publishes a hook to get this values from 
a different location).


$Id: ZenTableManager.py,v 1.4 2004/04/03 04:18:22 edahl Exp $"""

__revision__ = "$Revision: 1.4 $"[11:-2]

import re
import types
import ZTUtils
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from DocumentTemplate.sequence.SortEx import sort

from ZenTableState import ZenTableState


class TableStateNotFound(Exception): pass


def manage_addZenTableManager(context, id="", REQUEST = None):
    """make a CVDeviceLoader"""
    if not id: id = "ZenTableManager"
    ztm = ZenTableManager(id)
    context._setObject(id, ztm)
    ztm = context._getOb(id)
    ztm.initTableManagerSkins()
    
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url()
                                     +'/manage_main') 

class ZenTableManager(SimpleItem, PropertyManager):
    """ZenTableManager manages display of tabular data"""
    
    portal_type = meta_type = 'ZenTableManager'

    _properties = (
        {'id':'defaultBatchSize', 'type':'int','mode':'w'}, 
        {'id':'abbrStartLabel', 'type':'int','mode':'w'}, 
        {'id':'abbrEndLabel', 'type':'int','mode':'w'}, 
        {'id':'abbrPadding', 'type':'int','mode':'w'}, 
        {'id':'abbrSeparator', 'type':'string','mode':'w'}, 
    ) 

    manage_options = (
                        PropertyManager.manage_options +
                        SimpleItem.manage_options
                     )


    def __init__(self, id):
        self.id = id
        self.defaultBatchSize = 40
        self.abbrStartLabel = 15
        self.abbrEndLabel = 5
        self.abbrPadding = 5
        self.abbrSeparator = ".."
        self.abbrThresh = self.abbrStartLabel + \
                        self.abbrEndLabel + self.abbrPadding


    def getDefaultBatchSize(self):
        dbs = self.defaultBatchSize
        user = self.ZenUsers.getUserSettings()
        if user: dbs = user.defaultPageSize
        return dbs


    def setupTableState(self, tableName, **keys):
        """initialize or setup the session variable to track table state"""
        tableState = self.getTableState(tableName, **keys)
        request = self.REQUEST
        tableState.updateFromRequest(request)
        return tableState


    def getTableState(self, tableName, attrname=None, default=None, **keys):
        """return an existing table state or a single value from the state"""
        request = self.REQUEST
        tableStates = self.getTableStates()
        tableState = tableStates.get(tableName, None)
        if not tableState:
            dbs = self.getDefaultBatchSize()
            tableStates[tableName] = ZenTableState(request,tableName,dbs,**keys)
            tableState = tableStates[tableName]
        if attrname == None:
            return tableStates[tableName]
        return getattr(tableState, attrname, None)


    def getReqTableState(self, tableName, attrname):
        """
        Return attrname from request if present if not return from tableState.
        """
        request = self.REQUEST
        if request.has_key(attrname):
            return request[attrname]
        return self.getTableState(tableName, attrname)


    def setTableState(self, tableName, attrname, value):
        """Set the value of a table state attribute and return it."""
        tableState = self.getTableState(tableName)
        return tableState.setTableState(attrname, value)


    def setReqTableState(self, tableName, attrname, default=None, reset=False):
        """set the a value in the table state from the request"""
        tableState = self.getTableState(tableName)
        value = self.REQUEST.get(attrname, None)
        tableState = self.getTableState(tableName)
        return tableState.setTableState(attrname, value,
                                        default=default, reset=reset)


    def getBatch(self, tableName, objects, **keys):
        """Filter, sort and batch objects and pass return set.
        """
        tableState = self.setupTableState(tableName, **keys) 
        if tableState.filter and objects:
            objects = self.filterObjects(objects, tableState.filter, 
                                        tableState.filterFields)
        if tableState.sortedHeader:
            objects = self.sortObjects(objects, tableState)
        else:
            # objects needs to be list not generator.  sortObjects() takes
            # care of this for the other condition above.
            objects = list(objects)
        tableState.totalobjs = len(objects)
        tableState.buildPageNavigation(objects)
        if tableState.batchSize > 0:
            objects = ZTUtils.Batch(objects, tableState.batchSize,
                        start=tableState.start, orphan=0)
        return objects
            
   
    def getBatchForm(self, objects, request):
        """Create batch based on objects no sorting for filter applied.
        """
        batchSize = request.get('batchSize',self.defaultBatchSize)
        start = int(request.get('start',0))
        resetStart = int(request.get('resetStart',0))
        lastindex = request.get('lastindex',0)
        navbutton = request.get('navbutton',None)
        if navbutton == "first" or resetStart:
            start = 0
        elif navbutton == "last":
            start=lastindex
        elif navbutton == "next":
            start = start + batchSize
            if start > lastindex: start = lastindex
        elif navbutton == "prev":
            start = start - batchSize
        elif request.has_key("nextstart"):
            start = request.nextstart
        if 0 < start > len(objects): start = 0
        request.start = start
        if batchSize > 0:
            objects = ZTUtils.Batch(objects, batchSize,
                        start=request.start, orphan=0)
        return objects
       

    def filterObjects(self, objects, regex, filterFields):
        """filter objects base on a regex in regex and list of fields
        in filterFields."""
        if not regex: return objects
        try: search = re.compile(regex,re.I).search
        except re.error, e:
            self.REQUEST.SESSION['message'] = "Invalid regular expression." 
            return objects
        filteredObjects = []
        for obj in objects:
            target = []
            for field in filterFields:
                value = getattr(obj, field, None)
                if callable(value):
                    value = value()
                if type(value) not in types.StringTypes:
                    value = str(value)
                target.append(value)
            targetstring = " ".join(target)
            if search(targetstring): filteredObjects.append(obj)
        if self.REQUEST.SESSION.has_key('message'): self.REQUEST.SESSION.delete('message')
        return filteredObjects


    def sortObjects(self, objects, request):
        """Sort objects.
        """
        if (getattr(aq_base(request), 'sortedHeader', False) 
            and getattr(aq_base(request),"sortedSence", False)):
            sortedHeader = request.sortedHeader
            sortedSence = request.sortedSence
            sortRule = getattr(aq_base(request), "sortRule", "cmp")
            objects = sort(objects, ((sortedHeader, sortRule, sortedSence),))
        return objects
  

    def getTableHeader(self, tableName, fieldName, fieldTitle,
                sortRule='cmp', style='tableheader',attributes=""):
        """generate a <th></th> tag that allows column sorting"""
        href = self.getTableHeaderHref(tableName, fieldName, sortRule)
        style = self.getTableHeaderStyle(tableName, fieldName, style)
        tag = """<th class="%s" %s>""" % (style, attributes)
        tag += """<a class="%s" href="%s""" % (style, href)
        tag += fieldTitle + "</a></th>\n"
        return tag

    
    def getTableHeaderHref(self, tableName, fieldName,
                            sortRule='cmp',params=""):
        """build the href attribute for the table table headers"""

        tableState = self.getTableState(tableName)
        sortedHeader = tableState.sortedHeader
        sortedSence = tableState.sortedSence
        if sortedHeader == fieldName:
            if sortedSence == 'asc':
                sortedSence = 'desc'
            elif sortedSence == 'desc':
                fieldName = ''
                sortedSence = ''
        else:
            sortedSence = 'asc'
        href = "%s?tableName=%s&sortedHeader=%s&" % (
                self.REQUEST.URL, tableName, fieldName)
        href += "sortedSence=%s&sortRule=%s%s\">" % (
                sortedSence, sortRule, params)
        tableState.addFilterField(fieldName)
        return href
 

    def getTableHeaderStyle(self, tableName, fieldName, style):
        """apends "selected" onto the CSS style if this field is selected"""
        if self.getTableState(tableName, "sortedHeader") == fieldName:
            style = style + "selected"
        return style


    def getTableStates(self):
        session = self.REQUEST.SESSION
        if not session.has_key('zentablestates'):
            session['zentablestates'] = {}
        return session['zentablestates']


    def tableStatesHasTable(self, tableName):
        return self.getTableStates().has_key(tableName)


    def getNavData(self, objects, batchSize, sortedHeader):
        pagenav = []
        for index in range(0, len(objects), batchSize):
            if sortedHeader:
                label = self._buildTextLabel(objects[index], sortedHeader)
            else:
                label = str(1+index/batchSize)
            pagenav.append({ 'label': label, 'index': index })
        return pagenav


    def _buildTextLabel(self, item, sortedHeader):
        startAbbr = ""
        endAbbr = ""
        attr = getattr(item, sortedHeader, "")
        if callable(attr): attr = attr()
        label = str(attr)
        if len(label) > self.abbrThresh:
            startAbbr = label[:self.abbrStartLabel]
            if self.abbrEndLabel > 0:
                endAbbr = label[-self.abbrEndLabel:]
            label = "".join((startAbbr, self.abbrSeparator, endAbbr))
        return label


    def initTableManagerSkins(self):
        """setup the skins that come with ZenTableManager"""
        try:
            import string 
            from Products.CMFCore.utils import getToolByName
            from Products.CMFCore.DirectoryView import addDirectoryViews
            skinstool = getToolByName(self, 'portal_skins') 
            if 'zentablemanager' not in skinstool.objectIds():
                addDirectoryViews(skinstool, 'skins', globals())
            skins = skinstool.getSkinSelections()
            for skin in skins:
                path = skinstool.getSkinPath(skin)
                path = map(string.strip, string.split(path,','))
                if 'zentablemanager' not in path:
                    path.append('zentablemanager')
                    path = string.join(path, ', ')
                    skinstool.addSkinSelection(skin, path)
        except ImportError, e:
            if "Products.CMFCore.utils" in e.args: pass
            else: raise
        except AttributeError, e:
            if "portal_skin" in e.args: pass
            else: raise

    
InitializeClass(ZenTableManager)

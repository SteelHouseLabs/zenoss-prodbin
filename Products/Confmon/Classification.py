#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Classification

base class for all classification objects.  These objects
add class like information but through acuqisition.

$Id: Classification.py,v 1.31 2004/04/22 16:20:23 edahl Exp $"""

__version__ = "$Revision: 1.31 $"[11:-2]

from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ConfUtils.Utils import checkClass

from ConfmonBase import ConfmonBase

class Classification(ConfmonBase):
    isInTree = 1
    #index_html = PageTemplateFile('skins/misc/classList.pt',globals())
    
    portal_type = meta_type = "Classification"

    sub_meta_types = ('DTML Method', 'Folder', 'Page Template',
                    'External Method', 'Script (Python)')
    
    _properties = (
                {'id':'title', 'type':'string', 'mode':'w'},
                {'id':'sub_classes', 'type':'lines', 'mode':'w'},
                {'id':'sub_meta_types', 'type':'lines', 'mode':'w'},
                  )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Classification',
            'meta_type'      : 'Classification',
            'description'    : """Classification class""",
            'icon'           : 'Classification_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addClassification',
            'immediate_view' : 'classList',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'classList'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        ConfmonBase.__init__(self, id, title)
        self._buildSubClasses()


    def all_meta_types(self, interfaces=None):
        """Control what types of objects can be created within classification"""
        mts = []
        for mt in RelationshipManager.all_meta_types(self, interfaces):
            if mt['name'] in self.sub_meta_types:
                mts.append(mt)
            elif (mt.has_key('instance') and mt['instance']):
                for cl in self.sub_classes:
                    if checkClass(mt['instance'], cl):
                        mts.append(mt)
        return mts
   

    def objectSubValues(self, sub_classes=None):
        """get contained objects that are sub classes of sub_classes"""
        retdata = []
        if not sub_classes: sub_classes = self.sub_classes
        for obj in self.objectValues():
            for cl in sub_classes:
                if checkClass(obj.__class__, cl):
                    retdata.append(obj)
                    break
        return retdata


    def _buildSubClasses(self):
        # check self, without following the acquisition path
        if not hasattr(aq_base(self), 'sub_classes'):
            cname = self.__class__.__name__
            iname = cname[:-5]
            self.sub_classes = (cname, iname)


    def _getCatalog(self):
        '''Return the ZCatalog instance we're searching with'''
        catalog = None
        if hasattr(self, self.class_default_catalog):
            catalog = getattr(self, self.class_default_catalog)
        return catalog


    security.declareProtected('View', 'helpLink')
    def helpLink(self):
        '''return a link to the objects help file'''
        path = self.__class__.__module__.split('.')
        className = path[-1].replace('Class','')
        product = path[-2]
       
        path = ("", "Control_Panel", "Products", product, "Help", 
                "%s.stx"%className)

        # check to see if we have a help screen
        app = self.getPhysicalRoot()
        try:
            app.restrictedTraverse(path)
        except KeyError:
            return ""
            
        url = "/HelpSys?help_url="+ "/".join(path)

        return """<a class="tabletitle" href="%s" \
        onClick="window.open('%s','zope_help','width=600,height=500,menubar=yes,\
        toolbar=yes,scrollbars=yes,resizable=yes'); return false;" \
        onMouseOver="window.status='Open online help'; return true;" \
        onMouseOut="window.status=''; return true;">Help!</a>""" % (url, url)

    
    def createInstance(self, id):
        """must be implemented in lower class to create the appropriate
        instnace for a certain classification"""
        pass


InitializeClass(Classification)

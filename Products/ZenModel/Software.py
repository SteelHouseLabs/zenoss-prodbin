#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Software

Software represents a software vendor's product.

$Id: Software.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Product import Product

def manage_addSoftware(context, id, title = None, REQUEST = None):
    """make a Software"""
    d = Software(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSoftware = DTMLFile('dtml/addSoftware',globals())

class Software(Product):
    """Software object"""
    portal_type = meta_type = 'Software'

    _properties = (Product._properties + (
                    {'id':'version', 'type':'string', 'mode':'w'},
                ))

    factory_type_information = ( 
        { 
            'id'             : 'Software',
            'meta_type'      : 'Software',
            'description'    : """Class to manage product information""",
            'icon'           : 'Software_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addSoftware',
            'immediate_view' : 'viewSoftwareOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewProductOverview'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.ModifyPortalContent, )
                },
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewItem'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )
    
    def __init__(self, id, title = None, version = ''):
        Product.__init__(self, id, title)
        self.version = version

InitializeClass(Software)

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

__doc__="""HardwareClass

HardwareClass represents a software vendor's product.

$Id: HardwareClass.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ProductClass import ProductClass

def manage_addHardwareClass(context, id, title = None, REQUEST = None):
    """make a HardwareClass"""
    d = HardwareClass(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardwareClass = DTMLFile('dtml/addHardwareClass',globals())

class HardwareClass(ProductClass):
    """HardwareClass object"""
    portal_type = meta_type = 'HardwareClass'

#    factory_type_information = ( 
#        { 
#            'id'             : 'HardwareClass',
#            'meta_type'      : 'HardwareClass',
#            'description'    : """Class to manage product information""",
#            'icon'           : 'HardwareClass_icon.gif',
#            'product'        : 'ZenModel',
#            'factory'        : 'manage_addHardwareClass',
#            'immediate_view' : 'viewProductOverview',
#            'actions'        :
#            ( 
#                { 'id'            : 'overview'
#                , 'name'          : 'Overview'
#                , 'action'        : 'viewHardwareClassOverview'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Modifications'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#            )
#          },
#        )
    
InitializeClass(HardwareClass)

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

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *

from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from ZenPackable import ZenPackable


manage_addUserCommand = DTMLFile('dtml/addUserCommand',globals())


class UserCommand(ZenModelRM, ZenPackable):

    meta_type = 'UserCommand'

    security = ClassSecurityInfo()
  
    description = ""
    command = ''

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'command', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("commandable", ToOne(
                ToManyCont, 'Products.ZenModel.Commandable', 'userCommands')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'userCommandDetailNew',
        'actions'        :
        ( 
            {'id'            : 'overview',
             'name'          : 'User Command',
             'action'        : 'userCommandDetailNew',
             'permissions'   : ( Permissions.view, ),
            },
            { 'id'            : 'viewHistory',
              'name'          : 'Modifications',
              'action'        : 'viewNewHistory',
              'permissions'   : (ZEN_VIEW_MODIFICATIONS,),
            }
        )
    },
    )

    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object
        [('url','id'), ...]
        """
        crumbs = super(UserCommand, self).breadCrumbs(terminator)
        aqParent = self.getPrimaryParent()
        while aqParent.meta_type == 'ToManyContRelationship':
            aqParent = aqParent.getPrimaryParent()
        url = aqParent.absolute_url_path() + '/dataRootManage'
        return [(url, 'Commands')]
        

InitializeClass(UserCommand)

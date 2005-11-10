#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Location

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from Globals import DTMLFile

from AccessControl import ClassSecurityInfo

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer


def manage_addLocation(context, id, description = "", REQUEST = None):
    """make a Location"""
    loc = Location(id, description)
    context._setObject(id, loc)
    loc.description = description
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addLocation = DTMLFile('dtml/addLocation',globals())



class Location(DeviceOrganizer):
    """
    Location is a DeviceGroup Organizer that manages physical device Locations.
    """

    # Organizer configuration
    dmdRootName = "Locations"

    portal_type = meta_type = event_key = 'Location'
    
    _relations = DeviceOrganizer._relations + (
        ("devices", ToMany(ToOne,"Device","location")),
        )

    security = ClassSecurityInfo()
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Location',
            'meta_type'      : 'Location',
            'description'    : """Base class for all devices""",
            'icon'           : 'Location_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addLocation',
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
         },
        )

InitializeClass(Location)

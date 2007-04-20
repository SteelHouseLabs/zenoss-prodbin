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

__doc__="""Location

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from Globals import DTMLFile

from AccessControl import ClassSecurityInfo

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable


def manage_addLocation(context, id, description = "", REQUEST = None):
    """make a Location"""
    loc = Location(id, description)
    context._setObject(id, loc)
    loc.description = description
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addLocation = DTMLFile('dtml/addLocation',globals())



class Location(DeviceOrganizer, ZenPackable):
    """
    Location is a DeviceGroup Organizer that manages physical device Locations.
    """

    # Organizer configuration
    dmdRootName = "Locations"

    portal_type = meta_type = event_key = 'Location'
    
    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToOne,"Products.ZenModel.Device","location")),
        ("networks", ToMany(ToOne,"Products.ZenModel.IpNetwork","location")),
        )

    security = ClassSecurityInfo()
    
InitializeClass(Location)

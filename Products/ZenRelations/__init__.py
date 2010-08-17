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
__doc__="""__init__

Initialize the RelationshipManager Product

$Id: __init__.py,v 1.9 2002/12/06 14:25:57 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import logging

from RelationshipManager import RelationshipManager, addRelationshipManager, \
                                manage_addRelationshipManager
from ToOneRelationship import ToOneRelationship, addToOneRelationship, \
                                manage_addToOneRelationship
from ToManyRelationship import ToManyRelationship, addToManyRelationship, \
                                manage_addToManyRelationship
from ToManyContRelationship import ToManyContRelationship, \
                                addToManyContRelationship, \
                                manage_addToManyContRelationship
from Products.ZenRelations.ZenPropertyManager import setDescriptors

log = logging.getLogger("zen.ZenRelations")

def initialize(registrar):
    registrar.registerClass(
        RelationshipManager,
        constructors = (addRelationshipManager, manage_addRelationshipManager))
    registrar.registerBaseClass(RelationshipManager)
    registrar.registerClass(
        ToOneRelationship,
        constructors = (addToOneRelationship, manage_addToOneRelationship),
        icon = 'www/ToOneRelationship_icon.gif')
    registrar.registerClass(
        ToManyRelationship,
        constructors = (addToManyRelationship, manage_addToManyRelationship),
        icon = 'www/ToManyRelationship_icon.gif')
    registrar.registerClass(
        ToManyContRelationship,
        constructors = (addToManyContRelationship, 
                        manage_addToManyContRelationship),
        icon = 'www/ToManyContRelationship_icon.gif')
    app = registrar._ProductContext__app
    try:
        zport = app.zport
        dmd = zport.dmd
        setDescriptors(dmd.propertyTransformers)
    except Exception, e:
        args = (e.__class__.__name__, e)
        log.info("Unable to set property descriptors: %s: %s", *args)

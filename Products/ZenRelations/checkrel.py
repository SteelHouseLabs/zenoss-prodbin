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

import sys
import logging
logging.basicConfig()
root = logging.getLogger()
root.setLevel(logging.CRITICAL)

import Globals

from utils import importClass, importClasses
from Products.ZenRelations.Exceptions import ZenSchemaError

def checkRelationshipSchema(cls, baseModule):
    """
    Walk all relationship schema definitions and confirm that they
    have reciprical peers on the remote class.
    """
    for relname, rel in cls._relations:
        try:
            remoteClass = importClass(rel.remoteClass, None)    
        except AttributeError, e:
            logging.critical("RemoteClass '%s' from '%s.%s' not found",
                        rel.remoteClass, cls.__name__, relname)
            continue
                        
        try:
            rschema = remoteClass.lookupSchema(rel.remoteName)
        except ZenSchemaError, e:
            logging.critical("Inverse def '%s' for '%s.%s' not found on '%s'",
                rel.remoteName, cls.__name__, relname,rel.remoteClass)
            continue
        except Exception, e:
            logging.critical("RemoteClass '%s' for '%s.%s' problem.",
                rel.remoteName, cls.__name__, relname)
            logging.critical(e)
        try:
            localClass = importClass(rschema.remoteClass, None)
        except AttributeError, e:
            logging.critical(e)
        if not issubclass(cls, localClass):
            logging.critical("Inverse def '%s' from '%s.%s' wrong "
            "remoteClass: '%s'", rel.remoteName, cls.__name__,
                                 relname,rschema.remoteClass)
        if rschema.remoteName != relname:
            logging.critical("Inverse def '%s' from '%s.%s' wrong "
                "remoteName: '%s'", rel.remoteName, cls.__name__, relname,
                                    rschema.remoteName)
        if rel.remoteType != rschema.__class__:
            logging.critical("'%s.%s' inverse '%s' type %s != %s",
                            cls.__name__, relname, rel.remoteName, 
                            rschema.__class__.__name__, rel.remoteType.__name__)

        
baseModule = None
if len(sys.argv) > 1:
    baseModule = sys.argv[1]
    
classList = importClasses(basemodule=baseModule, 
            skipnames=("ZentinelPortal", "ZDeviceLoader"))

for classdef in classList:
    if hasattr(classdef, "lookupSchema"):
        logging.info("checking class %s...", classdef.__name__)
        checkRelationshipSchema(classdef, baseModule)

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
__doc__='''
This migration script adds the ZenManager role.
''' 

__version__ = "$Revision$"[11:-2]


import Migrate

from Products.ZenModel.ZenossSecurity import *

class ZenManagerRole(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        zport = dmd.zport
        if not ZEN_MANAGER_ROLE in zport.__ac_roles__:
            zport.__ac_roles__ += (ZEN_MANAGER_ROLE,)
        rm = dmd.getPhysicalRoot().acl_users.roleManager
        if not ZEN_MANAGER_ROLE in rm.listRoleIds():
            rm.addRole(ZEN_MANAGER_ROLE)
        mp = zport.manage_permission
        mp(ZEN_CHANGE_DEVICE, [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        mp(ZEN_MANAGE_DMD, [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        mp(ZEN_DELETE, [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        mp(ZEN_ADD, [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        mp(ZEN_VIEW, [ZEN_USER_ROLE,ZEN_MANAGER_ROLE,MANAGER_ROLE,OWNER_ROLE], 1)
        mp(ZEN_VIEW_HISTORY, [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_COMMON,[ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)
        mp(ZEN_CHANGE_SETTINGS, [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)
        
        if ZEN_CHANGE_ALERTING_RULES in zport.possible_permissions():
            mp(ZEN_CHANGE_ALERTING_RULES, [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)
        else:
            zport.__ac_permissions__=(
                zport.__ac_permissions__+((ZEN_CHANGE_ALERTING_RULES,(),[ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE]),))
                
        if ZEN_CHANGE_ADMIN_OBJECTS in zport.possible_permissions():
            mp(ZEN_CHANGE_ADMIN_OBJECTS, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        else:
            zport.__ac_permissions__=(
                zport.__ac_permissions__+((ZEN_CHANGE_ADMIN_OBJECTS,(),[ZEN_MANAGER_ROLE, MANAGER_ROLE]),))
                
        if ZEN_CHANGE_EVENT_VIEWS in zport.possible_permissions():
            mp(ZEN_CHANGE_EVENT_VIEWS, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        else:
            zport.__ac_permissions__=(
                zport.__ac_permissions__+((ZEN_CHANGE_EVENT_VIEWS,(),[ZEN_MANAGER_ROLE, MANAGER_ROLE]),))


ZenManagerRole()

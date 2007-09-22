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

from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenossSecurity import *


class AdministrativeRole(ZenModelRM):

    meta_type = "AdministrativeRole"

    _relations = (
        ("userSetting", ToOne(ToMany, "Products.ZenModel.UserSettings", "adminRoles")),
        ("managedObject", ToOne(ToManyCont, "Products.ZenModel.AdministrativeRoleable", "adminRoles")),
    )

    level = 1
    role = ZEN_USER_ROLE

    def __init__(self, userSettings, managedObject):
        userid = userSettings.getId()
        ZenModelRM.__init__(self, userid)
        self.role = userSettings.defaultAdminRole
        self.level = userSettings.defaultAdminLevel
        self.id = userid
        managedObject = managedObject.primaryAq()
        managedObject.adminRoles._setObject(userid, self)
        self.userSetting.addRelation(userSettings)
        managedObject.manage_setLocalRoles(userid, (self.role,),)
        managedObject.index_object()


    def update(self, role, level):
        self.role = role
        self.level = level
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_setLocalRoles(self.getId(), (self.role,))
        managedObject.index_object()


    def delete(self):
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_delLocalRoles((self.getId(),))
        managedObject.index_object()
        self.userSetting.removeRelation()
        self.managedObject.removeRelation()


    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()


    def managedObjectName(self):
        mo = self.managedObject()
        if mo.meta_type == 'Device':
            return mo.id
        return mo.getOrganizerName()


    def managedObjectLink(self):
        return self.managedObject().getPrimaryUrlPath()


    def getEventSummary(self):
        return self.managedObject().getEventSummary()
    
    def managedObjectType(self):
        return self.managedObject().meta_type

DeviceAdministrativeRole = AdministrativeRole
DevOrgAdministrativeRole = AdministrativeRole

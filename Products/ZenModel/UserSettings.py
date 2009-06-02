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

import types

from random import choice

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Acquisition import aq_base
from Products.PluggableAuthService import interfaces
from zExceptions import Unauthorized
from DateTime import DateTime

from Products.ZenEvents.ActionRule import ActionRule
from Products.ZenEvents.CustomEventView import CustomEventView
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenUtils.Utils import unused
from Products.ZenUtils import DotNetCommunication
from Products.ZenWidgets import messaging

from ZenossSecurity import *
from ZenModelRM import ZenModelRM
from Products.ZenUtils import Utils

from email.MIMEText import MIMEText
import socket

UserSettingsId = "ZenUsers"

def manage_addUserSettingsManager(context, REQUEST=None):
    """Create user settings manager."""
    ufm = UserSettingsManager(UserSettingsId)
    context._setObject(ufm.getId(), ufm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


def rolefilter(r): return r not in ("Anonymous", "Authenticated", "Owner")

class UserSettingsManager(ZenModelRM):
    """Manage zenoss user folders.
    """
    security = ClassSecurityInfo()

    meta_type = "UserSettingsManager"

    #zPrimaryBasePath = ("", "zport")

    sub_meta_types = ("UserSettings",)

    factory_type_information = (
        {
            'id'             : 'UserSettingsManager',
            'meta_type'      : 'UserSettingsManager',
            'description'    : """Base class for all devices""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addUserSettingsManager',
            'immediate_view' : 'manageUserFolder',
            'actions'        :
         (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../editSettings'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dataRootManage'
                , 'permissions'   : (ZEN_MANAGE_DMD,)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : 'manageUserFolder'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : '../ZenPackManager/viewZenPacks'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'jobs'
                , 'name'          : 'Jobs'
                , 'action'        : '../joblist'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'menus'
                , 'name'          : 'Menus'
                , 'action'        : '../editMenus'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../editPortletPerms'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : '../../About/zenossInfo'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../../About/zenossVersions'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'backups'
                , 'name'          : 'Backups'
                , 'action'        : '../backupInfo'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
           )
         },
        )


    def getAllUserSettings(self):
        """Return list user settings objects.
        """
        # This code used to filter out the admin user.
        # See ticket #1615 for why it no longer does.
        users = self.objectValues(spec="UserSettings")
        users.sort(lambda a,b:cmp(a.id, b.id))
        return users

    def getAllGroupSettings(self):
        """Return list user settings objects.
        """
        groups = self.objectValues(spec="GroupSettings")
        groups.sort(lambda a,b:cmp(a.id, b.id))
        return groups

    def getAllUserSettingsNames(self, filtNames=()):
        """Return list of all zenoss usernames. 
        """
        filt = lambda x: x not in filtNames
        return [ u.id for u in self.getAllUserSettings() if filt(u.id) ]

    def getAllGroupSettingsNames(self, filtNames=()):
        """Return list of all zenoss usernames. 
        """
        filt = lambda x: x not in filtNames
        return [ g.id for g in self.getAllGroupSettings() if filt(g.id) ]
        
    def getUsers(self):
        """Return list of Users wrapped in their settings folder.
        """
        users = []
        for uset in self.objectValues(spec="UserSettings"):
            user = self.acl_users.getUser(uset.id)
            if user: users.append(user.__of__(uset))
        return users
            

    def getUser(self, userid=None):
        """Return a user object.  If userid is not passed return current user.
        """
        if userid is None:
            user = getSecurityManager().getUser()
        else:
            user = self.acl_users.getUser(userid)
        if user: return user.__of__(self.acl_users)


    def getAllActionRules(self):
        for u in self.getAllUserSettings() + self.getAllGroupSettings():
            for ar in u.getActionRules():
                yield ar

    def getUserSettings(self, userid=None):
        """Return a user folder.  If userid is not passed return current user.
        """
        user=None
        if userid is None:
            user = getSecurityManager().getUser()
            userid = user.getId()
        if not userid: raise Unauthorized
        folder = self._getOb(userid,None)
        if not folder and userid:
            ufolder = UserSettings(userid)
            self._setObject(ufolder.getId(), ufolder)
            folder = self._getOb(userid)
            if not user:
                user = self.getUser(userid)
            if user:
                # Load default values from our auth backend
                psheets = user.listPropertysheets()
                psheets.reverse() # Because first sheet should have priority
                for ps in map(lambda ps: user.getPropertysheet(ps), psheets):
                    props = {}
                    for id in ps.propertyIds():
                        props[id] = ps.getProperty(id)
                    ufolder.updatePropsFromDict(props)
                folder.changeOwnership(user)
                folder.manage_setLocalRoles(userid, ("Owner",))
        return folder


    def getGroupSettings(self, groupid):
        if not self._getOb(groupid, False):
            gfolder = GroupSettings(groupid)
            self._setObject(gfolder.getId(), gfolder)
        return self._getOb(groupid)


    def setDashboardState(self, userid=None, REQUEST=None):
        """ Store a user's portlets and layout. If userid is not passed
            set the state for the current user.
        """
        user = self.getUserSettings(userid)
        posted = Utils.extractPostContent(REQUEST)
        if posted:
            user.dashboardState = posted
        return True

    def getUserSettingsUrl(self, userid=None):
        """Return the url to the current user's folder.
        """
        uf = self.getUserSettings(userid)
        if uf: return uf.getPrimaryUrlPath()
        return ""


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUser')
    def manage_addUser(self, userid, password=None,roles=("ZenUser",),
                    REQUEST=None,**kw):
        """
        Add a Zenoss user to the system and set the user's default properties.

        @parameter userid: username to add
        @parameter password: password for the username
        @parameter roles: tuple of role names
        @parameter REQUEST: Zope object containing details about this request
        """
        if not userid: return

        userid= userid.strip()

        illegal_usernames= [ 'user', ]

        user_name= userid.lower()
        if user_name in illegal_usernames:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'The username "%s" is reserved.' % userid,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return None

        if password is None:
            password = self.generatePassword()

        self.acl_users._doAddUser(userid,password,roles,"")
        self.acl_users.ZCacheable_invalidate()
        user = self.acl_users.getUser(userid)
        ufolder = self.getUserSettings(userid)
        if REQUEST: kw = REQUEST.form
        ufolder.updatePropsFromDict(kw)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'User Added',
                'User "%s" has been created.' % userid
            )
            return self.callZenScreen(REQUEST)
        else:
            return user


    def generatePassword(self):
        """ Generate a valid password.
        """
        # we don't use these to avoid typos: OQ0Il1
        chars = 'ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join( [ choice(chars) for i in range(6) ] )


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_changeUser')
    def manage_changeUser(self, userid, password=None, sndpassword=None,
                          roles=None, domains=None, REQUEST=None, **kw):
        """Change a zenoss users settings.
        """
        user = self.acl_users.getUser(userid)
        if not user:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'User "%s" was not found.' % userid,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return
        if password and password != sndpassword:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "Passwords didn't match. No change.",
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                raise ValueError("passwords don't match")
        if password is None: password = user._getPassword()
        if roles is None: roles = user.roles
        if domains is None: domains = user.domains
        self.acl_users._doChangeUser(userid,password,roles,domains)
        self.acl_users.ZCacheable_invalidate()
        ufolder = self.getUserSettings(userid)
        ufolder.updatePropsFromDict(kw)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Settings Saved',
                Time.SaveMessage()
            )
            return self.callZenScreen(REQUEST)
        else:
            return user


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUsers')
    def manage_deleteUsers(self, userids=(), REQUEST=None):
        """Delete a list of zenoss users from the system.
        """
        # get a list of plugins that can add manage users and then call the
        # appropriate methods
        # 
        # XXX this needs to be reviewed when new plugins are added, such as the
        # LDAP plugin 
        if 'admin' in userids:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                "Cannot delete admin user. No users were deleted.",
                messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        ifaces = [interfaces.plugins.IUserAdderPlugin]
        getPlugins = self.acl_users.plugins.listPlugins
        plugins = [ getPlugins(x)[0][1] for x in ifaces ]
        for userid in userids:
            try:
                for plugin in plugins:
                    plugin.removeUser(userid)
                self.acl_users.ZCacheable_invalidate()
            except KeyError:
                # this means that there's no user in the acl_users, but that
                # Zenoss still sees the user; we want to pass on this exception
                # so that Zenoss can clean up
                pass
            if getattr(aq_base(self), userid, False):
                us = self._getOb(userid)
                for ar in us.adminRoles():
                    ar.userSetting.removeRelation()
                    mobj = ar.managedObject().primaryAq()
                    mobj.adminRoles._delObject(ar.id)
                self._delObject(userid)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Deleted',
                "Users were deleted: %s." % (', '.join(userids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addGroup')
    def manage_addGroup(self, groupid, REQUEST=None): 
        """Add a zenoss group to the system and set its default properties.
        """
        if not groupid: return
        try:
            self.acl_users.groupManager.addGroup(groupid)
            self.acl_users.ZCacheable_invalidate()
        except KeyError: pass
        self.getGroupSettings(groupid)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Group Added',
                'Group "%s" has been created.' % groupid
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteGroups')
    def manage_deleteGroups(self, groupids=(), REQUEST=None):
        """ Delete a zenoss group from the system
        """
        gm = self.acl_users.groupManager
        if type(groupids) in types.StringTypes:
            groupids = [groupids]
        for groupid in groupids:
            if self._getOb(groupid): self._delObject(groupid)
            try:
                gm.removeGroup(groupid)
                self.acl_users.ZCacheable_invalidate()
            except KeyError: pass
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Groups Deleted',
                "Groups were deleted: %s." % (', '.join(groupids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUsersToGroups')
    def manage_addUsersToGroups(self, userids=(), groupids=(), REQUEST=None):
        """ Add users to a group
        """
        if type(userids) in types.StringTypes:
            userids = [userids]
        if type(groupids) in types.StringTypes:
            groupids = [groupids]
        for groupid in groupids:
            self._getOb(groupid).manage_addUsersToGroup(userids) 
        if REQUEST:
            if len(groupids) == 0:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No groups were selected.',
                    priority=messaging.WARNING
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Groups Modified',
                    'Users %s were added to group %s.' % (
                        ', '.join(userids), ', '.join(groupids))
                )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_emailTestAdmin')
    def manage_emailTestAdmin(self, userid, REQUEST=None):
        ''' Do email test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_emailTest()
        if msg:
            messaging.IMessageSender(self).sendToBrowser('Email Test', msg)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_pagerTestAdmin')
    def manage_pagerTestAdmin(self, userid, REQUEST=None):
        ''' Do pager test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_pagerTest()
        if msg:
            messaging.IMessageSender(self).sendToBrowser('Pager Test', msg)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def cleanUserFolders(self):
        """Delete orphaned user folders.
        """
        userfolders = self._getOb(UserSettingsId)
        userids = self.acl_users.getUserNames()
        for fid in userfolders.objectIds():
            if fid not in userids:
                userfolders._delObject(fid)
        self.acl_users.ZCacheable_invalidate()
   

    def getAllRoles(self):
        """Get list of all roles without Anonymous and Authenticated.
        """
        return filter(rolefilter, self.valid_roles())


    def exportXmlHook(self,ofile, ignorerels):
        map(lambda x: x.exportXml(ofile, ignorerels), self.getAllUserSettings())
    


def manage_addUserSettings(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = UserSettings(id, title)
    context._setObject(id, dc)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


addUserSettings = DTMLFile('dtml/addUserSettings',globals())


class UserSettings(ZenModelRM):
    """zenoss user folder has users preferences.
    """

    meta_type = "UserSettings"

    sub_meta_types = ("ActionRule",)

    email = ""
    pager = ""
    defaultPageSize = 40
    defaultEventPageSize = 30
    defaultAdminRole = "ZenUser"
    defaultAdminLevel = 1
    oncallStart = 0
    oncallEnd = 0
    escalationMinutes = 0
    dashboardState = ''
    netMapStartObject = ''
    eventConsoleRefresh = True
    zenossNetUser = ''
    zenossNetPassword = ''

    _properties = ZenModelRM._properties + (
        {'id':'email', 'type':'string', 'mode':'w'},
        {'id':'pager', 'type':'string', 'mode':'w'},
        {'id':'defaultPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultEventPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultAdminRole', 'type':'string', 'mode':'w'},
        {'id':'defaultAdminLevel', 'type':'int', 'mode':'w'},
        {'id':'oncallStart', 'type':'int', 'mode':'w'},
        {'id':'oncallEnd', 'type':'int', 'mode':'w'},
        {'id':'escalationMinutes', 'type':'int', 'mode':'w'},
        {'id':'dashboardState', 'type':'string', 'mode':'w'},
        {'id':'netMapStartObject', 'type':'string', 'mode':'w'},
        {'id':'eventConsoleRefresh', 'type':'boolean', 'mode':'w'},
        {'id':'zenossNetUser', 'type':'string', 'mode':'w'},
        {'id':'zenossNetPassword', 'type':'string', 'mode':'w'},
    )


    _relations =  (
        ("adminRoles", ToMany(ToOne, "Products.ZenModel.AdministrativeRole",
                              "userSetting")),
        ("messages", ToManyCont(ToOne,
            "Products.ZenWidgets.PersistentMessage.PersistentMessage",
            "messageQueue")),
    )

   # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'editUserSettings',
            'actions'        :
            (
                {'name'         : 'Edit',
                'action'        : 'editUserSettings',
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Administered Objects', 
                'action'        : 'administeredDevices', 
                'permissions'   : (ZEN_CHANGE_ADMIN_OBJECTS,)
                },
                {'name'         : 'Event Views',
                'action'        : 'editEventViews',
                # ideally make this its own permission
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Alerting Rules',
                'action'        : 'editActionRules',
                'permissions'   : (ZEN_CHANGE_ALERTING_RULES,),
                },
            )
         },
        )

    security = ClassSecurityInfo()

    security.declareProtected('View', 'zentinelTabs')
    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = super(UserSettings, self).zentinelTabs(templateName)
        # if we don't have any global roles take away edit tab
        if self.hasNoGlobalRoles():
            return tabs[:-1]
        return tabs

    def hasNoGlobalRoles(self):
        """This user doesn't have global roles. Used to limit access
        """
        return self.id != 'admin' and len(self.getUserRoles()) == 0

    def getUserRoles(self):
        """Get current roles for this user.
        """
        user = self.getUser(self.id)
        if user:
            # This call will create GroupSettings objects for any externally-
            # sourced groups.
            self.getAllAdminRoles()
            return filter(rolefilter, user.getRoles())
        return []


    def getUserGroupSettingsNames(self):
        """Return group settings objects for user
        """
        user = self.getUser(self.id)
        if user:
            return self.acl_users._getGroupsForPrincipal(user)
        return ()


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'updatePropsFromDict')
    def updatePropsFromDict(self, propdict):
        props = self.propertyIds()
        for k, v in propdict.items():
            if k in props: setattr(self,k,v)


    def iseditable(self):
        """Can the current user edit this settings object.
        """
        owner = self.getOwner()
        user = getSecurityManager().getUser()
        if owner.has_role("Manager") and not user.has_role("Manager"):
            return False
        
        return user.has_role("Manager") or \
               user.has_role("ZenManager") or \
               owner.getUserName() == user.getUserName()


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_editUserSettings')
    def manage_editUserSettings(self, password=None, sndpassword=None,
                                roles=None, groups=None, domains=None,
                                REQUEST=None, **kw):
        """Update user settings.
        """
        # get the user object; return if no user 
        user = self.acl_users.getUser(self.id)
        if not user:
            user = self.getPhysicalRoot().acl_users.getUser(self.id)
        if not user:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'User %s not found.' % self.id,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return

        # update role info
        roleManager = self.acl_users.roleManager
        origRoles = filter(rolefilter, user.getRoles())
        
        if not self.has_role('Manager') and roles and 'Manager' in roles:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'Only Managers can make more Managers.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return
        
        if not self.has_role('Manager') and origRoles and \
            'Manager' in origRoles:
            
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'Only Managers can modify other Managers.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return
        
        # if there's a change, then we need to update
        if roles != origRoles and self.isManager():
            from sets import Set as set
            # get roles to remove and then remove them
            removeRoles = list(set(origRoles).difference(set(roles)))
            for role in removeRoles:
                roleManager.removeRoleFromPrincipal(role, self.id)
            # get roles to add and then add them
            addRoles = list(set(roles).difference(set(origRoles)))
            for role in addRoles:
                roleManager.assignRoleToPrincipal(role, self.id)
        
        # update group info 
        groupManager = self.acl_users.groupManager
        origGroups = groupManager.getGroupsForPrincipal(user)
        # if there's a change, then we need to update 
        if groups != origGroups and self.isManager():
            # can we use the built-in set?
            try:
                set()
            except NameError:
                from sets import Set as set
            # get groups to remove and then remove them
            removeGroups = set(origGroups).difference(set(groups))
            for groupid in removeGroups:
                groupManager.removePrincipalFromGroup(user.getId(), groupid)
            # get groups to add and then add them
            addGroups = set(groups).difference(set(origGroups))
            for groupid in addGroups:
                try:
                    groupManager.addPrincipalToGroup(user.getId(), groupid)
                except KeyError:
                    # This can occur if the group came from an external source.
                    pass

        # we're not managing domains right now
        if domains:
            msg = 'Zenoss does not currently manage domains for users.'
            raise NotImplementedError(msg)

        # update Zenoss user folder settings
        if REQUEST:
            kw = REQUEST.form
        self.manage_changeProperties(**kw)

        # update password info
        userManager = self.acl_users.userManager
        if password:
            if password.find(':') >= 0:
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Passwords cannot contain a ":". Password not updated.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("Passwords cannot contain a ':' ") 
            elif password != sndpassword:
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Passwords did not match. Password not updated.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("Passwords don't match")
            else:
                try: userManager.updateUserPassword(self.id, password)
                except KeyError:
                    self.getPhysicalRoot().acl_users.userManager.updateUserPassword(
                                    self.id, password)
                if REQUEST:
                    loggedInUser = REQUEST['AUTHENTICATED_USER']
                    # we only want to log out the user if it's *their* passowrd
                    # they've changed, not, for example, if the admin user is
                    # changing another user's password
                    if loggedInUser.getUserName() == self.id:
                        self.acl_users.logout(REQUEST)

        self.acl_users.ZCacheable_invalidate()

        # finish up
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Settings Saved',
                Time.SaveMessage()
            )
            return self.callZenScreen(REQUEST)
        else:
            return user

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_addActionRule')
    def manage_addActionRule(self, id=None, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            ar = ActionRule(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()
            userid = user.getId()
            if userid != self.id:
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def getActionRules(self):
        return self.objectValues(spec=ActionRule.meta_type)

    security.declareProtected(ZEN_CHANGE_EVENT_VIEWS, 
        'manage_addCustomEventView')
    def manage_addCustomEventView(self, id=None, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            ar = CustomEventView(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()
            userid = user.getId()
            if userid != self.id:
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)

    
    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS, 
        'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, name=None, type='device', 
                                    role=None, REQUEST=None):
        "Add a Admin Role to this device"
        unused(role)
        mobj = None
        if not name:
            name = REQUEST.deviceName
        if type == 'device':
            mobj =self.getDmdRoot("Devices").findDevice(name)
        else:
            try:
                root = type.capitalize()+'s'
                if type == "deviceClass":
                    mobj = self.getDmdRoot("Devices").getOrganizer(name)
                else:
                    mobj = self.getDmdRoot(root).getOrganizer(name)
            except KeyError: pass        
        if not mobj:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "%s %s not found"%(type.capitalize(),name),
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else: return
        roleNames = [ r.id for r in mobj.adminRoles() ]
        if self.id in roleNames:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    (("Administrative Role for %s %s "
                     "for user %s already exists.") % (type, name, self.id)),
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else: return
        mobj.manage_addAdministrativeRole(self.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                ("Administrative Role for %s %s for user %s added" % 
                    (type, name, self.id))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS,
        'manage_editAdministrativeRoles')
    def manage_editAdministrativeRoles(self, ids=(), role=(), 
                                        level=(), REQUEST=None):
        """Edit list of admin roles.
        """
        if type(ids) in types.StringTypes:
            ids = [ids]
            level = [level]
            role = [role]
        else:
            ids = list(ids)
        for ar in self.adminRoles():
            mobj = ar.managedObject()
            try: i = ids.index(mobj.managedObjectName())
            except ValueError: continue
            mobj = mobj.primaryAq()
            mobj.manage_editAdministrativeRoles(self.id, role[i], level[i])
        if REQUEST:
            if ids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Updated',
                    "Administrative roles were updated."
                )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS,
        'manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        if type(delids) in types.StringTypes:
            delids = [delids]
        for ar in self.adminRoles():
            mobj = ar.managedObject()
            if mobj.managedObjectName() not in delids: continue
            mobj = mobj.primaryAq()
            mobj.manage_deleteAdministrativeRole(self.id)
        if REQUEST:
            if delids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Deleted',
                    "Administrative roles were deleted."
                )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'getAllAdminRoles')
    def getAllAdminRoles(self):
        """Return all admin roles for this user and its groups
        """
        ars = self.adminRoles()
        for group in self.getUser().getGroups():
            gs = self.getGroupSettings(group)
            ars.extend(gs.adminRoles())
        return ars


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_emailTest')
    def manage_emailTest(self, REQUEST=None):
        ''' Send a test email to the given userid.
        '''
        destSettings = self.getUserSettings(self.getId())
        destAddresses = destSettings.getEmailAddresses()
        msg = None
        if destAddresses:
            fqdn = socket.getfqdn()
            thisUser = self.getUser()
            srcId = thisUser.getId()
            self.getUserSettings(srcId)
            srcAddress = self.dmd.getEmailFrom()
            # Read body from file probably
            body = ('This is a test message sent by %s' % srcId +
                    ' from the Zenoss installation on %s.' % fqdn)
            emsg = MIMEText(body)
            emsg['Subject'] = 'Zenoss Email Test'
            emsg['From'] = srcAddress
            emsg['To'] = ', '.join(destAddresses)
            emsg['Date'] = DateTime().rfc822()
            result, errorMsg = Utils.sendEmail(emsg, self.dmd.smtpHost, 
                                self.dmd.smtpPort,
                                self.dmd.smtpUseTLS, self.dmd.smtpUser,
                                self.dmd.smtpPass)
            if result:
                msg = 'Test email sent to %s' % ', '.join(destAddresses)
            else:
                msg = 'Test failed: %s' % errorMsg
        else:
            msg = 'Test email not sent, user has no email address.'
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Email Test',
                msg.replace("'", "\\'")
            )
            return self.callZenScreen(REQUEST)
        else:
            return msg


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_pagerTest')
    def manage_pagerTest(self, REQUEST=None):
        ''' Send a test page 
        '''
        destSettings = self.getUserSettings(self.getId())
        destPagers = [ x.strip() for x in 
            (destSettings.getPagerAddresses() or []) ]
        msg = None
        fqdn = socket.getfqdn()
        srcId = self.getUser().getId()
        testMsg = ('Test sent by %s' % srcId + 
                ' from the Zenoss installation on %s.' % fqdn)
        for destPager in destPagers:
            result, errorMsg = Utils.sendPage(destPager, testMsg, 
                                    self.dmd.pageCommand)
            if result:
                msg = 'Test page sent to %s' % ', '.join(destPagers)
            else:
                msg = 'Test failed: %s' % errorMsg
                break
        if not destPagers:
            msg = 'Test page not sent, user has no pager number.'
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Pager Test', msg)
            return self.callZenScreen(REQUEST)
        else:
            return msg

    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all user configuration
        """
        for o in self.objectValues():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)

    def getPagerAddresses(self):
        if self.pager.strip():
            return [self.pager.strip()]
        return []

    def getEmailAddresses(self):
        if self.email.strip():
            return [self.email]
        return []

    def getDotNetSession(self):
        """
        Use the Zenoss.net credentials associated with this user to log in to a
        Zenoss.net session.
        """
        session = DotNetCommunication.getDotNetSession(
                                        self.zenossNetUser, 
                                        self.zenossNetPassword)
        return session

class GroupSettings(UserSettings):

    meta_type = 'GroupSettings'
    
    factory_type_information = (
        {
            'immediate_view' : 'editGroupSettings',
            'actions'        :
            (
                {'name'         : 'Edit',
                'action'        : 'editGroupSettings',
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Administered Objects', 
                'action'        : 'administeredDevices', 
                'permissions'   : (ZEN_CHANGE_ADMIN_OBJECTS,)
                },
                {'name'         : 'Event Views',
                'action'        : 'editEventViews',
                # ideally make this its own permission
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Alerting Rules',
                'action'        : 'editActionRules',
                'permissions'   : (ZEN_CHANGE_ALERTING_RULES,),
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def _getG(self):
        return self.zport.acl_users.groupManager


    def hasNoGlobalRoles(self):
        """This is a group we never have roles. This is set to false so that
        fuctionality that would normally be taken away for a restricted user is
        left in.
        """
        return False


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUsersToGroup')
    def manage_addUsersToGroup( self, userids, REQUEST=None ):
        """ Add user to this group
        """
        if type(userids) in types.StringTypes:
            userids = [userids]
        for userid in userids:
            self._getG().addPrincipalToGroup( userid, self.id )
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Added',
                'Added %s to Group %s' % (','.join(userids), self.id)
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUserFromGroup')
    def manage_deleteUserFromGroup( self, userid ):
        self._getG().removePrincipalFromGroup( userid, self.id )

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUsersFromGroup')
    def manage_deleteUsersFromGroup(self, userids=(), REQUEST=None ):
        """ Delete users from this group
        """
        for userid in userids:
            self.manage_deleteUserFromGroup(userid)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Removed',
                'Deleted users from Group %s' % self.id
            )
            return self.callZenScreen(REQUEST)

    def getMemberUserSettings(self):
        return [ self.getUserSettings(u[0])
         for u in self._getG().listAssignedPrincipals(self.id) ]

    def getMemberUserIds(self):
        return [ u[0] for u in self._getG().listAssignedPrincipals(self.id) ]

    def printUsers(self):
        return ", ".join(self.getMemberUserIds())

    def getEmailAddresses(self):
        result = []
        for username in self.getMemberUserIds():
            result.extend(self.getUserSettings(username).getEmailAddresses())
        return result

    def getPagerAddresses(self):
        result = []
        for username in self.getMemberUserIds():
            result.extend(self.getUserSettings(username).getPagerAddresses())
        return result


InitializeClass(UserSettingsManager)
InitializeClass(UserSettings)

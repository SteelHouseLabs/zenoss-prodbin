###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ZenPackManager
ZenPackManager is a Zope Product that helps manage ZenPacks
"""

from Globals import InitializeClass
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo
from ZenossSecurity import ZEN_MANAGE_DMD
from Products.ZenUtils.Utils import binPath
from Products.ZenWidgets import messaging
import os

def manage_addZenPackManager(context, newId='', REQUEST=None):
    """
    Create a ZenPackManager instance
    """
    if not newId:
        newId = 'ZenPackManager'
    zpm = ZenPackManager(newId)
    context._setObject(newId, zpm)
    zpm = context._getOb(newId)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() + '/manage_main') 


class ZenPackManager(ZenModelRM):
    """
    ZenPackManager is responsibe for managing ZenPacks
    """

    portal_type = meta_type = 'ZenPackManager'

    default_catalog = 'zenPackNameSearch'

    _relations = ZenModelRM._relations + (
        ('packs', ToManyCont(ToOne, 'Products.ZenModel.ZenPack', 'manager')),
        )

    factory_type_information = (
        {
            'immediate_view' : 'viewZenPacks',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../editSettings'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : '../ZenUsers/manageUserFolder'
                , 'permissions'   : ( 'Manage DMD', )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'jobs'
                , 'name'          : 'Jobs'
                , 'action'        : '../joblist'
                , 'permissions'   : ( "Manage DMD", )
                },
                #{ 'id'            : 'menus'
                #, 'name'          : 'Menus'
                #, 'action'        : '../editMenus'
                #, 'permissions'   : ( "Manage DMD", )
                #},
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : '../About/zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../About/zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'backups'
                , 'name'          : 'Backups'
                , 'action'        : '../backupInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
         },
        )

    security = ClassSecurityInfo()


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addZenPack')
    def manage_addZenPack(self, packId, REQUEST=None):
        """
        Create a new zenpack on the filesystem with the given info.
        Install the pack.  If REQUEST then render the REQUEST otherwise
        return the new zenpack.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd 
        
        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        # Make sure a zenpack can be created with given info
        canCreate, msgOrId = ZenPackCmd.CanCreateZenPack(self, packId)
        if canCreate:
            packId = msgOrId
        else:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Add ZenPack', msgOrId)
                return self.callZenScreen(REQUEST, redirect=False)
            from ZenPack import ZenPackException
            raise ZenPackException(msgOrId)

        # Create it
        zpDir = ZenPackCmd.CreateZenPack(packId)

        # Install it
        zenPacks = ZenPackCmd.InstallEggAndZenPack(self.dmd, zpDir, link=True,
                                                   forceRunExternal=True)
        zenPack = self.packs._getOb(packId, None)
        if REQUEST:
            if zenPack:
                return REQUEST['RESPONSE'].redirect(zenPack.getPrimaryUrlPath())
            messaging.IMessageSender(self).sendToBrowser(
                'Error', 'There was an error creating the ZenPack.',
                priority=messaging.WARNING)
            return self.callZenScreen(REQUEST)
        return zenPack


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_removeZenPacks')
    def manage_removeZenPacks(self, ids=(), REQUEST=None):
        """
        Uninstall the given zenpacks.  Uninstall the zenpack egg.  If not in
        development mode then also delete the egg from the filesystem.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd 

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)
        
        canRemove, dependents = ZenPackCmd.CanRemoveZenPacks(self.dmd, ids)
        if not canRemove:
            msg = 'The following ZenPacks depend on one or more of the ' + \
                ' ZenPacks you are trying to remove: %s' % ','.join(dependents)
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackDependentsException
            raise ZenPackDependentsException(msg)
        for zpId in ids:
            zp = self.packs._getOb(zpId, None)
            if zp:
                if zp.isEggPack():
                    ZenPackCmd.RemoveZenPack(self.dmd, zpId, skipDepsCheck=True)
                else:
                    os.system('%s --remove %s' % (
                                            binPath('zenpack'), zpId))
                    self._p_jar.sync()
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'fetchZenPack')
    def fetchZenPack(self, packName, packVersion=''):
        """
        Retrieve the given zenpack from Zenoss.net and install.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        zp = ZenPackCmd.FetchAndInstallZenPack(self.dmd, packName, packVersion)
        if REQUEST:
            return REQUEST['RESPONSE'].redirect(zp.getPrimaryUrlPath())
        return zp



    security.declareProtected(ZEN_MANAGE_DMD, 'manage_installZenPack')
    def manage_installZenPack(self, zenpack=None, REQUEST=None):
        """
        Installs the given zenpack.  Zenpack is a file upload from the browser.
        """
        import tempfile
        import fcntl
        import popen2
        import signal
        import time
        import select
        
        ZENPACK_INSTALL_TIMEOUT = 120
        
        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        tFile = None
        child = None
        try:
            # zenpack.filename gives us filename of the zenpack with the
            # path as it exists on the client. We need just the filename.
            import re
            base_filename = re.split(r"\\|/", zenpack.filename)[-1]
            
            # Write the zenpack to the filesystem                
            tDir = tempfile.gettempdir()
            tFile = open(os.path.join(tDir, base_filename), 'wb')
            tFile.write(zenpack.read())
            tFile.close()
        
            cmd = 'zenpack --install %s' % tFile.name
            child = popen2.Popen4(cmd)
            flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
            fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
            endtime = time.time() + ZENPACK_INSTALL_TIMEOUT
            pollPeriod = 1
            firstPass = True
            while time.time() < endtime and (firstPass or child.poll()==-1):
                firstPass = False
                r, w, e = select.select([child.fromchild],[],[], pollPeriod)
                if r:
                    t = child.fromchild.read()
        finally:
            if child and child.poll() == -1:
                os.kill(child.pid, signal.SIGKILL)

        REQUEST['RESPONSE'].redirect(REQUEST['HTTP_REFERER'])
        

    def getZnetProjectOptions(self):
        """
        Return a list of 2-tuples of (option value, option name) for the
        user to select a Zenoss.net project from.
        """
        projects = self.getZnetProjectsList()
        return [(p, p.split('/')[-1]) for p in projects]


    def getZnetProjectsList(self):
        """
        Return a list of the zenoss.net projects.
        """
        import json
        import Products.ZenUtils.DotNetCommunication as DotNetCommunication
        userSettings = self.dmd.ZenUsers.getUserSettings()
        session = DotNetCommunication.getDotNetSession(
                    userSettings.zenossNetUser,
                    userSettings.zenossNetPassword)
        projects = session.retrieve('projectList')
        projects = json.loads(projects)
        return projects


    def getBrokenPackName(self, ob):
        ''' Extract the zenpack name from the broken module
        '''
        return ob.id if ob.id else ob.__class__.__module__


InitializeClass(ZenPackManager)

#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''zenrestore

Restores a zenoss backup created by zenbackup.
'''

import logging
import sys
import os
import os.path
import ConfigParser

import Globals
from Products.ZenUtils.Utils import zenPath, binPath

from ZenBackupBase import *


class ZenRestore(ZenBackupBase):

    def __init__(self):
        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenrestore")
        logging.basicConfig()
        if self.options.verbose:
            self.log.setLevel(10)
        else:
            self.log.setLevel(40)
            
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenBackupBase.buildOptions(self)

        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.  Defaults'
                                    ' to value saved with backup or "events".')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.  Defaults'
                                    ' to value saved with backup or "zenoss".')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password. Defaults'
                                    ' to value saved with backup.')
        self.parser.add_option('--dbhost',
                               dest='dbhost',
                               default='localhost',
                               help='MySQL server host.'
                                ' Defaults to value saved with backup.'),
        self.parser.add_option('--dbport',
                               dest='dbport',
                               default='3306',
                               help='MySQL server port number.'
                                ' Defaults to value saved with backup.'),
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File from which to restore.')
        self.parser.add_option('--dir',
                               dest="dir",
                               default=None,
                               help='Path to an untarred backup file'
                                        ' from which to restore.')
        self.parser.add_option('--no-zodb',
                               dest="noZODB",
                               default=False,
                               action='store_true',
                               help='Do not restore the ZODB.')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not restore the events database.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfdata",
                               default=False,
                               action='store_true',
                               help='Do not restore performance data.')
        self.parser.add_option('--deletePreviousPerfData',
                               dest="deletePreviousPerfData",
                               default=False,
                               action='store_true',
                               help='Delete ALL existing performance data before restoring?')
        self.parser.add_option('--zenpacks',
                               dest='zenpacks',
                               default=False,
                               action='store_true',
                               help=('Experimental: Restore any ZenPacks in ' 
                                     'the backup. Some ZenPacks may not work '
                                     'properly. Reinstall ZenPacks if possible'))

    def getSettings(self, tempDir):
        ''' Retrieve some options from settings file
        '''
        try:
            f = open(os.path.join(tempDir, CONFIG_FILE), 'r')
        except:
            return
        try:
            config = ConfigParser.SafeConfigParser()
            config.readfp(f)
        finally:
            f.close()
        for key, default, zemAttr in CONFIG_FIELDS:
            if getattr(self.options, key, None) == None:
                if config.has_option(CONFIG_SECTION, key):
                    setattr(self.options, key, config.get(CONFIG_SECTION, key))
                else:
                    setattr(self.options, key, default)


    def createMySqlDb(self):
        '''
        Create the events schema in MySQL if it does not exist.
        Return true if the command was able to complete, otherwise
        (eg permissions or login error), return false.
        '''
        # The original dbname is stored in the backup within dbname.txt
        # For now we ignore it and use the database specified on the command
        # line.
        sql = 'create database if not exists %s' % self.options.dbname
        if self.runMysqlCmd(sql):
            self.msg('MySQL events database creation was successful.')
            return True
        else:
            self.msg('MySQL events database creation faild and returned %d' % result[2])
            return False

    def restoreEventsDatabase(self, tempDir):
        """
        Restore the MySQL events database
        """
        eventsSql = os.path.join(tempDir, 'events.sql')
        if not os.path.isfile(eventsSql):
            self.msg('This backup does not contain an events database backup.')
            return

        # Create the MySQL db if it doesn't exist already
        self.msg('Creating the events database (if necessary).')
        if not self.createMySqlDb():
            return

        # Restore the mysql tables
        self.msg('Restoring events database.')
        sql = 'source %s' % eventsSql
        if self.runMysqlCmd(sql, switchDB=True):
            self.msg('Successfully loaded events into MySQL database.')
        else:
            self.msg('FAILED to load events into MySQL events database.')

    def doRestore(self):
        '''
        Restore from a previous backup
        '''
        def hasZeoBackup(tempDir):
            repozoDir = os.path.join(tempDir, 'repozo')
            return os.path.isdir(repozoDir)

        if self.options.file and self.options.dir:
            sys.stderr.write('You cannot specify both --file and --dir.\n')
            sys.exit(-1)
        elif not self.options.file and not self.options.dir:
            sys.stderr.write('You must specify either --file or --dir.\n')
            sys.exit(-1)
        

        # Maybe check to see if zeo is up and tell user to quit zenoss first

        rootTempDir = ''
        if self.options.file:
            if not os.path.isfile(self.options.file):
                sys.stderr.write('The specified backup file does not exist: %s\n' %
                      self.options.file)
                sys.exit(-1)
            # Create temp dir and untar backup into it
            self.msg('Unpacking backup file')
            rootTempDir = self.getTempDir()
            cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
            if os.system(cmd): return -1
            tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        else:
            self.msg('Using %s as source of restore' % self.options.dir)
            if not os.path.isdir(self.options.dir):
                sys.stderr.write('The specified backup directory does not exist:'
                                ' %s\n' % self.options.dir)
                sys.exit(-1)
            tempDir = self.options.dir

        if self.options.zenpacks and not hasZeoBackup(tempDir):
            sys.stderr.write('archive does not contain ZEO database backup, '
                             'cannot restore ZenPacks.\n')
            sys.exit(-1)

        # Maybe use values from backup file as defaults for self.options.
        self.getSettings(tempDir)
        if not self.options.dbname:
            self.options.dbname = 'events'
        if not self.options.dbuser:
            self.options.dbuser = 'zenoss'

        # If there is not a Data.fs then create an empty one
        # Maybe should read file location/name from zeo.conf
        # but we're going to assume the standard location for now.
        if not os.path.isfile(zenPath('var', 'Data.fs')):
            self.msg('There does not appear to be a zeo database.'
                        ' Starting zeo to create one.')
            os.system(binPath('zeoctl') + 'start > /dev/null')
            os.system(binPath('zeoctl') + 'stop > /dev/null')

        # Restore zopedb
        if self.options.noZODB:
            self.msg('Skipping the ZEO database..')
        elif hasZeoBackup(tempDir):
            repozoDir = os.path.join(tempDir, 'repozo')
            self.msg('Restoring the ZEO database.')
            cmd ='%s %s --recover --repository %s --output %s' % (
                        binPath('python'),
                        binPath('repozo.py'),
                        repozoDir,
                        zenPath('var', 'Data.fs'))
            if os.system(cmd): return -1
        else:
            self.msg('Archive does not contain ZEO database backup')
        
        # Copy etc files
        self.msg('Restoring config files.')
        cmd = 'rm -rf %s' % zenPath('etc')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        zenPath(),
                        os.path.join(tempDir, 'etc.tar'))
        if os.system(cmd): return -1

        # Copy ZenPack files if requested
        # check for existence of ZEO backup
        if not self.options.noZODB and \
           self.options.zenpacks and \
           hasZeoBackup(tempDir):
            tempPacks = os.path.join(tempDir, 'ZenPacks.tar')
            if os.path.isfile(tempPacks):
                self.msg('Restoring ZenPacks.')
                cmd = 'rm -rf %s' % zenPath('ZenPacks')
                if os.system(cmd): return -1
                cmd = 'tar Cxf %s %s' % (
                                zenPath(),
                                os.path.join(tempDir, 'ZenPacks.tar'))
                if os.system(cmd): return -1
                # restore bin dir when restoring zenpacks
                #make sure bin dir is in tar
                tempBin = os.path.join(tempDir, 'bin.tar')
                if os.path.isfile(tempBin):
                    self.msg('Restoring bin dir.')
                    #k option prevents overwriting existing bin files
                    cmd = ['tar', 'Cxfk', zenPath(), 
                           os.path.join(tempDir, 'bin.tar')]
                    self.runCommand(cmd)
            else:
                self.msg('Backup contains no ZenPacks.')
        
        # Restore perf files
        if self.options.noPerfdata:
            self.msg('Skipping performance data.')
        else:
            tempPerf = os.path.join(tempDir, 'perf.tar')
            if os.path.isfile(tempPerf):
                if self.options.deletePreviousPerfData:
                    self.msg('Removing previous performance data...')
                    cmd = 'rm -rf %s' % os.path.join(zenPath(), 'perf')
                    if os.system(cmd):
                        return -1

                self.msg('Restoring performance data.')
                cmd = 'tar Cxf %s %s' % (
                                zenPath(),
                                os.path.join(tempDir, 'perf.tar'))
                if os.system(cmd): return -1
            else:
                self.msg('Backup contains no perf data.')

        if self.options.noEventsDb:
            self.msg('Skipping the events database.')
        else:
            self.restoreEventsDatabase(tempDir)

        # clean up
        if self.options.file:
            self.msg('Cleaning up temporary files.')
            cmd = 'rm -r %s' % rootTempDir
            if os.system(cmd): return -1

        self.msg('Restore complete.')
        return 0


if __name__ == '__main__':
    zb = ZenRestore()
    if zb.doRestore():
        sys.exit(-1)

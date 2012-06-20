#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


__doc__='''zenbackup

Creates backup of Zope data files, Zenoss conf files and the events database.
'''

import sys
import os
import os.path
from datetime import date
import time
import logging
import ConfigParser
import subprocess
import tarfile
import tempfile
import re
import gzip

import Globals
from ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath, binPath, readable_time, unused
from Products.ZenUtils.GlobalConfig import globalConfToDict
from ZenBackupBase import *

unused(Globals)

MAX_UNIQUE_NAME_ATTEMPTS = 1000

DEFINER_PATTERN = re.compile(r'/\*((?!/\*).)*DEFINER.*?\*/')

def strip_definer(mysqldump_line):
    """Strips DEFINER statements from mysqldump lines. See ZEN-326."""
    if not mysqldump_line.startswith("/*") or len(mysqldump_line) > 500:
        # speed things up, lines with DEFINER in them 
        #    (1) start with '/*'
        #    (2) are shorter than 500 characters.
        return mysqldump_line
    return DEFINER_PATTERN.sub('', mysqldump_line)

class ZenBackup(ZenBackupBase):

    def __init__(self, argv):
        # Store sys.argv so we can restore it for ZCmdBase.
        self.argv = argv

        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenbackup")
        logging.basicConfig()
        self.log.setLevel(self.options.logseverity)

    def isZeoUp(self):
        '''
        Returns True if Zeo appears to be running, false otherwise.

        @return: whether Zeo is up or not
        @rtype: boolean
        '''
        import ZEO
        zeohome = os.path.dirname(ZEO.__file__)
        cmd = [ binPath('python'),
                os.path.join(zeohome, 'scripts', 'zeoup.py')]
        cmd += '-p 8100 -h localhost'.split()
        self.log.debug("Can we access ZODB through Zeo?")

        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            return False
        return output.startswith('Elapsed time:')

    def readZEPSettings(self):
        '''
        Read in and store the ZEP DB configuration options
        to the 'options' object.
        '''
        globalSettings = globalConfToDict()
        zepsettings = {
            'zep-user': 'zepdbuser',
            'zep-host': 'zepdbhost',
            'zep-db': 'zepdbname',
            'zep-password': 'zepdbpass',
            'zep-port': 'zepdbport'
        }

        for key in zepsettings:
            if key in globalSettings:
                value = str(globalSettings[key])
                setattr(self.options, zepsettings[key], value)

    def saveSettings(self):
        '''
        Save the database credentials to a file for use during restore.
        '''
        config = ConfigParser.SafeConfigParser()
        config.add_section(CONFIG_SECTION)

        config.set(CONFIG_SECTION, 'zodb_host', self.options.zodb_host)
        config.set(CONFIG_SECTION, 'zodb_port', str(self.options.zodb_port))
        config.set(CONFIG_SECTION, 'zodb_db', self.options.zodb_db)
        config.set(CONFIG_SECTION, 'zodb_user', self.options.zodb_user)
        config.set(CONFIG_SECTION, 'zodb_password', self.options.zodb_password)
        if self.options.zodb_socket:
            config.set(CONFIG_SECTION, 'zodb_socket', self.options.zodb_socket)

        config.set(CONFIG_SECTION, 'zepdbhost', self.options.zepdbhost)
        config.set(CONFIG_SECTION, 'zepdbport', self.options.zepdbport)
        config.set(CONFIG_SECTION, 'zepdbname', self.options.zepdbname)
        config.set(CONFIG_SECTION, 'zepdbuser', self.options.zepdbuser)
        config.set(CONFIG_SECTION, 'zepdbpass', self.options.zepdbpass)

        creds_file = os.path.join(self.tempDir, CONFIG_FILE)
        self.log.debug("Writing MySQL credentials to %s", creds_file)
        f = open(creds_file, 'w')
        try:
            config.write(f)
        finally:
            f.close()


    def getDefaultBackupFile(self):
        """
        Return a name for the backup file or die trying.

        @return: unique name for a backup
        @rtype: string
        """
        def getName(index=0):
            """
            Try to create an unique backup file name.

            @return: tar file name
            @rtype: string
            """
            return 'zenbackup_%s%s.tgz' % (date.today().strftime('%Y%m%d'),
                                            (index and '_%s' % index) or '')
        backupDir = zenPath('backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir, 0750)
        for i in range(MAX_UNIQUE_NAME_ATTEMPTS):
            name = os.path.join(backupDir, getName(i))
            if not os.path.exists(name):
                break
        else:
            self.log.critical('Cannot determine an unique file name to use'
                    ' in the backup directory (%s).' % backupDir +
                    ' Use --outfile to specify location for the backup'
                    ' file.\n')
            sys.exit(-1)
        return name


    def buildOptions(self):
        """
        Basic options setup
        """
        # pychecker can't handle strings made of multiple tokens
        __pychecker__ = 'no-noeffect no-constCond'
        ZenBackupBase.buildOptions(self)
        self.parser.add_option('--dont-fetch-args',
                                dest='fetchArgs',
                                default=True,
                                action='store_false',
                                help='By default MySQL connection information'
                                    ' is retrieved from Zenoss if not'
                                    ' specified and if Zenoss is available.'
                                    ' This disables fetching of these values'
                                    ' from Zenoss.')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='Name of file in which the backup will be stored.'
                                     ' Backups will by default be placed'
                                     ' in $ZENHOME/backups/')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not include the events database'
                                    ' in the backup.')
        self.parser.add_option('--no-zodb',
                               dest="noZopeDb",
                               default=False,
                               action='store_true',
                               help='Do not include the ZODB'
                                    ' in the backup.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfData",
                               default=False,
                               action='store_true',
                               help='Do not include performance data'
                                    ' in the backup.')
        self.parser.add_option('--no-zepindexes',
                               dest='noZepIndexes',
                               default=False,
                               action='store_true',
                               help='Do not include zep indexes in the backup')
        self.parser.add_option('--no-zenpacks',
                               dest="noZenPacks",
                               default=False,
                               action='store_true',
                               help='Do not include ZenPack data'
                                    ' in the backup.')
        self.parser.add_option('--stdout',
                               dest="stdout",
                               default=False,
                               action='store_true',
                               help='Send backup to stdout instead of to a file.')
        self.parser.add_option('--no-save-mysql-access',
                                dest='saveSettings',
                                default=True,
                                action='store_false',
                                help='Do not include zodb and zep credentials'
                                    ' in the backup file for use during restore.')

        self.parser.remove_option('-v')
        self.parser.add_option('-v', '--logseverity',
                        dest='logseverity',
                        default=20,
                        type='int',
                        help='Logging severity threshold')

    def backupMySqlDb(self, host, port, db, user, passwdType, sqlFile, socket=None, tables=None):
        command = ['mysqldump', '-u%s' %user, '--single-transaction']
        credential = self.getPassArg(passwdType)
        database = [db]

        if host and host != 'localhost':
            command.append('-h%s' % host)
            if self.options.compressTransport:
                command.append('--compress')
        if port and str(port) != '3306':
            command.append('--port=%s' % port)
        if socket:
            command.append('--socket=%s' % socket)

        with gzip.open(os.path.join(self.tempDir, sqlFile),'wb') as gf:
            # If tables are specified, backup db schema and data from selected tables.
            if tables:
                self.log.debug(' '.join(command + ['*' * 8] + ['--no-data'] + database))
                schema = subprocess.Popen(command + credential + ['--no-data'] + database,
                    stdout=subprocess.PIPE)
                gf.writelines(schema.stdout)
                schema_rc = schema.wait()

                self.log.debug(' '.join(command + ['*' * 8] + ['--no-create-info'] + database + tables))
                data = subprocess.Popen(command + credential + ['--no-create-info'] + database + tables,
                    stdout=subprocess.PIPE)
                gf.writelines(data.stdout)
                data_rc = data.wait()
            else:
                self.log.debug(' '.join(command + ['*' * 8] + database))
                schema = subprocess.Popen(command + credential + database,
                    stdout=subprocess.PIPE)
                gf.writelines(schema.stdout)
                schema_rc = schema.wait()

                data_rc = 0

            if schema_rc or data_rc:
                self.log.critical("Backup of (%s) terminated abnormally." % sqlFile)
                return -1

    def _zepRunning(self):
        """
        Returns True if ZEP is running on the system (by invoking
        zeneventserver status).
        """
        zeneventserver_cmd = zenPath('bin', 'zeneventserver')
        with open(os.devnull, 'w') as devnull:
            return not subprocess.call([zeneventserver_cmd, 'status'], stdout=devnull, stderr=devnull)

    def backupZEP(self):
        '''
        Backup ZEP
        '''
        partBeginTime = time.time()
        
        # Setup defaults for db info
        if self.options.fetchArgs:
            self.log.info('Getting ZEP dbname, user, password, port from configuration files.')
            self.readZEPSettings()

        if self.options.saveSettings:
            self.saveSettings()

        if self.options.noEventsDb:
            self.log.info('Doing a partial backup of the events database.')
            tables=['config','event_detail_index_config','event_trigger','event_trigger_subscription', 'schema_version']
        else:
            self.log.info('Backing up the events database.')
            tables = None

        self.backupMySqlDb(self.options.zepdbhost, self.options.zepdbport,
                           self.options.zepdbname, self.options.zepdbuser,
                           'zepdbpass', 'zep.sql.gz', tables=tables)

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of events database completed in %s.", subtotalTime)

        if not self.options.noEventsDb:
            zeneventserver_dir = zenPath('var', 'zeneventserver')
            if self.options.noZepIndexes:
                self.log.info('Not backing up event indexes.')
            elif self._zepRunning():
                self.log.info('Not backing up event indexes - it is currently running.')
            elif os.path.isdir(zeneventserver_dir):
                self.log.info('Backing up event indexes.')
                zepTar = tarfile.open(os.path.join(self.tempDir, 'zep.tar'), 'w')
                zepTar.add(zeneventserver_dir, 'zeneventserver')
                zepTar.close()
                self.log.info('Backing up event indexes completed.')

    def backupZenPacks(self):
        """
        Backup the zenpacks dir
        """
        #can only copy zenpacks backups if ZEO is backed up
        if not self.options.noZopeDb and os.path.isdir(zenPath('ZenPacks')):
            # Copy /ZenPacks to backup dir
            self.log.info('Backing up ZenPacks.')
            etcTar = tarfile.open(os.path.join(self.tempDir, 'ZenPacks.tar'), 'w')
            etcTar.dereference = True
            etcTar.add(zenPath('ZenPacks'), 'ZenPacks')
            etcTar.close()
            self.log.info("Backup of ZenPacks completed.")
            # add /bin dir if backing up zenpacks
            # Copy /bin to backup dir 
            self.log.info('Backing up bin dir.')
            etcTar = tarfile.open(os.path.join(self.tempDir, 'bin.tar'), 'w')
            etcTar.dereference = True
            etcTar.add(zenPath('bin'), 'bin')
            etcTar.close()
            self.log.info("Backup of bin completed.")
    
    def backupZenPackContents(self):
        dmd = ZCmdBase(noopts=True).dmd
        self.log.info("Backing up ZenPack contents.")
        for pack in dmd.ZenPackManager.packs():
            pack.backup(self.tempDir, self.log)
        self.log.info("Backup of ZenPack contents complete.")

    def backupZODB(self):
        """
        Backup the Zope database.
        """
        partBeginTime = time.time()

        self.log.info('Backing up the ZODB.')
        if self.options.saveSettings:
            self.saveSettings()
        self.backupMySqlDb(self.options.zodb_host, self.options.zodb_port,
                           self.options.zodb_db, self.options.zodb_user,
                           'zodb_password', 'zodb.sql.gz',
                           socket=self.options.zodb_socket)

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of ZODB database completed in %s.", subtotalTime)

    def backupPerfData(self):
        """
        Back up the RRD files storing performance data.
        """
        perfDir = zenPath('perf')
        if not os.path.isdir(perfDir):
            self.log.warning('%s does not exist, skipping.', perfDir)
            return

        partBeginTime = time.time()

        self.log.info('Backing up performance data (RRDs).')
        tarFile = os.path.join(self.tempDir, 'perf.tar')
        #will change dir to ZENHOME so that tar dir structure is relative
        cmd = ['tar', 'chfC', tarFile, zenPath(), 'perf']
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of performance data completed in %s.",
                      subtotalTime )


    def packageStagingBackups(self):
        """
        Gather all of the other data into one nice, neat file for easy
        tracking. Returns the filename created.
        """
        self.log.info('Packaging backup file.')
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(self.tempDir)
        tarFile = outfile
        if self.options.stdout:
            tarFile = '-'
        cmd = ['tar', 'czfC', tarFile, tempHead, tempTail]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return None
        self.log.info('Backup written to %s' % outfile)
        return outfile


    def cleanupTempDir(self):
        """
        Remove temporary files in staging directory.
        """
        self.log.info('Cleaning up staging directory %s' % self.rootTempDir)
        cmd = ['rm', '-r', self.rootTempDir]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1


    def makeBackup(self):
        '''
        Create a backup of the data and configuration for a Zenoss install.
        '''
        backupBeginTime = time.time()

        # Create temp backup dir
        self.rootTempDir = self.getTempDir()
        self.tempDir = os.path.join(self.rootTempDir, BACKUP_DIR)
        self.log.debug("Use %s as a staging directory for the backup", self.tempDir)
        os.mkdir(self.tempDir, 0750)

        # Do a full backup of zep if noEventsDb is false, otherwise only back
        # up a small subset of tables to capture the event triggers.
        if not self.options.noEventsDb or not self.options.noZopeDb:
            self.backupZEP()
        else:
            self.log.info('Skipping backup of the events database.')

        if self.options.noZopeDb:
            self.log.info('Skipping backup of ZODB.')
        else:
            self.backupZODB()

        # Copy /etc to backup dir (except for sockets)
        self.log.info('Backing up config files.')
        etcTar = tarfile.open(os.path.join(self.tempDir, 'etc.tar'), 'w')
        etcTar.dereference = True
        etcTar.add(zenPath('etc'), 'etc')
        etcTar.close()
        self.log.info("Backup of config files completed.")

        if self.options.noZenPacks:
            self.log.info('Skipping backup of ZenPack data.')
        else:
            self.backupZenPacks()
            self.backupZenPackContents()
            self.log.info("Backup of ZenPacks completed.")

        if self.options.noPerfData:
            self.log.info('Skipping backup of performance data.')
        else:
            self.backupPerfData()

        # tar, gzip and send to outfile
        outfile = self.packageStagingBackups()

        self.cleanupTempDir()

        backupEndTime = time.time()
        totalBackupTime = readable_time(backupEndTime - backupBeginTime)
        self.log.info('Backup completed successfully in %s.', totalBackupTime)
        # TODO: There's no way to tell if this initiated through the UI.
        # audit('Shell.Backup.Create', file=outfile)
        return 0


if __name__ == '__main__':
    zb = ZenBackup(sys.argv)
    if zb.makeBackup():
        sys.exit(-1)

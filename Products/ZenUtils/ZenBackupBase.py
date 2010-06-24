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


__doc__='''ZenBackupBase

Common code for zenbackup.py and zenrestore.py
'''
import tempfile
from subprocess import Popen, PIPE

from CmdBase import CmdBase


BACKUP_DIR = 'zenbackup'
CONFIG_FILE = 'backup.settings'
CONFIG_SECTION = 'zenbackup'
                      # cmd-line flag, default, zem attribute
CONFIG_FIELDS = (   ('dbname', 'events', 'database'),
                    ('dbuser', 'root', 'username'),
                    ('dbpass', '', 'password'),
                    ('dbhost', 'localhost', 'host'),
                    ('dbport', '3306', 'port'),
                    )


class ZenBackupBase(CmdBase):
    doesLogging = False


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)

    def msg(self, msg):
        '''
        If --verbose then send msg to stdout
        '''
        if self.options.verbose:
            print(msg)


    def buildOptions(self):
        """
        Command-line options setup
        """
        CmdBase.buildOptions(self)
        self.parser.add_option('-v', '--verbose',
                               dest="verbose",
                               default=False,
                               action='store_true',
                               help='Send progress messages to stdout.')
        self.parser.add_option('--temp-dir',
                               dest="tempDir",
                               default=None,
                               help='Directory to use for temporary storage.')


    def getPassArg(self):
        '''
        Return string to be used as the -p (including the "-p")
        to MySQL commands.

        @return: password and flag
        @rtype: string
        '''
        if self.options.dbpass == None:
            return ''
        return '--password="%s"' % self.options.dbpass


    def getTempDir(self):
        '''
        Return directory to be used for temporary storage
        during backup or restore.

        @return: directory name
        @rtype: string
        '''
        if self.options.tempDir:
            dir = tempfile.mkdtemp('', '', self.options.tempDir)
        else:
            dir = tempfile.mkdtemp()
        return dir
    

    def runCommand(self, cmd=[], obfuscated_cmd=None):
        """
        Execute a command and return the results, displaying pre and
        post messages.

        @parameter cmd: command to run
        @type cmd: list
        @return: results of the command (output, warnings, returncode)
        """
        if obfuscated_cmd:
            self.log.debug(' '.join(obfuscated_cmd))
        else:
            self.log.debug(' '.join(cmd))

        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, warnings = proc.communicate()
        if proc.returncode:
            self.log.warn(warnings)
        self.log.debug(output or 'No output from command')
        return (output, warnings, proc.returncode)

    def runMysqlCmd(self, sql, switchDB=False):
        """
        Run a command that executes SQL statements in MySQL.
        Return true if the command was able to complete, otherwise
        (eg permissions or login error), return false.

        @parameter sql: an executable SQL statement
        @type sql: string
        @parameter switchDB: use -D options.dbname to switch to a database?
        @type switchDB: boolean
        @return: boolean
        @rtype: boolean
        """
        cmd = ['mysql', '-u', self.options.dbuser]

        obfuscatedCmd = None
        if self.options.dbpass:
            cmd.append('--password=%s' % self.options.dbpass)

        if self.options.dbhost and self.options.dbhost != 'localhost':
            cmd.append('--host=%s' % self.options.dbhost)
        if self.options.dbport and self.options.dbport != '3306':
            cmd.append('--port=%s' % self.options.dbport)

        if switchDB:
            cmd.extend(['-D', self.options.dbname])

        cmd.extend(['-e', sql])

        if self.options.dbpass:
            obfuscatedCmd = cmd[:]
            obfuscatedCmd[3] = '--pasword=%s' % ('*' * 8)

        result = self.runCommand(cmd, obfuscated_cmd=obfuscatedCmd)
        if result[2]: # Return code from the command
            return False
        return True


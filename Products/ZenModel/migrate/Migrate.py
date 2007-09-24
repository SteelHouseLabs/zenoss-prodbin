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

__doc__='''Migrate

A small framework for data migration.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import Globals
import transaction
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Version import Version as VersionBase
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.Utils import zenPath

import sys
import logging
from textwrap import wrap
log = logging.getLogger("zen.migrate")

allSteps = []

class MigrationFailed(Exception): pass

class Version(VersionBase):
    def __init__(self, *args, **kw):
        VersionBase.__init__(self, 'Zenoss', *args, **kw)

def cleanup():
    "recursively remove all files ending with .pyc"
    import os
    count = 0
    for p, d, fs in os.walk(zenPath('Products')):
        for f in fs: 
            if f.endswith('.pyc'):
                fullPath = os.path.join(p, f)
                os.remove(fullPath)
                count += 1
    log.debug('removed %d .pyc files from Products' % count)


class Step:
    'A single migration step, to be subclassed for each new change'

    # Every subclass should set this so we know when to run it
    version = -1
    dependencies = None


    def __init__(self):
        "self insert ourselves in the list of all steps"
        allSteps.append(self)

    def __cmp__(self, other):
        result = cmp(self.version, other.version)
        if result:
            return result
        # if we're in the other dependency list, we are "less"
        if self in other.getDependencies():
            return -1
        # if other is in the out dependency list, we are "greater"
        if other in self.getDependencies():
            return 1
        # otherwise, let's just go with a nice repeatable but arbitrary name
        return cmp(self.name(), other.name())

    def getDependencies(self):
        if not self.dependencies:
            return []
        result = []
        for d in self.dependencies:
            if d is not self:
                result.append(d)
                result.extend(d.getDependencies())
            else:
                log.error("Circular dependency among migration Steps: "
                          "%s is listed as a dependency of %s ",
                          self.name(), d.name())
        return result

    def prepare(self):
        "do anything you must before running the cutover"
        pass

    def cutover(self, dmd):
        "perform changes to the database"
        raise NotImplementedError

    def cleanup(self):
        "remove any intermediate results"
        pass

    def revert(self):
        pass

    def name(self):
        return self.__class__.__name__

class Migration(ZenScriptBase):
    "main driver for migration: walks the steps and performs commit/abort"

    useDatabaseVersion = True

    def __init__(self):
        ZenScriptBase.__init__(self, connect=False)
        self.connect()
        self.allSteps = allSteps[:]
        self.allSteps.sort()

    def message(self, msg):
        log.info(msg)

    def _currentVersion(self):
        if not hasattr(self.dmd, 'version') or not self.dmd.version:
            from Products.ZenModel.ZVersion import VERSION
            self.dmd.version = 'Zenoss ' + VERSION
        if type(self.dmd.version) == type(1.0):
            self.dmd.version = "Zenoss 0.%f" % self.dmd.version
        v = VersionBase.parse(self.dmd.version)
        v.name = 'Zenoss'
        return v

    def migrate(self):
        "walk the steps and apply them"
        steps = self.allSteps[:]
        
        # check version numbers
        good = True
        while steps and steps[0].version < 0:
            raise MigrationFailed("Migration %s does not set "
                                  "the version number" %
                                  steps[0].__class__.__name__)

        app = self.dmd.getPhysicalRoot()

        # dump old steps
        
        current = self._currentVersion()
        if self.useDatabaseVersion:
            while steps and steps[0].version < current:
                steps.pop(0)
        if self.options.newer:
            while steps and steps[0].version <= current:
                steps.pop(0)

        for m in steps:
            m.prepare()

        for m in steps:
            if m.version != current:
                self.message("Database going to version %s" % m.version.long())
            self.message('Installing %s' % m.name())
            m.cutover(self.dmd)
            self.dmd.version = m.version
        if type(self.dmd.version) != type(''):
            self.dmd.version = self.dmd.version.long()

        for m in steps:
            m.cleanup()

        cleanup()

        if not self.options.steps:
            rl = ReportLoader(noopts=True, app=self.app)
            rl.options.force = True
            rl.loadDatabase()


    def cutover(self):
        '''perform the migration, applying all the new steps,
        recovering on error'''
        self.backup()
        try:
            self.migrate()
            self.success()
        except Exception, ex:
            self.error("Recovering")
            self.recover()
            raise


    def error(self, msg):
        import sys
        print >>sys.stderr, msg


    def backup(self):
        pass


    def recover(self):
        transaction.abort()
        steps = self.allSteps[:]
        current = self._currentVersion()
        while steps and steps[0].version < current:
            steps.pop(0)
        for m in steps:
            m.revert()


    def success(self):
        if self.options.commit:
            self.message('committing')
            transaction.commit()
        else:
            self.message('rolling back changes')
            self.recover()
        self.message("Migration successful")


    def parseOptions(self):
        ZenScriptBase.parseOptions(self)
        if self.args:
            if self.args == ['run']:
                sys.stderr.write('Use of "run" is depracated.\n')
            elif self.args == ['help']:
                sys.stderr.write('Use of "help" is depracated,'
                                    'use --help instead.\n')
                self.parser.print_help()
                self.parser.exit()
            elif self.args[0]:
                self.parser.error('Unrecognized option(s): %s\n' %
                    ', '.join(self.args) +
                    'Use --help for list of options.\n')


    def buildOptions(self):
        self.parser.add_option('--step',
                               action='append',
                               dest="steps",
                               help="Run the given step")
        # NB: The flag for this setting indicates a false value for the setting.
        self.parser.add_option('--dont-commit',
                               dest="commit",
                               action='store_false',
                               default=True,
                               help="Don't commit changes to the database")
        self.parser.add_option('--list',
                               action='store_true',
                               default=False,
                               dest="list",
                               help="List all the steps")
        self.parser.add_option('--level',
                               dest="level",
                               type='string',
                               default=None,
                               help="Run the steps by version number")
        self.parser.add_option('--newer',
                               dest="newer",
                               action='store_true',
                               default=False,
                               help="Run only steps newer than the "
                               "current database version.")
        ZenScriptBase.buildOptions(self)


    def orderedSteps(self):
        return self.allSteps

    def list(self):
        print ' Ver      Name        Description'
        print '-----+---------------+-----------' + '-'*40
        for s in self.allSteps:
            doc = s.__doc__
            if not doc:
                doc = sys.modules[s.__class__.__module__].__doc__ or 'Not Documented'
                doc.strip()
            indent = ' '*22
            doc = '\n'.join(wrap(doc, width=80,
                                 initial_indent=indent,
                                 subsequent_indent=indent))
            doc = doc.lstrip()
            print "%-8s %-15s %s" % (s.version.short(), s.name(), doc)

    def main(self):
        if self.options.list:
            self.list()
            return

        if self.options.level is not None:
            self.options.level = VersionBase.parse('Zenoss ' + self.options.level)
            self.allSteps = [s for s in self.allSteps
                             if s.version == self.options.level]
            self.useDatabaseVersion = False
        if self.options.steps:
            import re
            def matches(name):
                for step in self.options.steps:
                    if re.match('.*' + step + '.*', name):
                        return True
                return False
            self.allSteps = [s for s in self.allSteps if matches(s.name())]
            if not self.allSteps:
                log.error('No steps matching %s found' % self.options.steps)
                return
            self.useDatabaseVersion = False
        log.debug("Level %s, steps = %s",
                  self.options.level, self.options.steps)
        self.cutover()

#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys
import os
import os.path
import code
import atexit
import logging
from subprocess import Popen, PIPE
from optparse import OptionParser


# Parse the command line for host and port; have to do it before Zope
# configuration, because it hijacks option parsing.


parser = OptionParser(usage='usage: %prog [options] -- [ipthon_options] [ipython_args]')
parser.add_option('--host',
            dest="host", default=None,
            help="Hostname of ZEO server")
parser.add_option('--port',
            dest="port", type="int", default=None,
            help="Port of ZEO server")
parser.add_option('--script',
            dest="script", default=None,
            help="Name of file to execute.")
parser.add_option('--commit',
            dest="commit", default=False, action="store_true",
            help="Run commit() at end of script?")
parser.add_option('-n', '--no-ipython', 
            dest="use_ipython", default=True, action="store_false", 
            help="Do not embed IPython shell if IPython is found")

opts, args = parser.parse_args()

readline = rlcompleter = None
Completer = object
IPShellEmbed = None

if opts.use_ipython:    
    try:
        import readline
    
        try:
            from IPython.Shell import IPShellEmbed
        except ImportError:
            IPShellEmbed = None
        except AttributeError:
            # Looks like we have IPython but the wrong version of readline, likely on OSX 10.6
            IPShellEmbed = None
        from rlcompleter import Completer
    except ImportError:
        pass

# Zope magic ensues!
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

# Now we have the right paths, so we can do the rest of the imports
from Products.CMFCore.utils import getToolByName
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.ZenUtils.Utils import zenPath, set_context
from Products.ZenModel.IpNetwork import IpNetworkPrinterFactory

_CUSTOMSTUFF = []


def set_db_config(host=None, port=None):
    # Modify the database configuration manually
    from App.config import getConfiguration
    serverconfig = getConfiguration().databases[1].config.storage.config
    xhost, xport = serverconfig.server[0].address
    if host: xhost = host
    if port: xport = port
    serverconfig.server[0].address = (xhost, xport)


def _customStuff():
    """
    Everything available in the console is defined here.
    """

    import socket
    from transaction import commit
    from pprint import pprint
    from Products.Zuul import getFacade, listFacades
    
    # Connect to the database, set everything up
    app = Zope2.app()
    app = set_context(app)

    def login(username='admin'):
        utool = getToolByName(app, 'acl_users')
        user = utool.getUserById(username)
        if user is None:
            user = app.zport.acl_users.getUserById(username)
        user = user.__of__(utool)
        newSecurityManager(None, user)
        from AccessControl.Implementation import setImplementation
        #Chip's pitched battle against segfault.
        #import pdb;pdb.set_trace()
        #setImplementation('PYTHON')

    login('admin')

    # Useful references
    zport = app.zport
    dmd   = zport.dmd
    sync  = zport._p_jar.sync
    find  = dmd.Devices.findDevice
    devices = dmd.Devices
    me = find(socket.getfqdn())
    shell_stdout = []
    shell_stderr = []

    def reindex():
        sync()
        dmd.Devices.reIndex()
        dmd.Events.reIndex()
        dmd.Manufacturers.reIndex()
        dmd.Networks.reIndex()
        commit()

    def logout():
        noSecurityManager()

    def zhelp():
        cmds = filter(lambda x: not x.startswith("_"), _CUSTOMSTUFF)
        cmds.sort()
        for cmd in cmds: print cmd

    def grepdir(obj, regex=""):
        if regex:
            import re
            pattern = re.compile(regex)
            for key in dir(obj):
                if pattern.search(key):
                    print key

    def lookupGuid(guid):
        """
        Given a guid this returns the object that it identifies
        """
        from Products.ZenUtils.guid.interfaces import IGUIDManager
        manager = IGUIDManager(dmd)
        return manager.getObject(guid)

    def version():
        for info in zport.About.getAllVersions():
            print "%10s: %s" % (info['header'], info['data'])
        print "%10s: %s" % ("DMD", dmd.version)

    def printNets(net=dmd.Networks, format="text", out=sys.stdout):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.  To print
        out everything call printNets(dmd.Networks).  format can be text,
        python, or xml.
        """
        factory = IpNetworkPrinterFactory()
        printer = factory.createIpNetworkPrinter(format, out)
        printer.printIpNetwork(net)


    def cleandir(obj):
        portaldir = set(dir(dmd))
        objdir = set(dir(obj))
        appdir = set(dir(app))
        result = list(objdir - portaldir - appdir)
        result.sort()
        pprint(result)

    def history(start=None, end=None, lines=30,
                   number=False):
        """
        Display the history starting from entry 'start' to
        entry 'end'. Only available on platforms where the
        readline module can be imported.

        History starts from 0 and goes to a large number.
        The history file is $ZENHOME/.pyhistory by default.

        @parameter start: Line number to start printing
        @type start: integer
        @parameter end: Line number to finish printing
        @type end: integer
        @parameter lines: number of lines to show if no end
        @type lines: integer
        @parameter number: show the line numbers?
        @type number: boolean
        """
        if readline is not None:
            maxHistLength = readline.get_current_history_length()
            if start is None:
                start = maxHistLength
            if end is None:
                end = maxHistLength - lines
            if start < end:
                end, start = start, end
            for i in range(end, start):
                if number:
                    print i, readline.get_history_item(i)
                else:
                    print readline.get_history_item(i)

    def setLogLevel(level=10):
        """
        Change the logging level to allow for more insight into the
        in-flight mechanics of Zenoss.

        @parameter level: logging level at which messages display (eg logging.INFO)
        @type level: integer
        """
        log = logging.getLogger()
        log.setLevel(level)
        for handler in log.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def sh(cmd, interactive=True):
        """
        Execute a shell command.  If interactive is False, then
        direct the contents of stdout into shell_stdout and the
        output of stderr into shell_stderr.

        @parameter cmd: shell command to execute
        @type cmd: string
        @parameter interactive: show outut to the screen or not
        @type interactive: boolean
        """
        if interactive:
            proc = Popen(cmd, shell=True)
        else:
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, errors = proc.communicate()
        proc.wait()
        if not interactive:
            output = output.split('\n')[:-1]
            errors = errors.split('\n')[:-1]
            _CUSTOMSTUFF['shell_stdout'] = output
            _CUSTOMSTUFF['shell_stderr'] = errors
        return output, errors

    def edit(file=None, start=None, end=None, lines=30):
        """
        Use the value of the EDITOR environment variable to
        edit a file.  Defaults to the original Unix IDE -- vi.

        @parameter file: name of file to edit -- defaults to a temp file
        @type file: string
        @parameter start: Line number to start printing
        @type start: integer
        @parameter end: Line number to finish printing
        @type end: integer
        @parameter lines: number of lines to show if no end
        @type lines: integer
        """
        editor = os.environ.get('EDITOR', 'vi')
        isNewFile = True
        isTmpName = False
        if file == None:
            isTmpName = True
            file = os.tempnam()
            fp = open(file, 'w')
        elif os.path.exists(file):
            isNewFile = False
        else:
            fp = open(file, 'w')

        if isNewFile and readline is not None:
            maxHistLength = readline.get_current_history_length()
            if start is None:
                start = maxHistLength
            if end is None:
                end = maxHistLength - lines
            if start < end:
                end, start = start, end
            for i in range(end, start):
                fp.write(readline.get_history_item(i) + '\n')
            fp.close()

        sh('%s %s' % (editor, file))
        execfile(file, globals(), _CUSTOMSTUFF)
        if isTmpName:
            os.unlink(file)

    _CUSTOMSTUFF = locals()
    return _CUSTOMSTUFF


class ZenCompleter(Completer):
    """
    Provides the abiility to specify *just* the zendmd-specific
    stuff when you first enter and hit tab-tab, and also the
    ability to remove junk that we don't need to see.
    """
    ignored_names = [
        "COPY", "DELETE", "HEAD", "HistoricalRevisions",
        "LOCK", "MKCOL", "MOVE", "OPTIONS",
        "Open", "PROPFIND", "PROPPATCH",
        "PUT", "REQUEST", "SQLConnectionIDs",
        "SiteRootAdd", "TRACE", "UNLOCK",
        "ac_inherited_permissions",
        "access_debug_info",
        "bobobase_modification_time",
        "manage_historyCompare",
        "manage_historyCopy",
        "manage_addDTMLDocument",
        "manage_addDTMLMethod",
        "manage_clone",
        "manage_copyObjects",
        "manage_copyright",
        "manage_cutObjects",
        "manage_historicalComparison",
        "validClipData",
        "manage_CopyContainerAllItems",
        "manage_CopyContainerFirstItem",
        "manage_DAVget",
        "manage_FTPlist",
        "manage_UndoForm",
        "manage_access",
    ]
    ignored_prefixes = [
       '_', 'wl_', 'cb_', 'acl', 'http__', 'dav_',
       'manage_before', 'manage_after',
       'manage_acquired',
    ]

    current_prompt = ''
    def complete(self, text, state):
        # Don't show all objects if we're typing in code
        if self.current_prompt == sys.ps2:
            if state == 0:
                if text == '':
                    return '    '
            else:
                return None

        return Completer.complete(self, text, state)


    def global_matches(self, text):
        """
        Compute matches when text is a simple name.
        """
        matches = []
        for name in self.namespace:
            if name.startswith(text):
                matches.append(name)

        return matches

    def attr_matches(self, text):
        """
        Compute matches when text contains a dot.
        """
        matches = []
        for name in Completer.attr_matches(self, text):
            if name.endswith("__roles__"):
                continue
            component = name.split('.')[-1]
            if component in self.ignored_names:
                continue
            ignore = False
            for prefix in self.ignored_prefixes:
                if component.startswith(prefix):
                    ignore = True
                    break

            if not ignore:
                matches.append(name)

        return matches
        #return filter(lambda x: not x.endswith("__roles__"),
                      #Completer.attr_matches(self, text))



class HistoryConsole(code.InteractiveConsole):
    """
    Subclass the default InteractiveConsole to get readline history
    """
    def __init__(self, locals=None, filename="<console>",
                 histfile=zenPath('.pyhistory')):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.completer = None
        if readline is not None:
            self.completer = ZenCompleter(locals)
            readline.set_completer(self.completer.complete)
            readline.parse_and_bind("tab: complete")
        self.init_history(histfile)


    def init_history(self, histfile):
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.write_history_file(histfile)

    def raw_input(self, prompt=""):
        if self.completer:
            self.completer.current_prompt = prompt
        return code.InteractiveConsole.raw_input(self, prompt)

    def runsource(self, source, filename):
        if source and source[0] == '!':
            self.locals['sh'](source[1:])
            return False
        elif source and source[0] == '|':
            self.locals['sh'](source[1:], interactive=False)
            return False
        return code.InteractiveConsole.runsource(self, source, filename)


if __name__=="__main__":
    # Do we want to connect to a database other than the one specified in
    # zope.conf?
    if opts.host or opts.port:
        set_db_config(opts.host, opts.port)

    vars = _customStuff()
    if opts.script:
        if not os.path.exists(opts.script):
            print "Unable to open script file '%s' -- exiting" % opts.script
            sys.exit(1)
        execfile(opts.script, globals(), vars)
        if opts.commit:
            from transaction import commit
            commit()
        sys.exit(0)

    _banner = ("Welcome to the Zenoss dmd command shell!\n"
             "'dmd' is bound to the DataRoot. 'zhelp()' to get a list of "
             "commands.")

    if IPShellEmbed:
        sys.argv[1:] = args
        ipshell = IPShellEmbed(banner=_banner)
        ipshell(local_ns=vars)
    else:
        if readline is not None:
            _banner = '\n'.join( [ _banner,
                           "Use TAB-TAB to see a list of zendmd related commands.",
                           "Tab completion also works for objects -- hit tab after"
                           " an object name and '.'", " (eg dmd. + tab-key)."])


        # Start up the console
        myconsole = HistoryConsole(locals=vars)
        myconsole.interact(_banner)


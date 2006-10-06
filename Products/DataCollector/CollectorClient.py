#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""CollectorClient

Base class for Telnet and Ssh client collectors

Device Tree Parameters are:

zCommandLoginTries - number of times to try login default: 1
zCommandPathList - list of path to check for a command
zCommandExistanceCheck - shell command issued to look for executible
                        must echo succ if executible is found
                        default: test -f executible

$Id: CollectorClient.py,v 1.5 2004/04/05 02:05:30 edahl Exp $"""


__version__ = "$Revision: 1.5 $"[11:-2]

import os, sys, getpass
import logging
log = logging.getLogger("zen.CmdClient")

from twisted.internet import protocol, reactor

#Default option values
if os.environ.has_key('USER'):
    defaultUsername = os.environ['USER']
else:
    defaultUsername = ""
defaultPassword = ""
defaultLoginTries = 1
defaultLoginTimeout = 10
defaultCommandTimeout = 10 
defaultSearchPath = []
defaultExistanceTest = 'test -f %s'
        

class CollectorClient(protocol.ClientFactory):
    
    maintainConnection = False 
    cmdindex = 0
    
    def __init__(self, hostname, ip, port, commands=None, options=None, 
                    device=None, datacollector=None, log=None):

        self.hostname = hostname
        self.ip = ip
        self.port = port
        commands = commands or []
        self.cmdmap = {}
        self._commands = []
        for pname, cmd in commands:
            self.cmdmap[cmd] = pname
            self._commands.append(cmd)
        self.device = device
        self.results = []
        self.protocol = None
        self.datacollector = datacollector

        if options:
            defaultUsername = options.username
            defaultPassword = options.password
            defaultLoginTries = options.loginTries
            defaultLoginTimeout = options.loginTimeout
            defaultCommandTimeout = options.commandTimeout
            defaultSearchPath = options.searchPath
            defaultExistanceTest = options.existenceTest
            
        if device: # if we are in zope look for parameters in aq path
            self.username = getattr(device, 
                        'zCommandUsername', defaultUsername)
            self.password = getattr(device, 
                        'zCommandPassword', defaultPassword)
            self.loginTries = getattr(device, 
                        'zCommandLoginTries', defaultLoginTries)
            self.loginTimeout = getattr(device, 
                        'zCommandLoginTimeout', defaultLoginTimeout)
            self.commandTimeout = getattr(device, 
                        'zCommandCommandTimeout', defaultCommandTimeout)
            self.port = getattr(device, 'zCommandPort', self.port)
            self.searchPath = getattr(device, 
                        'zCommandSearchPath', defaultSearchPath)
            self.existenceTest = getattr(device, 
                        'zCommandExistanceTest', defaultExistanceTest)
        else:
            self.username = defaultUsername
            self.password = defaultPassword
            self.loginTries = defaultLoginTries
            self.loginTimeout = defaultLoginTimeout
            self.commandTimeout = defaultCommandTimeout
            self.searchPath = defaultSearchPath
            self.existenceTest = defaultExistanceTest

                    

    
    def addCommand(self, command):
        if type(command) == type(''):
            self._commands.append(command)
        else:
            self._commands.extend(command)


    def addResult(self, command, data, exitCode):
        "add a result pair to the results store"
        pname = self.cmdmap.get(command, command)
        self.results.append((pname, data))

  
    def getCommands(self):
        return self._commands


    def getResults(self):
        return self.results


    def commandsFinished(self):
        """called by protocol to see if all commands have been run"""
        return len(self.results) == len(self._commands)


    def clientFinished(self):
        """tell the datacollector that we are all done"""
        log.info("command client finished collection for %s",self.hostname)
        self.cmdindex = 0
        if self.datacollector:
            self.datacollector.clientFinished(self)

        

def buildOptions(parser=None, usage=None):
    "build options list that both telnet and ssh use"
   

    if not usage:
        usage = "%prog [options] hostname[:port] command"

    if not parser:
        from optparse import OptionParser
        parser = OptionParser(usage=usage, 
                                   version="%prog " + __version__)
  
    parser.add_option('-u', '--user',
                dest='username',
                default=defaultUsername,
                help='Login username')
    parser.add_option('-P', '--password',
                dest='password',
                default=defaultPassword,
                help='Login password')
    parser.add_option('-t', '--loginTries',
                dest='loginTries',
                default=defaultLoginTries,
                type = 'int',
                help='number of times to try login')
    parser.add_option('-L', '--loginTimeout',
                dest='loginTimeout',
                type = 'float',
                default = defaultLoginTimeout,
                help='timeout login expect statments')
    parser.add_option('-T', '--commandTimeout',
                dest='commandTimeout',
                type = 'float',
                default = defaultCommandTimeout,
                help='timeout when issuing a command')
    parser.add_option('-s', '--searchPath',
                dest='searchPath',
                default=defaultSearchPath,
                help='Path to use when looking for commands')
    parser.add_option('-e', '--existenceTest',
                dest='existenceTest',
                default=defaultExistanceTest,
                help='how to check for command')
    if not parser.has_option('-v'):
        parser.add_option('-v', '--logseverity',
                    dest='logseverity',
                    default=logging.INFO,
                    type='int',
                    help='Logging severity threshold')
    return parser


def parseOptions(parser, port):
    options, args = parser.parse_args()
    if len(args) < 2: 
        parser.print_help()
        sys.exit(1)
    if args[0].find(':') > -1:
        hostname,port = args[0].split(':')
    else:
        hostname = args[0]
    options.hostname = hostname
    options.port = port
    options.commands = args[1:]
    return options

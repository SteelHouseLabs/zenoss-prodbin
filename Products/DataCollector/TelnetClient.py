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

__doc__="""TelnetClient

TelnetClient is used by TelnetClient to issue commands to a machine
and return their output over the telnet protocol.

Device Tree Parameters are:

zTelnetLoginTries - number of times to try login default: 1
zTelnetLoginTimeout - timeout for expect statements during login default: 2
zTelnetPromptTimeout - pause used during prompt discovery default: 0.2
zTelnetCommandTimeout - default timeout when executing a command default: 5
zTelnetLoginRegex - regex to match the login prompt default: 'ogin:.$'
zTelnetPasswordRegex - regext to match the password prompt default: 'assword:.$'

Other Parameters that are used by both TelnetClient and SshClient:
zCommandPathList - list of path to check for a command
zCommandExistanceCheck - shell command issued to look for executible
                        must echo succ if executible is found
                        default: test -f executible

"""

import Globals

#FIXME take away except when we are totally migrated
try:
    from twisted.conch import telnet
except:
    from twisted.protocols import telnet

from twisted.internet import reactor

import re
import logging
log = logging.getLogger("zen.TelnetClient")

import CollectorClient
from Exceptions import *

from Products.ZenUtils.Utils import unused

defaultPromptTimeout = 10 
defaultLoginRegex = 'ogin:.$'
defaultPasswordRegex = 'assword:'
defaultEnable = False
defaultTermLength = False

responseMap = ("WILL", "WONT", "DO", "DONT")

def check(hostname):
    """
    Check to see if a device supports telnet

    @param hostname: name or IP address of device
    @type hostname: string
    @return: whether or not telnet port is available
    @rtype: integer
    @todo: support alternate ports
    """
    from telnetlib import Telnet
    import socket
    try:
        tn = Telnet(hostname)
        tn.close()
        return 1
    except socket.error:
        return 0


class TelnetClientProtocol(telnet.Telnet):
    """
    State-machine-based class for telnet

    To switch from one state to the next, methods
    return the next state.
    """
    mode = 'Login'

    timeout = 0
    timeoutID = None
    p1 = ""
    p2 = ""
    commandPrompt = ""
    command = ''
    enabled = -1 
    scCallLater = None
    bytes = ''
    lastwrite = ''
    result = ''
    buffer = ""

    def connectionMade(self):
        """
        Called when a telnet session is established
        """
        self.factory.myprotocol = self #bogus hack
        self.hostname = self.factory.hostname
        log.info("connected to device %s" % self.hostname)
        self.startTimeout(self.factory.loginTimeout, self.loginTimeout)
        self.protocol = telnet.TelnetProtocol()


    def iac_DO(self, feature):
        """
        Do we support this telnet feature?
        Reply back appropriately.

        @param feature: IAC feature request
        @type feature: string
        """
        log.debug("Received telnet DO feature %s" % ord(feature))
        if ord(feature) == 1: 
            self._iac_response(telnet.WILL, feature)
        else:
            self._iac_response(telnet.WONT, feature)

    def iac_DONT(self, feature):
        """
        Do we support this telnet feature?
        Reply back appropriately.

        @param feature: IAC feature request
        @type feature: string
        """
        # turn off telnet options
        log.debug("Received telnet DONT feature %s" % ord(feature))
        self._iac_response(telnet.WONT, feature)


    def iac_WILL(self, feature):
        """
        Do we support this telnet feature?
        Reply back appropriately.

        @param feature: IAC feature request
        @type feature: string
        """
        log.debug("Received telnet WILL feature %s" % ord(feature))
        # turn off telnet options
        self._iac_response(telnet.DONT, feature)


    def iac_WONT(self, feature):
        """
        Do we support this telnet feature?
        Reply back appropriately.

        @param feature: IAC feature request
        @type feature: string
        """
        log.debug("Received telnet WONT feature %s" % ord(feature))
        # turn off telnet options
        self._iac_response(telnet.DONT, feature)


    def _iac_response(self, action, feature):
        """
        Respond to IAC request with our response

        @param action: IAC action
        @type action: string
        @param feature: IAC feature request
        @type feature: string
        """
        log.debug("Sending telnet action %s feature %s" % 
                            (responseMap[ord(action)-251], ord(feature)))
        self.write(telnet.IAC+action+feature)


    def write(self, data):
        """
        Write data across the wire and record it.

        @param data: data to write
        @type data: string
        """
        self.lastwrite = data
        self.transport.write(data)


    def processChunk(self, chunk):
        """
        Given data returned from the remote device, test out
        the current chunk of data to determine whether
        or not to switch states, or just add the chunk to
        the list of data received from the host.

        If we find the end condition for the state, process
        the line.

        @param chunk: data
        @type chunk: string
        """
        self.buffer = self.buffer + chunk
        regex = None
        if self.factory.modeRegex.has_key(self.mode):
            regex = self.factory.modeRegex[self.mode] 
        log.debug("Mode '%s' regex = %s" % (self.mode, regex))
        log.debug("Chunk received = '%s'" % chunk)
        if regex and re.search(regex, chunk):
            self.processLine(self.buffer)
            self.buffer = ""
        

    def processLine(self, line):
        """
        Call a method that looks like 'telnet_*' where '*' is filled
        in by the current mode. telnet_* methods should return a string which
        will become the new mode.

        @param line: data
        @type line: string
        """
        line = re.sub("\r\n|\r", "\n", line) #convert \r\n to \n
        #if server is echoing take it out
        if self.lastwrite.startswith(line):
            self.lastwrite = self.lastwrite[len(line):]
            line = ''
        elif line.find(self.lastwrite) == 0: 
            line = line[len(self.lastwrite):]
        log.debug("mode = %s", self.mode)
        self.mode = getattr(self, "telnet_"+self.mode)(line)


    def dataReceived(self, data):
        """
        Look for data and send to processLine()

        @param data: output from telnet
        @type data: string
        """
        telnet.Telnet.dataReceived(self, data)
        log.debug('Line %r', self.bytes)
        if self.bytes:
            self.processLine(self.bytes)
        self.bytes = ''
            

    def applicationDataReceived(self, bytes):
        """
        Store any bytes received

        @param bytes: output from telnet
        @type bytes: string
        """
        self.bytes += bytes


    def startTimeout(self, timeout=1, timeoutfunc=None):
        """
        Start a timer to decide if we continue or not.

        @param timeout: time in seconds to wait
        @type timeout: integer
        @param timeoutfunc: override for the default timeout timer
        @type timeoutfunc: function
        """
        self.cancelTimeout() 
        if timeoutfunc is None: timeoutfunc = self.defaultTimeout
        self.timeoutID = reactor.callLater(timeout, timeoutfunc) 


    def cancelTimeout(self):
        """
        Cancel the timeout timer
        """
        if self.timeoutID: self.timeoutID.cancel()
        self.timeoutID = None


    def defaultTimeout(self):
        """
        Reset the timeout timer
        """
        self.transport.loseConnection()
        if self.factory.commandsFinished():
            self.factory.clientFinished()
        regex = self.factory.modeRegex.get(self.mode, "")
        log.warn("Dropping connection to %s: "
            "state '%s' timeout %.1f seconds regex '%s' buffer '%s'",
            self.factory.hostname, self.mode, self.timeout,regex,self.buffer)

                                                    

    def loginTimeout(self, loginTries=0):
        """
        Called when the timeout timer expires.

        @param loginTries: number of login failures to accept
        @type loginTries: integer
        @return: next state (Done, Login)
        @rtype: string
        """
        if loginTries == 0:
            loginTries = self.factory.loginTries

        elif loginTries == 1:
            self.transport.loseConnection()
            self.factory.clientFinished()
            log.warn("Login to device %s failed" % self.hostname)
            return "Done"

        else:
            self.factory.loginTries -= 1
            return "Login"
   

    def telnet_Login(self, data):
        """
        Called when login prompt is expected

        @param data: data sent back from the remote device
        @type data: string
        @return: next state (Login, Password)
        @rtype: string
        """
        log.debug('Search for login regex (%s) in (%s) finds: %r' % \
                  (self.factory.loginRegex, data, \
                   re.search(self.factory.loginRegex, data)))
        if not re.search(self.factory.loginRegex, data): # login failed
            return 'Login'
        log.debug("Login tries=%s" % self.factory.loginTries)
        if not self.factory.loginTries:
            self.transport.loseConnection()
            log.warn("Login to %s with username %s failed" % (
                                self.factory.hostname, self.factory.username))
        else:
            self.factory.loginTries -= 1
        log.debug("Sending username %s" % self.factory.username)
        self.write(self.factory.username + '\n')
        return 'Password'


    def telnet_Password(self, data):
        """
        Called when the password prompt is expected

        @param data: data sent back from the remote device
        @type data: string
        @return: next state (Password, FindPrompt)
        @rtype: string
        """
        log.debug('Search for password regex (%s) in (%s) finds: %r' % \
                  (self.factory.passwordRegex, data, \
                   re.search(self.factory.loginRegex, data)))
        if not re.search(self.factory.passwordRegex, data): # look for pw prompt
            return 'Password'
        log.debug("Sending password %s" % self.factory.password)
        self.write(self.factory.password + '\n')
        self.startTimeout(self.factory.promptTimeout)
        return 'FindPrompt'


    def telnet_Enable(self, unused):
        """
        Switch to 'enable' mode on a Cisco device

        @param unused: unused (unused)
        @type unused: string
        @return: next state (Password)
        @rtype: string
        """
        self.write('enable\n')
        self.startTimeout(self.factory.loginTimeout, self.loginTimeout)
        return "Password"


    def telnet_FindPrompt(self, data):
        """
        Called after login to figure out the command prompt

        @param data: data sent back from the remote device
        @type data: string
        @return: next state (ClearPromptData, FindPrompt, Password)
        @rtype: string
        """
        if not data.strip(): return 'FindPrompt'
        if re.search(self.factory.loginRegex, data): # login failed
            return self.telnet_Login(data)
        self.p1 = data
        if self.p1 == self.p2:
            self.cancelTimeout() # promptTimeout
            self.commandPrompt = self.p1
            log.debug("found command prompt '%s'" % self.p1)
            self.factory.modeRegex['Command'] = re.escape(self.p1) + "$"
            self.factory.modeRegex['SendCommand'] = re.escape(self.p1) + "$"
            if self.factory.enable:
                self.factory.enable = False
                # NB: returns Password
                return self.telnet_Enable("")
            else:
                self.scCallLater = reactor.callLater(1.0, 
                    self.telnet_SendCommand, "")
                return "ClearPromptData"
        self.p2 = self.p1
        self.p1 = ""
        log.debug("sending \\n")
        reactor.callLater(.1, self.write, "\n")
        return 'FindPrompt' 


    def telnet_ClearPromptData(self, unused):
        """
        Called to try to restore sanity to output from the user.
        Send an empty string to get back a prompt

        @param unused: unused (unused)
        @type unused: string
        @return: next state (ClearPromptData)
        @rtype: string
        """
        if self.scCallLater: self.scCallLater.cancel()
        self.scCallLater = reactor.callLater(1.0, self.telnet_SendCommand, "")
        return "ClearPromptData"


    def telnet_SendCommand(self, unused):
        """
        Get a command of the command stack and send it

        @param unused: unused (unused)
        @type unused: string
        @return: next state (Command)
        @rtype: string
        """
        if self.scCallLater and self.scCallLater.active(): 
            self.scCallLater.cancel()
        log.debug("sending command '%s'" % self.curCommand())
        self.write(self.curCommand() + '\n')
        self.startTimeout(self.factory.commandTimeout)
        self.mode = 'Command'
        return 'Command'
        

    def telnet_Command(self, data):
        """
        Process the data from a sent command
        If there are no more commands move to final state

        @param data: data sent back from the remote device
        @type data: string
        @return: next state (Command, Done)
        @rtype: string
        """
        self.result += data
        if not self.result.endswith(self.commandPrompt):
            log.debug("Prompt '%s' not found", self.commandPrompt)
            log.debug("Line ends wth '%s'", data[-5:])
            return 'Command'
        self.cancelTimeout()
        data, self.result = self.result, ''
        log.debug("command = %s" % self.curCommand())
        log.debug("data=%s" % data)
        self.factory.addResult(self.curCommand(), data[0:-len(self.p1)], None)
        self.factory.cmdindex += 1
        if self.factory.commandsFinished():
            self.factory.clientFinished()
            if not self.factory.maintainConnection:
                self.transport.loseConnection()
            return 'Done'
        else:
            # Command
            return self.telnet_SendCommand("")


    def curCommand(self):
        """
        Return the current command to run

        @return: next command to run
        @rtype: string
        """
        return self.factory._commands[self.factory.cmdindex]



class TelnetClient(CollectorClient.CollectorClient):
    """
    Reactor code to start communications and invoke our
    telnet transport mechanism.
    """
    
    def __init__(self, hostname, ip, port, plugins=[], options=None, 
                    device=None, datacollector=None):
        """
        Initializer

        @param hostname: hostname of the device
        @type hostname: string
        @param ip: IP address of the device
        @type ip: string
        @param port: port number to use to connect to device
        @type port: integer
        @param plugins: plugins
        @type plugins: list of plugins
        @param options: options
        @type options: list
        @param device: name of device
        @type device: string
        @param datacollector: object
        @type datacollector: object
        """
        CollectorClient.CollectorClient.__init__(self, hostname, ip, port, 
                            plugins, options, device, datacollector)
        global defaultPromptTimeout
        global defaultLoginRegex
        global defaultPasswordRegex
        global defaultEnable
        
        self.protocol = TelnetClientProtocol
        self.modeRegex = { 
                    'FindPrompt' : '.*',
                    'WasteTime' : '.*',
                    'Done' : '',
                    }
        self.promptPause = 1

        if options:
            defaultPromptTimeout = options.promptTimeout
            defaultLoginRegex = options.loginRegex
            defaultPasswordRegex = options.passwordRegex
            defaultEnable = options.enable

        if device: # if we are in Zope look for zProperties
            self.promptTimeout = getattr(device, 
                        'zTelnetPromptTimeout', defaultPromptTimeout)
            self.loginRegex = getattr(device, 
                        'zTelnetLoginRegex', defaultLoginRegex)
            self.passwordRegex = getattr(device, 
                        'zTelnetPasswordRegex', defaultPasswordRegex)
            self.enable = getattr(device, 
                        'zTelnetEnable', defaultEnable)
            self.termlen = getattr(device, 
                        'zTelnetTermLength', defaultTermLength)

        else:
            self.promptTimeout = defaultPromptTimeout
            self.loginRegex = defaultLoginRegex
            self.passwordRegex = defaultPasswordRegex
            self.enable = defaultEnable
            self.termlen = defaultTermLength

        self.modeRegex['Login'] = self.loginRegex
        self.modeRegex['Password'] = self.passwordRegex


    def run(self):
        """
        Start telnet collection.
        """
        if self.termlen:
            self._commands.insert(0, "terminal length 0")
        reactor.connectTCP(self.ip, self.port, self)


    def Command(self, commands):
        """
        Add new commands to be run reset cmdindex to 0

        @param commands: commands to run on the remote device
        @type commands: list of commands
        """
        CollectorClient.CollectorClient.addCommand(self, commands)
        if self.myprotocol.mode != "Command": 
            self.myprotocol.telnet_SendCommand("")


    def clientConnectionFailed(self, connector, reason):
        """
        If we don't connect let the modeler know

        @param connector: unused (unused)
        @type connector: unused
        @param reason: error message to report
        @type reason: string
        """
        unused(connector)
        log.warn(reason.getErrorMessage())
        self.clientFinished()
       


def buildOptions(parser=None, usage=None):
    """
    Command-line telnet options
    """
    
    parser = CollectorClient.buildOptions(parser,usage)

    parser.add_option('-r', '--promptTimeout',
                dest='promptTimeout',
                type = 'float',
                default = defaultPromptTimeout,
                help='Timeout when discovering prompt')
    parser.add_option('-x', '--loginRegex',
                dest='loginRegex',
                default = defaultLoginRegex,
                help='Python regular expression that will find the login prompt')
    parser.add_option('-w', '--passwordRegex',
                dest='passwordRegex',
                default = defaultPasswordRegex,
                help='Python regex that will find the password prompt')
    parser.add_option('--enable',
                dest='enable', action='store_true', default=False,
                help="Enter 'enable' mode on a Cisco device")
    parser.add_option('--termlen',
                dest='termlen', action='store_true', default=False,
                help="Enter 'send terminal length 0' on a Cisco device")
    return parser


class FakePlugin(object):
    """
    Fake class to provide plugin instances for command-line processing.
    """
    def __init__( self, command='' ):
        self.command= command
    
    def __repr__( self ):
        return "'%s'" % self.command
    

def commandsToPlugins( commands ):
    """
    The TelntClient class expects plugins.
    Convert commands like 'ls a', 'ls b' to plugin instances.
    Duplicate commands will (eventually) be removed.
    This is used to support command-line arguments.

    @param commands: list of commands from command-line
    @type commands: list of strings
    @return: list of commands, plugin-style
    @rtype: list of FakePlugins
    """
    return [ FakePlugin( cmd ) for cmd in commands ]


def main():
    """
    Test harness main()

    Usage:

    python TelnetClient.py hostname[:port] comand [command]

    Each command must be enclosed in quotes (") to be interpreted
    properly as a complete unit.
    """
    import socket
    import getpass
    import pprint

    parser = buildOptions()
    options = CollectorClient.parseOptions(parser, 23)
    if not options.password:
        options.password = getpass.getpass("%s@%s's password: " % 
                        (options.username, options.hostname))
    logging.basicConfig()
    log.setLevel(options.logseverity)
    commands = commandsToPlugins( options.commands )
    client = TelnetClient(options.hostname,
                          socket.gethostbyname(options.hostname),
                          options.port,
                          plugins=commands, options=options)
    client.run()
    client.clientFinished= reactor.stop

    reactor.run()

    pprint.pprint(client.getResults())

if __name__ == '__main__':
    main()

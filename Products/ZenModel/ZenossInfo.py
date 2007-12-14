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

import os
import sys
import re
import logging
log = logging.getLogger("zen.ZenossInfo")

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelItem import ZenModelItem
from Products.ZenUtils import Time
from Products.ZenUtils.Version import *
from Products.ZenUtils.Utils import zenPath

from Products.ZenEvents.UpdateCheck import UpdateCheck, parseVersion

def manage_addZenossInfo(context, id='About', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    context._setObject(id, about)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() +'/manage_main')

class ZenossInfo(ZenModelItem, SimpleItem):

    portal_type = meta_type = 'ZenossInfo'

    security = ClassSecurityInfo()

    _properties = (
        {'id':'id', 'type':'string'},
        {'id':'title', 'type':'string'},
    )

    factory_type_information = (
        {
            'immediate_view' : 'zenossInfo',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../dmd/editSettings'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dmd/dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : '../dmd/ZenUsers/manageUserFolder'
                , 'permissions'   : ( 'Manage DMD', )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : '../dmd/viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'menus'
                , 'name'          : 'Menus'
                , 'action'        : '../dmd/editMenus'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../dmd/editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : 'zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : 'zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
           )
          },
        )


    security.declarePublic('getZenossVersion')
    def getZenossVersion(self):
        from Products.ZenModel.ZVersion import VERSION
        return Version.parse("Zenoss %s %s" %
                    (VERSION, self.getZenossRevision()))


    security.declarePublic('getZenossVersionShort')
    def getZenossVersionShort(self):
        return self.getZenossVersion().short()


    def getOSVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getOSVersion())
            v.full()
        """
        if os.name == 'posix':
            sysname, nodename, version, build, arch = os.uname()
            name = "%s (%s)" % (sysname, arch)
            major, minor, micro = getVersionTupleFromString(version)
            comment = ' '.join(os.uname())
        elif os.name == 'nt':
            from win32api import GetVersionEx
            major, minor, micro, platformID, additional = GetVersionEx()
            name = 'Windows %s (%s)' % (os.name.upper(), additional)
            comment = ''
        else:
            raise VersionNotSupported
        return Version(name, major, minor, micro, 0, comment)


    def getPythonVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getPythonVersion())
            v.full()
        """
        name = 'Python'
        major, minor, micro, releaselevel, serial = sys.version_info
        return Version(name, major, minor, micro)


    def getMySQLVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getMySQLVersion())
            v.full()

        The regex was tested against the following output strings:
            mysql  Ver 14.12 Distrib 5.0.24, for apple-darwin8.5.1 (i686) using readline 5.0
            mysql  Ver 12.22 Distrib 4.0.24, for pc-linux-gnu (i486)
            mysql  Ver 14.12 Distrib 5.0.24a, for Win32 (ia32)
        """
        cmd = 'mysql --version'
        fd = os.popen(cmd)
        output = fd.readlines()
        version = "0"
        if fd.close() is None and len(output) > 0:
            output = output[0].strip()
            regexString = '(mysql).*Ver [0-9]{2}\.[0-9]{2} '
            regexString += 'Distrib ([0-9]+.[0-9]+.[0-9]+)(.*), for (.*\(.*\))'
            regex = re.match(regexString, output)
            if regex:
                name, version, release, info = regex.groups()
        comment = 'Ver %s' % version
        # the name returned in the output is all lower case, so we'll make our own
        name = 'MySQL'
        major, minor, micro = getVersionTupleFromString(version)
        return Version(name, major, minor, micro, 0, comment)


    def getRRDToolVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getRRDToolVersion())
            v.full()
        """
        cmd = zenPath('bin', 'rrdtool')
        if not os.path.exists(cmd):
            cmd = 'rrdtool'
        fd = os.popen(cmd)
        output = fd.readlines()[0].strip()
        fd.close()
        name, version = output.split()[:2]
        major, minor, micro = getVersionTupleFromString(version)
        return Version(name, major, minor, micro)


    def getTwistedVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getTwistedVersion())
            v.full()
        """
        from twisted._version import version as v

        return Version('Twisted', v.major, v.minor, v.micro)


    def getZopeVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use extended call syntax:

            v = Version(*getZopeVersion())
            v.full()
        """
        from App import version_txt as version

        name = 'Zope'
        major, minor, micro, status, release = version.getZopeVersion()
        return Version(name, major, minor, micro)

    
    def getZenossRevision(self):
        try:
            os.chdir(zenPath('Products'))
            fd = os.popen("svn info 2>/dev/null | grep Revision | awk '{print $2}'")
            return fd.readlines()[0].strip()
        except:
            return ''


    def getNetSnmpVersion(self):
        from pynetsnmp.netsnmp import lib
        return Version.parse('NetSnmp %s ' % lib.netsnmp_get_version())


    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        versions = (
        {'header': 'Zenoss', 'data': self.getZenossVersion().full(), 
            'href': "http://www.zenoss.com" },
        {'header': 'OS', 'data': self.getOSVersion().full(),
            'href': "http://www.tldp.org" },
        {'header': 'Zope', 'data': self.getZopeVersion().full(),
            'href': "http://www.zope.org" },
        {'header': 'Python', 'data': self.getPythonVersion().full(),
            'href': "http://www.python.org" },
        {'header': 'Database', 'data': self.getMySQLVersion().full(),
            'href': "http://www.mysql.com" },
        {'header': 'RRD', 'data': self.getRRDToolVersion().full(),
            'href': "http://oss.oetiker.ch/rrdtool" },
        {'header': 'Twisted', 'data': self.getTwistedVersion().full(),
            'href': "http:///twistedmatrix.com/trac" },
        )
        try:
            versions += (
                {'header': 'NetSnmp', 'data': self.getNetSnmpVersion().full(),
                 'href': "http://net-snmp.sourceforge.net"  },
                )
        except:
            pass
        return versions

    security.declareProtected('View','getAllVersions')


    def getAllUptimes(self):
        """
        Return a list of daemons with their uptimes.
        """
        app = self.getPhysicalRoot()
        uptimes = []
        zope = {
            'header': 'Zope',
            'data': app.Control_Panel.process_time(),
        }
        uptimes.append(zope)
        return uptimes
    security.declareProtected('View','getAllUptimes')



    daemon_tooltips= {
      "zeoctl": "Zope Enterprise Objects server (shares database between Zope instances)",
      "zopectl": "The Zope open source web application server",
      "zenhub": "Broker between the data layer and the collection daemons",
      "zenping": "ICMP ping status monitoring",
      "zensyslog": "Collection of and classification of syslog events",
      "zenstatus": "Active TCP connection testing of remote daemons",
      "zenactions": "Alerts (SMTP, SNPP and Maintenance Windows)",
      "zentrap": "Receives SNMP traps and turns them into events",
      "zenmodeler": "Configuration collection and configuration",
      "zenperfsnmp": "High performance asynchronous SNMP performance collection",
      "zencommand": "Runs plug-ins on the local box or on remote boxes through SSH",
      "zenprocess": "Process monitoring using SNMP host resources MIB",
      "zenwin": "Windows Service Monitoring (WMI)",
      "zeneventlog": "Collect (WMI) event log events (aka NT Eventlog)",
      "zenwinmodeler": "MS Windows configuration collection and configuration",
      "zendisc": "Discover the network topology to find active IPs and devices",
      "zenperfxmlrpc": "XML RPC data collection",
    }


    def getZenossDaemonStates(self):
        """
        Return a data structures representing the states of the supported
        Zenoss daemons.
        """
        states = []
        activeButtons = {'button1': 'Restart', 'button2': 'Stop', 'button2state': True}
        inactiveButtons = {'button1': 'Start', 'button2': 'Stop', 'button2state': False}
        for daemon in self._getDaemonList():
            pid = self._getDaemonPID(daemon)
            if pid:
                buttons = activeButtons
                msg = 'Up'
                color = '#0F0'
            else:
                buttons = inactiveButtons
                msg = 'Down'
                color = '#F00'

            if daemon in self.daemon_tooltips:
               tooltip= self.daemon_tooltips[ daemon ]
            else:
               tooltip= ''

            states.append({
                'name': daemon,
                'pid': pid,
                'msg': msg,
                'tooltip': tooltip,
                'color': color,
                'buttons': buttons})

        return states


    def _pidRunning(self, pid):
        try:
            os.kill(pid, 0)
            return pid
        except OSError, ex:
            import errno
            errnum, msg = ex.args
            if errnum == errno.EPERM:
                return pid


    def _getDaemonPID(self, name):
        """
        For a given daemon name, return its PID from a .pid file.
        """
        if name == 'zopectl':
            name = 'Z2'
        elif name == 'zeoctl':
            name = 'ZEO'
        else:
            name = "%s.py" % name
        pidFile = zenPath('var', '%s.pid' % name)
        if os.path.exists(pidFile):
            pid = open(pidFile).read()
            try:
                pid = int(pid)
            except ValueError:
                return None
            return self._pidRunning(int(pid))
        else:
            pid = None
        return pid


    def _getDaemonList(self):
        """
        Get the list of supported Zenoss daemons.
        """
        masterScript = zenPath('bin', 'zenoss')
        daemons = []
        for line in os.popen("%s list" % masterScript).readlines():
            daemons.append(line.strip())
        return daemons


    def getZenossDaemonConfigs(self):
        """
        Return a data structures representing the config infor for the
        supported Zenoss daemons.
        """
        return [ dict(name=x) for x in self._getDaemonList() ]

    def _readLogFile(self, filename, maxBytes):
        fh = open(filename)
        try:
            size = os.path.getsize(filename)
            if size > maxBytes:
                fh.seek(-maxBytes, 2)
                # the first line could be a partial line, so skip it
                fh.readline()
            return fh.read()
        finally:
           fh.close()

    def getLogData(self, daemon, kb=500):
        """
        Get the last kb kilobytes of a daemon's log file contents.
        """
        maxBytes = 1024 * int(kb)
        if daemon == 'zopectl':
            daemon = 'event'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        if daemon == 'zopectl':
            daemon = 'event'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        filename = zenPath('log', "%s.log" % daemon)
        # if there is no data read, we don't want to return something that can
        # be interptreted as "None", so we make the default a single white
        # space
        data = ' '
        try:
            data = self._readLogFile(filename, maxBytes) or ' '
        except IOError:
            data = 'Error reading log file'
        return data


    def _getConfigFilename(self, daemon):
        if daemon == 'zopectl':
            daemon = 'zope'
        elif daemon == 'zeoctl':
            daemon = 'zeo'
        return zenPath('etc', "%s.conf" % daemon)

    def _readConfigFile(self, filename):
       fh = open(filename)
       try:
           return fh.read()
       finally:
           fh.close()
        
    def getConfigData(self, daemon):
        """
        Return the contents of the daemon's config file.
        """
        filename = self._getConfigFilename(daemon)
        # if there is no data read, we don't want to return something that can
        # be interptreted as "None", so we make the default a single white
        # space
        data = ' '
        try:
            data = self._readConfigFile(filename) or  ' '
        except IOError:
            data = 'Unable to read config file'
        return data


    def manage_saveConfigData(self, REQUEST):
        """
        Save config data from REQUEST to the daemon's config file.
        """
        daemon = REQUEST.form.get('daemon')
        filename = self._getConfigFilename(daemon)
        try:
            fh = open(filename, 'w+')
            data = REQUEST.form.get('data')
            fh.write(data)
        finally:
            fh.close()
        return self.callZenScreen(REQUEST, redirect=True)


    def manage_daemonAction(self, REQUEST):
        """
        Start, stop, or restart Zenoss daemons from a web interface.
        """
        legalValues = ['start', 'restart', 'stop']
        action = (REQUEST.form.get('action') or '').lower()
        if action not in legalValues:
            return self.callZenScreen(REQUEST)
        daemonName = REQUEST.form.get('daemon')
        self.doDaemonAction(daemonName, action)
        return self.callZenScreen(REQUEST)
    security.declareProtected('Manage DMD','manage_daemonAction')


    def doDaemonAction(self, daemonName, action):
        """
        Do the given action (start, stop, restart) or the given daemon.
        Block until the action is completed.
        No return value.
        """
        import time
        import subprocess
        daemonPath = zenPath('bin', daemonName)
        if not os.path.isfile(daemonPath):
            return
        log.info('Processing a %s for %s' % (action, daemonName))
        proc = subprocess.Popen([daemonPath, action], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
        code = proc.wait()
        if code:
            log.info('Error from %s: %s (%s)' % (daemonName, proc.stdout.read(),
                        code))
        if action in ('stop', 'restart'):
            time.sleep(2)


    def manage_checkVersion(self, optInOut=False, optInOutMetrics=False, REQUEST=None):
        "Check for Zenoss updates on the Zenoss website"
        self.dmd.versionCheckOptIn = optInOut
        self.dmd.reportMetricsOptIn = optInOutMetrics
        # There is a hidden field for manage_checkVersions in the form so that
        # the javascript submit() calls will end up calling this method.
        # That means that when user hits the Check Now button we will receive
        # 2 values for that field.  (button is that same field name.)
        # We want to initiate only when the button is pressed.
        if self.dmd.versionCheckOptIn \
          and REQUEST \
          and isinstance(REQUEST.form['manage_checkVersion'], list):
            uc = UpdateCheck()
            uc.check(self.dmd, self.dmd.ZenEventManager, manual=True)
        return self.callZenScreen(REQUEST)
    security.declareProtected('Manage DMD','manage_checkVersion')


    def lastVersionCheckedString(self):
        if not self.dmd.lastVersionCheck:
            return "Never"
        return Time.LocalDateTime(self.dmd.lastVersionCheck)


    def versionBehind(self):
        if self.dmd.availableVersion is None:
            return False
        if parseVersion(self.dmd.availableVersion) > self.getZenossVersion():
            return True
        return False

    
InitializeClass(ZenossInfo)

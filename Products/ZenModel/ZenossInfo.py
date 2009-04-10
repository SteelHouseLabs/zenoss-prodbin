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

import os
import os.path
import sys
import re
from urllib import unquote
from subprocess import Popen, PIPE, call
from xml.dom.minidom import parse
import shutil
import traceback
import logging
log = logging.getLogger("zen.ZenossInfo")

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelItem import ZenModelItem
from Products.ZenUtils import Time
from Products.ZenUtils.Version import *
from Products.ZenUtils.Utils import zenPath, binPath
from Products.ZenWidgets import messaging

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
                , 'action'        : '../dmd/ZenPackManager/viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'jobs'
                , 'name'          : 'Jobs'
                , 'action'        : '../dmd/joblist'
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
                { 'id'            : 'backups'
                , 'name'          : 'Backups'
                , 'action'        : '../dmd/backupInfo'
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
            /usr/local/zenoss/mysql/bin/mysql.bin  Ver 14.12 Distrib 5.0.45, for unknown-linux-gnu (x86_64) using readline 5.0
        """
        cmd = 'mysql --version'
        fd = os.popen(cmd)
        output = fd.readlines()
        version = "0"
        if fd.close() is None and len(output) > 0:
            output = output[0].strip()
            regexString = '.*(mysql).*Ver [0-9]{2}\.[0-9]{2} '
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
        cmd = binPath('rrdtool')
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
        """
        Determine the Zenoss version number

        @return: version number or ''
        @rtype: string
        """
        try:
            products = zenPath("Products")
            cmd = "svn info '%s' 2>/dev/null | awk '/Revision/ {print $2}'" % products
            fd = os.popen(cmd)
            return fd.readlines()[0].strip()
        except:
            return ''


    def getNetSnmpVersion(self):
        from pynetsnmp.netsnmp import lib
        return Version.parse('NetSnmp %s ' % lib.netsnmp_get_version())


    def getPyNetSnmpVersion(self):
        from pynetsnmp.version import VERSION
        return Version.parse('PyNetSnmp %s ' % VERSION)


    def getWmiVersion(self):
        from pysamba.version import VERSION
        return Version.parse('Wmi %s ' % VERSION)


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
        try:
            versions += (
                {'header': 'PyNetSnmp', 'data': self.getPyNetSnmpVersion().full(),
                 'href': "http://www.zenoss.com"  },
                )
        except:
            pass
        try:
            versions += (
                {'header': 'WMI', 'data': self.getWmiVersion().full(),
                 'href': "http://www.zenoss.com"  },
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
        elif '_' in name:
            collector, daemon = name.split('_', 1)
            name = '%s-%s' % (daemon, collector)
        else:
            name = "%s-localhost" % name
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
        masterScript = binPath('zenoss')
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

    def _getLogPath(self, daemon):
        """
        Returns the path the log file for the daemon this is monkey-patched
        in the distributed collector zenpack to support the localhost
        subdirectory.
        """
        return zenPath('log', "%s.log" % daemon)

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
        filename = self._getLogPath(daemon)
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

    def parseconfig(self, filename=""):
        """
        From the given configuration file construct a configuration object
        """
        configs = {}

        config_file = open(filename)
        try:
            for line in config_file:
                line = line.strip()
                if line.startswith('#'): continue
                if line == '': continue

                try:
                    key, value = line.split(None, 1)
                except ValueError:
                    # Ignore errors
                    continue
                configs[key] = value
        finally:
            config_file.close()

        return configs

    def show_daemon_xml_configs(self, daemon, REQUEST=None ):
        """
        Display the daemon configuration options in an XML format.
        Merges the defaults with options in the config file.
        """
        # Sanity check
        if not daemon or daemon == '':
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error',
                'Called without a daemon name',
                priority=messaging.WARNING
            )
            return []

        if daemon in [ 'zeoctl', 'zopectl' ]:
            return []

        xml_default_name = zenPath( "etc", daemon + ".xml" )
        try:
            # Always recreate the defaults file in order to avoid caching issues
            log.debug("Creating XML config file for %s" % daemon)
            make_xml = ' '.join([daemon, "genxmlconfigs", ">", xml_default_name])
            proc = Popen(make_xml, shell=True, stdout=PIPE, stderr=PIPE)
            output, errors = proc.communicate()
            proc.wait()
            if proc.returncode != 0:
                log.error(errors)
                messaging.IMessageSender(self).sendToBrowser(
                    'Internal Error', errors,
                    priority=messaging.CRITICAL
                )
                return [["Output", output, errors, make_xml, "string"]]
        except Exception, ex:
            msg = "Unable to execute '%s'\noutput='%s'\nerrors='%s'\nex=%s" % (
                        make_xml, output, errors, ex)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Error in command", output, errors, make_xml, "string"]]

        try:
            xml_defaults = parse( xml_default_name )
        except:
            info = traceback.format_exc()
            msg = "Unable to parse XML file %s because %s" % (
                xml_default_name, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Error parsing XML file", xml_default_name, "XML", info, "string"]]

        configfile = self._getConfigFilename(daemon)
        try:
            # Grab the current configs
            current_configs = self.parseconfig( configfile )
        except:
            info = traceback.format_exc()
            msg = "Unable to obtain current configuration from %s because %s" % (
                       configfile, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["Configuration file issue", configfile, configfile, info, "string"]]

        all_options = {}
        ignore_options = ['configfile', 'cycle', 'daemon', 'weblog']
        try:
            for option in xml_defaults.getElementsByTagName('option'):
                id = option.attributes['id'].nodeValue
                if id in ignore_options:
                    continue
                try:
                    help = unquote(option.attributes['help'].nodeValue)
                except:
                    help = ''

                try:
                    default = unquote(option.attributes['default'].nodeValue)
                except:
                    default = ''
                if default == '[]':  # Attempt at a list argument -- ignore
                    continue

                all_options[id] = [
                    id,
                    current_configs.get(id, default),
                    default,
                    help,
                    option.attributes['type'].nodeValue,
                ]

        except:
            info = traceback.format_exc()
            msg = "Unable to merge XML defaults with config file" \
                      " %s because %s" % (configfile, info)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return [["XML file issue", daemon, xml_default_name, info, "string"]]

        return [all_options[name] for name in sorted(all_options.keys())]


    def save_daemon_configs( self, REQUEST=None, **kwargs ):
        """
        Save the updated daemon configuration to disk.
        """
        if not REQUEST:
            return
        elif not hasattr(REQUEST, 'form'):
            return

        # Sanity check
        formdata = REQUEST.form
        ignore_names = ['save_daemon_configs', 'zenScreenName', 'daemon_name']

        daemon = formdata.get('daemon_name', '')
        if not daemon or daemon in ['zeoctl', 'zopectl']:
            return
        for item in ignore_names:
            del formdata[item]

        if not formdata: # If empty, don't overwrite -- assume an error
            msg = "Received empty form data for %s config -- ignoring" % (
                      daemon)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            return

        configfile = self._getConfigFilename(daemon)
        config_file_pre = configfile + ".pre"
        try:
            config = open( config_file_pre, 'w' )
            config.write("# Config file written out from GUI\n")
            for key, value in formdata.items():
                if value == '':
                    continue
                if key == value: # Yes, this is strange
                    value = True
                config.write('%s %s\n' % (key, value))
            config.close()
        except Exception, ex:
            msg = "Couldn't write to %s because %s" % (config_file_pre, ex)
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )
            config.close()
            try:
                os.unlink(config_file_pre)
            except:
                pass
            return

        # If we got here things succeeded
        config_file_save = configfile + ".save"
        try:
            shutil.copy(configfile, config_file_save)
        except:
            log.error("Unable to make backup copy of %s" % configfile)
            # Don't bother telling the user
        try:
            shutil.move(config_file_pre, configfile)
        except:
            msg = "Unable to save contents to %s" % configfile
            log.error(msg)
            messaging.IMessageSender(self).sendToBrowser(
                'Internal Error', msg,
                priority=messaging.CRITICAL
            )


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
        daemonPath = binPath(daemonName)
        if not os.path.isfile(daemonPath):
            return
        log.info('Telling %s to %s' % (daemonName, action))
        proc = subprocess.Popen([daemonPath, action], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
        output, _ = proc.communicate()
        code = proc.wait()
        if code:
            log.info('Error from %s: %s (%s)' % (daemonName, output, code))
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

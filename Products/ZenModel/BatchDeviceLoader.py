###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """zenbatchload

zenbatchload loads a list of devices read from a file.
"""

import sys
import re

import Globals
from ZODB.POSException import ConflictError
from ZODB.transact import transact
from zope.component import getUtility

from Products.ZenModel.interfaces import IDeviceLoader
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenModel.Device import Device
from Products.ZenRelations.ZenPropertyManager import iszprop
from zExceptions import BadRequest


class BatchDeviceLoader(ZCmdBase):
    """
    Base class wrapping around dmd.DeviceLoader
    """

    sample_configs = """#
# Example zenbatchloader device file
#
# This file is formatted with one entry per line, like this:
#
#  /Devices/device_class_name Python-expression
#  hostname Python-expression
#
# For organizers (ie the /Devices path), the Python-expression
# is used to define defaults to be used for devices listed
# after the organizer. The defaults that can be specified are:
#
#   * loader arguments (use the --show_options flag to show these)
#   * zPropertie (from a device, use the More -> zProperties
#      menu option to see the available ones.)
#
#      NOTE: new zProperties *cannot* be created through this file
#
#  The Python-expression is used to create a dictionary of settings.
#  device_settings = eval( 'dict(' + python-expression + ')' )
#


# If no organizer is specified at the beginning of the file,
# defaults to the /Devices/Discovered device class.
device0 comments="A simple device"
# All settings must be seperated by a comma.
device1 comments="A simple device", zSnmpCommunity='blue', zSnmpVer='v1'

# Notes for this file:
#  * Oraganizer names *must* start with '/'
#
/Devices/Server/Linux zSnmpPort=1543
# Python strings can use either ' or " -- there's no difference.
# As a special case, it is also possible to specify the IP address
linux_device1 setManageIp='10.10.10.77', zSnmpCommunity='blue', zSnmpVer="v2c"
# A '\' at the end of the line allows you to place more
# expressions on a new line. Don't forget the comma...
linux_device2 zLinks="<a href='http://example.org'>Support site</a>",  \
zTelnetEnable=True, \
zTelnetPromptTimeout=15.3

# A new organizer drops all previous settings, and allows
# for new ones to be used.  Settings do not span files.
/Devices/Server/Windows zWinUser="administrator", zWinPassword='fred'
# Bind templates
windows_device1 zDeviceTemplates=[ 'Device', 'myTemplate' ]
# Override the default from the organizer setting.
windows_device2 zWinUser="administrator", zWinPassword='thomas'

# Apply other settings to the device
settingsDevice setManageIp='10.10.10.77', setLocation="123 Elm Street", \
  setSystems=['/mySystems'], setPerformanceMonitor='remoteCollector1', \
  setHWSerialNumber="abc123456789", setGroups=['/myGroup'], \
  setHWProduct=('myproductName','manufacturer'), setOSProduct=('OS Name','manufacturer')

# If the device or device class contains a space, then it must be quoted (either ' or ")
"/Server/Windows/WMI/Active Directory/2008"

# Now, what if we have a device that isn't really a device, and requires
# a special loader?
# The 'loader' setting requires a registered utility, and 'loader_arg_keys' is
# a list from which any other settings will be passed into the loader callable.
#
# Here is a commmented-out example of how a VMware endpoint might be added:
#
#/Devices/VMware loader='vmware', loader_arg_keys=['host', 'username', 'password', 'useSsl', 'id']
#esxwin2 id='esxwin2', host='esxwin2.zenoss.loc', username='testuser', password='password', useSsl=True
"""

    def __init__(self):
        ZCmdBase.__init__(self)
        self.defaults = {}

        self.loader = self.dmd.DeviceLoader.loadDevice

        # Create the list of options we want people to know about
        self.loader_args = dict.fromkeys( self.loader.func_code.co_varnames )
        unsupportable_args = [
            'REQUEST', 'device', 'self', 'xmlrpc', 'e', 'handler',
        ]
        for opt in unsupportable_args:
            if opt in self.loader_args:
                del self.loader_args[opt]

    def loadDeviceList(self, args=None):
        """
        Read through all of the files listed as arguments and
        return a list of device entries.

        @parameter args: list of filenames (uses self.args is this is None)
        @type args: list of strings
        @return: list of device specifications
        @rtype: list of dictionaries
        """
        if args is None:
            args = self.args

        device_list = []
        for filename in args:
            try:
                data = open(filename,'r').readlines()
            except IOError:
                self.log.critical("Unable to open the file '%s'" % filename)
                continue

            temp_dev_list = self.parseDevices(data)
            if temp_dev_list:
                device_list += temp_dev_list

        return device_list

    def applyZProps(self, device, device_specs):
        """
        Apply zProperty settings (if any) to the device.

        @parameter device: device to modify
        @type device: DMD device object
        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        """
        self.log.debug( "Applying zProperties..." )
        # Returns a list of (key, value) pairs.
        # Convert it to a dictionary.
        dev_zprops = dict( device.zenPropertyItems() )

        for zprop, value in device_specs.items():
            if not iszprop(zprop):
               continue

            if zprop in dev_zprops:
                try:
                    device.setZenProperty(zprop, value)
                except BadRequest:
                    self.log.warn( "Object %s zproperty %s is invalid or duplicate" % (
                       device.titleOrId(), zprop) )
            else:
                self.log.warn( "The zproperty %s doesn't exist in %s" % (
                       zprop, device_specs.get('deviceName', device.id)))

    def addAllLGSOrganizers(self, device_specs):
        location = device_specs.get('setLocation')
        if location:
            self.addLGSOrganizer('Locations', (location,) )

        systems = device_specs.get('setSystems')
        if systems:
            if not isinstance(systems, list) and not isinstance(systems, tuple):
                systems = (systems,)
            self.addLGSOrganizer('Systems', systems)

        groups = device_specs.get('setGroups')
        if groups:
            if not isinstance(groups, list) and not isinstance(groups, tuple):
                groups = (groups,)
            self.addLGSOrganizer('Groups', groups)

    def addLGSOrganizer(self, lgsType, paths=[]):
        """
        Add any new locations, groups or organizers
        """
        prefix = '/zport/dmd/' + lgsType
        base = getattr(self.dmd, lgsType)
        if hasattr(base, 'sync'):
            base.sync()
        existing = [x.getPrimaryUrlPath().replace(prefix, '') \
                                      for x in base.getSubOrganizers()]
        for path in paths:
            if path in existing:
                continue
            base.manage_addOrganizer(path)

    def addOrganizer(self, device_specs):
        """
        Add any organizers as required, and apply zproperties to them.
        """
        path = device_specs.get('devicePath')
        baseOrg = path.split('/', 2)[1]
        base = getattr(self.dmd, baseOrg, None)
        if base is None:
            self.log.error("The base of path %s (%s) does not exist -- skipping",
                           baseOrg, path)
            return

        try:
            org = base.getDmdObj(path)
        except KeyError:
            self.log.info("Creating organizer %s", path)
            @transact
            def inner():
                base.manage_addOrganizer(path)
            inner()
            org = base.getDmdObj(path)
        self.applyZProps(org, device_specs)
        self.applyOtherProps(org, device_specs)

    def applyOtherProps(self, device, device_specs):
        """
        Apply non-zProperty settings (if any) to the device.

        @parameter device: device to modify
        @type device: DMD device object
        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        """
        self.log.debug( "Applying other properties..." )
        internalVars = [
           'deviceName', 'devicePath', 'comments',
        ]
        @transact
        def setDescription(org, description):
            setattr(org, 'description', description)

        for functor, value in device_specs.items():
            if iszprop(functor) or functor in internalVars:
               continue

            # Special case for organizers which can take a description
            if functor == 'description':
                if hasattr(device, functor):
                    setDescription(device, value)
                continue

            try:
                self.log.debug("For %s, calling device.%s(%s)",
                              device.id, functor, value)
                func = getattr(device, functor, None)
                if func is None:
                    self.log.warn("The function '%s' for device %s is not found.",
                                  functor, device.id)
                elif isinstance(value, type([])) or isinstance(value, type(())):
                    # The function either expects a list or arguments
                    try: # arguments
                        func(*value)
                    except TypeError: # Try as a list
                        func(value)
                else:
                    func(value)
            except ConflictError:
                raise
            except Exception:
                self.log.exception("Device %s device.%s(%s) failed" % (
                                   device.id, functor, value))

    def runLoader(self, loader, device_specs):
        """
        It's up to the loader now to figure out what's going on.

        @parameter loader: device loader
        @type loader: callable
        @parameter device_specs: device entries
        @type device_specs: dictionary
        """
        argKeys = device_specs.get('loader_arg_keys', [])
        loader_args = {}
        for key in argKeys:
            if key in device_specs:
                loader_args[key] = device_specs[key]

        result = loader().load_device(self.dmd, **loader_args)

        # If the loader returns back a device object, carry
        # on processing
        if isinstance(result, Device):
            return result
        return None

    def processDevices(self, device_list):
        """
        Read the input and process the devices
          * create the device entry
          * set zproperties
          * model the device

        @parameter device_list: list of device entries
        @type device_list: list of dictionaries
        """

        def transactional(f):
            return f if self.options.nocommit else transact(f)

        processed = {'total':0}

        @transactional
        def _process(device_specs):
            # Get the latest bits
            self.dmd.zport._p_jar.sync()

            loaderName = device_specs.get('loader')
            if loaderName is not None:
                try:
                    orgName = device_specs['devicePath']
                    organizer = self.dmd.getObjByPath('dmd' + orgName)
                    deviceLoader = getUtility(IDeviceLoader, loaderName, organizer)
                    devobj = self.runLoader(deviceLoader, device_specs)
                except ConflictError:
                    raise
                except Exception:
                    self.log.exception("Ignoring device loader issue for %s",
                                       device_specs)
                    return
            else:
                devobj = self.getDevice(device_specs)

            if devobj is None:
                if deviceLoader is not None:
                    processed['total'] += 1
            else:
                self.addAllLGSOrganizers(device_specs)
                self.applyZProps(devobj, device_specs)
                self.applyOtherProps(devobj, device_specs)

            return devobj

        @transactional
        def _snmp_community(device_specs, devobj):
            # Discover the SNMP community if it isn't explicitly set.
            if 'zSnmpCommunity' not in device_specs:
                self.log.debug('Discovering SNMP version and community')
                devobj.manage_snmpCommunity()

        @transactional
        def _model(devobj):
            try:
                devobj.collectDevice(setlog=self.options.showModelOutput)
            except ConflictError:
                raise
            except Exception:
                self.log.exception("Modeling error for %s", devobj.id)
            processed['total'] += 1

        for device_specs in device_list:
            devobj = _process(device_specs)

            # We need to commit in order to model, so don't bother
            # trying to model unless we can do both
            if devobj and not self.options.nocommit and not self.options.nomodel:
                _snmp_community(device_specs, devobj)
                _model(devobj)

        self.log.info("Processed %d of %d devices",
                      processed['total'], len(device_list))

    def getDevice(self, device_specs):
        """
        Find or create the specified device

        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        @return: device or None
        @rtype: DMD device object
        """
        if 'deviceName' not in device_specs:
            return None
        name = device_specs['deviceName']
        devobj  = self.dmd.Devices.findDevice(name)
        if devobj is not None:
            self.log.info("Found existing device %s" % name)
            return devobj

        specs = {}
        for key in self.loader_args:
            if key in device_specs:
                specs[key] = device_specs[key]

        try:
            self.log.info("Creating device %s" % name)

            # Do NOT model at this time
            specs['discoverProto'] = 'none'

            self.loader(**specs)
            devobj  = self.dmd.Devices.findDevice(name)
            if devobj is None:
                self.log.error("Unable to find newly created device %s -- skipping" \
                              % name)
        except Exception, ex:
            self.log.exception("Unable to load %s -- skipping" % name )

        return devobj

    def buildOptions(self):
        """
        Add our command-line options to the basics
        """
        ZCmdBase.buildOptions(self)

        self.parser.add_option('--show_options',
            dest="show_options", default=False,
            action="store_true",
            help="Show the various options understood by the loader")

        self.parser.add_option('--sample_configs',
            dest="sample_configs", default=False,
            action="store_true",
            help="Show an example configuration file.")

        self.parser.add_option('--showModelOutput',
            dest="showModelOutput", default=True,
            action="store_false",
            help="Show modelling activity")

        self.parser.add_option('--nocommit',
            dest="nocommit", default=False,
            action="store_true",
            help="Don't commit changes to the ZODB. Use for verifying config file.")

        self.parser.add_option('--nomodel',
            dest="nomodel", default=False,
            action="store_true",
            help="Don't model the remote devices. Must be able to commit changes.")

    def parseDevices(self, data):
        """
        From the list of strings in rawDevices, construct a list
        of device dictionaries, ready to load into Zenoss.

        @parameter data: list of strings representing device entries
        @type data: list of strings
        @return: list of parsed device entries
        @rtype: list of dictionaries
        """
        if not data:
            return []

        comment = re.compile(r'^\s*#.*')

        defaults = {'devicePath':"/Discovered" }
        finalList = []
        i = 0
        while i < len(data):
            line = data[i]
            line = re.sub(comment, '', line).strip()
            if line == '':
                i += 1
                continue

            # Check for line continuation character '\'
            while line[-1] == '\\' and i < len(data):
                i += 1
                line = line[:-1] + data[i]
                line = re.sub(comment, '', line).strip()

            if line[0] == '/' or line[1] == '/': # Found an organizer
                defaults = self.parseDeviceEntry(line, {})
                if defaults is None:
                    defaults = {'devicePath':"/Discovered" }
                else:
                    defaults['devicePath'] = defaults['deviceName']
                    del defaults['deviceName']
                self.addOrganizer(defaults)

            else:
                configs = self.parseDeviceEntry(line, defaults)
                if configs:
                    finalList.append(configs)
            i += 1

        return finalList

    def parseDeviceEntry(self, line, defaults):
        """
        Build a dictionary of properties from one line's input

        @parameter line: string containing one device's info
        @type line: string
        @parameter defaults: dictionary of default settings
        @type defaults: dictionary
        @return: parsed device entry
        @rtype: dictionary
        """
        options = []
        # Note: organizers and device names can have spaces in them
        if line[0] in ["'", '"']:
            delim = line[0]
            eom = line.find(delim, 1)
            if eom == -1:
                self.log.error("While reading name, unable to parse" \
                               " the entry for %s -- skipping", name )
                self.log.error( "Raw string: %s" % options )
                return None
            name = line[1:eom]
            options = line[eom+1:]

        else:
            options = line.split(None, 1)
            name = options.pop(0)
            if options:
                options = options.pop(0)

        configs = defaults.copy()
        configs['deviceName'] = name

        if options:
            try:
                # Add a newline to allow for trailing comments
                evalString = 'dict(' + options + '\n)'
                configs.update(eval(evalString))
            except:
                self.log.error( "Unable to parse the entry for %s -- skipping" % name )
                self.log.error( "Raw string: %s" % options )
                return None

        return configs


if __name__=='__main__':
    batchLoader = BatchDeviceLoader()

    if batchLoader.options.show_options:
        print "Options = %s" % sorted( batchLoader.loader_args.keys() )
        help(batchLoader.loader)
        sys.exit(0)

    if batchLoader.options.sample_configs:
        print batchLoader.sample_configs
        sys.exit(0)

    device_list = batchLoader.loadDeviceList()
    batchLoader.processDevices(device_list)

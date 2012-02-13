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

__doc__ = """RRDUtil

Wrapper routines around the rrdtool library.
"""

import logging
log = logging.getLogger("zen.RRDUtil")

import os
import re

from Products.ZenUtils.Utils import zenPath, rrd_daemon_running


EMPTY_RRD = zenPath('perf', 'empty.rrd')


def _checkUndefined(x):
    """
    Sanity check on the min, max values

    @param x: RRD min or max value
    @type x: number
    @return: Either the number or 'U' (for undefined)
    @rtype: number or string
    """
    if x is None or x == '' or x == -1 or x == '-1':
        return 'U'
    return x


def convertToRRDTime(val):
    """
    Convert any value that is passed in to a string that is acceptable to use
    for RRDtool's start and end parameters. Raises ValueError if this is not
    possible.

    See the AT-STYLE TIME SPECIFICATION and TIME REFERENCE SPECIFICATION
    sections of the following document.

        http://oss.oetiker.ch/rrdtool/doc/rrdfetch.en.html

    Note: Currently this method is only fixing floats by turning them into
          strings with no decimal places.
    """
    # Integers are ok. This will also strip decimal precision.
    try:
        result = int(val)
        return str(result)
    except ValueError:
        pass

    return str(val)


def fixMissingRRDs(gopts):
    """
    Parses a list of RRDtool gopts for DEFs. Runs all of the filenames
    referenced by those DEFs through the fixRRDFilename method to make sure
    that they will exist and not cause the rendering to fail.
    """
    fixed_gopts = []

    def_match = re.compile(r'^DEF:([^=]+)=([^:]+)').match
    for gopt in gopts:
        match = def_match(gopt)
        if not match:
            fixed_gopts.append(gopt)
            continue

        rrd_filename = match.group(2)
        fixed_gopts.append(gopt.replace(
            rrd_filename, fixRRDFilename(rrd_filename)))

    return fixed_gopts


def fixRRDFilename(filename):
    """
    Attempting to render a graph containing a DEF referencing a non-existent
    filename will cause the entire graph to fail to render. This method is a
    helper to verify existence of an RRD file. If the file doesn't exist, a
    placeholder RRD filename with no values in it will be returned instead.
    """
    if os.path.isfile(filename):
        return filename

    if not os.path.isfile(EMPTY_RRD):
        import rrdtool
        rrdtool.create(EMPTY_RRD, "--step", '300', 'DS:ds0:GAUGE:900:U:U',
            'RRA:AVERAGE:0.5:1:1', 'RRA:MAX:0.5:1:1', 'RRA:LAST:0.5:1:1')

    return EMPTY_RRD

def read(path, consolidationFunction, start, end):
    import rrdtool
    try:
        return rrdtool.fetch(path, consolidationFunction, start, end)
    except rrdtool.error, err:
        import sys
        err_str = '%s: %s' % (err.__class__.__name__, err)
        msg = 'Failed to read RRD file %s. %s' % (path, err_str)
        raise StandardError(msg), None, sys.exc_info()[2]

class RRDUtil:
    """
    Wrapper class around rrdtool
    """

    def __init__(self, defaultRrdCreateCommand, defaultCycleTime):
        """
        Initializer

        The RRD creation command is only used if the RRD file doesn't
        exist and no rrdCommand was specified with the save() method.

        @param defaultRrdCreateCommand: RRD creation command
        @type defaultRrdCreateCommand: string
        @param defaultCycleTime: expected time to periodically collect data
        @type defaultCycleTime: integer
        """
        self.defaultRrdCreateCommand = defaultRrdCreateCommand
        self.defaultCycleTime = defaultCycleTime
        self.dataPoints = 0
        self.cycleDataPoints = 0


    def endCycle(self):
        """
        Report on the number of data points collected in a cycle,
        and reset the counter for a new cycle.

        @return: number of data points collected during the cycle
        @rtype: number
        """
        result = self.cycleDataPoints
        self.cycleDataPoints = 0
        return result


    def performancePath(self, path):
        """
        Given a path, return its location from $ZENHOME and the
        perf/ directories.

        @param path: name for a datapoint in a path (eg device/component/datasource_datapoint)
        @type path: string
        @return: absolute path
        @rtype: string
        """
        from Products.ZenModel.PerformanceConf import performancePath
        return performancePath(path)


    def getStep(self, cycleTime):
        """
        Return the step value for the provided cycleTime. This is a hook for
        altering the default step calculation.
        """
        return int(cycleTime)


    def getHeartbeat(self, cycleTime):
        """
        Return the heartbeat value for the provided cycleTime. This is a hook
        for altering the default heartbeat calculation.
        """
        return int(cycleTime) * 3


    def save(self, path, value, rrdType, rrdCommand=None, cycleTime=None,
             min='U', max='U', useRRDDaemon=True, timestamp='N', start=None):
        """
        Save the value provided in the command to the RRD file specified in path.

        If the RRD file does not exist, use the rrdType, rrdCommand, min and
        max parameters to create the file.

        @param path: name for a datapoint in a path (eg device/component/datasource_datapoint)
        @type path: string
        @param value: value to store into the RRD file
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        @param rrdCommand: RRD file creation command
        @type rrdCommand: string
        @param cycleTime: length of a cycle
        @type cycleTime: number
        @param min: minimum value acceptable for this metric
        @type min: number
        @param max: maximum value acceptable for this metric
        @type max: number
        @return: the parameter value converted to a number
        @rtype: number or None
        """
        import rrdtool, os

        daemon_args = ()
        if useRRDDaemon:
            daemon = rrd_daemon_running()
            if daemon:
                daemon_args = ('--daemon', daemon)

        if value is None: return None

        self.dataPoints += 1
        self.cycleDataPoints += 1

        if cycleTime is None:
            cycleTime = self.defaultCycleTime

        filename = self.performancePath(path) + '.rrd'
        if not rrdCommand:
            rrdCommand = self.defaultRrdCreateCommand
        if not os.path.exists(filename):
            log.debug("Creating new RRD file %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname, 0750)

            min, max = map(_checkUndefined, (min, max))
            dataSource = 'DS:%s:%s:%d:%s:%s' % (
                'ds0', rrdType, self.getHeartbeat(cycleTime), min, max)
            args = [str(filename), "--step",
                str(self.getStep(cycleTime)),]
            if start is not None:
                args.extend(["--start", "%d" % start])
            args.append(str(dataSource))
            args.extend(rrdCommand.split())
            rrdtool.create(*args),
      

        if rrdType in ('COUNTER', 'DERIVE'):
            try:
                value = long(value)
            except (TypeError, ValueError):
                return None
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
        try:
            rrdtool.update(str(filename), *(daemon_args + ('%s:%s' % (timestamp, value),)))
            log.debug('%s: %r', str(filename), value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            log.error('rrdtool reported error %s %s', err, path)

        if rrdType in ('COUNTER', 'DERIVE'):
            startStop, names, values = \
                rrdtool.fetch(filename, 'AVERAGE',
                    '-s', 'now-%d' % (cycleTime*2),
                    '-e', 'now', *daemon_args)
            values = [ v[0] for v in values if v[0] is not None ]
            if values: value = values[-1]
            else: value = None
        return value

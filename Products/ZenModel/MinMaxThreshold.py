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
from Products.ZenModel.ThresholdInstance import RRDThresholdInstance

__doc__= """MinMaxThreshold
Make threshold comparisons dynamic by using TALES expresssions,
rather than just number bounds checking.
"""

from AccessControl import Permissions

from Globals import InitializeClass
from ThresholdClass import ThresholdClass
from ThresholdInstance import ThresholdContext
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp
from Products.ZenUtils.ZenTales import talesEval, talesEvalStr
from Products.ZenEvents.Exceptions import pythonThresholdException, \
        rpnThresholdException

import logging
log = logging.getLogger('zen.MinMaxCheck')

from Products.ZenUtils.Utils import unused, nanToNone

# Note:  this import is for backwards compatibility.
# Import Products.ZenRRD.utils.rpneval directy.
from Products.ZenRRD.utils import rpneval

NaN = float('nan')

class MinMaxThreshold(ThresholdClass):
    """
    Threshold class that can evaluate RPNs and Python expressions
    """
    
    minval = ""
    maxval = ""
    eventClass = Perf_Snmp
    severity = 3
    escalateCount = 0
    
    _properties = ThresholdClass._properties + (
        {'id':'minval',        'type':'string',  'mode':'w'},
        {'id':'maxval',        'type':'string',  'mode':'w'},
        {'id':'escalateCount', 'type':'int',     'mode':'w'}
        )

    factory_type_information = (
        { 
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        ( 
        { 'id'            : 'edit'
          , 'name'          : 'Min/Max Threshold'
          , 'action'        : 'editRRDThreshold'
          , 'permissions'   : ( Permissions.view, )
          },
        )
        },
        )

    def createThresholdInstance(self, context):
        """Return the config used by the collector to process min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        mmt = MinMaxThresholdInstance(self.id,
                                      ThresholdContext(context),
                                      self.dsnames,
                                      minval=self.getMinval(context),
                                      maxval=self.getMaxval(context),
                                      eventClass=self.eventClass,
                                      severity=self.severity,
                                      escalateCount=self.escalateCount)
        return mmt

    def getMinval(self, context):
        """Build the min value for this threshold.
        """
        minval = None
        if self.minval:
            try:
                express = "python:%s" % self.minval
                minval = talesEval(express, context)
            except:
                msg= "User-supplied Python expression (%s) for minimum value caused error: %s" % \
                           ( self.minval,  self.dsnames )
                log.error( msg )
                raise pythonThresholdException(msg)
                minval = None
        return nanToNone(minval)


    def getMaxval(self, context):
        """Build the max value for this threshold.
        """
        maxval = None
        if self.maxval:
            try:
                express = "python:%s" % self.maxval
                maxval = talesEval(express, context)
            except:
                msg= "User-supplied Python expression (%s) for maximum value caused error: %s" % \
                           ( self.maxval,  self.dsnames )
                log.error( msg )
                raise pythonThresholdException(msg)
                maxval = None
        return nanToNone(maxval)

InitializeClass(MinMaxThreshold)
MinMaxThresholdClass = MinMaxThreshold



class MinMaxThresholdInstance(RRDThresholdInstance):
    # Not strictly necessary, but helps when restoring instances from
    # pickle files that were not constructed with a count member.
    count = {}
    
    def __init__(self, id, context, dpNames,
                 minval, maxval, eventClass, severity, escalateCount):
        RRDThresholdInstance.__init__(self, id, context, dpNames, eventClass, severity)
        self.count = {}
        self.minimum = minval
        self.maximum = maxval
        self.escalateCount = escalateCount

    def countKey(self, dp):
        return ':'.join(self.context().key()) + ':' + dp
        
    def getCount(self, dp):
        countKey = self.countKey(dp)
        if not countKey in self.count:
            return None
        return self.count[countKey]

    def incrementCount(self, dp):
        countKey = self.countKey(dp)
        if not countKey in self.count:
            self.resetCount(dp)
        self.count[countKey] += 1
        return self.count[countKey]

    def resetCount(self, dp):
        self.count[self.countKey(dp)] = 0
    
    def checkRange(self, dp, value):
        'Check the value for min/max thresholds'
        log.debug("Checking %s %s against min %s and max %s",
                  dp, value, self.minimum, self.maximum)
        if value is None:
            return []
        if isinstance(value, basestring):
            value = float(value)
        thresh = None

        # Handle all cases where both minimum and maximum are set.
        if self.maximum is not None and self.minimum is not None:
            if self.maximum >= self.minimum:
                if value > self.maximum:
                    thresh = self.maximum
                    how = 'exceeded'
                elif value < self.minimum:
                    thresh = self.minimum
                    how = 'not met'
            elif self.maximum < value < self.minimum:
                thresh = self.maximum
                how = 'violated'

        # Handle simple cases where only minimum or maximum is set.
        elif self.maximum is not None and value > self.maximum:
            thresh = self.maximum
            how = 'exceeded'
        elif self.minimum is not None and value < self.minimum:
            thresh = self.minimum
            how = 'not met'

        if thresh is not None:
            severity = self.severity
            count = self.incrementCount(dp)
            if self.escalateCount and count >= self.escalateCount:
                severity = min(severity + 1, 5)
            summary = 'threshold of %s %s: current value %f' % (
                self.name(), how, float(value))
            evtdict = self._create_event_dict(value, summary, severity, how)
            if self.escalateCount:
                evtdict['escalation_count'] = count
            return self.processEvent(evtdict)
        else:
            count = self.getCount(dp)
            if count is None or count > 0:
                summary = 'threshold of %s restored: current value %f' % (
                    self.name(), value)
                self.resetCount(dp)
                return self.processClearEvent(self._create_event_dict(value, summary, Event.Clear))
        return []

    def _create_event_dict(self, current, summary, severity, how=None):
        event_dict = dict(device=self.context().deviceName,
                          summary=summary,
                          eventKey=self.id,
                          eventClass=self.eventClass,
                          component=self.context().componentName,
                          min=self.minimum,
                          max=self.maximum,
                          current=current,
                          severity=severity)
        deviceUrl = getattr(self.context(), "deviceUrl", None)
        if deviceUrl is not None:
            event_dict["zenoss.device.url"] = deviceUrl
        devicePath = getattr(self.context(), "devicePath", None)
        if devicePath is not None:
            event_dict["zenoss.device.path"] = devicePath
        if how is not None:
            event_dict['how'] = how
        return event_dict
    

    def processEvent(self, evt):
        """
        When a threshold condition is violated, pre-process it for (possibly) nicer
        formatting or more complicated logic.

        @paramater evt: event
        @type evt: dictionary
        @rtype: list of dictionaries
        """
        return [evt]

    def processClearEvent(self, evt):
        """
        When a threshold condition is restored, pre-process it for (possibly) nicer
        formatting or more complicated logic.

        @paramater evt: event
        @type evt: dictionary
        @rtype: list of dictionaries
        """
        return [evt]

    def raiseRPNExc( self ):
        """
        Raise an RPN exception, taking care to log all details.
        """
        msg= "The following RPN exception is from user-supplied code."
        log.exception( msg )
        raise rpnThresholdException(msg)


    def getGraphElements(self, template, context, gopts, namespace, color, 
                         legend, relatedGps):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        unused(template, namespace)
        if not color.startswith('#'):
            color = '#%s' % color
        minval = self.minimum
        if minval is None:
            minval = NaN
        maxval = self.maximum
        if maxval is None:
            maxval = NaN
        if not self.dataPointNames:
            return gopts
        gp = relatedGps[self.dataPointNames[0]]

        # Attempt any RPN expressions
        rpn = getattr(gp, 'rpn', None)
        if rpn:
            try:
                rpn = talesEvalStr(rpn, context)
            except:
                self.raiseRPNExc()
                return gopts

            try:
                minval = rpneval(minval, rpn)
            except:
                minval= 0
                self.raiseRPNExc()

            try:
                maxval = rpneval(maxval, rpn)
            except:
                maxval= 0
                self.raiseRPNExc()

        minstr = self.setPower(minval)
        maxstr = self.setPower(maxval)

        minval = nanToNone(minval)
        maxval = nanToNone(maxval)
        if legend:
            gopts.append(
                "HRULE:%s%s:%s\\j" % (minval or maxval, color, legend))
        elif minval is not None and maxval is not None:
            if minval == maxval:
                gopts.append(
                    "HRULE:%s%s:%s not equal to %s\\j" % (minval, color,
                        self.getNames(relatedGps), minstr))
            elif minval < maxval:
                gopts.append(
                    "HRULE:%s%s:%s not within %s and %s\\j" % (minval, color,
                        self.getNames(relatedGps), minstr, maxstr))
                gopts.append("HRULE:%s%s" % (maxval, color))
            elif minval > maxval:
                gopts.append(
                    "HRULE:%s%s:%s between %s and %s\\j" % (minval, color,
                        self.getNames(relatedGps), maxstr, minstr))
                gopts.append("HRULE:%s%s" % (maxval, color))
        elif minval is not None :
            gopts.append(
                "HRULE:%s%s:%s less than %s\\j" % (minval, color,
                    self.getNames(relatedGps), minstr))
        elif maxval is not None:
            gopts.append(
                "HRULE:%s%s:%s greater than %s\\j" % (maxval, color,
                    self.getNames(relatedGps), maxstr))

        return gopts


    def getNames(self, relatedGps):
        names = sorted(set(x.split('_', 1)[1] for x in self.dataPointNames))
        return ', '.join(names)

    def setPower(self, number):
        powers = ("k", "M", "G")
        if number < 1000: return number
        for power in powers:
            number = number / 1000.0
            if number < 1000:  
                return "%0.2f%s" % (number, power)
        return "%.2f%s" % (number, powers[-1])

    def _checkImpl(self, dataPoint, value):
        return self.checkRange(dataPoint, value)

from twisted.spread import pb
pb.setUnjellyableForClass(MinMaxThresholdInstance, MinMaxThresholdInstance)

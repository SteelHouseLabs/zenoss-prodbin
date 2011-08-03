###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re
# how to parse each value from a nagios command
NagParser = re.compile(r"""([^ =']+|'(.*)'+)=([-0-9.eE]+)([^;]*;?){0,5}""")
# how to parse each value from a cacti command
from Cacti import CacParser

from Products.ZenUtils.Utils import getExitMessage
from Products.ZenRRD.CommandParser import CommandParser

class Auto(CommandParser):

    def processResults(self, cmd, result):
        output = cmd.result.output
        output = output.split('\n')[0].strip()
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        if output.find('|') >= 0:
            msg, values = output.split('|', 1)
        elif CacParser.search(output):
            msg, values = '', output
        else:
            msg, values = output, ''
        msg = msg.strip() or 'Datasource: %s - Code: %s - Msg: %s' % (
            cmd.name, exitCode, getExitMessage(exitCode))
        if exitCode != 0:
            if exitCode == 2:
                severity = min(severity + 1, 5)
            result.events.append(dict(device=cmd.deviceConfig.device,
                                      summary=msg,
                                      severity=severity,
                                      message=msg,
                                      performanceData=values,
                                      eventKey=cmd.eventKey,
                                      eventClass=cmd.eventClass,
                                      component=cmd.component))

        for parts in NagParser.findall(values) or CacParser.findall(values):
            label = parts[0].replace("''", "'")
            try:
                value = float(parts[2])
            except Exception:
                value = 'U'
            for dp in cmd.points:
                if dp.id == label:
                    result.values.append( (dp, value) )
                    break


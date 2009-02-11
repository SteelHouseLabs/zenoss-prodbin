###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.DataCollector.ProcessCommandPlugin import ProcessCommandPlugin

class process(ProcessCommandPlugin):
    """
    Linux command plugin for parsing ps command output and modeling processes.
    """
    
    command = 'ps axho args'
    
    def condition(self, device, log):
        return device.os.uname == 'Linux'

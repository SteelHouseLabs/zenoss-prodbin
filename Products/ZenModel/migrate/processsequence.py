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

__doc__='''ProcessSequence

Make sure OSProcesses are sequenced

'''
import Migrate

class ProcessSequence(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        dmd.Processes.getSubOSProcessClassesSorted()

ProcessSequence()


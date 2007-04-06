#################################################################
#
#   Copyright (c) 2007 Zenoss Corporation. All rights reserved.
#
#################################################################

import string

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap
from sets import Set
import md5


class process(CommandPlugin):
    """
    maps ps output to process
    """
    maptype = "OSProcessMap" 
    command = '/bin/ps axho command'
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting process information for device %s' % device.id)

        rm = self.relMap()

        procs = Set()

        for line in results.split("\n"):
            if line.strip() in ['', 'COMMAND']:
                continue

            vals = line.split()

            if len(vals) == 0:
                continue

            procName = vals[0]
            parameters = string.join(vals[1:], ' ')

            proc = {
                'procName' : procName,
                'parameters' : parameters
                }

            om = self.objectMap(proc)
            fullname = (om.procName + " " + om.parameters).rstrip()

            processes = device.getDmdRoot("Processes")
            for pc in processes.getSubOSProcessClassesGen():
                if pc.match(fullname):
                    om.setOSProcessClass = pc.getPrimaryDmdId()
                    id = om.procName
                    parameters = om.parameters.strip()
                    if parameters and not pc.ignoreParameters:
                        parameters = md5.md5(parameters).hexdigest()
                        id += ' ' + parameters
                    om.id = self.prepId(id)
                    if id not in procs:
                        procs.add(id)
                        rm.append(om)
                    break

        return rm

#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''UpdateCheck

'''

import Globals
import transaction
import Products.ZenUtils.Version
from Products.ZenUtils.Version import Version
from Products.ZenEvents import Event
import urllib
import string
import time

URL = 'http://update.zenoss.org/cgi-bin/version'

DAY_SECONDS = 60*60*24

def parseVersion(s):
    if s is None: return s
    v = Version.parse('Zenoss ' + s)
    v.revision = None
    return v

class UpdateCheck:

    def getUpdate(self, dmd, manual):
        available = None
        args = {}
        if dmd.uuid is None:
            import commands
            dmd.uuid = commands.getoutput('uuidgen')
        args['sk'] = dmd.uuid
        args['ac'] = (manual and '0') or '1'
        args['zv'] = dmd.About.getZenossVersion().long()
        args['pv'] = dmd.About.getPythonVersion().long()
        args['mv'] = dmd.About.getMySQLVersion().long()
        args['os'] = dmd.About.getOSVersion().long()
        #args['rv'] = Products.ZenUtils.Version.getZenossRevision()
        args['rv'] = 'bad bad bad' 
        args['up'] = time.time() - dmd.getPhysicalRoot().Control_Panel.process_start

        # If they have not opted-out and this is not a manual check then
        # gather usage numbers and include in request
        if not manual and dmd.reportMetricsOptIn:
            args['nd'] = dmd.Devices.countDevices()
            args['nu'] = len(dmd.ZenUsers.objectIds())
            args['nm'] = dmd.Events.countInstances()
            args['ne'] = dmd.ZenEventManager.countEventsSince(
                                            time.time() - 24 * 60 * 60)
            numProducts = 0
            manufacturers = dmd.Manufacturers.objectValues(spec='Manufacturer')
            for m in manufacturers:
                numProducts += m.products.countObjects()
            args['np'] = numProducts
            args['nr'] = dmd.Reports.countReports()
            args['nt'] = dmd.Devices.rrdTemplates.countObjects()
            args['ns'] = dmd.Systems.countChildren()
            args['ng'] = dmd.Groups.countChildren()
            args['nl'] = dmd.Locations.countChildren()
            
        query = urllib.urlencode(args.items())
        for line in urllib.urlopen(URL + '?' + query):
            # skip blank lines and http gunk
            if line.strip() and line[0] not in '<' + string.whitespace:
                try:
                    available = parseVersion(line.strip())
                    break
                except ValueError:
                    pass
        return available

    def check(self, dmd, zem, manual=False):
        "call home with version information"
        if not manual:
            if time.time() - dmd.lastVersionCheck < DAY_SECONDS:
                return
            if not dmd.versionCheckOptIn:
                return
        try:
            available = self.getUpdate(dmd, manual)
        except Exception, ex:
            raise
            log.debug("Cannot fetch version information", ex)
            return
        availableVersion = parseVersion(dmd.availableVersion)
        if (availableVersion is None 
            or dmd.About.getZenossVersion() < availableVersion):
            if availableVersion != available:
                import socket
                summary = ('A new version of Zenoss (%s) has been released' % 
                           available.short())
                zem.sendEvent(Event.Event(device=socket.getfqdn(),
                                          eventClass='/Status/Update',
                                          severity=Event.Info,
                                          summary=summary))
        dmd.availableVersion = available.short()
        dmd.lastVersionCheck = long(time.time())
        return True

if __name__ == "__main__":
    from Products.ZenUtils import ZCmdBase
    class zendmd(ZCmdBase.ZCmdBase):
        pass
    zendmd = zendmd()
    uc = UpdateCheck()
    uc.getUpdate = lambda *args: parseVersion('0.24.0')
    uc.check(zendmd.dmd, zendmd.dmd.ZenEventManager, manual=True)
    transaction.commit()

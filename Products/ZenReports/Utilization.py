##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils import Time

def getSummaryArgs(dmd, args):
    zem = dmd.ZenEventManager
    startDate = args.get('startDate', zem.defaultAvailabilityStart())
    endDate = args.get('endDate', zem.defaultAvailabilityEnd())
    startDate, endDate = map(Time.ParseUSDate, (startDate, endDate))
    endDate = Time.getEndOfDay(endDate)
    startDate = min(startDate, endDate - 24 * 60 * 60 + 1) # endDate - 23:59:59
    how = args.get('how', 'AVERAGE')
    return dict(start=startDate, end=endDate, function=how)

def reversedSummary(summary):
    swapper = { 'MAXIMUM':'MINIMUM', 'MINIMUM':'MAXIMUM'}
    summary = summary.copy()
    current = summary['function']
    summary['function'] = swapper.get(current, current)
    return summary


def filteredDevices(dmd, args):
    import re

    deviceFilter = args.get('deviceFilter', '') or ''
    deviceMatch = re.compile('.*%s.*' % deviceFilter)

    # Fall back for backwards compatibility
    if 'deviceClass' in args:
        # deviceClass should always start with a '/'
        args['organizer'] = '/Devices' + args['deviceClass']

    # Get organizer
    organizer = args.get('organizer', '/Devices') or '/Devices'

    # Determine the root organizer
    try:
        root = dmd.getObjByPath(organizer.lstrip('/'))
    except KeyError:
        root = dmd.Devices # Show all if org not found

    # Iterate all sub-organizers and devices
    for d in root.getSubDevices():
        if not d.monitorDevice(): continue
        if not deviceMatch.match(d.id): continue
        yield d

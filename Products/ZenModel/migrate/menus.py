#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add menu relations to all device organizers, OsProcesses, Services, etc
Add default menus to dmd and device organizers

$Id:$
'''
import Migrate
import os
from Products.ZenRelations.ImportRM import ImportRM
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device

zenhome = os.environ['ZENHOME']
menuxml = os.path.join(zenhome, "Products/ZenModel/data/menus.xml")

ZenPackItems = dict(
    id=         'addToZenPack',
    description='Add to ZenPack...',
    action=     'dialog_addToZenPack',
    permissions=('View',),
    isdialog=True,
    )

class MenuRelations(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        dmd.buildRelations()
#        for dev in dmd.Devices.getSubDevices():
#            dev.buildRelations()
#        for name in ['Devices', 'Systems', 'Groups', 'Locations',
#                        'Services', 'Processes']:
#            top = getattr(dmd, name)
#            orgs = top.getSubOrganizers()
#            orgs.insert(0, top)
#            for o in orgs:
#                o.buildRelations()
#                if name == 'Devices':
#                    for d in o.devices():
#                        d.buildRelations()
#                        if getattr(d, 'os', None):
#                            for n in ['ipservices', 'winservices', 'processes']:
#                                for p in getattr(d.os, n)():
#                                    p.buildRelations()
#                if name == 'Services':
#                    for sc in o.serviceclasses():
#                        sc.buildRelations()
#                if name == 'Processes':
#                    for pc in o.osProcessClasses():
#                        pc.buildRelations()

        # Add menus.
        
# Get rid of all menus

        hasmenus = lambda x: hasattr(x, 'zenMenus') 
        if hasmenus(dmd): dmd.zenMenus.removeRelation()
        if hasmenus(dmd.Devices): dmd.Devices.zenMenus.removeRelation()
        if hasmenus(dmd.Networks): dmd.Networks.zenMenus.removeRelation()

        dmd.buildMenus(
            {
            'Edit':[
                dict(action='objRRDTemplate',
                    allowed_classes=['Device',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'OSProcess'],
                    description='PerfConf',
                    id='objRRDTemplate',
                    permissions=('Change Device',)
                    ),
                dict(action='../objRRDTemplate',
                    allowed_classes=['OperatingSystem'],
                    description='PerfConf',
                    id='objRRDTemplate_os',
                    permissions=('Change Device',)
                    ),
                dict(
                    id=         'addToZenPack',
                    description='Add to ZenPack...',
                    action=     'dialog_addToZenPack',
                    permissions=('View',),
                    isdialog=True,
                    allowed_classes = ['ZenPackable'],
                    ),
                dict(action='dialog_lock',
                    allowed_classes=['Device',
                    'OperatingSystem',
                    'WinService',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'IpService',
                    'OSProcess',
                    'IpRouteEntry'],
                    description='Lock',
                    id='lockObject',
                    isdialog=True,
                    permissions=('Change Device',)
                    ),
                dict(action='dialog_deleteComponent',
                    allowed_classes=['WinService',
                    'FileSystem',
                    'HardDisk',
                    'IpInterface',
                    'IpService',
                    'OSProcess',
                    'IpRouteEntry'],
                    description='Delete',
                    id='deleteObject',
                    isdialog=True,
                    permissions=('Change Device',)
                    ),
                dict(action='editStatusMonitorConf',
                    allowed_classes=['StatusMonitorConf'],
                    description='Edit',
                    id='editStatusMonitorConf',
                    permissions=('Manage DMD',)
                    ),
                dict(action='pushConfig',
                    allowed_classes=['DeviceClass', 
                        'Device'],
                    description='Push Changes to Collectors',
                    id='pushConfig',
                    permissions=('Change Device',)
                    ),
                dict(action='../pushConfig',
                    allowed_classes=['OperatingSystem'],
                    description='Push Changes to Collectors',
                    id='pushConfig_os',
                    permissions=('Change Device',)
                    ),
                dict(action='deviceCustomEdit',
                    allowed_classes=['Device'],
                    description='Custom',
                    id='deviceCustomEdit',
                    permissions=('View',)
                    ),
                dict(action='../deviceCustomEdit',
                    allowed_classes=['OperatingSystem'],
                    description='Custom',
                    id='deviceCustomEdit_os',
                    permissions=('View',)
                    ),
                dict(action='eventClassInstEdit',
                    allowed_classes=['EventClassInst'],
                    description='Edit',
                    id='eventClassInstEdit',
                    permissions=('Manage DMD',)
                    ),
                dict(action='ipServiceClassEdit',
                    allowed_classes=['IpServiceClass'],
                    description='Edit',
                    id='ipServiceClassEdit',
                    permissions=('Manage DMD',)
                    ),
                dict(action='deviceManagement',
                    allowed_classes=['Device'],
                    description='Manage',
                    id='deviceManagement',
                    permissions=('Change Device',)
                    ),
                dict(action='../deviceManagement',
                    allowed_classes=['OperatingSystem'],
                    description='Manage',
                    id='deviceManagement_os',
                    permissions=('Change Device',)
                    ),
                dict(action='serviceOrganizerManage',
                    allowed_classes=['ServiceOrganizer'],
                    description='Manage',
                    id='serviceOrganizerManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessOrganizerManage',
                    allowed_classes=['OSProcessOrganizer'],
                    description='Manage',
                    id='osProcessOrganizerManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='ipServiceClassManage',
                    allowed_classes=['IpServiceClass'],
                    description='Manage',
                    id='ipServiceClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editManufacturer',
                    allowed_classes=['Manufacturer'],
                    description='Edit',
                    id='editManufacturer',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessManage',
                    allowed_classes=['OSProcess'],
                    description='Manage',
                    id='osProcessManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='serviceClassManage',
                    allowed_classes=['ServiceClass'],
                    description='Manage',
                    id='serviceClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editPerformanceConf',
                    allowed_classes=['PerformanceConf'],
                    description='Edit',
                    id='editPerformanceConf',
                    permissions=('Manage DMD',)
                    ),
                dict(action='ipServiceManage',
                    allowed_classes=['IpService'],
                    description='Manage',
                    id='ipServiceManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editProductClass',
                    allowed_classes=['ProductClass'],
                    description='Edit',
                    id='editProductClass',
                    permissions=('Manage DMD',)
                    ),
                dict(action='osProcessClassManage',
                    allowed_classes=['OSProcessClass'],
                    description='Manage',
                    id='osProcessClassManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='deviceOrganizerManage',
                    allowed_classes=['DeviceOrganizer',
                    'DeviceGroup',
                    'Location',
                    'DeviceClass', 
                    'System'],
                    description='Manage',
                    id='deviceOrganizerManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='editDevice',
                    allowed_classes=['Device'],
                    description='Edit',
                    id='editDevice',
                    permissions=('Change Device',)
                    ),
                dict(action='../editDevice',
                    allowed_classes=['OperatingSystem'],
                    description='Edit',
                    id='editDevice_os',
                    permissions=('Change Device',)
                    ),
                dict(action='winServiceManage',
                    allowed_classes=['WinService'],
                    description='Manage',
                    id='winServiceManage',
                    permissions=('Manage DMD',)
                    ),
                dict(action='eventClassInstSequence',
                    allowed_classes=['EventClassInst'],
                    description='Sequence',
                    id='eventClassInstSequence',
                    permissions=('View',)
                    ),
                dict(action='osProcessClassEdit',
                    allowed_classes=['OSProcessClass'],
                    description='Edit',
                    id='osProcessClassEdit',
                    permissions=('Manage DMD',)
                    ),
                dict(action='performanceTemplates',
                    allowed_classes=['DeviceClass'],
                    description='All Performance Templates',
                    id='performanceTemplates',
                    permissions=('View Device',)
                    ),
                dict(action='perfConfig',
                    allowed_classes=['DeviceClass'],
                    description='Perf Config',
                    id='perfConfig',
                    permissions=('Change Device',)
                    ),
                dict(action='zPropertyEdit',
                    allowed_classes=['Device',
                    'DeviceClass',
                    'IpNetwork',
                    'IpServiceClass',
                    'Manufacturer',
                    'OSProcessClass',
                    'OSProcessOrganizer',
                    'ProductClass',
                    'ServiceClass',
                    'ServiceOrganizer',
                    'EventClassInst',
                    'EventClass'],
                    description='zProperties',
                    id='zPropertyEdit',
                    permissions=('View',)
                    ),
                dict(action='../zPropertyEdit',
                    allowed_classes=['OperatingSystem'],
                    description='zProperties',
                    id='zPropertyEdit_os',
                    permissions=('View',)
                    ),
                dict(action='serviceClassEdit',
                    allowed_classes=['ServiceClass'],
                    description='Edit',
                    id='serviceClassEdit',
                    permissions=('Manage DMD',)
                    ),
                ],
            'Organizer_list':            [
                ZenPackItems,
                dict(
                    id=         'addOrganizer',
                    description='Add New Organizer...',
                    action=     'dialog_addOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    id=         'moveOrganizer',
                    description='Move Organizers...',
                    action=     'dialog_moveOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=   True,
                    ),
                dict(
                    id=         'removeOrganizers',
                    description='Delete Organizers...',
                    action=     'dialog_removeOrganizer',
                    permissions=('Manage DMD',),
                    isdialog=True
                    ),
            ],
            'Service_list':                    [
                ZenPackItems,
                dict(
                    id=         'addServiceClass',
                    description='Add Service...',
                    action=     'dialog_addServiceClass',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeServiceClasses',
                    description='Delete Services...',
                    action=     'dialog_removeServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveServiceClasses',
                    description='Move Services...',
                    action=     'dialog_moveServiceClasses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'OSProcess_list': [
                ZenPackItems,
                dict(
                    id=         'addOSProcess',
                    description='Add Process...',
                    action=     'dialog_addOSProcess',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeOSProcesses',
                    description='Delete Processes...',
                    action=     'dialog_removeOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveOSProcesses',
                    description='Move Processes...',
                    action=     'dialog_moveOSProcesses',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'Manufacturer_list':               [
                ZenPackItems,
                dict(
                    id=         'addManufacturer',
                    description='Add Manufacturer...',
                    action=     'dialog_addManufacturer',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeManufacturers',
                    description='Delete Manufacturers...',
                    action=     'dialog_removeManufacturers',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'Mib_list':                    [
                ZenPackItems,
                dict(
                    id=         'addMibModule',
                    description='Add Mib...',
                    action=     'dialog_addMibModule',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeMibModules',
                    description='Delete Mibs...',
                    action=     'dialog_removeMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveMibModules',
                    description='Move Mibs...',
                    action=     'dialog_moveMibModules',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'EventMapping_list':               [
                ZenPackItems,
                dict(
                    id=         'addInstance',
                    description='Add Mapping...',
                    action=     'dialog_createInstance',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeInstances',
                    description='Delete Mappings...',
                    action=     'dialog_removeInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'moveInstances',
                    description='Move Mappings...',
                    action=     'dialog_moveInstances',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                    ],
            'PerformanceMonitor_list': [
                dict(
                    id=         'addPMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removePMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            'StatusMonitor_list': [
                dict(
                    id=         'addSMonitor',
                    description='Add Monitor...',
                    action=     'dialog_addMonitor',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                dict(
                    id=         'removeSMonitors',
                    description='Delete Monitors...',
                    action=     'dialog_removeMonitors',
                    permissions=('Manage DMD',),
                    isdialog=   True),
                ],
            # doesn't work:
            # 'ReportClass_list':                [ZenPackItems],
            'ZenPack_list':[
                dict(
                    id=         'addZenPack',
                    description='Create a new ZenPack...',
                    action=     'dialog_addZenPack',
                    permissions=('Manage DMD',),
                    isdialog=True,
                    ),
                dict(
                    id=         'removeZenPack',
                    description='Delete ZenPack',
                    permissions=('Manage DMD',),
                    action=     'dialog_removeZenPacks',
                    isdialog=True,
                    ),
                ],
            'Device_list':[
                dict(
                    id=         'moveclass',
                    description='Move to Class...',
                    action=     'dialog_moveDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    id=         'setGroups',
                    description='Set Groups...',
                    action=     'dialog_setGroups',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    id=         'setSystems',
                    description='Set Systems...',
                    action=     'dialog_setSystems',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    id=         'setLocation',
                    description='Set Location...',
                    action=     'dialog_setLocation',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    id=         'removeDevices',
                    description='Delete devices...',
                    action=     'dialog_removeDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    ),
                dict(
                    id=         'lockDevices',
                    description='Lock devices...',
                    action=     'dialog_lockDevices',
                    permissions=('Change Device',),
                    isdialog=True
                    )
                ],
            'IpInterface':[
                dict(
                    id=         'addIpInterface',
                    description='Add IpInterface...',
                    action=     'dialog_addIpInterface',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteIpInterfaces',
                    description='Delete IpInterfaces...',
                    action=     'dialog_deleteIpInterfaces',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockIpInterfaces',
                    description='Lock IpInterfaces...',
                    action=     'dialog_lockIpInterfaces',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'OSProcess':[
                dict(
                    id=         'addOSProcess',
                    description='Add OSProcess...',
                    action=     'dialog_addOSProcess',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteOSProcesses',
                    description='Delete OSProcesses...',
                    action=     'dialog_deleteOSProcesses',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockOSProcesses',
                    description='Lock OSProcesses...',
                    action=     'dialog_lockOSProcesses',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'FileSystem':[
                dict(
                    id=         'addFileSystem',
                    description='Add File System...',
                    action=     'dialog_addFileSystem',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteFileSystems',
                    description='Delete FileSystems...',
                    action=     'dialog_deleteFileSystems',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockFileSystems',
                    description='Lock FileSystems...',
                    action=     'dialog_lockFileSystems',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'IpRouteEntry':[
                dict(
                    id=         'addIpRouteEntry',
                    description='Add Route...',
                    action=     'dialog_addIpRouteEntry',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteIpRouteEntries',
                    description='Delete IpRouteEntries...',
                    action=     'dialog_deleteIpRouteEntries',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockIpRouteEntries',
                    description='Lock IpRouteEntries...',
                    action=     'dialog_lockIpRouteEntries',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'IpService':[
                dict(
                    id=         'addIpService',
                    description='Add IpService...',
                    action=     'dialog_addIpService',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteIpServices',
                    description='Delete IpServices...',
                    action=     'dialog_deleteIpServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockIpServices',
                    description='Lock IpServices...',
                    action=     'dialog_lockIpServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'WinService':[
                dict(
                    id=         'addWinService',
                    description='Add WinService...',
                    action=     'dialog_addWinService',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'deleteWinServices',
                    description='Delete WinServices...',
                    action=     'dialog_deleteWinServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                dict(
                    id=         'lockWinServices',
                    description='Lock WinServices...',
                    action=     'dialog_lockWinServices',
                    isdialog=True,
                    permissions=('Change Device',),
                    )
                ],
            'Event_list':[
                dict(
                    id=         'acknowledgeEvents',
                    description='Acknowledge Events',
                    action=     ('javascript:submitFormToMethod('
                                 '"control", "manage_ackEvents")'),
                    permissions=('Manage DMD',)
                    ),
                dict(
                    id=         'historifyEvents',
                    description='Move Events to History...',
                    action=     'dialog_moveEventsToHistory',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
                dict(
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
            ],
            'HistoryEvent_list':[
                dict(
                    id=         'createEventMap',
                    description='Map Events to Class...',
                    action=     'dialog_createEventMap',
                    permissions=('Manage DMD',),
                    isdialog=   True
                    ),
                dict(
                    id=         'exportAllEvents',
                    description='Download as CSV',
                    action=     'javascript:goExport()',
                    permissions=('View',)
                    ),
                dict(
                    id=         'undeleteHistoryEvents',
                    description='Undelete Events...',
                    action=     'dialog_undeleteHistoryEvents',
                    permissions=('Manage DMD',),
                    isdialog=True
                    )
                ],
            'DataSource_list':[
                dict(
                    id = 'addDataSource',
                    description = 'Add DataSource...',
                    action = 'dialog_addDataSource',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    id = 'deleteDataSource',
                    description = 'Delete DataSource...',
                    action = 'dialog_deleteDataSource',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'DataPoint_list':[
                dict(
                    id = 'addDataPoint',
                    description = 'Add DataPoint...',
                    action = 'dialog_addDataPoint',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    id = 'deleteDataPoint',
                    description = 'Delete DataPoint...',
                    action = 'dialog_deleteDataPoint',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Threshold_list':[
                dict(
                    id = 'addThreshold',
                    description = 'Add Threshold...',
                    action = 'dialog_addThreshold',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    id = 'deleteThreshold',
                    description = 'Delete Threshold...',
                    action = 'dialog_deleteThreshold',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Graph_list':[
                dict(
                    id = 'addGraph',
                    description = 'Add Graph...',
                    action = 'dialog_addGraph',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    id = 'deleteGraph',
                    description = 'Delete Graph...',
                    action = 'dialog_deleteGraph',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                dict(
                    id = 'resequenceGraphs',
                    description = 'Re-sequence Graphs',
                    action = 'manage_resequenceRRDGraphs',
                    permissions= ('Change Device',),
                    isdialog=True,
                    ),
                ],
            'Subnetworks':[
                dict(
                    id=         'deleteNetwork',
                    description='Delete Networks...',
                    action=     'dialog_deleteNetwork',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                ],
            'IpAddresses':[
                dict(
                    id=         'deleteIpAddress',
                    description='Delete IpAddresses...',
                    action=     'dialog_deleteIpAddress',
                    isdialog=True,
                    permissions=('Change Device',),
                    ),
                ],                    
            'Add': [
                dict(
                    id=         'addIpInterface',
                    description='Add IpInterface...',
                    action=     'dialog_addIpInterface',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    id=         'addOSProcess',
                    description='Add OSProcess...',
                    action=     'dialog_addOSProcess',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    id=         'addFileSystem',
                    description='Add File System...',
                    action=     'dialog_addFileSystem',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    id=         'addIpRouteEntry',
                    description='Add Route...',
                    action=     'dialog_addIpRouteEntry',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    id=         'addIpService',
                    description='Add IpService...',
                    action=     'dialog_addIpService',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                dict(
                    id=         'addWinService',
                    description='Add WinService...',
                    action=     'dialog_addWinService',
                    isdialog=True,
                    permissions=('Change Device',),
                    allowed_classes = ('OperatingSystem',),
                    ),
                ]
            })
        
        dmd.Networks.buildMenus(
            {'Actions':[
                dict(
                    id=             'discover',
                    description=    'Discover Devices', 
                    action=         'discoverDevices', 
                    allowed_classes= ('IpNetwork',)
                    ),
                ]
            })
            
MenuRelations()

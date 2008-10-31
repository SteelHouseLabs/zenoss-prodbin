###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate

class MonitoringMenuItem(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'IpService': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'WinService': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'FileSystem': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'IpInterface': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'OSProcess': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
        })

MonitoringMenuItem()

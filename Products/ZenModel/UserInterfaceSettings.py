###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.utils import ZuulMessageFactory as _t
from copy import deepcopy

class UserInterfaceSettings(ZenModelRM):
    """
    Container for various settings on the User Interface. This is
    serialized and sent down to the server on every page request. Any
    user configurable settings that apply to the user interface should
    be added here
    """

    _relations = ()

    _properties = (
        {'id': 'enableLiveSearch', 'type': 'boolean', 'mode': 'w'},
        {'id': 'incrementalTreeLoad', 'type': 'boolean', 'mode': 'w'},
        {'id': 'enableTreeFilters', 'type': 'boolean', 'mode': 'w'},
        {'id': 'deviceGridBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'componentGridBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'eventConsoleBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'deviceMoveJobThreshold', 'type': 'int', 'mode': 'w'},
        {'id': 'zenjobsRefreshInterval', 'type' : 'int', 'mode':'w'},
        )

    # information about the properties that is used for the UI
    _propertyMetaData = {
        'enableLiveSearch': {'xtype': 'checkbox', 'name': _t('Enable Live Filters'), 'defaultValue': False},
        'incrementalTreeLoad': {'xtype': 'checkbox', 'name': _t('Enable Incremental Tree Loading on the Infrastructure Page'), 'defaultValue': True},
        'enableTreeFilters': {'xtype': 'checkbox', 'name': _t('Enable Tree Filters'), 'defaultValue': True},
        'deviceGridBufferSize': {'xtype': 'numberfield', 'name': _t('Device Grid Buffer Size'), 'defaultValue': 100, 'minValue': 50, 'maxValue': 1000, 'allowBlank': False},
        'componentGridBufferSize': {'xtype': 'numberfield', 'name': _t('Component Grid Buffer Size'), 'defaultValue': 50, 'minValue': 25, 'maxValue': 1000, 'allowBlank': False},
        'eventConsoleBufferSize': {'xtype': 'numberfield', 'name': _t('Event Console Buffer Size'), 'defaultValue': 200, 'minValue': 50, 'maxValue': 1000, 'allowBlank': False},
        'deviceMoveJobThreshold': {'xtype': 'numberfield', 'name': _t('Device Move Job Threshold'), 'defaultValue': 5, 'minValue': 0, 'allowBlank': False},
        'zenjobsRefreshInterval': {'xtype': 'numberfield', 'name': _t('Job Notification Refresh Interval (seconds)'), 'defaultValue' : 5, 'minValue' : 1, 'maxValue': 300, 'allowBlank': False},
    }

    def getInterfaceSettings(self):
        """
        @rtype:   Dictionary
        @return Key/Value pair of all settings for the UserInterface
        """
        settings = {}
        for prop in self.getSettingsData():
            propId = prop['id']
            settings[propId] = prop['value']
        return settings

    def getSettingsData(self):
        """
        @rtype: Dictionary
        @return: The value of the settings along with some meta information
        for display
        """
        settings = deepcopy(self._properties)
        for prop in settings:
            prop.update(self._propertyMetaData[prop['id']])
            prop['value'] = getattr(self, prop['id'], prop['defaultValue'])
        return settings



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


from Hardware import Hardware

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from Exceptions import *


class DeviceHW(Hardware):

    __pychecker__='no-override'

    meta_type = "DeviceHW"

    totalMemory = 0L

    _properties = Hardware._properties + (
        {'id':'totalMemory', 'type':'long', 'mode':'w'},
    )

    _relations = Hardware._relations + (
        ("cpus", ToManyCont(ToOne, "Products.ZenModel.CPU", "hw")),
        ("cards", ToManyCont(ToOne, "Products.ZenModel.ExpansionCard", "hw")),
        ("harddisks", ToManyCont(ToOne, "Products.ZenModel.HardDisk", "hw")),
        ("fans", ToManyCont(ToOne, "Products.ZenModel.Fan", "hw")),
        ("powersupplies", ToManyCont(ToOne, "Products.ZenModel.PowerSupply",
            "hw")),
        ("temperaturesensors", ToManyCont(ToOne,
            "Products.ZenModel.TemperatureSensor", "hw")),
    )

    security = ClassSecurityInfo()

    def __init__(self):
        id = "hw"
        Hardware.__init__(self, id)

    
    def __call__(self, REQUEST=None):
        pp = self.getPrimaryParent()
        screen = getattr(pp, "deviceHardwareDetail", False)
        if not screen: return pp()
        return screen()

    def totalMemoryString(self):
        return self.totalMemory and convToUnits(self.totalMemory) or 'Unknown' 

    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()



InitializeClass(DeviceHW)

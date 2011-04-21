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
objnoprops = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
</object>
"""


objwithprops = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
</object>
"""

objwithtoone = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<toone id='location' objid='loc'/>
</object>
"""

objwithtomany = \
"""<object id='loc' module='Products.ZenRelations.tests.TestSchema' class='Location'>
<tomany id='devices'>
<link objid='dev'/>
</tomany>
</object>
"""

objwithtomanycont = \
"""<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface'>
</object>
</tomanycont>
</object>
"""

objwithoutskip = \
"""<object id='dev' module='ZenPacks.zenoss.ZenVMware.VMwareHost' class='VMwareHost'>
<tomanycont id='guestDevices'>
<object id='guest0' module='ZenPacks.zenoss.ZenVMware.VMwareGuest' class='VMwareGuest'>
</object>
</tomanycont>
</object>
"""

objwithskip = \
"""<object id='dev' module='Products.ZenModel.Device' class='Device'>
<tomanycont id='guestDevices'>
<object id='guest0' module='ZenPacks.zenoss.ZenVMware.VMwareGuest' class='VMwareGuest'>
</object>
</tomanycont>
</object>
"""


devicexml = \
"""
<objects>
<object id='/loc' module='Products.ZenRelations.tests.TestSchema' class='Location'/>
<object id='dev' module='Products.ZenRelations.tests.TestSchema' class='Device'>
<property setter="setPingStatus" type="int" id="pingStatus" mode="w" >
0
</property>
<tomanycont id='interfaces'>
<object id='eth0' module='Products.ZenRelations.tests.TestSchema' class='IpInterface'>
<toone id='device' objid='dev'/>
</object>
</tomanycont>
<toone id='location' objid='/loc'/>
</object>
</objects>
"""

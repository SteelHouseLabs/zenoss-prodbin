#!/bin/bash
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#
# If the pre-upgrade zenpack is installed, switch over the global catalog's class
# and remove the zenpack
#
echo "Testing for the pre-upgrade ZenPack..."
if ${ZENHOME}/bin/zenpack --list | grep PreUpgrade30 2>/dev/null 1>&1 ;then
    echo "Adjusting class of global catalog"
    ${ZENHOME}/bin/zendmd --script ${ZENHOME}/bin/fix_catalog_class.py  --commit
    
    echo "Removing the pre-upgrade zenpack"
    ${ZENHOME}/bin/zenpack --remove ZenPacks.zenoss.PreUpgrade30
fi

#
# Don't cause troubles if one of the above steps had issues.
#
exit 0

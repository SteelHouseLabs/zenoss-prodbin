#! /usr/bin/env python
###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

NUMB_EVENTS = 120

evts = dict(
# will hit default rules and be mapped to /Ingore
#REPEAT = "<165> message repeated 4 times",

# /Security/Login/Fail
FAIL = "<165> dropbear[23]: exit before auth (user 'root', 3 fails): Max auth tries reached - user root",

# /Security/Login/BadPass
SSHBADPASS = "<165> ssh[3]: Failed password for user from 10.1.2.3 port 53529 ssh2",

# Cisco Power Loss /HW/Power/PowerLoss (will clear)
PLOSS = "<165>%C6KPWR-SP-4-PSFAIL: power supply 1 output failed",
POK = "<165>%C6KPWR-SP-4-PSOK: power supply 1 turned on",

)
keys = evts.keys()
import random
for i in range(NUMB_EVENTS):
    print evts[random.choice(keys)]

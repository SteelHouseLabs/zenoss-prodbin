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

#! /usr/bin/python

from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials

import Globals
from Products.ZenUtils.Driver import drive

from zenhub import PB_PORT

class Listener(pb.Referenceable):

    def remote_beat(self, ts):
        import time
        print time.time() - ts

def error(reason):
    reason.printTraceback()
    reactor.stop()

def main():
    def go(driver):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", PB_PORT, factory)

        yield factory.login(credentials.UsernamePassword("zenoss", "zenoss"))
        perspective = driver.next()

        yield perspective.callRemote('getService', 'Beat', listener=Listener())
        service = driver.next()

    drive(go).addErrback(error)
    reactor.run()
    
if __name__ == '__main__':
    main()

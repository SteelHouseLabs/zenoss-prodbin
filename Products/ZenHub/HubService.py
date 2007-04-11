from twisted.spread import pb

import logging
log = logging.getLogger("zenhub")


class HubService(pb.Referenceable):

    def __init__(self, dmd, instance):
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []

    def update(self, object):
        pass

    def deleted(self, object):
        pass

    def addListener(self, remote):
        remote.notifyOnDisconnect(self.removeListener)
        log.info("adding listener")
        self.listeners.append(remote)

    def removeListener(self, listener):
        log.warning("removing listener")
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")

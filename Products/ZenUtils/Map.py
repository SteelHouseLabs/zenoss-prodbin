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

import threading
import time
from functools import wraps


class Timed(object):
    "Store elements in a map for the given time"

    def __init__(self, map, timeout):
        self.map = map
        self.timeout = timeout
        self.lastClean = 0


    def clean(self, now = None):
        "remove old values"
        # FIXME O(N) search
        if now is None:
            now = time.time()
        if self.lastClean + self.timeout > now:
            return
        for k, (v, t) in self.map.items():
            if t + self.timeout < now:
                del self.map[k]
        self.lastClean = now

    
    def get(self, key, default):
        now = time.time()
        self.clean(now)
        v, t = self.map.get(key, (default, None) )
        if t is None or t + self.timeout < now:
            return default
        return v


    def __getitem__(self, key):
        now = time.time()
        v, t = self.map[key]
        if t + self.timeout < now:
            del self.map[key]
            raise KeyError
        return v


    def __setitem__(self, key, value):
        now = time.time()
        self.clean(now)
        self.map[key] = (value, now)


    def update(self, d):
        now = time.time()
        self.clean(now)
        for k, v in d.items():
            self.map[k] = (v, now)



def Locked_synchronize(fn):
    @wraps(fn)
    def _closure(self, *args, **kwargs):
        with self.lock:
            return fn(self, *args, **kwargs)
    return _closure

class Locked(object):
    "Use a simple lock for all read/write access to a map"

    def __init__(self, map):
        self.map = map
        self.lock = threading.Lock()

    @Locked_synchronize
    def __contains__(self, key):
        return key in self.map

    def has_key(self, key):
        "Deprecated, convert to using 'key in map' form"
        return key in self

    @Locked_synchronize
    def get(self, *args):
        if not args:
            raise TypeError("get takes at least 1 argument : {0} given".format(len(args)))
        return self.map.get(*args[:2])

    @Locked_synchronize
    def __setitem__(self, key, item):
        self.map[key] = item

    @Locked_synchronize
    def __getitem__(self, key):
        return self.map[key]

    @Locked_synchronize
    def update(self, other):
        self.map.update(other)


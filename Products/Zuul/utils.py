###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import transaction
from operator import attrgetter
from itertools import islice
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from Acquisition import aq_base

def resolve_context(context, default=None):
    """
    Make sure that a given context is an actual object, and not a path to
    the object, by trying to traverse from the dmd if it's a string.
    """
    dmd = get_dmd()
    if dmd:
        if isinstance(context, basestring):
            # Should be a path to the object we want
            if context.startswith('/') and not context.startswith('/zport/dmd'):
                context = context[1:]
            try:
                context = dmd.unrestrictedTraverse(context)
            except (KeyError, AttributeError):
                context = None
    if context is None:
        context = default
    return context


def get_dmd():
    """
    Retrieve the DMD object.
    """
    connections = transaction.get()._synchronizers.data.values()[:]
    connections.reverse()
    # Make sure we don't get the temporary connection
    for cxn in connections:
        if cxn._db.database_name != 'temporary':
            app = cxn.root()['Application']
            return app.zport.dmd


_MARKER = object()
def safe_hasattr(object, name):
    return getattr(object, name, _MARKER) is not _MARKER

def unbrain(item):
    if isinstance(item, AbstractCatalogBrain):
        return item.getObject()
    return item
    

class LazySortableList(object):

    def __init__(self, iterable, cmp=None, key=None, orderby=None, 
                 reverse=False):
        self.iterator = iter(iterable)
        if cmp is not None or key is not None or orderby is not None:
            # Might as well exhaust it now
            if orderby is not None:
                key = attrgetter(orderby)
            self.seen = sorted(self.iterator, cmp=cmp, key=key, 
                               reverse=reverse)
        else:
            self.seen = []

    def __getitem__(self, index):
        self.exhaust(index)
        return self.seen[index]

    def __getslice__(self, start, stop):
        self.exhaust(stop-1)
        return self.seen[start:stop]

    def __len__(self):
        return len(self.seen)

    def __repr__(self):
        return repr(self.seen)

    def exhaust(self, i):
        if i<0:
            raise ValueError("Negative indices not supported")
        delta = i-len(self)
        if delta > 0:
            self.seen.extend(islice(self.iterator, delta+1))


class BrainWhilePossible(object):
    def __init__(self, ob):
        self._ob = ob
    def __getattr__(self, attr):
        if isinstance(self._ob, AbstractCatalogBrain):
            try:
                return getattr(aq_base(self._ob), attr)
            except AttributeError:
                # Not metadata; time to go get the ob
                self._ob = unbrain(self._ob)
        return getattr(self._ob, attr)

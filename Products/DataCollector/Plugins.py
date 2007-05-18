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

from Products.ZenUtils.Utils import importClass
import sys
import os

import logging
log = logging.getLogger('dc.plugins')

import plugins

_pluginskip = ("CollectorPlugin.py", "DataMaps.py")
def _plfilter(f):
    return f.endswith(".py") and not (f.startswith("_") or f in _pluginskip)

def _loadPluginDir(pdir):
    collectorPlugins = {}
    log.info("loading collector plugins from: %s", pdir)
    lpdir = len(pdir)+1
    for path, dirname, filenames in os.walk(pdir):
        path = path[lpdir:]
        for filename in filter(_plfilter, filenames):
            modpath = os.path.join(path,filename[:-3]).replace("/",".")
            log.debug("loading: %s", modpath)
            try:
                sys.path.insert(0, pdir)
                const = importClass(modpath)
                sys.path.remove(pdir)
                plugin = const()
                collectorPlugins[plugin.name()] = plugin
            except ImportError:
                log.exception("problem loading plugin:%s",modpath)
    return collectorPlugins
 

def loadPlugins(dmd):
    """Load plugins from the plugin directory.
    """
    plugins = filter(lambda x: x.startswith("plugins"), sys.modules)
    for key in ['zenoss'] + plugins:
        log.debug("clearing plugin %s", key)
        if sys.modules.has_key(key):
            del sys.modules[key]
    pdir = os.path.join(os.path.dirname(__file__),"plugins")
    log.info("loading collector plugins from:%s", pdir)
    plugins = _loadPluginDir(pdir)
    try:
        for pack in dmd.packs():
            plugins.update(_loadPluginDir(pack.path('modeler', 'plugins')))
    except:
        log.error('Could not load modeler plugins from zenpacks.'
                    ' One of the zenpacks is missing or broken.')
    return plugins



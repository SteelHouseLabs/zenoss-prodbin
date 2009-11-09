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
import os
import re
import simplejson
import Globals
from Products.Five.browser import BrowserView

JSBFILE = os.path.join(os.path.dirname(__file__), 'zenoss.jsb2')


class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++extjs')[name]


class ZenUIResourcesShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++zenui')[name]


def get_js_file_list(pkg='Zenoss Application'):
    """
    Parse the JSBuilder2 config file to get a list of file names in the same
    order as that used by JSBuilder to generate its version.
    """
    jsb = open(JSBFILE)
    paths = []
    try:
        cfg = simplejson.load(jsb)
        for p in cfg['pkgs']:
            if p['name']==pkg:
                for f in p['fileIncludes']:
                    path = re.sub('^resources', 'zenui', f['path'])
                    paths.append(path + f['text'])
    finally:
        jsb.close()
    return paths


class ZenossJavaScript(BrowserView):
    """
    When Zope is in debug mode, we want to use the development JavaScript
    source files, so we don't have to make changes to a single huge file. When
    Zope is in production mode, we want a single minified file.
    """
    def __call__(self):
        if Globals.DevelopmentMode:
            return self.dev()
        else:
            return self.production()

    def dev(self):
        """
        Read in the files in the same order as JSBuilder does when creating the
        minified version, concatenate them, and returnt the output.
        """
        src = []
        for p in get_js_file_list():
            fob = self.context.unrestrictedTraverse(p)
            src.append(fob.GET())
        return '\n'.join(src)

    def production(self):
        """
        Redirect to the minified file containing all Zenoss js.
        """
        self.request.RESPONSE.redirect('/zenui/js/deploy/zenoss-compiled.js')


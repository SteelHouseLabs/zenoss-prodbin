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
import zope.interface
from zope.viewlet.manager import WeightOrderedViewletManager
from zope.viewlet.viewlet import JavaScriptViewlet
from interfaces import IExtDirectJavaScriptManager
from interfaces import IJsonApiJavaScriptManager
from interfaces import IExtDirectJavaScriptAndSourceManager

class ExtDirectJavaScriptManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptManager)

class JsonApiJavaScriptManager(WeightOrderedViewletManager):
    zope.interface.implements(IJsonApiJavaScriptManager)

class ExtDirectJavaScriptAndSourceManager(WeightOrderedViewletManager):
    zope.interface.implements(IExtDirectJavaScriptAndSourceManager)

DirectSourceViewlet = JavaScriptViewlet('direct.js')

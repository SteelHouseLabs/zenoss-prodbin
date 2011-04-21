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
from zope.interface import Interface
from Products.ZenUI3.utils.interfaces import IJavaScriptSnippetManager
from zope.viewlet.interfaces import IViewlet, IViewletManager

class IMainSnippetManager(IJavaScriptSnippetManager):
    """
    A viewlet manager to handle general javascript snippets.
    """

class IJavaScriptSrcManager(IViewletManager):
    """
    a viewlet manager to handle java script src viewlets
    """

class IJavaScriptSrcViewlet(IViewlet):
    """
    A viewlet that will generate java a script src file includes
    """

class IJavaScriptBundleViewlet(IViewlet):
    """
    A viewlet that will generate a list of java script src file includes
    """

class IHeadExtraManager(IViewletManager):
    """
    A viewlet manager to allow ZenPacks, etc. to plug in extra stuff.
    """

class INewPath(Interface):
    """
    Translates old paths into new ones.
    """

class IErrorMessage(Interface):
    """
    A 404 or 500 page.
    """

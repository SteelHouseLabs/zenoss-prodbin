######################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
######################################################################

from zope.interface import implements
from zope.component import adapts
from Products.ZenUtils.Ext import DirectRouter
from Products import Zuul
from Products.Zuul.search import ISearchResult
from Products.Zuul.search import IQuickSearchResultSnippet

class DefaultQuickSearchResultSnippet(object):
    implements(IQuickSearchResultSnippet)
    adapts(ISearchResult)

    def __init__(self, result):
        self._result = result

    @property
    def category(self):
        return self._result.category

    defaultTemplate = '<table>' + \
                          '<td class="icon">%s</td>' + \
                          '<td class="excerpt">%s</td>' + \
                      '</table>'
    @property
    def content(self):
        return self.defaultTemplate % ( self._result.icon, self._result.excerpt)

    @property
    def url(self):
        return self._result.url

    @property
    def popout(self):
        return False
    

class SearchRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('search', self.context)

    def _addAllResultsLink(self, results):
        # HERE'S WHERE WE ADD THE LINK TO THE MAIN SEARCH PAGE
        pass

    def getLiveResults(self, query):
        facade = self._getFacade()
        results = facade.getQuickSearchResults(query)
        snippets = []
        for result in results:
            snippet = IQuickSearchResultSnippet( result )
            snippets.append( snippet )
        #self._addAllResultsLink( results )
        return {'results': sorted(Zuul.marshal(snippets),
            lambda x, y: cmp(x['category'], y['category']))}

    def noProvidersPresent(self):
        return self._getFacade().noProvidersPresent()
    

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

'''
This module contains monkey patches we needed to make to PAS when we switched
from native ZODB-managed authentication to pluggable authentication.

This module needs to be imported by ZenUtils/__init__.py.

Related tickets:
  http://dev.zenoss.org/trac/ticket/379
  http://dev.zenoss.org/trac/ticket/402
  http://dev.zenoss.org/trac/ticket/443
  http://dev.zenoss.org/trac/ticket/1042
  http://dev.zenoss.org/trac/ticket/4225
'''

# monkey patch PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
from Products.PluggableAuthService import PluggableAuthService
from Products.ZenUtils.Security import _createInitialUser
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser

# monkey patches for the PAS login form
from Products.PluggableAuthService.plugins import CookieAuthHelper
import urlparse
from cgi import parse_qs

def manage_afterAdd(self, item, container):
    """We don't want CookieAuthHelper setting the login attribute, we we'll
    override manage_afterAdd().

    For now, the only thing that manage_afterAdd does is set the login_form
    attribute, but we will need to check this after every upgrade of the PAS.
    """
    pass

CookieAuthHelper.CookieAuthHelper.manage_afterAdd = manage_afterAdd

def login(self):
    """
    Set a cookie and redirect to the url that we tried to
    authenticate against originally.

    FIXME - I don't think we need this any more now that the EULA is gone -EAD
    """
    import urllib

    request = self.REQUEST
    response = request['RESPONSE']

    login = request.get('__ac_name', '')
    password = request.get('__ac_password', '')
    submitted = request.get('submitted', '')

    pas_instance = self._getPAS()

    if pas_instance is not None:
        pas_instance.updateCredentials(request, response, login, password)

    came_from = request.form.get('came_from') or ''
    if came_from:
        parts = urlparse.urlsplit(came_from)
        querydict = parse_qs(parts[3])
        if querydict.has_key('terms'):
            del querydict['terms']
        if 'submitted' not in querydict.keys():
            querydict['submitted'] = submitted
        newqs = urllib.urlencode(querydict, doseq=True)
        parts = parts[:3] + (newqs,) + parts[4:]
        came_from = urlparse.urlunsplit(parts)
    else:
        submittedQs = 'submitted=%s' % submitted
        came_from = '/zport/dmd?%s' % submittedQs
    if not self.dmd.acceptedTerms:
        url = "%s/zenoss_terms/?came_from=%s" % (
                    self.absolute_url(), urllib.quote(came_from))
    else:
        url = came_from

    if self.dmd.uuid is None:
        from uuid import uuid1
        self.dmd.uuid = str(uuid1())
    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.login = login


def termsCheck(self):
    """ Check to see if the user has accepted the Zenoss terms.
    """
    request = self.REQUEST
    response = request['RESPONSE']

    acceptStatus = request.form.get('terms') or ''
    url = request.form.get('came_from') or self.absolute_url()

    if acceptStatus != 'Accept':
        self.resetCredentials(request, response)
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += 'terms=Decline'
    else:
        self.dmd.acceptedTerms = True
        from uuid import uuid1
        self.dmd.uuid = str(uuid1())
    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.termsCheck = termsCheck

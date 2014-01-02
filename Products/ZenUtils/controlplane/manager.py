##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
ControlPlaneClient
"""

import json
import urllib2

from cookielib import CookieJar
from fnmatch import fnmatch

from zope.interface import implementer

from Products.ZenUtils.GlobalConfig import globalConfToDict

from .interfaces import IControlPlaneClient
from .data import json2ServiceApplication, ServiceApplication

_DEFAULT_PORT = 8787


def _getDefaults(options=None):
    if options is None:
        o = globalConfToDict()
    else:
        o = options
    settings = {
        "port": o.get("controlplane-port", _DEFAULT_PORT),
        "user": o.get("controlplane-user", "zenoss"),
        "password": o.get("controlplane-password", "zenoss"),
    }
    return settings


def _login(opener, settings):
    body = {
        "username": settings["user"], "password": settings["password"]
    }
    encodedbody = json.dumps(body)
    headers = {
        "Content-Type": "application/json"
    }
    req = urllib2.Request(
        "http://localhost:%(port)s/login" % settings,
        encodedbody,
        headers
    )
    response = opener.open(req)
    response.close()


def _dorequest(request, opener, settings):
    response = None
    try:
        response = opener.open(request)
    except urllib2.HTTPError as ex:
        if ex.getcode() == 401:
            _login(opener, settings)
            response = opener.open(request)
        else:
            raise
    return response


def _services(opener, settings):
    req = urllib2.Request(
        "http://localhost:%(port)s/services" % settings
    )
    return _dorequest(req, opener, settings)


@implementer(IControlPlaneClient)
class ControlPlaneClient(object):
    """
    """

    def __init__(self):
        """
        """
        self._cj = CookieJar()
        self._opener = urllib2.build_opener(
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self._cj)
        )
        self._settings = _getDefaults()

    def queryServices(self, name="*", **kwargs):
        """
        """
        response = _services(self._opener, self._settings)
        body = ''.join(response.readlines())
        decoded = json.loads(body, object_hook=json2ServiceApplication)
        #results = json.loads(_apps, object_hook=json2ServiceApplication)
        return [app for app in decoded if fnmatch(app.name, name)]

    def getService(self, instanceId):
        """
        """
        # get data from url
        if instanceId == "app-name":
            return json.loads(_app1, object_hook=json2ServiceApplication)
        elif instanceId == "app2-name":
            return json.loads(_app2, object_hook=json2ServiceApplication)
        else:
            return default

    def updateService(self, instance):
        """
        """

    def getServiceLog(self, uri, start=0, end=None):
        """
        """

    def getServiceConfiguration(self, uri):
        """
        """

    def updateServiceConfiguration(self, uri, config):
        """
        """

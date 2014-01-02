##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Application JSON format:

    'query' result
    [
        <application-node>,...
    ]

    /services 'get' result example
    {
        "Id":              "9827-939070095",
        "Name":            "zentrap",
        "Startup":         "/bin/true",
        "Description":     "This is a collector deamon 4",
        "Instances":       0,
        "ImageId":         "zenoss",
        "PoolId":          "default",
        "DesiredState":    1,
        "Launch":          "auto",
        "Endpoints":       {
            "Protocol" : "tcp",
            "PortNumber": 6379,
            "Application": "redis",
            "Purpose": "export"
        },
        "ParentServiceId": "293482085035",
        "CreatedAt":       "0001-01-01T00:00:00Z",
        "UpdatedAt":       "2013-10-29T07:31:22-05:00"
    }
    missing current-state, conf, and log.
    
    {
        "id":     <string>,
        "name":   <string>,
        "uri":    <string>,
        "tags":   [<string>, ...],
        "log":    <uri-string>,
        "conf":   <uri-string>,
        "status": <string>,
        "state":  <string>,
    }
"""

import json

class _Value(object):

    def __init__(self, name, value=None):
        self._name = name
        self._value = value if value is not None else name

    def __str__(self):
        return self._name

    def __int__(self):
        return int(self._value)

    def __repr__(self):
        return str(self._value)


_serviceKeys = set([
    "Id", "Name", "ParentServiceId", "Description", "Launch", "DesiredState",
])

def _decodeServiceJsonObject(obj):
    foundKeys = _serviceKeys & set(obj.keys())
    if foundKeys == _serviceKeys:
        service = ServiceApplication()
        service.__setstate__(obj)
        return service
    return obj


class ServiceJsonDecoder(json.JSONDecoder):
    """
    """

    def __init__(self):
        kwargs = {"object_hook": _decodeServiceJsonObject}
        super(ServiceJsonDecoder, self).__init__(**kwargs)


class ServiceJsonEncoder(json.JSONEncoder):
    """
    """

    def encode(self, src):
        data = src.__getstate__()
        return super(ServiceJsonEncoder, self).encode(data)


class ServiceApplication(object):
    """
    """

    class STATE(object):
        RUN = _Value("RUN", 1)
        STOP = _Value("STOP", 0)
        RESTART = _Value("RESTART", -1)

    class STATUS(object):
        AUTO = _Value("AUTO", "auto")
        MANUAL = _Value("MANUAL", "manual")

    __map = {
        1: STATE.RUN, 2: STATE.STOP, -1: STATE.RESTART
    }

    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    #def __init__(self, **kwargs):
    #    """
    #    """
    #    self._data = {}
    #    self._id = kwargs.get("id")
    #    self._name = kwargs.get("name")
    #    self._parentId = kwargs.get("parentId")
    #    self._description = kwargs.get("description")
    #    self.status = kwargs.get("status").upper()
    #    self._currentstate = self.__map.get(kwargs.get("currentState"))
    #    self._desiredstate = self.__map.get(kwargs.get("desiredState"))
    #    self._loguri = kwargs.get("logResourceId")
    #    self._confuri = kwargs.get("configResourceId")
    #    self._uri = "/services/%s" % self._id

    @property
    def id(self):
        return self._data.get("Id")
    
    @property
    def resourceId(self):
        return "/services/%s" % (self._data.get("Id"),)

    @property
    def name(self):
        return self._data.get("Name")

    @property
    def parentId(self):
        return self._data.get("ParentServiceId")

    @property
    def description(self):
        return self._data.get("Description")

    @property
    def status(self):
        return self.STATUS.__dict__.get(self._data.get("Launch").upper())

    @status.setter
    def status(self, value):
        if str(value) not in self.STATUS.__dict__:
            raise ValueError("Invalid status value: %s" % (value,))
        self._data["Launch"] = repr(value)

    @property
    def state(self):
        return self.__map.get(self._data.get("DesiredState"))

    @state.setter
    def state(self, value):
        if str(value) not in self.STATE.__dict__:
            raise ValueError("Invalid state: %s" % (value,))
        self._data["DesiredState"] = int(value)

    @property
    def logResourceId(self):
        return self._data.get("LogId")

    @property
    def configResourceId(self):
        return self._data.get("ConfigurationId")


# Define the names to export via 'from data import *'.
__all__ = (
    "ServiceJsonDecoder", "ServiceJsonEncoder", "ServiceApplication"
)

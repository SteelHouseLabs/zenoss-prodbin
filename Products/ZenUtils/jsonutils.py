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

import json as _json

def _recursiveCaster(ob):
    if isinstance(ob, dict):
        result = {}
        for k, v in ob.iteritems():
            result[str(k)] = _recursiveCaster(v)
        return result
    elif isinstance(ob, list):
        return [_recursiveCaster(x) for x in ob]
    elif isinstance(ob, unicode):
        return str(ob)
    else:
        return ob


class StringifyingDecoder(_json.JSONDecoder):
    """
    Casts all unicode objects as strings. This is necessary until Zope is less
    stupid.
    """
    def decode(self, s):
        result = super(StringifyingDecoder, self).decode(s)
        return _recursiveCaster(result)


def json(value, **kw):
    """
    Serialize C{value} into a JSON string.

    If C{value} is callable, a decorated version of C{value} that serializes its
    return value will be returned.

        >>> value = (dict(a=1L), u"123", 123)
        >>> print json(value)
        [{"a": 1}, "123", 123]
        >>> @json
        ... def f():
        ...     return value
        ...
        >>> print f()
        [{"a": 1}, "123", 123]

    @param value: An object to be serialized
    @type value: dict, list, tuple, str, etc. or callable
    @return: The JSON representation of C{value} or a decorated function
    @rtype: str, func
    """
    if callable(value):
        # Decorate the given callable
        def inner(*args, **kwargs):
            return _json.dumps(value(*args, **kwargs))
        # Well-behaved decorators look like the decorated function
        inner.__name__ = value.__name__
        inner.__dict__.update(value.__dict__)
        inner.__doc__ = value.__doc__
        return inner
    else:
        # Simply serialize the value passed
        return _json.dumps(value, **kw)

def unjson(value, **kw):
    """
    Create the Python object represented by the JSON string C{value}.

        >>> jsonstr = '[{"a": 1}, "123", 123]'
        >>> print unjson(jsonstr)
        [{'a': 1}, '123', 123]

    @param value: A JSON string
    @type value: str
    @return: The object represented by C{value}
    """
    if 'cls' not in kw:
        kw['cls'] = StringifyingDecoder
    return _json.loads(value, **kw)

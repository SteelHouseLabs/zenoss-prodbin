##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# import any monkey patches that may be necessary
from patches import pasmonkey
from patches import dirviewmonkey
from Products.ZenUtils.Utils import unused
unused(pasmonkey, dirviewmonkey)

from Products.ZenUtils.MultiPathIndex import MultiPathIndex , \
                                             manage_addMultiPathIndex, \
                                             manage_addMultiPathIndexForm

def initialize(context):
    context.registerClass(
        MultiPathIndex,
        permission='Add Pluggable Index',
        constructors=(manage_addMultiPathIndexForm, manage_addMultiPathIndex),
        #icon="www/index.gif",
        visibility=None)

def safeTuple(arg):
    """
    >>> safeTuple(["foo", "blam"])
    ('foo', 'blam')
    >>> safeTuple([])
    ()
    >>> safeTuple(None)
    ()
    >>> safeTuple("foo")
    ('foo',)
    """
    if arg is not None:
        return tuple(arg) if hasattr(arg, '__iter__') else (arg,)
    else:
        return ()

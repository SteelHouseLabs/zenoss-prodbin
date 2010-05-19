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



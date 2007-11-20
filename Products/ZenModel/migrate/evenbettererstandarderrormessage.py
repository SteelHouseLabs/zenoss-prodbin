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
__doc__='''

Create standard_error_message at the root level of zope

'''

import Migrate
from Products.ZenUtils.Utils import zenPath

class EvenBettererStandardErrorMessage(Migrate.Step):
    version = Migrate.Version(2, 1, 1)

    def cutover(self, dmd):
        ''' try/except to better handle access restrictions
        '''
        app = dmd.getPhysicalRoot()
        if app.hasObject('standard_error_message'):
            app._delObject('standard_error_message')
        file = open(zenPath('Products/ZenModel/dtml/standard_error_message.dtml'))
        try:
            text = file.read()
        finally:
            file.close()
        import OFS.DTMLMethod
        OFS.DTMLMethod.addDTMLMethod(app, id='standard_error_message',
                                        file=text)

EvenBettererStandardErrorMessage()

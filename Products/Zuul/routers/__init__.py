###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products import Zuul
import logging
log = logging.getLogger(__name__)

class TreeRouter(DirectRouter):
    """
    A common base class for routers that have Trees on them (more specifically
    the HierarchyTreePanel and want to add/remove nodes
    """
    @require('Manage DMD')
    def addNode(self, type, contextUid, id, description=None):
        result = {}
        try:
            facade = self._getFacade()
            if type.lower() == 'class':
                uid = facade.addClass(contextUid, id)
            else:
                organizer = facade.addOrganizer(contextUid, id, description)
                uid = organizer.uid

            treeNode = facade.getTree(uid)
            result['nodeConfig'] = Zuul.marshal(treeNode)
            result['success'] = True
        except Exception, e:
            log.exception(e)
            result['msg'] = str(e)
            result['success'] = False
        return result

    @require('Manage DMD')
    def deleteNode(self, uid):
        # make sure we are not deleting a root node
        if not self._canDeleteUid(uid):
            raise Exception('You cannot delete the root node')
        facade = self._getFacade()
        facade.deleteNode(uid)
        msg = "Deleted node '%s'" % uid
        return {'success': True, 'msg': msg}

    def moveOrganizer(self, targetUid, organizerUid):
        """
        Moves the organizer uid to be underneath the targetuid
        """
        facade = self._getFacade()
        data = facade.moveOrganizer(targetUid, organizerUid)
        return DirectResponse.succeed(data=Zuul.marshal(data))
    
    def _getFacade(self):
        """
        Abstract method for child classes to use to get their facade
        """
        raise NotImplementedError, " you must implement the _getFacade method"

    def _canDeleteUid(self,uid):
        """
        We can not delete top level UID's. For example:
        '/zport/dmd/Processes' this will return False (we can NOT delete)
        '/zport/dmd/Processes/Child' will return True (we can delete this)
        """
        # check the number of levels deep it is
        levels = len(uid.split('/'))
        return levels > 4



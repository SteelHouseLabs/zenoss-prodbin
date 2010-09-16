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
"""
Operations for Reports.

Available at:  /zport/dmd/report_router
"""

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.utils import ZuulMessageFactory as _t

log = logging.getLogger('zen.ReportRouter')
class ReportRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on reports
    """

    _newReportTypes = [
        'customDeviceReport',
        'graphReport',
        'multiGraphReport',
    ]

    _reportMenuItems = [
        _t('Custom Device Report'),
        _t('Graph Report'),
        _t('Multi-Graph Report'),
    ]

    _createOrganizers = {
        _newReportTypes[0]: 'Custom Device Reports',
        _newReportTypes[1]: 'Graph Reports',
        _newReportTypes[2]: 'Multi-Graph Reports',
    }

    _createMethods = {
        _newReportTypes[0]: 'manage_addDeviceReport',
        _newReportTypes[1]: 'manage_addGraphReport',
        _newReportTypes[2]: 'manage_addMultiGraphReport',
    }

    _essentialNodes = [
        '/zport/dmd/Reports',
        '/zport/dmd/Reports/Custom%20Device%20Reports',
        '/zport/dmd/Reports/Graph%20Reports',
        '/zport/dmd/Reports/Multi-Graph%20Reports',
    ]


    def getReportTypes(self):
        """
        Get the available report types.

        @rtype:   DirectResponse
        @return:  B{Properties}:
           - menuText: ([string]) Human readable list of report types
           - reportTypes: ([string]) A list of the available report types
        """
        return DirectResponse.succeed(reportTypes=ReportRouter._newReportTypes,
                menuText=ReportRouter._reportMenuItems)


    def getTree(self, id='/zport/dmd/Reports'):
        """
        Returns the tree structure of an organizer hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: (optional) Id of the root node of the tree to be returned
                   (default: Reports)
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        root_organizer = self.context.dmd.restrictedTraverse(id)
        root_node = self._getReportOrganizersTree(root_organizer)
        return [root_node]


    def _getReportOrganizersTree(self, reportOrg):
        rorg_node = self._createTreeNode(reportOrg)
        for rorg in reportOrg.children():
            rorg_node['children'].append(self._getReportOrganizersTree(rorg))
        for report in reportOrg.reports():
            rorg_node['children'].append(self._createTreeNode(report))
        return rorg_node


    @require('Manage DMD')
    def addNode(self, nodeType, contextUid, id):
        """
        Add a new report or report organizer.

        @type  nodeType: string
        @param nodeType: Type of new node. Can either be 'organizer' or one of
                         the report types returned from getReportTypes()
        @type  contextUid: string
        @param contextUid: The organizer where the new node should be added
        @type  id: string
        @param id: The new node's ID
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
           - newNode: (dictionary) Object representing the added node
        """
        if nodeType not in ['organizer'] + ReportRouter._newReportTypes :
            return DirectResponse.fail('Not creating "%s"' % nodeType)

        try:
            if nodeType == 'organizer':
                uid = contextUid + '/' + id
                maoUid = uid.replace('/zport/dmd', '')
                self.context.dmd.Reports.manage_addOrganizer(maoUid)
                represented = self.context.dmd.restrictedTraverse(uid)
            else:
                creatingOrganizer = self.context.dmd.restrictedTraverse(
                        "/zport/dmd/Reports/" + 
                        ReportRouter._createOrganizers[nodeType])
                createMethod = eval('creatingOrganizer.' + 
                        ReportRouter._createMethods[nodeType])
                represented = createMethod(id)
                represented.getParentNode()._delObject(id)
                targetNode = self.context.dmd.restrictedTraverse(contextUid)
                targetNode._setObject(id, represented)

            node = self._createTreeNode(represented)
            return DirectResponse.succeed(tree=self.getTree(), newNode=node)
        except Exception, e:
            return DirectResponse.fail(str(e))


    @require('Manage DMD')
    def deleteNode(self, uid):
        """
        Remove a report or report organizer.

        @type  uid: string
        @param uid: The UID of the node to delete
        @rtype:   [dictionary]
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
        """
        represented = self.context.dmd.restrictedTraverse(uid)
        if represented.absolute_url_path() in ReportRouter._essentialNodes:
            return DirectResponse.fail('Not deleting "%s"' % \
                    represented.absolute_url_path())
        represented.getParentNode().zmanage_delObjects([represented.id])
        return DirectResponse.succeed(tree=self.getTree())


    @require('Manage DMD')
    def moveNode(self, uids, target):
        """
        Move a report or report organizer from one organizer to another.

        @type  uids: [string]
        @param uids: The UID's of nodes to move
        @type  target: string
        @param target: The UID of the target Report organizer
        @rtype:   [dictionary]
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
           - newNode: (dictionary) Object representing the moved node
        """
        targetNode = self.context.dmd.restrictedTraverse(target)
        for uid in uids:
            represented = self.context.dmd.restrictedTraverse(uid)
            representedTitle = represented.titleOrId()
            represented.getParentNode()._delObject(representedTitle)
            targetNode._setObject(representedTitle, represented)
            representedNode = self._createTreeNode(represented)
        return DirectResponse.succeed(tree=self.getTree(), 
                newNode=representedNode)


    def _createTreeNode(self, represented):
        path = represented.getDmdKey()
        if path.startswith('/') :
            path = path[1:]

        text = represented.titleOrId()
        leaf = not isinstance(represented, represented.getReportClass())
        if not leaf:
            description = ('reports', 'report')[represented.countReports() == 1]
            text = {'count': represented.countReports(),
                    'text': represented.titleOrId(),
                    'description': description}

        return {'uid': represented.getPrimaryId(),
                'children': [],
                'path': path,
                'id': represented.getPrimaryId().replace('/', '.'),
                'uiProvider': 'report', 
                'leaf': leaf,
                'expandable': not leaf,
                'deletable' : represented.absolute_url_path() not in ReportRouter._essentialNodes,
                'meta_type': represented.meta_type,
                'text': text }

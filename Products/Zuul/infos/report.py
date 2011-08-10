###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import imap, chain

from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.interfaces import IReportClassNode, IReportNode, ICatalogTool
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.routers.report import essentialReportOrganizers


class ReportClassNode(TreeNode):
    implements(IReportClassNode)
    adapts(ReportClass)

    @property
    def children(self):
        # make sure the report classes show up for non global roles
        obj = self._object._unrestrictedGetObject()
        children = []
        for kid in obj.children():
            children.append(ReportClassNode(kid, self._root, self))
        for report in obj.reports():
            children.append(ReportNode(report, self._root, self))
        return children

    @property
    def leaf(self):
        return False

    @property
    def iconCls(self):
        return 'severity-icon-small clear'

    @property
    def qtip(self):
        return self._object.description

    @property
    def deletable(self):
        return self.uid not in essentialReportOrganizers

    @property
    def meta_type(self):
        return self._object.meta_type

    @property
    def text(self):
        numReports = self._object._unrestrictedGetObject().countReports()
        return {
            'text': self._object.name,
            'count': numReports,
            'description': 'reports'
        }

    @property
    def edit_url(self):
        return None

class ReportNode(TreeNode):
    implements(IReportNode)
    adapts(ZenModelRM)

    @property
    def leaf(self):
        return True

    @property
    def iconCls(self):
        return 'leaf'

    @property
    def qtip(self):
        return self._object.description

    @property
    def deletable(self):
        return True

    @property
    def meta_type(self):
        return self._object.meta_type

    @property
    def children(self):
        return ()

    @property
    def edit_url(self):
        if self._object.meta_type == 'Report':
            return None
        return "%s/edit%s" % (self.uid, self._object.meta_type)


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

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: ToManyRebuildKeys.py,v 1.2 2004/10/19 22:28:59 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import gc

from Acquisition import aq_parent

from Products.ZenUtils.Utils import getSubObjectsMemo

from ZCmdBase import ZCmdBase

class ToManyRebuildKeys(ZCmdBase):

    def rebuild(self):
        ccount = 0
        for tomany in getSubObjectsMemo(self.dmd, self.filter, self.decend):
            self.log.debug("rebuilding keys for relation %s on object %s" %
                                (tomany.getId(), aq_parent(tomany).getId()))
            ccount += tomany.rebuildKeys(self.log)
            if ccount >= self.options.commitCount and not self.options.noCommit:
                trans = get_transaction()
                trans.note('ToManyRebuildKeys rebuilt keys')
                trans.commit()
                ccount = 0
                self.dmd._p_jar.sync()
                gc.collect()
        if self.options.noCommit:
            self.log.info("not commiting any changes")
        else:
            trans = get_transaction()
            trans.note('ToManyRebuildKeys rebuilt keys')
            trans.commit()


    def filter(self, obj):
        return obj.meta_type == "To Many Relationship"


    def decend(self, obj):
        from Products.ZenModel.ZenModelRM import ZenModelRM
        from Products.ZenRelations.ToManyRelationship \
            import ToManyRelationship
        from Products.ZenRelations.ToOneRelationship \
            import ToOneRelationship
        return (
                isinstance(obj, ZenModelRM) or 
                isinstance(obj, ToManyRelationship))
                #isinstance(obj, ToOneRelationship))


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=1000,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


if __name__ == "__main__":
    tmbk = ToManyRebuildKeys()
    tmbk.rebuild()

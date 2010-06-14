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
import os
import transaction
import Globals

from Products.ZenRelations.ImportRM import ImportRM

class XmlDataLoader(ImportRM):

    def loadDatabase(self):

        # This is an initial load, so we can forgo incremental commits
        self.options.chunk_size = 0

        datadir = os.path.join(os.path.dirname(__file__),"data")
        self.log.info("loading data from:%s", datadir)
        for path, dirname, filenames in os.walk(datadir):
            filenames.sort()
            for filename in filter(lambda f: f.endswith(".xml"), filenames):
                self.options.infile = os.path.join(path,filename)
                self.log.info("loading: %s", self.options.infile)
                ImportRM.loadDatabase(self)
        # Reindex ProductKeys and EventClassKeys after XML load
        self.dmd.Manufacturers.reIndex()
        self.dmd.Events.reIndex()
        transaction.commit()


if __name__ == "__main__":
    rl = XmlDataLoader()
    rl.loadDatabase()

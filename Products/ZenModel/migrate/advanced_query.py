#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='''
This migration script integrates support for the ManagableIndex and
AdvancedQuery Products by removing old indexes and replacing them with
ManagableFieldIndex indices.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError

from Products.ZenModel.Search import makeFieldIndex
from Products.ZenModel.Search import makeKeywordIndex

import Migrate

allCatalogs = {
    'Devices': {
        'componentSearch': ['meta_type', 'monitored'],
        'deviceSearch': ['id', 'summary'],
    },
    'Services': {
        'serviceSearch': ['serviceKeys'],
    },
    'Manufacturers': {
        'productSearch': ['productKeys'],
    },
    'Mibs': {
        'mibSearch': ['id', 'oid', 'summary'],
    },
    'Events': {
        'eventClassSearch': ['eventClassKey'],
    },
    'Networks': {
        'ipSearch': ['id'],
    },
}

class AdvancedQuery(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        # create a new index
        for section, catalogNames in allCatalogs.items():
            # see which king of index we need to create
            if section in ['Services', 'Manufacturers', 'Mibs']:
                makeIndex = makeKeywordIndex
            else:
                makeIndex = makeFieldIndex
            for catalogName, indexNames in catalogNames.items():
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                # remove the lexicon, if it's there
                delID = 'myLexicon'
                try:
                    zcat._getOb(delID)
                    lexExists = True
                except AttributeError:
                    #print "No lexicon found at %s.%s" % (section, catalogName)
                    lexExists = False
                if lexExists:
                    #print "Deleting %s.%s.%s ..." % (section, catalogName, delID)
                    zcat._delOb(delID)
                    newObjs = []
                    for obj in zcat._objects:
                        if obj.get('id') != delID:
                            newObjs.append(obj)
                    zcat._objects = tuple(newObjs)
                # replace the indices
                for indexName in indexNames:
                    if (catalogName == 'componentSearch' and 
                        indexName == 'monitored'):
                        # the monitored index contains bools, so we're not
                        # going to mess with it
                        continue
                    # get rid of the old index
                    try:
                        cat.delIndex(indexName)
                    except CatalogError: pass
                    # add the new one
                    cat.addIndex(indexName, makeIndex(indexName))
            # reindex the sections
            dmd.getDmdRoot(section).reIndex()

AdvancedQuery()

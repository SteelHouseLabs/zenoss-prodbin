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

import os
from pprint import pprint, pformat
import logging

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.tests.BaseParsersTestCase import Object, filenames

from Products.DataCollector.plugins.DataMaps \
        import RelationshipMap, ObjectMap, MultiArgs

class BasePluginsTestCase(BaseTestCase):
    
    def _testDataFiles(self, datadir, Plugins):
        """
        Run tests for all of the data files in the data directory.
        """
        counter = 0

        for filename in filenames(datadir):
            counter += self._testDataFile(filename, Plugins)

        self.assert_(counter > 0, counter)
        print self.__class__.__name__, "made", counter, "assertions."


    def _testDataFile(self, filename, Plugins):
        """
        Test a data file.
        """
        
        # read the data file
        datafile = open(filename)
        command = datafile.readline().rstrip("\n")
        output = "".join(datafile.readlines())
        datafile.close()
        
        # read the file containing the expected values
        expectedfile = open('%s.py' % (filename,))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()
        
        plugins = [P() for P in Plugins 
                if P.command == command and P.__name__ in expected]
        
        if not plugins:
            self.fail("No plugins for %s" % command)
        
        device = Object()
        device.id = filename.split(os.path.sep)[-2]
        
        expecteds = [expected[p.__class__.__name__] for p in plugins]
        dataMaps = [p.process(device, output, logging) for p in plugins]
        #pprint(dataMaps)
        return self._testDataMaps(zip(expecteds, dataMaps), filename)
        
        
    def _testDataMaps(self, expectedActuals, filename):
        """
        Test the DataMaps contained in the expectedActuals list.
        """
        
        counter = 0
        
        for expected, actual in expectedActuals:
            
            if isinstance(expected, list):
                
                for exp, act in zip(expected, actual):
                    counter += self._testDataMap(exp, act, filename)
                    
            else: 
                
                counter += self._testDataMap(expected, actual, filename)
        
        return counter        
                
    def _testDataMap(self, expected, actual, filename):
        """
        Test the DataMap returned by a plugin.
        """
        
        counter = 0

        if isinstance(actual, RelationshipMap):
            counter += self._testRelationshipMap(expected, actual, filename)
        elif isinstance(actual, ObjectMap):
            counter += self._testObjectMap(expected, actual)
        else:
            self.fail("Data map type %s not supported." % (type(dataMap),))
            
        return counter
        
        
    def _testRelationshipMap(self, expected, relationshipMap, filename):
        """
        Check all of the objectMaps found in the provided relationshipMaps
        maps attribute.
        """
        counter = 0
        objectMapDct = dict([(map.id, map) for map in relationshipMap.maps])
        
        for id in expected:
        
            if objectMapDct.has_key(id):
                counter += self._testObjectMap(expected[id], objectMapDct[id])
            
            else:
                plugin = os.path.sep.join(filename.split(os.path.sep)[-3:])
                self.fail("No ObjectMap with id=%s in the RelationshipMap " \
                          "returned by the plugin (%s).\n%s" % (
                          id, plugin, relationshipMap))
        
        return counter
        
    def _testObjectMap(self, expectedDct, actualObjMap):
        """
        Check the expected values against those in the actual ObjectMap that
        was returned by the plugin.
        """
        
        counter = 0
        
        for key in expectedDct:
            
            if hasattr(actualObjMap, key):
                actual = getattr(actualObjMap, key)
                if isinstance(actual, MultiArgs): actual = actual.args
                self.assertEqual(expectedDct[key], actual)
                counter += 1
                
            else:
                
                self.fail("ObjectMap %s does not have a %s attribute." % (
                        actualObjMap, key))
                        
        return counter
        
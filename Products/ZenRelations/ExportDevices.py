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
import sys
from xml.dom.minidom import parseString
import StringIO
import re

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

_newlines = re.compile('\n[\t \r]*\n', re.M)

class ExportDevices(ZCmdBase):

    def __init__(self):
        ZCmdBase.__init__(self)
        if not self.options.outfile:
            self.outfile = sys.stdout
        else:
            self.outfile = open(self.options.outfile, 'w')
        
    
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest="outfile",
                    help="output file for export default is stdout")
        self.parser.add_option('--ignore', action="append",
                    dest="ignorerels", default=[],
                    help="relations that should be ignored can be many")


    def stripUseless(self, doc):

        _retain_class = (
            "Products.ZenModel.DeviceClass",
            "Products.ZenModel.Device",
            )

        _retain_props = (
            "description",
            "productionState",
            "priority",
            "monitors",
            )

        def denewline(s):
            while re.search(_newlines, s):
                s = re.sub(_newlines, '\n', s)
            return s
        
        def clearObjects(node):
            def keepDevice(elem):
                try: return not elem.getAttribute('module') in _retain_class
                except: return True
            try: elems = node.getElementsByTagName('object')
            except AttributeError: pass
            else:
                elems = filter(keepDevice, elems)
                [elem.parentNode.removeChild(elem) for elem in elems]

        def clearProps(node):
            try: props = node.getElementsByTagName('property')
            except AttributeError: pass
            else:
                for prop in props:
                    if prop.getAttribute('module') not in _retain_props:
                        prop.parentNode.removeChild(prop)
        
        root = doc.getElementsByTagName('objects')[0]
        clearObjects(root)
        clearProps(root)

        #for dev in getDevices(doc): print dev.getAttribute('id')

        return denewline(doc.toprettyxml().replace('\t', ' '*4))


    def export(self):
        root = self.dmd.Devices
        if hasattr(root, "exportXml"):
            buffer = StringIO.StringIO()
            buffer.write("""<?xml version="1.0" encoding='latin-1'?>\n""")
            buffer.write("<objects>\n")
            root.exportXml(buffer,self.options.ignorerels,True)
            buffer.write("</objects>\n")
            doc = parseString(buffer.getvalue())
            finalxml = self.stripUseless(doc)
            self.outfile.write(finalxml)
            self.outfile.close()
            buffer.close()
            doc.unlink()
        else:
            print "ERROR: root object not a exportable (exportXml not found)"
            


if __name__ == '__main__':
    ex = ExportDevices()
    ex.export()

#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RenderServer

Frontend that passes rrd graph options to rrdtool to render.  

$Id: RenderServer.py,v 1.14 2003/06/04 18:25:58 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

import os
import time

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.Image import manage_addFile

from zLOG import LOG, INFO, DEBUG

from pyrrdtool import rrd_graph, rrd_test_error, rrd_get_error

from Products.ZenUtils.PObjectCache import PObjectCache
from Products.ZenUtils.PObjectCache import CacheObj

from RRDToolItem import RRDToolItem

import utils

def manage_addRenderServer(context, id, REQUEST = None):
    """make a RenderServer"""
    rs = RenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRenderServer = DTMLFile('dtml/addRenderServer',globals())

class RRDToolError(utils.RRDException):pass

class RenderServer(RRDToolItem):

    meta_type = "RenderServer"

    cacheName = 'RRDRenderCache'
    
    security = ClassSecurityInfo()

    def __init__(self, id, tmpdir = '/tmp/renderserver', cachetimeout=300):
        self.id = id
        self.tmpdir = tmpdir
        self.cachetimeout = cachetimeout


    security.declareProtected('View', 'render')
    def render(self, gopts, drange, ftype='PNG', REQUEST=None):
        """render a graph and return it"""
        gopts = gopts.split('|')
        drange = int(drange)
        id = self.graphId(gopts, drange, ftype)
        graph = self.getGraph(id, ftype, REQUEST)
        if not graph:
            gopts.insert(0, "--imgformat=%s" % ftype)
            #gopts.insert(0, "--lazy")
            end = int(time.time())-300
            start = end - drange
            gopts.insert(0, '--end=%d' % end)
            gopts.insert(0, '--start=%d' % start)
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir)
            filename = "%s/graph-%s" % (self.tmpdir,id)
            gopts.insert(0, filename)
            rrd_graph(gopts)
            if rrd_test_error():
                LOG('RenderServer', INFO, rrd_get_error())     
                LOG('RenderServer', INFO, ' '.join(gopts))
                raise RRDToolError, rrd_get_error()
            return self._loadfile(filename)
            self.addGraph(id, filename)
            graph = self.getGraph(id, ftype, REQUEST)
        return graph 

    
    security.declareProtected('GenSummary', 'summary')
    def summary(self, gopts, drange):
        """return summary information as a list but no graph"""
        drange = int(drange)
        end = int(time.time())-300
        start = end - drange
        gopts.insert(0, '--end=%d' % end)
        gopts.insert(0, '--start=%d' % start)
        gopts.insert(0, '/dev/null') #no graph generated
        values = rrd_graph(gopts)[1]
        if rrd_test_error():
            LOG('RenderServer', INFO, rrd_get_error())     
            LOG('RenderServer', INFO, ' '.join(gopts))
            raise RRDToolError, rrd_get_error()
        return values
        
    

    def rrdcmd(self, gopts, ftype='PNG'): 
        filename, gopts = self._setfile(gopts, ftype)
        return "rrdtool graph " + " ".join(gopts)


    def graphId(self, gopts, drange, ftype):
        import md5
        id = md5.new(''.join(gopts)).hexdigest() 
        id += str(drange) + '.' + ftype.lower()
        return id
    
    def _loadfile(self, filename):
        f = open(filename)
        graph = f.read()
        f.close()
        return graph


    def setupCache(self):
        """make new cache if we need one"""
        if not hasattr(self, '_v_cache') or not self._v_cache:
            tmpfolder = self.getPhysicalRoot().temp_folder
            if not hasattr(tmpfolder, self.cacheName):
                cache = PObjectCache(self.cacheName, self.cachetimeout)
                tmpfolder._setObject(self.cacheName, cache)
            self._v_cache = tmpfolder._getOb(self.cacheName)
        return self._v_cache


    def addGraph(self, id, filename):
        """add graph to temporary folder"""
        cache = self.setupCache()
        graph = self._loadfile(filename)
        cache.addToCache(id, graph)


    def getGraph(self, id, ftype, REQUEST):
        """get a previously generated graph"""
        cache = self.setupCache()
        ftype = ftype.lower()
        if REQUEST:
            response = REQUEST.RESPONSE
            response.setHeader('Content-Type', 'image/%s'%ftype)
        return cache.checkCache(id)


InitializeClass(RenderServer)

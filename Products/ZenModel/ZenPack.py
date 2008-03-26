###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007,2008 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import importClass, zenPath
from Products.ZenUtils.Version import getVersionTupleFromString
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPackLoader import *
from AccessControl import ClassSecurityInfo
from ZenossSecurity import ZEN_MANAGE_DMD
import exceptions
import pkg_resources
import string
import subprocess
from Acquisition import aq_parent
import os, sys

__doc__="ZenPacks base definitions"


class ZenPackException(exceptions.Exception):
    pass

class ZenPackNotFoundException(ZenPackException):
    pass

class ZenPackDuplicateNameException(ZenPackException):
    pass

class ZenPackNeedMigrateException(ZenPackException):
    pass

class ZenPackDependentsException(ZenPackException):
    pass

class ZenPackDevelopmentModeExeption(ZenPackException):
    pass



def eliminateDuplicates(objs):
    def compare(x, y):
        return cmp(x.getPrimaryPath(), y.getPrimaryPath())
    objs.sort(compare)
    result = []
    for obj in objs:
        for alreadyInList in result:
            path = alreadyInList.getPrimaryPath()
            if obj.getPrimaryPath()[:len(path)] == path:
                break
        else:
            result.append(obj)
    return result


class ZenPackMigration:
    version = Version(0, 0, 0)
    
    def migrate(self, pack): pass
    
    def recover(self, pack): pass


class ZenPack(ZenModelRM):
    '''The root of all ZenPacks: has no implementation,
    but sits here to be the target of the Relation'''

    objectPaths = None
    
    # Metadata
    version = '0.1'
    author = ''
    organization = ''
    url = ''
    license = ''

    # New-style zenpacks (eggs) have this set to True when they are
    # first installed
    eggPack = False
                        
    # isDevelopment indicates that the zenpack can be exported
    # and that objects can be added to it.  Also allows editing on
    # viewPackDetail.pt
    development = False

    requires = () # deprecated

    loaders = (ZPLObject(), ZPLReport(), ZPLDaemons(), ZPLBin(), ZPLLibExec(),
                ZPLSkins(), ZPLDataSources(), ZPLLibraries(), ZPLAbout())
                
    _properties = ZenModelRM._properties + (
        {'id':'objectPaths','type':'lines','mode':'w'},
        {'id':'version', 'type':'string', 'mode':'w'},
        {'id':'author', 'type':'string', 'mode':'w'},
        {'id':'organization', 'type':'string', 'mode':'w'},
        {'id':'url', 'type':'string', 'mode':'w'},
        {'id':'license', 'type':'string', 'mode':'w'},
    )

    _relations =  (
        # root is deprecated, use manager now instead
        # root should be removed post zenoss 2.2
        ('root', ToOne(ToManyCont, 'Products.ZenModel.DataRoot', 'packs')),
        ('manager', 
            ToOne(ToManyCont, 'Products.ZenModel.ZenPackManager', 'packs')),
        ("packables", ToMany(ToOne, "Products.ZenModel.ZenPackable", "pack")),
        )

    factory_type_information = (
        { 'immediate_view' : 'viewPackDetail',
          'factory'        : 'manage_addZenPack',
          'actions'        :
          (
           { 'id'            : 'viewPackDetail'
             , 'name'          : 'Detail'
             , 'action'        : 'viewPackDetail'
             , 'permissions'   : ( "Manage DMD", )
             },
           )
          },
        )

    packZProperties = [
        ]

    security = ClassSecurityInfo()


    def __init__(self, id, title=None, buildRelations=True):
        #self.dependencies = {'zenpacksupport':''}
        self.dependencies = {}
        ZenModelRM.__init__(self, id, title, buildRelations)


    def install(self, app):
        #self.stopDaemons()
        for loader in self.loaders:
            loader.load(self, app)
        self.createZProperties(app)
        #self.startDaemons()


    def upgrade(self, app):
        #self.stopDaemons()
        for loader in self.loaders:
            loader.upgrade(self, app)
        self.createZProperties(app)
        self.migrate()
        #self.startDaemons()


    def remove(self, app, leaveObjects=False):
        #self.stopDaemons()
        for loader in self.loaders:
            loader.unload(self, app)
        self.removeZProperties(app)
        self.removeCatalogedObjects(app)
        

    def migrate(self):
        instances = []
        # find all the migrate modules
        root = self.path("migrate")
        for p, ds, fs in os.walk(root):
            for f in fs:
                if f.endswith('.py') and not f.startswith("__"):
                    path = os.path.join(p[len(root) + 1:], f)
                    log.debug("Loading %s", path)
                    sys.path.insert(0, p)
                    try:
                        try:
                            c = importClass(path[:-3].replace("/", "."))
                            instances.append(c())
                        finally:
                            sys.path.remove(p)
                    except ImportError, ex:
                        log.exception("Problem loading migration step %s", path)
        # sort them by version number
        instances.sort()
        # install those that are newer than our pack version
        current = getVersionTupleFromString(self.version)
        recover = []
        try:
            for instance in instances:
                if instance.version >= current:
                    recover.append(instance)
                    instance.migrate(self)
        except Exception, ex:
            # give the pack a chance to recover from problems
            recover.reverse()
            for r in recover:
                r.recover(self)
            raise ex


    def list(self, app):
        result = []
        for loader in self.loaders:
            result.append((loader.name,
                           [item for item in loader.list(self, app)]))
        return result
        
        
    def createZProperties(self, app):
        for name, value, pType in self.packZProperties:
            if not app.zport.dmd.Devices.hasProperty(name):
                app.zport.dmd.Devices._setProperty(name, value, pType)
        
        
    def removeZProperties(self, app):
        for name, value, pType in self.packZProperties:
            app.zport.dmd.Devices._delProperty(name)


    def removeCatalogedObjects(self, app):
        """
        Delete all objects in the zenPackPersistence catalog that are
        associated with this zenpack.
        """
        objects = self.getCatalogedObjects()
        for o in objects:
            parent = aq_parent(o)
            if parent:
                parent._delObject(o.id)


    def getCatalogedObjects(self):
        """
        Return a list of objects from the ZenPackPersistence catalog
        for this zenpack.
        """
        from ZenPackPersistence import GetCatalogedObjects
        return GetCatalogedObjects(self.dmd, self.id) or []


    def zmanage_editProperties(self, REQUEST, redirect=False):
        """
        Edit a ZenPack object
        """
        
        if self.isEggPack():
            # Handle the dependencies fields and recreate self.dependencies
            newDeps = {}
            depNames = REQUEST.get('dependencies', [])
            if not isinstance(depNames, list):
                depNames = [depNames]
            #depNames.insert(0, 'zenpacksupport')
            newDeps = {}
            for depName in depNames:
                vers = REQUEST.get('version_%s' % depName, '').strip()
                if vers and vers[0] in string.digits:
                    vers = '==' + vers
                try:
                    gen = pkg_resources.parse_requirements(depName + vers)
                    [r for r in gen]
                except ValueError:
                    REQUEST['message'] = '%s is not a valid ' % vers + \
                                            'version specification'
                    return self.callZenScreen(REQUEST)
                newDeps[depName] = vers
            self.dependencies = newDeps

        result =  ZenModelRM.zmanage_editProperties(self, REQUEST, redirect)
        
        if self.isEggPack():
            self.writeSetupValues()
            self.buildEggInfo()
        return result


    def manage_deletePackable(self, packables=(), REQUEST=None):
        "Delete objects from this ZenPack"
        from sets import Set
        packables = Set(packables)
        for obj in self.packables():
            if obj.getPrimaryUrlPath() in packables:
                self.packables.removeRelation(obj)
        if REQUEST: 
            REQUEST['message'] = 'Deleted objects from ZenPack %s' % self.id 
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_exportPack')
    def manage_exportPack(self, download="no", REQUEST=None):
        """
        Export the ZenPack to the /export directory
        """
        if not self.isDevelopment():
            msg = 'Only ZenPacks installed in development mode can be exported.'
            if REQUEST:
                REQUEST['message'] = msg
                return self.callZenScreen(REQUEST)
            raise ZenPackDevelopmentModeExeption(msg)

        from StringIO import StringIO
        xml = StringIO()
        
        # Write out packable objects
        xml.write("""<?xml version="1.0"?>\n""")
        xml.write("<objects>\n")
        packables = eliminateDuplicates(self.packables())
        for obj in packables:
            # obj = aq_base(obj)
            xml.write('<!-- %r -->\n' % (obj.getPrimaryPath(),))
            obj.exportXml(xml,['devices','networks','pack'],True)
        xml.write("</objects>\n")
        path = self.path('objects')
        if not os.path.isdir(path):
            os.mkdir(path, 0750)
        objects = file(os.path.join(path, 'objects.xml'), 'w')
        objects.write(xml.getvalue())
        objects.close()
        
        # Create skins dir if not there
        path = self.path('skins')
        if not os.path.isdir(path):
            os.makedirs(path, 0750)
            
        # Create __init__.py
        init = self.path('__init__.py')
        if not os.path.isfile(init):
            fp = file(init, 'w')
            fp.write(
'''
import Globals
from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory("skins", globals())
''')
            fp.close()
        
        if self.isEggPack():
            # Create the egg
            exportDir = zenPath('export')
            if not os.path.isdir(exportDir):
                os.makedirs(exportDir, 0750)
            eggPath = self.eggPath()
            os.chdir(eggPath)
            if os.path.isdir(os.path.join(eggPath, 'dist')):
                os.system('rm -rf dist/*')
            p = subprocess.Popen('python setup.py bdist_egg',
                            stderr=sys.stderr,
                            shell=True,
                            cwd=eggPath)
            p.wait()
            os.system('cp dist/* %s' % exportDir)
            exportFileName = self.eggName()
        else:
            # Create about.txt
            about = self.path(CONFIG_FILE)
            values = {}
            parser = ConfigParser.SafeConfigParser()
            if os.path.isfile(about):
                try:
                    parser.read(about)
                    values = dict(parser.items(CONFIG_SECTION_ABOUT))
                except ConfigParser.Error:
                    pass
            current = [(p['id'], str(getattr(self, p['id'], '') or ''))
                        for p in self._properties]
            values.update(dict(current))
            if not parser.has_section(CONFIG_SECTION_ABOUT):
                parser.add_section(CONFIG_SECTION_ABOUT)
            for key, value in values.items():
                parser.set(CONFIG_SECTION_ABOUT, key, value)
            fp = file(about, 'w')
            try:
                parser.write(fp)
            finally:
                fp.close()
            # Create the zip file
            path = zenPath('export')
            if not os.path.isdir(path):
                os.makedirs(path, 0750)
            from zipfile import ZipFile, ZIP_DEFLATED
            zipFilePath = os.path.join(path, '%s.zip' % self.id)
            zf = ZipFile(zipFilePath, 'w', ZIP_DEFLATED)
            base = zenPath('Products')
            for p, ds, fd in os.walk(self.path()):
                if p.split('/')[-1].startswith('.'): continue
                for f in fd:
                    if f.startswith('.'): continue
                    if f.endswith('.pyc'): continue
                    filename = os.path.join(p, f)
                    zf.write(filename, filename[len(base)+1:])
                ds[:] = [d for d in ds if d[0] != '.']
            zf.close()
            exportFileName = '%s.zip' % self.id

        if REQUEST:
            if download == 'yes':
                REQUEST['doDownload'] = 'yes'
            REQUEST['message'] = 'ZenPack exported to $ZENHOME/export/%s' % (
                                                    exportFileName)
            return self.callZenScreen(REQUEST)
            
        return exportFileName


    def manage_download(self, REQUEST):
        """
        Download the already exported zenpack from $ZENHOME/export
        """
        if self.isEggPack():
            filename = self.eggName()
        else:
            filename = '%s.zip' % self.id
        path = os.path.join(zenPath('export'), filename)
        if os.path.isfile(path):
            REQUEST.RESPONSE.setHeader('content-type', 'application/zip')
            REQUEST.RESPONSE.setHeader('content-disposition',
                                        'attachment; filename=%s' %
                                        filename)
            zf = file(path, 'r')
            try:
                REQUEST.RESPONSE.write(zf.read())
            finally:
                zf.close()
        else:
            REQUEST['message'] = 'An error has occured, the ZenPack could not' \
                                ' be exported.'
            return self.callZenScreen(REQUEST)    
        

    def _getClassesByPath(self, name):
        dsClasses = []
        for path, dirs, files in os.walk(self.path(name)):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.') \
                        and f.endswith('.py') \
                        and not f == '__init__.py':
                    subPath = path[len(self.path()):]
                    parts = subPath.strip('/').split('/')
                    parts.append(f[:f.rfind('.')])
                    modName = '.'.join([self.moduleName()] + parts)
                    dsClasses.append(importClass(modName))
        return dsClasses

    def getDataSourceClasses(self):
        return self._getClassesByPath('datasources')

    def getThresholdClasses(self):
        return self._getClassesByPath('thresholds')

    def getFilenames(self):
        '''
        Get the filenames of a ZenPack exclude .svn, .pyc and .xml files 
        '''
        filenames = []
        for root, dirs, files in os.walk(self.path()):
            if root.find('.svn') == -1:
                    for f in files:
                        if not f.endswith('.pyc') \
                        and not f.endswith('.xml'):
                            filenames.append('%s/%s' % (root, f))
        return filenames


    def getDaemonNames(self):
        """
        Return a list of daemons in the daemon subdirectory that should be
        stopped/started before/after an install or an upgrade of the zenpack.
        """
        daemonsDir = os.path.join(self.path(), 'daemons')
        if os.path.isdir(daemonsDir):
            daemons = [f for f in os.listdir(daemonsDir) 
                        if os.path.isfile(os.path.join(daemonsDir,f))]
        else:
            daemons = []
        return daemons


    def stopDaemons(self):
        """
        Stop all the daemons provided by this pack.
        Called before an upgrade or a removal of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'stop')


    def startDaemons(self):
        """
        Start all the daemons provided by this pack.
        Called after an upgrade or an install of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'start')


    def restartDaemons(self):
        """
        Restart all the daemons provided by this pack.
        Called after an upgrade or an install of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'restart')


    def path(self, *parts):
        """
        Return the path to the ZenPack module.
        It would be convenient to store the module name/path in the zenpack
        object, however this would make things more complicated when the
        name of the package under ZenPacks changed on us (do to a user edit.)
        """
        if self.isEggPack():
            module = self.getModule()
            return os.path.join(module.__path__[0], *[p.strip('/') for p in parts])
        return zenPath('Products', self.id, *parts)


    def isDevelopment(self):
        """
        Return True if this pack is installed in dev mode or if it's an
        old (non-egg) style zenpack which didn't differentiate between
        dev and non-dev zenpacks.
        """
        return self.development or not self.isEggPack()


    def isEggPack(self):
        """
        Return True if this is a new-style (egg) zenpack, false otherwise
        """
        return self.eggPack


    def moduleName(self):
        """
        Return the importable dotted module name for this zenpack.
        """
        if self.isEggPack():
            name = self.getModule().__name__
        else:
            name = 'Products.%s' % self.id
        return name


    ##########
    # Egg-related methods
    # Nothing below here should be called for old-style zenpacks
    ##########


    def writeSetupValues(self):
        """
        Write appropriate values to the setup.py file
        """
        if not self.isEggPack():
            raise ZenPackException('Calling writeSetupValues on non-egg zenpack.')
        attrs = {
            'version': 'version',
            'author': 'author',
            # 'author_email': 'authorEmail',
            # 'organization': 'organization',
            # 'description': 'description',
            # 'maintainer': 'maintainer',
            # 'maintainer_email': 'maintainerEmail',
            }
        
        setupPath = self.eggPath('setup.py')
        f = open(setupPath, 'r')
        setup = f.readlines()
        f.close()
        newSetup = []
        for line in setup:
            setting = line.split('=', 1)[0].strip()
            if setting in attrs.keys():
                newSetup.append("    %s = '%s',\n" % (setting, 
                                            getattr(self, attrs[setting], '')))
            elif setting == 'install_requires':
                oldDeps = eval(line.split('=', 1)[1].strip().strip(','))
                for i, d in enumerate(oldDeps):
                    if d.startswith('zenpacksupport'):
                        oldDeps[:i+1] = []
                        break
                newDeps = []
                for dName, dVers in self.dependencies.items():
                    d = '%s%s' % (dName, dVers)
                    if dName == 'zenpacksupport':
                        newDeps.append(d)
                    else:
                        newDeps.insert(0, d)
                newDeps += oldDeps
                newSetup.append('    install_requires = %s,\n' % `newDeps`)
            else:
                newSetup.append(line)
        f = open(setupPath, 'w')
        f.writelines(newSetup)
        f.close()


    def buildEggInfo(self):
        """
        Rebuild the egg info to update dependencies, etc
        """
        p = subprocess.Popen('python setup.py egg_info',
                        stderr=sys.stderr,
                        shell=True,
                        cwd=self.eggPath())
        p.wait()


    def getDistribution(self):
        """
        Return the distribution that provides this zenpack
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getDistribution on non-egg zenpack.')
        return pkg_resources.get_distribution(self.id)


    def getEntryPoint(self):
        """
        Return a tuple of (packName, packEntry) that comes from the
        distribution entry map for zenoss.zenopacks.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getEntryPoints on non-egg zenpack.')
        dist = self.getDistribution()
        entryMap = pkg_resources.get_entry_map(dist, 'zenoss.zenpacks')
        if not entryMap or len(entryMap) > 1:
            raise ZenPackException('A ZenPack egg must contain exactly one' 
                    ' zenoss.zenpacks entry point.  This egg appears to contain' 
                    ' %s such entry points.' % len(entryMap))
        packName, packEntry = entryMap.items()[0]
        return (packName, packEntry)


    def getModule(self):
        """
        Get the loaded module from the given entry point.  if not packEntry
        then retrieve it.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getModule on non-egg zenpack.')        
        _, packEntry = self.getEntryPoint()
        return packEntry.load()


    def eggPath(self, *parts):
        """
        Return the path to the egg supplying this zenpack
        """
        if not self.isEggPack():
            raise ZenPackException('Calling eggPath on non-egg zenpack.')
        d = self.getDistribution()
        return os.path.join(d.location, *[p.strip('/') for p in parts])


    def eggName(self):
        if not self.isEggPack():
            raise ZenPackException('Calling eggName on non-egg zenpack.')
        d = self.getDistribution()
        return d.egg_name() + '.egg'


    def shouldDeleteFilesOnRemoval(self):
        """
        Return True if the egg itself should be deleted when this ZenPack
        is removed from Zenoss.
        If the ZenPack is in development mode and if it lives outside
        $ZENHOME/ZenPackDev then don't delete, otherwise do delete.
        This logic is based on the assumed case where anything in ZenPackDev
        was likely created through the gui, where eggs outside it are more
        likely to be created by hand.  Packs created from the GUI should be
        deleted without any trace because they likely contain only db objects
        and no code per se.  
        """
        if self.isDevelopment():
            eggPath = self.eggPath()
            oneFolderUp = eggPath[:eggPath.rfind('/')-1]
            if oneFolderUp == zenPath('ZenPackDev'):
                delete = True
            else:
                delete = False
        else:
            delete = True
        return delete


    def getPackageName(self):
        """
        Return the name of submodule of zenpacks that contains this zenpack.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getPackageName on a non-egg '
                                        'zenpack')
        modName = self.moduleName()
        return modName.split('.')[1]


    def getEligibleDependencies(self):
        """
        Return a list of installed zenpacks that could be listed as
        dependencies for this zenpack
        """
        return [zp for zp in self.dmd.ZenPackManager.packs()
                    if zp.id != self.id
                    and zp.isEggPack()]

    # def getDependentZenPacks(self):
    #     """
    #     Return a list of ZenPacks that have this zenpack as a
    #     dependency.
    #     """
    #     return [p for p in self.dmd.ZenPackManager.packs()
    #             if p.isEggPack()
    #             and self.id in p.dependencies.keys()]


# ZenPackBase is here for backwards compatibility with older installed
# zenpacks that used it.  ZenPackBase was rolled into ZenPack when we
# started using about.txt files instead of ZenPack subclasses to set
# zenpack metadata.
ZenPackBase = ZenPack

InitializeClass(ZenPack)

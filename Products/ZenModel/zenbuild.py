###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""zenbuild

Build the zentinel portal object and the dmd database

$Id: DmdBuilder.py,v 1.11 2004/04/06 22:33:07 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

import os
import Globals
import transaction
import subprocess

from Products.ZenUtils.Utils import zenPath

from Products.ZenUtils import Security
from Products.ZenUtils.CmdBase import CmdBase
from Products.PluggableAuthService import plugins
from MySQLdb import OperationalError

class zenbuild(CmdBase):

    sitename = "zport"

    def connect(self):
        zopeconf = zenPath("etc/zope.conf")
        import Zope2
        Zope2.configure(zopeconf)
        self.app = Zope2.app()

    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('--xml', dest="fromXml",
                action='store_true', default=False,
                help="Load data from XML files instead of SQL")
        self.parser.add_option('-s','--evthost', dest="evthost",
                default="127.0.0.1", help="events database hostname")
        self.parser.add_option('-u','--evtuser', dest="evtuser", default="root",
                help="username used to connect to the events database")
        self.parser.add_option('-p','--evtpass', dest="evtpass", default="",
                help="password used to connect to the events database")
        self.parser.add_option('-d','--evtdb', dest="evtdb", default="events",
                help="name of events database")
        self.parser.add_option('-t','--evtport', dest="evtport",
                type='int', default=3306,
                help="port used to connect to the events database")
        self.parser.add_option('--smtphost', dest="smtphost", default="localhost",
                help="smtp host")
        self.parser.add_option('--smtpport', dest="smtpport", default=25,
                help="smtp port")
        self.parser.add_option('--cachesize',
                    dest="cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of MySQL object store")
        self.parser.add_option('--port',
                    dest="port", type="int", default=3306,
                    help="port of MySQL object store")
        self.parser.add_option('--mysqluser', dest='mysqluser', default='zenoss',
                    help='username for MySQL object store')
        self.parser.add_option('--mysqlpasswd', dest='mysqlpasswd', default='zenoss',
                    help='passwd for MySQL object store')
        self.parser.add_option('--mysqldb', dest='mysqldb', default='zodb',
                    help='Name of database for MySQL object store')
        self.parser.add_option('--cacheservers', dest='cacheservers',
                    default="127.0.0.1:11211",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        self.parser.add_option('--pagecommand', dest="pagecommand", default="$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT",
                help="page command")
        # amqp stuff
        self.parser.add_option('--amqphost', dest="amqphost", default="localhost",
                               help="AMQP Host Location")
        self.parser.add_option('--amqpport', dest="amqpport", default=5672,
                               help="AMQP Server Port")
        self.parser.add_option('--amqpvhost', dest="amqpvhost", default="/zenoss",
                               help="Default Virtual Host")
        self.parser.add_option('--amqpuser', dest="amqpuser", default="zenoss",
                               help="AMQP User Name")
        self.parser.add_option('--amqppassword', dest="amqppassword", default="zenoss",
                               help="AMQP Password")

    def zodbConnect(self):
        """
        Used to connect to ZODB (without going through the entire ZOPE
        initialization process. This allows us to get a lightweight
        connection to the database to test to see if the database is already
        initialized.
        """
        self.options.port = self.options.port or 3306
        from relstorage.storage import RelStorage
        from relstorage.adapters.mysql import MySQLAdapter
        adapter = MySQLAdapter(
            host=self.options.host,
            port=self.options.port,
            user=self.options.mysqluser,
            passwd=self.options.mysqlpasswd,
            db=self.options.mysqldb
        )
        self.storage = RelStorage(adapter)
        from ZODB import DB
        self.db = DB(self.storage, cache_size=self.options.cachesize)

    def build(self):
        mysqlcmd = ['mysql', '-u', self.options.mysqluser]
        if self.options.mysqlpasswd:
            mysqlcmd.append('-p%s' % self.options.mysqlpasswd)
        mysqlcmd.extend([
            '-h', self.options.host,
            '--port', str(self.options.port)
        ])

        mysqlcmd = subprocess.list2cmdline(mysqlcmd)

        conn = None
        try:
            self.zodbConnect()
            conn = self.db.open()
            root = conn.root()
            app = root.get('Application')
            if app and getattr(app, self.sitename, None) is not None:
                print "zport portal object exists; exiting."
                return
        except OperationalError, e:
            if 'Unknown database' in e[1]:
                queries = (
                    'CREATE DATABASE %s;' % self.options.mysqldb,
                    "GRANT ALL ON %s.* TO %s@'%s' IDENTIFIED BY '%s';" % (
                        self.options.mysqldb, self.options.mysqluser,
                        self.options.host, self.options.mysqlpasswd),
                    "GRANT ALL ON %s.* TO %s@'%%' IDENTIFIED BY '%s';" % (
                        self.options.mysqldb, self.options.mysqluser,
                        self.options.mysqlpasswd),
                    "FLUSH PRIVILEGES;"
                )

                for query in queries:
                    cmd = mysqlcmd + ' -e "%s"' % query
                    os.system(cmd)
            else:
                raise
        finally:
            if conn:
                conn.close()
            if self.db:
                self.db.close()
                self.db = None
            if self.storage:
                self.storage.close()
                self.storage = None

        if self.options.fromXml:
            self.connect()
            from Products.ZenModel.ZentinelPortal import manage_addZentinelPortal
            manage_addZentinelPortal(self.app, self.sitename)
            site = self.app._getOb(self.sitename)

            # build index_html
            if self.app.hasObject('index_html'):
                self.app._delObject('index_html')
            from Products.PythonScripts.PythonScript import manage_addPythonScript
            manage_addPythonScript(self.app, 'index_html')
            newIndexHtml = self.app._getOb('index_html')
            text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
            newIndexHtml.ZPythonScript_edit('', text)

            # build standard_error_message
            if self.app.hasObject('standard_error_message'):
                self.app._delObject('standard_error_message')
            file = open(zenPath('Products/ZenModel/dtml/standard_error_message.dtml'))
            try:
                text = file.read()
            finally:
                file.close()
            import OFS.DTMLMethod
            OFS.DTMLMethod.addDTMLMethod(self.app, id='standard_error_message',
                                            file=text)

            # Convert the acl_users folder at the root to a PAS folder and update
            # the login form to use the Zenoss login form
            Security.replaceACLWithPAS(self.app, deleteBackup=True)

            # Add groupManager to zport.acl
            acl = site.acl_users
            if not hasattr(acl, 'groupManager'):
                plugins.ZODBGroupManager.addZODBGroupManager(acl, 'groupManager')
            acl.groupManager.manage_activateInterfaces(['IGroupsPlugin',])

            trans = transaction.get()
            trans.note("Initial ZentinelPortal load by zenbuild.py")
            trans.commit()
            print "ZentinelPortal loaded at %s" % self.sitename

            # build dmd
            from Products.ZenModel.DmdBuilder import DmdBuilder
            dmdBuilder = DmdBuilder(site,
                                    self.options.evthost,
                                    self.options.evtuser,
                                    self.options.evtpass,
                                    self.options.evtdb,
                                    self.options.evtport,
                                    self.options.smtphost,
                                    self.options.smtpport,
                                    self.options.pagecommand)
            dmdBuilder.build()
            transaction.commit()

            # Load XML Data
            from Products.ZenModel.XmlDataLoader import XmlDataLoader
            dl = XmlDataLoader(noopts=True, app=self.app)
            dl.loadDatabase()

        else:

            mysqlcmd += ' %s' % self.options.mysqldb

            cmd = 'cat $ZENHOME/Products/ZenModel/data/zodb.sql.gz | gzip -c -d | %s' % mysqlcmd
            os.system(cmd)

            # Relstorage may have already loaded items into the cache in the
            # initial connection to the database. We have to expire everything
            # in the cache in order to prevent errors with overlapping
            # transactions from the model which was just imported above.
            if self.options.cacheservers:
                self.flush_memcached(self.options.cacheservers.split())

            self.connect()

            # Set all the attributes
            site = getattr(self.app, self.sitename, None)
            site.dmd.smtpHost = self.options.smtphost
            site.dmd.smtpPort = self.options.smtpport
            site.dmd.pageCommand = self.options.pagecommand
            site.dmd.uuid = None
            site.dmd._rq = False
            for evmgr in (site.dmd.ZenEventManager, site.dmd.ZenEventHistory):
                evmgr.username = self.options.evtuser
                evmgr.password = self.options.evtpass
                evmgr.database = self.options.evtdb
                evmgr.host = self.options.evthost
                evmgr.port = self.options.evtport
            transaction.commit()

        # Update the global conf
        print "Updating global.conf"
        zenglobalconf = zenPath('bin', 'zenglobalconf')
        cmd = [zenglobalconf, '-u']
        for opt in ('host', 'port', 'mysqldb', 'mysqluser', 'mysqlpasswd',
                    'amqphost', 'amqpport', 'amqpvhost', 'amqpuser',
                    'amqppassword', 'cacheservers'):
            cmd.append('%s=%s' % (opt, getattr(self.options, opt)))
        subprocess.call(cmd)

        # Load reports
        from Products.ZenReports.ReportLoader import ReportLoader
        rl = ReportLoader(noopts=True, app=self.app)
        rl.loadDatabase()

    def flush_memcached(self, cacheservers):
        import memcache
        mc = memcache.Client(cacheservers, debug=0)
        mc.flush_all()
        mc.disconnect_all()

if __name__ == "__main__":
    zb = zenbuild()
    zb.build()

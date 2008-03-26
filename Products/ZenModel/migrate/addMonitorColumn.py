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

__doc__='Add colums monitor column to status and history tables'

import Migrate
from MySQLdb import OperationalError
import logging
log = logging.getLogger("zen.migrate")

from MySQLdb.constants import ER
MYSQL_ERROR_TRIGGER_DOESNT_EXIST = 1360

trigger = """
    CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history SET
            dedupid=OLD.dedupid,
            evid=OLD.evid,
            device=OLD.device,
            component=OLD.component,
            eventClass=OLD.eventClass,
            eventKey=OLD.eventKey,
            summary=OLD.summary,
            message=OLD.message,
            severity=OLD.severity,
            eventState=OLD.eventState,
            eventClassKey=OLD.eventClassKey,
            eventGroup=OLD.eventGroup,
            stateChange=OLD.stateChange,
            firstTime=OLD.firstTime,
            lastTime=OLD.lastTime,
            count=OLD.count,
            prodState=OLD.prodState,
            suppid=OLD.suppid,
            manager=OLD.manager,
            agent=OLD.agent,
            DeviceCLass=OLD.DeviceClass,
            Location=OLD.Location,
            Systems=OLD.Systems,
            DeviceGroups=OLD.DeviceGroups,
            ipAddress=OLD.ipAddress,
            facility=OLD.facility,
            priority=OLD.priority,
            ntevid=OLD.ntevid,
            ownerid=OLD.ownerid,
            deletedTime=NULL,
            clearid=OLD.clearid,
            DevicePriority=OLD.DevicePriority,
            eventClassMapping=OLD.eventClassMapping,
            monitor=OLD.monitor
            ;
            """
            



class AddMonitorColumn(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        zem = dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            for table in ('status', 'history'):
                try:
                    curs.execute('alter table %s ' % table +
                                'add column monitor '
                                'varchar(128) default ""')
                except OperationalError, e:
                    if e[0] != ER.DUP_FIELDNAME:
                        raise
            try:
                curs.execute('drop trigger status_delete')
            except OperationalError, e:
                if e[0] != MYSQL_ERROR_TRIGGER_DOESNT_EXIST:
                    raise
            curs.execute(trigger)
            zem.loadSchema()
        finally: zem.close(conn)

AddMonitorColumn()

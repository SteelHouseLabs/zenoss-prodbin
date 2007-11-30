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

__doc__='''

Add a DevicePriority column to the status and history tables

'''

__version__ = "$Revision$"[11:-2]

import Migrate
from MySQLdb import OperationalError
from MySQLdb.constants import ER
MYSQL_ERROR_TRIGGER_DOESNT_EXIST = 1360

trigger = """
    CREATE TRIGGER status_delete BEFORE DELETE ON status
    FOR EACH ROW INSERT INTO history VALUES (
            OLD.dedupid,
            OLD.evid,
            OLD.device,
            OLD.component,
            OLD.eventClass,
            OLD.eventKey,
            OLD.summary,
            OLD.message,
            OLD.severity,
            OLD.eventState,
            OLD.eventClassKey,
            OLD.eventGroup,
            OLD.stateChange,
            OLD.firstTime,
            OLD.lastTime,
            OLD.count,
            OLD.prodState,
            OLD.suppid,
            OLD.manager,
            OLD.agent,
            OLD.DeviceClass,
            OLD.Location,
            OLD.Systems,
            OLD.DeviceGroups,
            OLD.ipAddress,
            OLD.facility,
            OLD.priority,
            OLD.ntevid,
            OLD.ownerid,
            NULL,
            OLD.clearid,
            OLD.DevicePriority
            )"""
            


class DevicePriority(Migrate.Step):
    "Add a DevicePriority column to the status and history tables"
    version = Migrate.Version(1, 1, 0)

    def cutover(self, unused):
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            cmd = 'ALTER TABLE %s ADD COLUMN ' + \
                  '(DevicePriority smallint(6) default 3)'
            for table in ('status', 'history'):
                try:
                    curs.execute(cmd % table)
                except OperationalError, e:
                    if e[0] != ER.DUP_FIELDNAME:
                        raise
            try:
                curs.execute('DROP TRIGGER status_delete')
            except OperationalError, e:
                if e[0] != MYSQL_ERROR_TRIGGER_DOESNT_EXIST:
                    raise
            curs.execute(trigger)
        finally: zem.close(conn)

DevicePriority()

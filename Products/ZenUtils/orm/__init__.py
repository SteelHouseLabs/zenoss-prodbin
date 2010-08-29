#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
from sqlalchemy import create_engine
import meta

session = meta.Session

import logging
log = logging.getLogger('zen.ORM')

model_ready = False
def init_model(user="zenoss", passwd="zenoss", host="localhost", port="3306",
               db="events"):
    """
    Call at startup.
    """
    global model_ready
    if not model_ready:
        meta.engine = create_engine(
            ('mysql://%(user)s:%(passwd)s@%(host)s:%(port)s'
             '/%(db)s?charset=utf8') % locals(),
            pool_recycle=60)
        meta.metadata.bind = meta.engine
        meta.Session.configure(autoflush=False, autocommit=True, binds={
            meta.metadata:meta.engine
        })
        model_ready = True


class nested_transaction(object):
    """
    Context manager for managing commit and rollback on error. Example usage:

    with nested_transaction() as session:
        ob = ModelItem()
        session.add_all([ob])

    It'll be committed for you and rolled back if there's a problem.
    """
    def __enter__(self):
        if session.is_active:
            session.begin_nested()
        else:
            session.begin(subtransactions=True)
        return session

    def __exit__(self, type, value, traceback):
        if type is not None:
            # Error occurred
            log.exception(value)
            log.debug('Rolling back')
            session.rollback()
            raise type(value)
        else:
            try:
                log.debug('Committing nested transaction')
                session.commit()
            except Exception, e:
                log.exception(e)
                log.debug('Rolling back after attempted commit')
                session.rollback()
                raise
        return False

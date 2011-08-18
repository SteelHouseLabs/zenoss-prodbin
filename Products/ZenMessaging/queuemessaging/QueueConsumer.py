###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


import Globals
import logging
from zope.component import getUtility
from twisted.internet import defer
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.twisted.amqp import AMQPFactory
from interfaces import IQueueConsumerTask

log = logging.getLogger('zen.queueconsumer')


class QueueConsumer(object):
    """
    Listens to the model change queue and translates the
    events into graph protobufs
    """
    MARKER = str(hash(object()))

    def __init__(self, task, dmd, amqpConnectionInfo=None, queueSchema=None):
        self.dmd = dmd
        if not amqpConnectionInfo:
            amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        if not queueSchema:
            queueSchema = getUtility(IQueueSchema)
        self.consumer = AMQPFactory(amqpConnectionInfo, queueSchema)
        self.onReady = self._ready()
        self.onShutdown = self._shutdown()
        self.onTestMessage = defer.Deferred()
        if not IQueueConsumerTask.providedBy(task):
            raise AssertionError("%s does not implement IQueueConsumerTask" % task)
        self.task = task
        self.task.dmd = self.dmd
        # give a reference to the consumer to the task
        self.task.queueConsumer = self


    @defer.inlineCallbacks
    def _ready(self):
        """
        Calls back once everything's ready and test message went through.
        """
        yield self.consumer.onConnectionMade
        yield self.onTestMessage
        log.info('Queue consumer ready.')
        defer.returnValue(None)

    @defer.inlineCallbacks
    def _shutdown(self):
        """
        Calls back once everything has shut down.
        """
        yield self.consumer.onConnectionLost
        defer.returnValue(None)

    def run(self):
        """
        Tell all the services to start up. Begin listening for queue messages.
        """
        log.debug("listening to zenoss.queues.impact.modelchange queue")
        task = self.task
        self.consumer.listen(task.queue, callback=task.processMessage)
        return self.onReady

    def shutdown(self, *args):
        """
        Tell all the services to shut down.
        """
        self.consumer.shutdown()
        return self.onShutdown

    def acknowledge(self, message):
        """
        Called from a task when it is done successfully processing
        the message
        """
        self.consumer.acknowledge(message)

    def publishMessage(self, exchange, routing_key, message):
        """
        Publishes a message to another queue. This is for tasks that are both
        consumers and producers.
        """
        return self.consumer.send(exchange,
                           routing_key,
                           message )

    def syncdb(self):
        self.dmd.getPhysicalRoot()._p_jar.sync()





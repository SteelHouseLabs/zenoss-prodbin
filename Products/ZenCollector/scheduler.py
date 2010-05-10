###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import random

"""
Support for scheduling tasks and running them on a periodic interval. Tasks
are associated directly with a device, but multiple tasks may exist for a
single device or other monitored object.
"""

import logging
import math
import signal
import time

import zope.interface

from twisted.internet import defer, reactor, task
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import IScheduler, IScheduledTask
from Products.ZenCollector.tasks import TaskStates
from Products.ZenUtils.Utils import dumpCallbacks

#
# creating a logging context for this module to use
#
log = logging.getLogger("zen.collector.scheduler")


class StateStatistics(object):
    def __init__(self, state):
        self.state = state
        self.reset()

    def addCall(self, elapsedTime):
        self.totalElapsedTime += elapsedTime
        self.totalElapsedTimeSquared += elapsedTime ** 2
        self.totalCalls += 1

        if self.totalCalls == 1:
            self.minElapsedTime = elapsedTime
            self.maxElapsedTime = elapsedTime
        else:
            self.minElapsedTime = min(self.minElapsedTime, elapsedTime)
            self.maxElapsedTime = max(self.maxElapsedTime, elapsedTime)

    def reset(self):
        self.totalElapsedTime = 0.0
        self.totalElapsedTimeSquared = 0.0
        self.totalCalls = 0
        self.minElapsedTime = 0xffffffff
        self.maxElapsedTime = 0

    @property
    def mean(self):
        return float(self.totalElapsedTime) / float(self.totalCalls)

    @property
    def stddev(self):
        if self.totalCalls == 1:
            return 0
        else:
            # see http://www.dspguide.com/ch2/2.htm for stddev of running stats
            return math.sqrt((self.totalElapsedTimeSquared - self.totalElapsedTime ** 2 / self.totalCalls) / (self.totalCalls - 1))


class TaskStatistics(object):
    def __init__(self, task):
        self.task = task
        self.totalRuns = 0
        self.failedRuns = 0
        self.missedRuns = 0
        self.states = {}
        self.stateStartTime = None

    def trackStateChange(self, oldState, newState):
        now = time.time()

        # record how long we spent in the previous state, if there was one
        if oldState is not None and self.stateStartTime:
            # TODO: how do we properly handle clockdrift or when the clock
            # changes, or is time.time() independent of that?
            elapsedTime = now - self.stateStartTime
            previousState = newState

            if not self.states.has_key(oldState):
                stats = StateStatistics(oldState)
                self.states[oldState] = stats
            stats = self.states[oldState]
            stats.addCall(elapsedTime)

        self.stateStartTime = now


class CallableTaskFactory(object):
    """
    Our CallableTaskFactory just returns this module's CallableTask, instead
    of the one in Core.
    """
    def getCallableTask(self, newTask, scheduler):
        return CallableTask(newTask, scheduler)


class CallableTask(object):
    """
    A CallableTask wraps an object providing IScheduledTask so that it can be
    treated as a callable object. This allows the scheduler to make use of the
    Twisted framework's LoopingCall construct for simple interval-based
    scheduling.
    """
    def __init__(self, task, scheduler):
        if not IScheduledTask.providedBy(task):
            raise TypeError("task must provide IScheduledTask")
        else:
            self.task = task

        self._scheduler = scheduler
        self.paused = False
        self.taskStats = None

    def running(self):
        """
        Called whenever this task is being run.
        """
        self.taskStats.totalRuns += 1

    def finished(self, result):
        """
        Called whenever this task has finished.
        """
        if isinstance(result, Failure):
            self.taskStats.failedRuns += 1

    def late(self):
        """
        Called whenever this task is late and missed its scheduled run time.
        """
        # TODO: report an event
        self.taskStats.missedRuns += 1

    def __call__(self):
        if self.task.state is TaskStates.STATE_PAUSED and not self.paused:
            self.task.state = TaskStates.STATE_IDLE

        if self.task.state is TaskStates.STATE_IDLE:
            if self.paused:
                self.task.state = TaskStates.STATE_PAUSED
            else:
                d = defer.maybeDeferred(self._run)
                d.addBoth(self._finished)
                # don't return the Deferred because we want LoopingCall to keep
                # rescheduling so that we can keep track of late intervals

                # dump the deferred chain if we're in ludicrous debug mode
                if log.getEffectiveLevel() < logging.DEBUG:
                    print "Callback Chain for Task %s" % self.task.name
                    dumpCallbacks(d)

        else:
            self._late()

    def _run(self):
        self.task.state = TaskStates.STATE_RUNNING
        self.running()
        return self.task.doTask()

    def _finished(self, result):
        log.debug("Task %s finished, result: %r", self.task.name, 
                  result)

        # Make sure we always reset the state to IDLE once the task is
        # finished, regardless of what the outcome was.
        self.task.state = TaskStates.STATE_IDLE

        self._scheduler.taskDone(self.task.name)

        self.finished(result)
        # We handled any error; eat the result!

    def _late(self):
        log.debug("Task %s skipped because it was not idle", 
                  self.task.name)
        self.late()

class CallableTaskFactory(object):
    """
    A factory that creates instances of CallableTask, allowing it to be
    easily subclassed or replaced in different scheduler implementations.
    """
    def getCallableTask(self, newTask, scheduler):
        return CallableTask(newTask, scheduler)


class Scheduler(object):
    """
    A simple interval-based scheduler that makes use of the Twisted framework's
    LoopingCall construct.
    """

    zope.interface.implements(IScheduler)

    CLEANUP_TASKS_INTERVAL = 10 # seconds

    def __init__(self, callableTaskFactory=CallableTaskFactory()):
        self._loopingCalls = {}
        self._tasks = {}
        self._taskCallback = {}
        self._taskStats = {}
        self._callableTaskFactory = callableTaskFactory

        # create a cleanup task that will periodically sweep the 
        # cleanup dictionary for tasks that need to be cleaned
        self._tasksToCleanup = {}
        self._cleanupTask = task.LoopingCall(self._cleanupTasks)
        self._cleanupTask.start(Scheduler.CLEANUP_TASKS_INTERVAL)

    def addTask(self, newTask, callback=None, now=False):
        """
        Add a new IScheduledTask to the scheduler for execution.
        @param newTask the new task to schedule
        @type newTask IScheduledTask
        @param callback a callback to be notified each time the task completes
        @type callback a Python callable
        """
        if self._tasks.has_key(newTask.name):
            raise ValueError("Task %s already exists" % newTask.name)

        callableTask = self._callableTaskFactory.getCallableTask(newTask, self)
        loopingCall = task.LoopingCall(callableTask)
        self._loopingCalls[newTask.name] = loopingCall
        self._tasks[newTask.name] = callableTask
        self._taskCallback[newTask.name] = callback
        self.taskAdded(callableTask)

        # start the task using a callback so that its put at the bottom of
        # the Twisted event queue, to allow other processing to continue and
        # to support a task start-time jitter
        def _startTask(result):
            log.debug("Task %s starting on %d second intervals",
                      newTask.name, newTask.interval)
            loopingCall.start(newTask.interval)
        d = defer.Deferred()
        d.addCallback(_startTask)
        startDelay = 0
        if not now:
            startDelay = self._getStartDelay(newTask)
        reactor.callLater(startDelay, d.callback, None)

    def _getStartDelay(self, task):
        """
        amount of time to delay the start of a task. Prevents bunching up of 
        task execution when a large amount of tasks are scheduled at the same 
        time.
        """
        #simple delay of random number between 0 and half the task interval
        delay = random.randint(0, int(task.interval/2))
        return delay
    
    def taskAdded(self, taskWrapper):
        """
        Called whenever the scheduler adds a task.
        """
        task = taskWrapper.task

        # watch the task's state attribute changes
        task.attachAttributeObserver('state', self._taskStateChangeListener)

        # create the statistics data for this task
        self._taskStats[task.name] = TaskStatistics(task)
        taskWrapper.taskStats = self._taskStats[task.name]

    def taskRemoved(self, taskWrapper):
        """
        Called whenever the scheduler removes a task.
        """
        task = taskWrapper.task
        task.detachAttributeObserver('state', self._taskStateChangeListener)

    def taskPaused(self, taskWrapper):
        """
        Called whenever the scheduler pauses a task.
        """
        pass

    def taskResumed(self, taskWrapper):
        """
        Called whenever the scheduler resumes a task.
        """
        pass

    def removeTasksForConfig(self, configId):
        """
        Remove all tasks associated with the specified identifier.
        @param configId the identifier to search for
        @type configId string
        """
        doomedTasks = []
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Stopping task %s", taskName)

                if self._loopingCalls[taskName].running:
                    self._loopingCalls[taskName].stop()

                doomedTasks.append(taskName)
                self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            self._tasksToCleanup[taskName] = self._tasks[taskName].task

            del self._loopingCalls[taskName]
            del self._tasks[taskName]

            # TODO: ponder task statistics and keeping them around?

        # TODO: don't let any tasks for the same config start until
        # these old tasks are really gone

    def pauseTasksForConfig(self, configId):
        for (taskName, taskWrapper) in self._tasks.items():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Pausing task %s", taskName)
                taskWrapper.paused = True
                self.taskPaused(taskWrapper)

    def resumeTasksForConfig(self, configId):
        for (taskName, taskWrapper) in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Resuming task %s", taskName)
                taskWrapper.paused = False
                self.taskResumed(taskWrapper)

    def taskDone(self, taskName):
        if callable(self._taskCallback[taskName]):
            self._taskCallback[taskName](taskName=taskName)

    def _taskStateChangeListener(self, observable, attrName, oldValue, newValue):
        task = observable

        log.debug("Task %s changing state from %s to %s", task.name, oldValue,
                  newValue)

        taskStat = self._taskStats[task.name]
        taskStat.trackStateChange(oldValue, newValue)

    def displayStatistics(self, verbose):
        totalRuns = 0
        totalFailedRuns = 0
        totalMissedRuns = 0
        totalTasks = 0
        stateStats = {}

        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]

            totalTasks += 1
            totalRuns += taskStats.totalRuns
            totalFailedRuns += taskStats.failedRuns
            totalMissedRuns += taskStats.missedRuns

            for state, stats in taskStats.states.iteritems():
                if not stateStats.has_key(state):
                    stateStats[state] = StateStatistics(state)
                totalStateStats = stateStats[state]
                totalStateStats.totalElapsedTime += stats.totalElapsedTime
                totalStateStats.totalElapsedTimeSquared += stats.totalElapsedTimeSquared
                totalStateStats.totalCalls += stats.totalCalls
                totalStateStats.minElapsedTime = min(totalStateStats.minElapsedTime, stats.minElapsedTime)
                totalStateStats.maxElapsedTime = max(totalStateStats.maxElapsedTime, stats.maxElapsedTime)

        log.info("Tasks: %d Successful_Runs: %d Failed_Runs: %d Missed_Runs: %d",
                 totalTasks, totalRuns, totalFailedRuns, totalMissedRuns)

        if verbose:
            buffer = "Task States Summary:\n"
            buffer = self._displayStateStatistics(buffer, stateStats)

            buffer += "\nTasks:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                buffer += "%s Current State: %s Successful_Runs: %d Failed_Runs: %d Missed_Runs: %d\n" \
                    % (task.name, task.state, taskStats.totalRuns, 
                       taskStats.failedRuns, taskStats.missedRuns)

            buffer += "\nDetailed Task States:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                buffer = self._displayStateStatistics(buffer,
                                             taskStats.states,
                                             "%s " % task.name)
                buffer += "\n"

            log.info("Detailed Scheduler Statistics:\n%s", buffer)

        # TODO: the above logic doesn't print out any stats for the 'current'
        # state... i.e. enter the PAUSED state and wait there an hour, and 
        # you'll see no data

        # TODO: should we reset the statistics here, or do it on a periodic
        # interval, like once an hour or day or something?

    def _displayStateStatistics(self, buffer, stateStats, prefix=''):
        for state, stats in stateStats.iteritems():
            buffer += "%sState: %s Total: %d Total Elapsed: %.4f Min: %.4f Max: %.4f Mean: %.4f StdDev: %.4f\n" \
                % (prefix,
                   state, stats.totalCalls, stats.totalElapsedTime,
                   stats.minElapsedTime, stats.maxElapsedTime, stats.mean,
                   stats.stddev)
        return buffer

    def _cleanupTasks(self):
        """
        Periodically cleanup and tasks that have been queued up for such 
        activity.
        """
        # Build a list of the tasks that need to be cleaned up so that there
        # is no issue with concurrent modifications to the _tasksToCleanup
        # dictionary when tasks are quickly cleaned up.
        todoList = [task for task in self._tasksToCleanup.values()
                             if self._isTaskCleanable(task)]

        for task in todoList:
            # changing the state of the task will keep the next cleanup run
            # from processing it again
            task.state = TaskStates.STATE_CLEANING

            d = defer.maybeDeferred(task.cleanup)
            d.addBoth(self._cleanupTaskComplete, task)

    def _cleanupTaskComplete(self, result, task):
        """
        Twisted callback to remove a task from the cleanup queue once it has
        completed its cleanup work.
        """
        del self._tasksToCleanup[task.name]
        return result

    def _isTaskCleanable(self, task):
        """
        Determines if a task is able to be cleaned up or not.
        """
        return task.state in (TaskStates.STATE_IDLE, TaskStates.STATE_PAUSED)


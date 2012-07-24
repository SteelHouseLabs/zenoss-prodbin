##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import multiprocessing
import logging
import signal
import os
import sys

from time import sleep
from twisted.internet import reactor
from Products.ZenUtils.CmdBase import remove_args

log = logging.getLogger("zen.workers")

MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS = 5  # ask it nicely and wait.
MAX_SECONDS_TO_FORCE_KILL_WORKERS      = 5  # loop "kill -9" then give up.

def workersBuildOptions(parser, default=1):
    """
    Adds option for number or workers
    """
    parser.add_option('--workers',
                      type="int",
                      default=default,
                      help="The number of processing workers to run "
                           "(ignored when running in the foreground)")

def exec_worker():
    """
    used to create a worker for an existing zenoss daemon. Removes the
    "workers" and "daemon" sys args and replace the current process by
    executing sys args
    """
    argv = [sys.executable]
    # Remove unwanted parameters from worker processes
    argv.extend(remove_args(sys.argv[:], ['-D','--daemon'], ['--workers']))
    # Tell the worker process to log to the log file and not just to console
    argv.append('--duallog')
    try:
        os.execvp(argv[0], argv)
    except:
        log.exception("Failed to start process")

class ProcessWorkers(object):
    """
    class for starting and restarting Multiprocessing process from
    within a twisted reactor
    """
    def __init__(self, maxWorkers, workerTarget, workerName=None):
        self._maxWorkers = maxWorkers
        self._workerTarget = workerTarget
        self._workerName = workerName
        #keeps track of number of workers started and restarted
        self._workerCount = 0
        self._workers = []
        self._checking=False
        self._shutdown = False

    def _sigchldhandler(self, signum=None, frame=None):
        if not self._shutdown:
            log.debug("_sigchldhandler reactor checkworkers")
            reactor.callLater(1, self.checkWorkers)
        else:
            log.debug("_sigchldhandler: shutting down, skipping")

    def sendSignal(self, signum):
        for worker in self._workers:
            log.debug("Sending signal %s to %s" % (signum, worker.pid))
            os.kill(worker.pid, signum)
            
    def startWorkers(self):
        def _doStart():
            for i in xrange(self._maxWorkers):
                self._startWorker()
            log.debug("Registering SIGCHLD handler")
            signal.signal(signal.SIGCHLD, self._sigchldhandler)
        reactor.callWhenRunning(_doStart)


    def shutdown(self):
        """
        Workers can be in one of four states:
             Not fully started yet        -- is_alive False, ignores SIGTERM, can't SIGKILL
             Started but not initialized  -- is_alive True,  ignores SIGTERM, can SIGKILL
             Initialized                  -- is_alive True,  SIGTERM will terminate it
             Died early                   -- is_alive False, SIGTERM doesn't matter

        Since the normal case is the third one, we'll nicely ask our workers to 
        quit with SIGTERM, then after some time force kill everything.

        However, on some systems we get the first case where even "kill -9" fails until 
        the process fully registers with the OS, so we'll just do our best.

        Note: A more robust way would be just to pass SIGTERM then exit, and let 
               the remaining workers commit suicide when they notice we died.
               This requires passing our PID to workers as an argument, and having
               workers periodically check on its parent.
               See:  http://stackoverflow.com/questions/2542610/python-daemon-doesnt-kill-its-kids
               We may also want to use this:  http://pypi.python.org/pypi/python-daemon
        """
        self._shutdown = True
        if not self._shutdownWorkersNicely():
            self._shutdownWorkersForcefully()
        self._workers = []

    def _shutdownWorkersNicely(self):
        """
        Ask workers to quit via SIGTERM and give them time to finish.
        Returns true if we think all the workers quit nicely.
        """
        no_problem_children = True
        for worker in self._workers:
            log.info("Stopping worker %s..." % worker)
            if not worker.is_alive():
                no_problem_children = False  # Worker may be starting up.
            worker.terminate()

        # Give them some time to quit.
        # (This logic is built into Python 3.3 via Process.sentinel)
        for i in range(MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS):
            foundLivingWorker = False
            for p in self._workers:
                if p.is_alive():
                    foundLivingWorker = True
                    break
            if not foundLivingWorker:
                # All workers either quit or haven't fully started yet.
                return no_problem_children

            if i < MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS - 1:
                sleep(1)  # Give them another second to finish up.
        
        return False  # Out of time.

    def _shutdownWorkersForcefully(self):
        """
        Continually run kill -9 on workers, but give up after a while.
        """
        log.warn("Forcefully killing worker processes...")
        # TODO: We don't need to keep killing workers who nicely changed from
        #       is_alive to dead, or who we successfully kill then join here.
        #       Currently we loop every time, trying to kill all every time.
        #       This means "zenblah shutdown" will take 10 seconds instead of 5.
        for i in range(MAX_SECONDS_TO_FORCE_KILL_WORKERS):
            for worker in self._workers:
                try:
                    os.kill(worker.pid, signal.SIGKILL)
                    os.waitpid(worker.pid, os.WNOHANG)
                    worker.join()
                    log.info("Force killed worker pid %s" % worker.pid)
                except OSError:
                    # It hasn't fully started, or it died, or we already force killed it.
                    # We'll try again but log it just in case.
                    log.info("Could not kill worker pid %s" % worker.pid)

            if i < MAX_SECONDS_TO_FORCE_KILL_WORKERS - 1:
                sleep(1) # Give them another second to finish up.

    def checkWorkers(self, *args):
        log.debug("checkWorkers method")
        if self._checking:
            log.debug("already checking")
            return
        try:
            self._checking = True
            log.debug("checking workers: current %s, max %s"%(len(self._workers), self._maxWorkers))
            currentWorkers = []
            currentWorkers.extend(self._workers)
            for worker in currentWorkers:
                if not worker.is_alive():
                    # It's possible this worker hasn't fully registered with the OS
                    # and will soon start, but it's unlikely we'd be here that soon.
                    log.info("worker %s is dead" % worker)
                    self._workers.remove(worker)
            while len(self._workers) < self._maxWorkers:
                log.debug("starting worker...")
                self._startWorker()
        finally:
            self._checking = False
            
    def _startWorker(self):
        self._workerCount +=1
        workerName = None
        if self._workerName:
            workerName = '%s %s' % (self._workerName, self._workerCount)
        log.debug('starting worker %s' % workerName)
        p = multiprocessing.Process(
            target=self._workerTarget,
            name=workerName
            )
        p.daemon = True
        p.start()
        log.info("Started worker {0}: pid={0.pid}".format(p))
        self._workers.append(p)

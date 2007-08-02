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
import os
import types
import time
import select
import socket
import ip
import icmp
import errno
import pprint
import logging
log = logging.getLogger("zen.Ping")


class PermissionError(Exception):
    """Not permitted to access resource."""


class PingJob:
    """
    Class representing a single target to be pinged.
    """
    def __init__(self, ipaddr, hostname="", status=0, cycle=60):
        self.ipaddr = ipaddr 
        self.hostname = hostname
        self.status = status
        self.rtt = 0
        self.start = 0
        self.sent = 0
        self.message = ""
        self.severity = 5
        self.inprocess = False
        self.pathcheck = 0
        self.eventState = 0


    def reset(self):
        self.rrt = 0
        self.start = 0
        self.sent = 0
        self.message = ""
        self.severity = 5
        self.inprocess = False
        self.pathcheck = 0
        self.eventState = 0


    def checkpath(self):
        parent = getattr(self, "parent", False)
        if parent: return parent.checkpath()


    def routerpj(self):
        parent = getattr(self, "parent", False)
        if parent: return parent.routerpj()


plog = logging.getLogger("zen.Ping")
class Ping(object):    
    """
    Class that provides syncronous icmp ping.
    """

    def __init__(self, tries=2, timeout=2, chunkSize=10, fileDescriptor=None):
        self.tries = tries
        self.timeout = timeout
        self.chunkSize = chunkSize
        self.procId = os.getpid()
        self.jobqueue = {}
        self.pingsocket = None
        self.morepkts = True
        self.devcount = 0
        self.pktdata = 'zenping %s %s' % (socket.getfqdn(), self.procId)
        self.incount = self.outcount = 0
        self.fileDescriptor = fileDescriptor


    def __del__(self):
        if self.pingsocket and not self.fileDescriptor is None:
            self.closePingSocket()


    def createPingSocket(self):
        """make an ICMP socket to use for sending and receiving pings"""
        sargs = socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP
        if self.fileDescriptor is None:
            try:
                sock = socket.socket(*sargs)
            except socket.error, e:
                if e.args[0] == 1: 
                    raise PermissionError("must be root to send icmp.")
        else:
            sock = socket.fromfd(self.fileDescriptor, *sargs)
            # consume any packets that might be queued
            while 1:
                rd, wr, ex = select.select([sock], [], [], 0.)
                if not rd: break
                sock.recv(1024)
        sock.setblocking(0)
        self.pingsocket = sock


    def closePingSocket(self):
        """unregister poll and close socket"""
        self.pingsocket.close()

    
    def sendPackets(self):
        """send numbtosend number of pingJobs and re"""
        try:
            numbtosend = self.chunkSize - len(self.jobqueue) 
            for i in range(numbtosend):
                pingJob = self.sendqueue.next()
                self.devcount += 1
                self.sendPacket(pingJob)
                if self.devcount % self.chunkSize == 0:
                    log.debug("Sent %d packets", self.devcount)
        except StopIteration: self.morepkts = False
            

    def sendPacket(self, pingJob):
        """Take a pingjob and send an ICMP packet for it"""
        #### sockets with bad addresses fail
        try:
            pkt = icmp.Echo(id=self.procId, seq=pingJob.sent, data=self.pktdata)
            buf = icmp.assemble(pkt)
            pingJob.start = time.time()
            plog.debug("send icmp to '%s'", pingJob.ipaddr)
            self.pingsocket.sendto(buf, (pingJob.ipaddr, 0))
            pingJob.sent += 1 
            self.jobqueue[pingJob.ipaddr] = pingJob
        except (SystemExit, KeyboardInterrupt): raise
        except Exception, e:
            pingJob.rtt = -1
            pingJob.message = "%s sendto error %s" % (pingJob.ipaddr, e)
            log.debug("Error sending ping: %s", e)
            if hasattr(self, "reportPingJob"):
                self.reportPingJob(pingJob)


    def recvPacket(self):
        """receive a packet and decode its header"""
        while 1:
            try:
                data = self.pingsocket.recv(1024)
                if not data: return
                ipreply = ip.disassemble(data)
                icmppkt = icmp.disassemble(ipreply.data)
                sip =  ipreply.src
                if (icmppkt.get_type() == icmp.ICMP_ECHOREPLY and 
                    icmppkt.get_id() == self.procId and self.jobqueue.has_key(sip)):
                    plog.debug("echo reply pkt %s %s", sip, icmppkt)
                    self.pingJobSucceed(self.jobqueue[sip])
                elif icmppkt.get_type() == icmp.ICMP_UNREACH:
                    plog.debug("host unreachable pkt %s %s", sip, icmppkt)
                    try:
                        origpkt = icmppkt.get_embedded_ip()
                        dip = origpkt.dst
                        if (origpkt.data.find(self.pktdata) > -1 
                            and self.jobqueue.has_key(dip)):
                            self.pingJobFail(self.jobqueue[dip])
                    except ValueError:
                        plog.exception("failed to parse host unreachable packet")
                else:
                    plog.debug("unexpected pkt %s %s", sip, icmppkt)
            except (SystemExit, KeyboardInterrupt): raise
            except socket.error, err:
                err, errmsg = err.args
                if err == errno.EAGAIN:
                    return
                raise err
            except Exception, e:
                log.exception("receiving packet")



    def pingJobSucceed(self, pj):
        """PingJob completed successfully.
        """
        plog.debug("pj succeed for %s", pj.ipaddr)
        pj.rtt = time.time() - pj.start
        pj.message = "%s ip %s is up" % (pj.hostname, pj.ipaddr)
        del self.jobqueue[pj.ipaddr]
        if hasattr(self, "reportPingJob"):
            self.reportPingJob(pj)


    def pingJobFail(self, pj):
        """PingJob has failed remove from jobqueue.
        """
        plog.debug("pj fail for %s", pj.ipaddr)
        pj.rtt = -1
        pj.message = "%s ip %s is down" % (pj.hostname, pj.ipaddr) 
        del self.jobqueue[pj.ipaddr]
        if hasattr(self, "reportPingJob"):
            self.reportPingJob(pj)


    def checkTimeouts(self):
        """check to see if pingJobs in jobqueue have timed out"""
        joblist = self.jobqueue.values()
        #plog.debug("processing timeouts")
        for pj in joblist:
            if time.time() - pj.start > self.timeout:
                if pj.sent >= self.tries:
                    plog.debug("pj timeout for %s", pj.ipaddr)
                    self.pingJobFail(pj)
                else:
                    self.sendPacket(pj)


    def eventLoop(self, sendqueue):
        startLoop = time.time()
        plog.info("starting ping cycle %s" % (time.asctime()))
        if type(sendqueue) == types.ListType:
            self.sendqueue = iter(sendqueue)
        else:
            self.sendqueue = sendqueue
        self.morepkts = True
        self.devcount = 0
        self.createPingSocket()
        self.sendPackets()
        while self.morepkts or len(self.jobqueue):
            plog.debug("morepkts=%s jobqueue=%s",self.morepkts,
                        len(self.jobqueue))
            plog.debug("incount=%s outcount=%s", self.incount, self.outcount)
            while 1:
                data = select.select([self.pingsocket,], [], [], 0.1)
                if data[0]:
                    self.recvPacket()
                    self.sendPackets()
                else: break
            self.checkTimeouts()
            self.sendPackets()
        self.closePingSocket()
        plog.info("ping cycle complete %s" % (time.asctime()))
        runtime = time.time() - startLoop
        plog.info("pinged %d devices in %3.2f seconds" % 
                    (self.devcount, runtime))
        return runtime
    

    def ping(self, ips):
        """Perform async ping of a list of ips returns (goodips, badips).
        """
        if type(ips) == types.StringType: ips = [ips,]
        pjobs = map(lambda ip: PingJob(ip), ips)
        self.eventLoop(pjobs)
        goodips = []
        badips = []
        for pj in pjobs:
            if pj.rtt >= 0: goodips.append(pj.ipaddr)
            else: badips.append(pj.ipaddr)
        return (goodips, badips)
            

if __name__ == "__main__":
    ping = Ping()
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    if len(sys.argv) > 1: targets = sys.argv[1:]
    else: targets = ("127.0.0.1",)
    good, bad = ping.ping(targets)
    if good: print "Good ips: %s" % " ".join(good)
    if bad: print "Bad ips: %s" % " ".join(bad)

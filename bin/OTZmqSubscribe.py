# -*-mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8-dos -*-

# This Python script requires pyzmq
# http://pypi.python.org/packages/source/p/pyzmq/

"""
Usage: OTZmqSubscribe.py [options] message-types...

Collect ticks from OTMql4Zmq

IMPORTANT: do NOT run this until the expert has been loaded onto a chart
and has received its first tick. It will prevent the expert from binding
to the Pub.Sub ports. So be sure to not keave it running between restarting
Metatrader,

"""
import sys
from datetime import datetime
from optparse import OptionParser
import time

import zmq

lKnownTypes = ['tick', 'cmd', 'retval', 'bar', 'timer']

sUsage = __doc__.strip()
oParser = OptionParser(usage=sUsage)
# I doubt the idea of subscribing at the same time works as we block on the
# publishing. We need to refactor with threads.
oParser.add_option("-s", "--subport", action="store", dest="sSubPort", type="string",
                  default="2027",
                  help="the TCP port number to subscribe to (default 2027)")
# if sPubPort is > 0 then publish a Zmq version query
oParser.add_option("-p", "--pubport", action="store", dest="sPubPort", type="string",
                  default="0",
                  help="the TCP port number to publish to (default 0)")
oParser.add_option("-a", "--address", action="store", dest="sIpAddress", type="string",
                  default="127.0.0.1",
                  help="the TCP address to subscribe on (default 127.0.0.1)")
oParser.add_option("-v", "--verbose", action="store", dest="iVerbose", type="string",
                  default="1",
                  help="the verbosity, 0 for silent 4 max (default 1)")

def bCloseContextSockets(oContext, oSubSocket, oPubSocket, lOptions):
     oSubSocket.setsockopt(zmq.LINGER, 0)
     oSubSocket.close()
     if oPubSocket:
        oPubSocket.setsockopt(zmq.LINGER, 0)
        oPubSocket.close()
     if lOptions and lOptions.iVerbose >= 1:
         print "destroying the context"
     sys.stdout.flush()
     oContext.destroy()
     return True

def iMain():
    (lOptions, lArgs) = oParser.parse_args()

    # Always subscribe to retval so we can always see
    # the value returned by Publish.py
    if "retval" not in lArgs: lArgs.append("retval")
    if lKnownTypes:
        for sElt in lArgs: assert sElt in lKnownTypes

    sSubPort = lOptions.sSubPort
    assert int(sSubPort) > 0 and int(sSubPort) < 66000
    
    sIpAddress = lOptions.sIpAddress
    assert sIpAddress

    try:
        oContext = zmq.Context()
        #print("INFO: setting linger to 0")
        oContext.linger = 0
        oSubSocket = oContext.socket(zmq.SUB)
        if lOptions.iVerbose >= 1:
            print("INFO: Connecting to: " + sIpAddress + ":" + sSubPort + \
                  " and subscribing to: " + " ".join(lArgs))
        oSubSocket.connect("tcp://"+sIpAddress+":"+sSubPort)

        # FixMe: This should subscribe to only the message types listed
        # on the command line, but there is a bug, and the first 16 chars
        # of the message are coming in garbled (including null bytes).
        # So we subscribe to everything so that we can see the garble.
        for sElt in lArgs:
            oSubSocket.setsockopt(zmq.SUBSCRIBE, sElt)

        sPubPort = lOptions.sPubPort
        if int(sPubPort) > 0 and int(sPubPort) < 66000:
            oPubSocket = oContext.socket(zmq.PUB)

            if lOptions.iVerbose >= 1:
                print "Publishing to: " + sIpAddress + ":" + sPubPort
            oPubSocket.connect("tcp://"+sIpAddress+":"+sPubPort)

            sRequest = b"cmd|ZmqVersion"
            if lOptions.iVerbose >= 1:
                print("Sending request %s ..." % sRequest)
            oPubSocket.send(sRequest)
        else:
            oPubSocket = None

        bBlock = False
        sTopic = ''
        while True:
            if bBlock:
                # zmq.NOBLOCK raises zmq.error.Again:
                # Resource temporarily unavailable
                try:
                    sTopic, sString = oSubSocket.recv_multipart(flags=zmq.NOBLOCK)
                except zmq.error.Again:
                    time.sleep(0.1)
                    continue
            else:
                sTopic, sString = oSubSocket.recv_multipart()
            # if not sString: continue
            assert sTopic in lKnownTypes
            print("%s|%s|%15.5f" % (sTopic , sString , time.time()))
            sTopic = ''
            # print map(ord, sString[:18])
    except KeyboardInterrupt:
        pass
    finally:
        bCloseContextSockets(oContext, oSubSocket, oPubSocket, lOptions)

if __name__ == '__main__':
    iMain()
     
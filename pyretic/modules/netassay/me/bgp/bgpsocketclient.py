import sys
import re
#import pickle
import cPickle as pickle
from bgpupdate import *
from time import sleep
from datetime import *
from socket import *


FILENAME   = '/home/mininet/bgptools/update.snip.txt'
SERVERNAME = '127.0.0.1'
SERVERPORT = 12345

''' Example message:

TIME: 01/01/15 00:09:59
TYPE: BGP4MP/MESSAGE/Update
FROM: 147.28.7.2 AS3130
TO: 128.223.51.102 AS6447
ORIGIN: INCOMPLETE
ASPATH: 3130 2914 209 721 27066 647
NEXT_HOP: 147.28.7.2
MULTI_EXIT_DISC: 0
COMMUNITY: 2914:420 2914:1007 2914:2000 2914:3000 3130:380
WITHDRAW
  64.29.130.0/24
ANNOUNCE
  205.108.24.0/22
'''


class push_updates:
    def __init__(self, filename):
        self.filename = filename

    def execute(self):
        blank_line_re = re.compile('^\s*$')
        srcas_re = re.compile('FROM: ([0-9\.]+) AS([0-9]+)')
        aspath_re = re.compile('ASPATH: ([0-9 ]+)')
        network_re = re.compile('  ([0-9\./]+)')
        nexthop_re = re.compile('NEXT_HOP: ([0-9\.]+)')
        withdraw_re = re.compile('WITHDRAW')
        announce_re = re.compile('ANNOUNCE')
        time_re = re.compile('TIME: ([0-9 :/]+)')

        self.file = open(self.filename, 'r')

        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((SERVERNAME, SERVERPORT))

        prev_time = None
        current_time = None
        wd_active = False
        an_active = False
        wd_list = []
        an_list = []
        aspath = None
        src_as = None
        next_hop = None

        linecount = 0
        for line in self.file:
            if blank_line_re.match(line):
                updates = []
                for prefix in wd_list:
                    updates.append(
                        BGPUpdate(src_as, aspath, next_hop, prefix))
                for prefix in an_list:
                    updates.append(
                        BGPUpdate(src_as, aspath, next_hop, prefix))

                if prev_time == None:
                    sleep_time = 0
                else:
                    delta = current_time - prev_time
                    sleep_time = delta.total_seconds()

                print "SLEEPING FOR " + str(sleep_time) + " seconds"

                sleep(sleep_time)

                #Loop through, sending everything.
                for update in updates:
                    print "Sending - " 
                    print str(update)
                    self.client_socket.send(pickle.dumps(update))
                
                # Cleanup all the things that are active.
                prev_time = current_time
                current_time = None
                wd_active = False
                an_active = False
                wd_list = []
                an_list = []
                aspath = None
                src_as = None
                next_hop = None

            elif srcas_re.match(line):
                src_as = srcas_re.match(line).group(2)
            elif aspath_re.match(line):
                aspath = aspath_re.match(line).group(1)
            elif network_re.match(line):
                if wd_active:
                    wd_list.append(network_re.match(line).group(1))
                elif an_active:
                    an_list.append(network_re.match(line).group(1))
                else:
                    print "Problem on line " + str(linecount) + " - Not in ANNOUNCE or WITHDRAW"
            elif withdraw_re.match(line):
                wd_active = True
                an_active = False
            elif announce_re.match(line):
                wd_active = False
                an_active = True
            elif time_re.match(line):
                current_time = self.parse_time(time_re.match(line).group(1))

            linecount = linecount + 1

            if linecount % 10000 == 0:
                print "On line " + str(linecount)
        
        self.client_socket.close()
        self.file.close()

    def parse_time(self, timestr):
        return datetime.strptime(timestr, "%m/%d/%y %H:%M:%S")   







if __name__ == "__main__":
    updates = push_updates(FILENAME)

    print "Pulling updates from " + FILENAME
    print "Please press enter to start updates."
    raw_input("")

    updates.execute()

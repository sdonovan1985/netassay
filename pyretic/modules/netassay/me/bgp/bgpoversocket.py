#!/bin/python
# Copyright 2015 - Sean Donovan

# This version of the bgpqueryhandler is for testing purposes. This creates a
# server socket that listens for update streams based on the also-defined 
# BGPUpdate class


import threading
import sys
import re
import pickle
from socket import *

FILENAME = '/home/mininet/bgptools/rib.snip.txt'
SOCKETNUM = 12345


class BGPUpdate:
    
    WITHDRAWAL = 1
    UPDATE     = 2

    def __init__(self, src_as, aspath, next_hop, network):
        self.src_as = src_as
        self.aspath = aspath
        self.next_hop = next_hop
        self.network = network
        self.type = None

    def equivalent(self, other):
        if ((other.src_as == self.src_as) and 
            (other.aspath == self.aspath) and
            (other.next_hop == self.next_hop) and
            (other.network == self.network)):
            return True
        return False

    def __str__(self):
        returnstr = "    src_as   : " + str(self.src_as) + "\n"
        returnstr = returnstr + "    aspath   : " + str(self.aspath)   + "\n"
        returnstr = returnstr + "    next_hop : " + str(self.next_hop) + "\n"
        returnstr = returnstr + "    network  : " + str(self.network)  + "\n"
        return returnstr


class BGPQueryHandler:
    def __init__(self):
        # callback dictionaries
        self.update_as_callbacks = {}
        self.remove_as_callbacks = {}
        self.update_in_path_callbacks = {}
        self.remove_in_path_callbacks = {}

        # Setup data base - list of dictionaries
        # Dictionary has 4 pieces:
        #    'asn'     : AS number of announced route
        #    'src_asn' : AS that route came from
        #    'network' : The prefix announced
        #    'update'  : the BGPUpdate class that's most current.
        self.db = []
        

        # Preload data source - Load from RIB
        print "Starting parsing RIB"
        self.parse_rib(FILENAME)
        print "Finished parsing RIB"
        
        # Update data source - socket handling in seperate thread. 
        # Note: May not clean up nicely.
        self.server_thread = threading.Thread(target=self.listen_for_updates)
        self.server_thread.daemon = True
        self.server_thread.start()

    def register_for_update_AS(self, cb, asnum):
        if asnum not in self.update_as_callbacks.keys():
            self.update_as_callbacks[asnum] = list()
        if cb not in self.update_as_callbacks[asnum]:
            self.update_as_callbacks[asnum].append(cb)

    def register_for_remove_AS(self, cb, asnum):
        if asnum not in self.remove_as_callbacks.keys():
            self.remove_as_callbacks[asnum] = list()
        if cb not in self.remove_as_callbacks[asnum]:
            self.remove_as_callbacks[asnum].append(cb)

    def register_for_update_in_path(self, cb, asnum):
        if asnum not in self.update_in_path_callbacks.keys():
            self.update_in_path_callbacks[asnum] = list()
        if cb not in self.update_in_path_callbacks[asnum]:
            self.update_in_path_callbacks[asnum].append(cb)

    def register_for_remove_in_path(self, cb, asnum):
        if asnum not in self.remove_in_path_callbacks.keys():
            self.remove_in_path_callbacks[asnum] = list()
        if cb not in self.remove_in_path_callbacks[asnum]:
            self.remove_in_path_callbacks[asnum].append(cb)


    def call_update_AS_callbacks(self, asn, prefix):
        for cb in self.update_as_callbacks[asn]:
            cb(prefix)

    def call_remove_AS_callbacks(self, asn, prefix):
        for cb in self.remove_as_callbacks[asn]:
            cb(prefix)

    def call_update_path_AS_callbacks(self, asn, prefix):
        for cb in self.update_in_path_callbacks[asn]:
            cb(prefix)

    def call_remove_path_AS_callbacks(self, asn, prefix):
        for cb in self.remove_in_path_callbacks[asn]:
            cb(prefix)


    def new_route(self, update):
        aspath = upate.aspath
        asn = aspath.split()[-1]
        src_as = update.src_as
        network = update.network

        as_cb = self.remove_as_callbacks.keys()
        in_path_cb = self.remove_in_path_callbacks.keys()
                

        
        # Check if the main parts of the updates are in the database
        for entry in self.db:
            if ((entry['asn'] == asn) and
                (entry['src_asn'] == src_asn) and
                (entry['network'] == network) and
                (entry['update'].equivalent(update) == True)):
                # They're the same... Do nothing:
                return
            if ((entry['asn'] == asn) and
                (entry['src_asn'] == src_asn) and
                (entry['network'] == network) and
                (entry['update'].equivalent(update) == False)):

                # Different, remove old routes.
                if asnin in as_cb:
                    self.call_remove_AS_callbacks(asn, network)
                
                for asnin in aspath.split():
                    if asnin in in_path_cb:
                        self.call_remove_path_AS_callbacks(asnin, network)

                self.db.remove(entry)
                break
        # add new one to DB
        self.db.append({'asn':asn, 'src_asn':src_as, 
                        'network':network, 'update':update})

        # install new rules through the callbacks
        if asnin in as_cb:
            self.call_update_AS_callbacks(asn, network)
            
        for asnin in aspath.split():
            if asnin in in_path_cb:
                self.call_update_path_AS_callbacks(asnin, network)
                    

        pass

    def withdraw_route(self, update):
        aspath = upate.aspath
        asn = aspath.split()[-1]
        src_as = update.src_as
        network = update.network

        as_cb = self.remove_as_callbacks.keys()
        in_path_cb = self.remove_in_path_callbacks.keys()
                

        
        # Check if the main parts of the updates are in the database
        for entry in self.db:
            if ((entry['asn'] == asn) and
                (entry['src_asn'] == src_asn) and
                (entry['network'] == network) and
                (entry['update'].equivalent(update) == True)):
                # They're the same... Do nothing:
                return
            if ((entry['asn'] == asn) and
                (entry['src_asn'] == src_asn) and
                (entry['network'] == network) and
                (entry['update'].equivalent(update) == True)):

                # Different, remove old routes.
                if asnin in as_cb:
                    self.call_remove_AS_callbacks(asn, network)
                
                for asnin in aspath.split():
                    if asnin in in_path_cb:
                        self.call_remove_path_AS_callbacks(asnin, network)

                self.db.remove(entry)
                break
        
    
    def query_from_AS(self, asn):
        # Loop through the database, add prefixes to prefixes list
        prefixes = []
        
        for entry in self.db:
            if entry['asn'] == str(asn):
                prefixes.append(entry['network'])

        return prefixes

    def query_in_path(self, asn):
        prefixes = []

        for entry in self.db:
            aspath = entry['update'].aspath.split()
            if asn in aspath:
                prefixes.append(entry['network'])



    def parse_rib(self, filename):
        inputfile = open(filename, 'r')

        # lots of REs
        blank_line_re = re.compile('^\s*$')
        aspath_re = re.compile('ASPATH: ([0-9 ]+)')
        network_re = re.compile('PREFIX: ([0-9\./]+)')
        nexthop_re = re.compile('NEXT_HOP: ([0-9\.]+)')
        
        src_as = None
        aspath = None
        next_hop = None
        network = None
        linecount = 0
        for line in inputfile:
            if blank_line_re.match(line):
                update = BGPUpdate(src_as, aspath, next_hop, network)
                asn = aspath.split()[-1]
                self.db.append({'asn':asn, 'src_asn':src_as,
                                'network':network, 'update':update})
                src_as = None
                aspath = None
                next_hop = None
                network = None
            elif aspath_re.match(line):
                aspath = aspath_re.match(line).group(1)
            elif network_re.match(line):
                network = network_re.match(line).group(1)
            elif nexthop_re.match(line):
                next_hop = nexthop_re.match(line).group(1)
            linecount = linecount + 1

            
        inputfile.close()

    def listen_for_updates(self):
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind(('127.0.0.1', SOCKETNUM))
        self.server_socket.listen(1)

        print "Waiting for connection."
        connection_socket, client_address = self.server_socket.accept()
        print "Connection opened by " + str(client_address)

        while True:
            try:
                update = pickle.loads(connection_socket.recv(2048))
            except EOFError:
                # Client closed socket. 
                break

            print "Received - "
            print str(update)
            
            if update.type == BGPUpdate.UPDATE:
                self.new_route(update)
            elif update.type == BGPUpdate.WITHDRAWAL:
                self.withdraw_route(update)

#            connection_socket.send("THANKS")
        connection_socket.close()
        self.server_socket.close()

            
            

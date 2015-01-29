#!/bin/python
# Copyright 2015 - Sean Donovan

# This version of the bgpqueryhandler is for testing purposes. This creates a
# server socket that listens for update streams based on the also-defined 
# BGPUpdate class

import threading


class BGPUpdate:
    def __init__(self, src_as, aspath, next_hop, network):
        self.src_as = src_as
        self.aspath = aspath
        self.next_hop = next_hop
        self.network = network

    def equivalent(self, other):
        if ((other.src_as == self.src_as) && 
            (other.aspath == self.aspath) &&
            (other.next_hop == self.next_hop) &&
            (other.network == self.network)):
            return True
        return False


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
        #TODO
        
        # update data source - socket handling in seperate thread.
        #TODO

    def register_for_update_AS(self, cb, asnum):
        if asnum not in self.as_callbacks.keys():
            self.update_as_callbacks[asnum] = list()
        if cb not in self.as_callbacks[asnum]:
            self.update_as_callbacks[asnum].append(cb)

    def register_for_remove_AS(self, cb, asnum):
        if asnum not in self.as_callbacks.keys():
            self.remove_as_callbacks[asnum] = list()
        if cb not in self.as_callbacks[asnum]:
            self.remove_as_callbacks[asnum].append(cb)

    def register_for_update_in_path(self, cb, asnum):
        if asnum not in self.in_path_callbacks.keys():
            self.update_in_path_callbacks[asnum] = list()
        if cb not in self.in_path_callbacks[asnum]:
            self.update_in_path_callbacks[asnum].append(cb)

    def register_for_remove_in_path(self, cb, asnum):
        if asnum not in self.in_path_callbacks.keys():
            self.remove_in_path_callbacks[asnum] = list()
        if cb not in self.in_path_callbacks[asnum]:
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
            if ((entry['asn'] == asn) &&
                (entry['src_asn'] == src_asn) &&
                (entry['network'] == network) &&
                (entry['update'].equivalent(update))):
                # They're the same... Do nothing:
                return
            if ((entry['asn'] == asn) &&
                (entry['src_asn'] == src_asn) &&
                (entry['network'] == network) &&
                (!entry['update'].equivalent(update))):

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
            if ((entry['asn'] == asn) &&
                (entry['src_asn'] == src_asn) &&
                (entry['network'] == network) &&
                (entry['update'].equivalent(update))):
                # They're the same... Do nothing:
                return
            if ((entry['asn'] == asn) &&
                (entry['src_asn'] == src_asn) &&
                (entry['network'] == network) &&
                (!entry['update'].equivalent(update))):

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
            if entry['asn'] == asn:
                prefixes.append(entry['network'])

        return prefixes

    def query_in_path(self, asn):
        prefixes = []

        for entry in self.db:
            aspath = entry['update'].aspath.split()
            if asn in aspath:
                prefixes.append(entry['network'])


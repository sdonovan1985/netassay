#!/bin/python
# Copyright 2015 - Sean Donovan

# This version of the bgpqueryhandler is for testing purposes. This creates a
# server socket that listens for update streams based on the also-defined 
# BGPUpdate class

import threading


class BGPUpdate:
    def __init__(self, update, src_as, aspath, next_hop, network):
        self.update = update
        self.src_as = src_as
        self.aspath = aspath
        self.next_hop = next_hop
        self.network = network

    def equivalent(self, src_as, network):
        if (src_as == self.src_as) && (network == self.network):
            return True
        return False


class BGPQueryHandler:
    def __init__(self):
        # callback dictionaries
        self.update_as_callbacks = {}
        self.remove_as_callbacks = {}
        self.update_in_path_callbacks = {}
        self.remove_in_path_callbacks = {}

        # Setup data base - dictionary
        # Dictionary has 4 pieces:
        #    'asn'     : AS number of announced route
        #    'src_asn' : AS that route came from
        #    'network' : The prefix announced
        #    'update'  : the BGPUpdate class that's most current.
        self.db = {}
        

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
        #TODO

        pass
        

    def withdraw_route(self, update):
        #TODO
        pass
        
    
    def query_from_AS(self, asn):
        #TODO
        pass

    def query_in_path(self, asn):
        #TODO
        pass


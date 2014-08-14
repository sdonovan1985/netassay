#!/bin/python

from rv_parser import *

FILENAME = "/home/mininet/netassay/pyretic/modules/netassay/me/bgp/bgpclassifier/part_of_oix-full-snapshot-2014-06-01-0200"

# Perhaps this should just be a class that's inherited from... 
# If so, would need to get rid of the data sources and seperate out the callback
# calling function.
class BGPQueryHandler:
    def __init__(self):
        # callback dictionaries
        self.as_callbacks = {}
        self.in_path_callbacks = {}

        # data source - This is for testing and the like...
        self.data = RVData()
        self.data.parse_file(FILENAME, 10000)


    def query_from_AS(self, asnum):
        ases = self.data.get_all_from_AS_number(asnum)
        paths = []
        for entry in ases:
            paths.append(entry.network)

        return paths

    def query_in_path(self, asnum):
        ases = self.data.get_all_in_AS_path(asnum)
        paths = []
        for entry in ases:
            paths.append(entry.network)

        return paths


    def register_for_AS(self, cb, asnum):
        if asnum not in self.as_callbacks.keys():
            self.as_callbacks[asnum] = list()
        if cb not in self.as_callbacks[asnum]:
            self.as_callbacks[asnum].append(cb)

    def register_for_in_path(self, cb, asnum):
        if asnum not in self.in_path_callbacks.keys():
            self.in_path_callbacks[asnum] = list()
        if cb not in self.in_path_callbacks[asnum]:
            self.in_path_callbacks[asnum].append(cb)

    def new_route(self, route):
        pass

    def withdraw_route(self, route):
        pass
    


if __name__ == "__main__":
    handler = BGPQueryHandler()
    paths_from_15169 = handler.query_from_AS('15169')
    paths_with_7545 = handler.query_in_path('7545')

    print "num of 15169  " + str(len(paths_from_15169))
    print "num with 7545 " + str(len(paths_with_7545))
    
    print "Adding new AS with 7545 in it"
    line7545 = RVLine()
    line7545.parse_line("*  5.62.20.0/24       85.114.0.217             0      0      0 8492 6939 7545 2764 2764 38220 i")
    
    handler.data.entries.append(line7545)
    paths_from_15169_2 = handler.query_from_AS('15169')
    paths_with_7545_2 = handler.query_in_path('7545')

    print "num of 15169  " + str(len(paths_from_15169_2))
    print "num with 7545 " + str(len(paths_with_7545_2))


    print "Adding new AS ending with 15169"
    line15169 = RVLine()
    line15169.parse_line("*  1.2.3.0/24         134.222.87.1             0      0      0 286 15169 i")
    handler.data.entries.append(line15169)
    paths_from_15169_3 = handler.query_from_AS('15169')
    paths_with_7545_3 = handler.query_in_path('7545')

    print "num of 15169  " + str(len(paths_from_15169_3))
    print "num with 7545 " + str(len(paths_with_7545_3))

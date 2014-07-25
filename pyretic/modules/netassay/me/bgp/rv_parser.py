#!/bin/python

import sys

class RVData:
    def __init__(self):
        self.entries = []

    def parse_file(self, file, num_entries = None):
        # skip over lines that start with something other than *
        f = open(file, "r")
        line_no = 0
        
        for line in f:
            if line[0:1] != '*':
                continue
            
            rv = RVLine()
            rv.parse_line(line)
            self.entries.append(rv)

            line_no += 1

            if (num_entries != None) and (line_no >= num_entries):
                break
        f.close()
    
    def print_all_entires(self):
        for entry in self.entries:
            print str(entry)

    def get_all_from_AS_number(self, asnum):
        entries_from_AS = []
        for entry in self.entries:
            if entry.get_AS() == asnum:
                entries_from_AS.append(entry)
        return entries_from_AS

    def get_all_in_AS_path(self, asnum):
        entries_from_AS = []
        for entry in self.entries:
            if entry.get_in_path(asnum):
                entries_from_AS.append(entry)
        return entries_from_AS
        

class RVLine:
    def parse_line(self, line):
        #    Network            Next Hop            Metric LocPrf Weight Path
        # *  0.0.0.0/0          196.7.106.245            0      0      0 2905 65023 16637 i
        self.network = line[3:21].strip()
        self.nexthop = line[22:37].strip()
        self.metric = line[38:48].strip()
        self.localpref = line[49:55].strip()
        self.weight = line[56:62].strip()
        self.aspath = line[63:-2].split()   # note the split!
        self.origin = line[-2:].strip()
        
    def __str__(self):
        ret = "Network      : " + self.network + "\n"
        ret = ret + "  Next Hop   : " + self.nexthop + "\n"
        ret = ret + "  Metric     : " + self.metric + "\n"
        ret = ret + "  Local Pref : " + self.localpref + "\n"
        ret = ret + "  Weight     : " + self.weight + "\n"
        ret = ret + "  AS Path    : " + " ".join(self.aspath) + "\n"
        ret = ret + "  Origin     : " + self.origin + "\n"
        return ret

    def get_AS(self):
#        for asnum in self.aspath:
#            print "as: " + str(asnum)
        return (self.aspath[-1])

    def get_in_path(self, asnum):
#        print "checking " + " ".join(self.aspath) + " for " + asnum
#        if asnum in self.aspath:
#            print "   asnum " + asnum + "in the aspath " + " ".join(self.aspath)
        return (asnum in self.aspath)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Command line broken!")
    print sys.argv[1]

    rvfile = RVData()
    rvfile.parse_file(sys.argv[1], 10)
    rvfile.print_all_entires()

    entry_count = 0
    for entry in rvfile.get_all_from_AS_number('15169'):
        print str(entry)
        entry_count += 1
    print "Total Number of entries: " + str(entry_count)
    

#    f = open (sys.argv[1], "r")
#
#    rv = RVLine()
#    lineno = 0
#
#    for line in f:
#        print "line number: " + str(lineno)
#        rv.parse_line(line)
#        print str(rv)
#        lineno += 1


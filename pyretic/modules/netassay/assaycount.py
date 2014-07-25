# Copyright 2014 - Sean Donovan

from pyretic.lib.query import AggregateFwdBucket

'''
This is a simplification of the count_bytes and count_packets queries.
Makes it a one shot thing. 
'''

# All the new count_XXXX_assay policies should inherit from here. They are all 
# very similar, so there is tremendous reuse of code. 
# This is based on match from pyretic.core.langauge
class AssayCount(AggregateFwdBucket):
    def __init__(self, policy, interval=30, group_by=[], cb=None):
        super(AssayCount, self).__init__(interval, group_by)
        if cb is not None:
            self.register_callback(cb)
        self.passed_in_policy = policy
        self.policy = self.passed_in_policy >> self

class count_packets_assay(AssayCount):
    """ Duplicate of count_packets() from pyretic.core.query """
    def aggregator(self,aggregate,pkt):
        return aggregate + 1

class count_bytes_assay(AssayCount):
    """ Duplicate of count_bytes() from pyretic.core.query """
    def aggregator(self,aggregate,pkt):
        return aggregate + pkt['header_len'] + pkt['payload_len']

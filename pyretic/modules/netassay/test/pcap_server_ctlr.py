from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
from pyretic.modules.netassay.assaymcm import *
import logging



#              +----+ 3   1               
#Internet +----+ s1 +------+ PCAP_server
#              ++--++                   
#               |  |2  1                  
#              1|  +---+ h1             
#               |                       
#               +--+ h2                 
#                 1
#
# All traffic going to google.com is also sent to the PCAP_server, in addition
# to where it belongs.

# python pyretic.py pyretic.modules.netassay.test.pcap_server_ctlr
# PCAP_server sudo wireshark
# h1 ping yahoo.com 
# h1 ping google.com


class pcap_ctlr(DynamicPolicy):
    def __init__(self):
        super(pcap_ctlr, self).__init__()
        self.logger = logging.getLogger('netassay.test')

        #Start up Assay and register update_policy()
        self.assay_mcm = AssayMainControlModule.get_instance()
        
        self.update_policy()

    def update_policy(self):
        basic_fwd = if_(match(dstip="10.0.0.1"), fwd(1),
                        if_(match(dstip="10.0.0.2"), fwd(2), fwd(4)))
                        
        self.policy = self.assay_mcm.get_assay_ruleset() + (match(domain='google.com') >> fwd(3)) + basic_fwd
                       
        print self.policy

        

def main():
    return pcap_ctlr()
    

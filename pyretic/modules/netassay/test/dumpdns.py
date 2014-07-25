

################################################################################
# The Pyretic Project                                                          #
# frenetic-lang.org/pyretic                                                    #
# author: Joshua Reich (jreich@cs.princeton.edu)                               #
# author: Sean Donovan (sdonovan@cs.gatech.edu)
#         Heavily modified by Sean to test DNS parsing with ryu.
################################################################################
# Licensed to the Pyretic Project by one or more contributors. See the         #
# NOTICES file distributed with this work for additional information           #
# regarding copyright and ownership. The Pyretic Project licenses this         #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################

################################################################################
# SETUP                                                                        #
# -------------------------------------------------------------------          #
# mininet:  mininet.sh --topo linear,3 (or other single subnet)                #
# test:     start xterms - e.g., 'xterm h1 h2 h3' in mininet console           #
#           start tcpdump:  in each xterm,                                     #
#           IF=`ifconfig | head -n 1 | awk '{print $1}'`;                      #
#           tcpdump -XX -vvv -t -n -i $IF not ether proto 0x88cc > $IF.dump    #
#           h1 ping -c 2 h3                                                    #
#           examine dumps, confirm that h2 does not see packets on second ping #
################################################################################

from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
from ryu.lib.packet.dns import *
from pyretic.modules.dnsclassify import *
from datetime import datetime
from threading import Timer
from dnsentry import DNSClassifierEntry

    

class dumpdns(DynamicPolicy):
    """Standard MAC-learning logic"""
    def __init__(self):
        super(dumpdns,self).__init__()
        self.flood = flood()           # REUSE A SINGLE FLOOD INSTANCE
        self.set_initial_state()
        self.classifier = DNSClassifier()
        self.dns_cleanup()             # Starts the timer as well.
        self.classifier.set_all_callback(self.print_it)
        
    def __del__(self):
        self.timer.cancel()
        del self.timer

    def print_it(self, addr, entry):
        print addr
        entry.print_entry() 
        entry.register_timeout_callback(self.expiry_cb)
    
    def expiry_cb(self, entry):
        print entry.IP + " has expired."        

    def set_initial_state(self):
        dnspkts = packets(None, ['srcmac'])
        dnspkts.register_callback(self.learn_dns)
        self.dns_inbound = match(srcport = 53) >> dnspkts
        self.dns_outbound = match(dstport = 53) >> dnspkts

        self.query = packets(1,['srcmac','switch'])
        self.query.register_callback(self.learn_new_MAC)

        self.forward = self.flood  # REUSE A SINGLE FLOOD INSTANCE
        self.update_policy()


    def set_network(self,network):
        self.set_initial_state()

    def update_policy(self):
        """Update the policy based on current forward and query policies"""
        self.policy = self.forward + self.query + self.dns_inbound + self.dns_outbound

    def learn_new_MAC(self,pkt):
        """Update forward policy based on newly seen (mac,port)"""
        self.forward = if_(match(dstmac=pkt['srcmac'],
                                switch=pkt['switch']),
                          fwd(pkt['inport']),
                          self.forward) 
        self.update_policy()
    
    def print_dns(self,pkt):

        offset = len(pkt['raw']) - pkt['payload_len']
        offset = 42 #FIXME! THIS ONLY WORKS WITH UDP!
        parsed_dns = dns.parser(pkt['raw'][offset:])
        print "Packet:"
        print parsed_dns._to_str()

        print "Sending packet to database"
        self.classifier.parse_new_DNS(pkt['raw'][offset:])
        
        print ""
        print ""
        print "PRINTING DNS DATABASE"
        print "---------------------"
        self.classifier.print_entries()
        print "---------------------"
        print "Time now:"
        now = datetime.now()
        print str(now)
        print ""
        print ""
        

    def learn_dns(self,pkt):
        offset = 42 #FIXME! THIS ONLY WORKS WITH 
        self.classifier.parse_new_DNS(pkt['raw'][offset:])
    
    def dns_cleanup(self):
        self.classifier.clean_expired()
        self.timer = Timer(30, self.dns_cleanup)
        self.timer.start()

        
def main():
    return dumpdns()

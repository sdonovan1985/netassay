from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
from pyretic.core.language import union
from pyretic.modules.netassay.assaymcm import *
import logging
from random import randrange

from pyretic.modules.netassay.me.dns.dnsme import DNSMetadataEngine
from pyretic.modules.netassay.lib.py_timer import py_timer as Timer

DOMAIN_LIST = "pyretic/modules/netassay/test/alexa-top-100-2014-12-03.txt"
AS_LIST     = "pyretic/modules/netassay/test/ribs-with-updates.txt"
#SWITCH_WIDTH = 10
#RULES_TOTAL = 1000
SWITCH_WIDTH = 10
RULES_TOTAL = 100
BGP_AS_MIN = 1
BGP_AS_MAX = 1000

def get_list_of_domains():
    f = open(DOMAIN_LIST, 'r')
    domain_list = []
    for line in f:
        domain_list.append(line.strip())
    f.close()
    return domain_list

def get_list_of_ases():
    f = open(AS_LIST, 'r')
    as_list = []
    for line in f:
        as_list.append(line.strip())
    f.close()
    return as_list
    
def get_list_of_hosts(num):
    host_list = []
    for i in range(0,num):
        host_list.append("h%i" % i)
    return host_list

def get_list_of_switches(num):
    switch_list = []
    for i in range(0,num):
        switch_list.append("s%i" % i)
    return switch_list

class LargeTest(DynamicPolicy):
    def __init__(self):
        super(LargeTest, self).__init__()
        self.flood = flood()
        self.logger = logging.getLogger('netassay.test')

        # Topology components
        self.switch_names = get_list_of_switches(SWITCH_WIDTH + 1)
        self.host_names   = get_list_of_hosts(SWITCH_WIDTH * SWITCH_WIDTH)
        self.root_switch_name = self.switch_names[0]
        self.domains = get_list_of_domains()
        self.ases = get_list_of_ases()
        
        self.assay_mcm = AssayMainControlModule.get_instance()
        self.dnsme = DNSMetadataEngine.get_instance()

        # RootSwitch gets no rules
        # Each of the children switches gets RULES_PER_SWITCH rules.

        self.list_of_rules = []        
        for i in range(RULES_TOTAL):
            r = self.generate_a_rule()
            print "RULE #" + str(i) +" : " + str(r)
            logging.getLogger("netassay.evaluation").critical("RULE " + str(i))
            self.list_of_rules.append(r)

#        self.logger.warning("STARTING TIMER install_new_rule")
#        self.update_timer = Timer(30, self.install_new_rule)
#        self.update_timer.start() 
        print "SETUP COMPLETE!"
        self.assay_mcm.init_complete()
        logging.getLogger("netassay.evaluation2").critical("SETUP COMPLETE")
        self.update_policy()

        
        
#        print self.policy

    def update_policy(self):
        self.policy = self.assay_mcm.get_assay_ruleset() + union(self.list_of_rules)
#        self.policy = self.assay_mcm.get_assay_ruleset() + disjoint(self.list_of_rules)



    def generate_a_rule(self):
        rand_rule = randrange(0, 4)
        rand_rule = 1
        if rand_rule == 1:
            return self.generate_bgp_rule()
        else:
            return self.generate_dns_rule()

    def generate_dns_rule(self):
        random_switch = randrange(0, SWITCH_WIDTH + 1)
        random_port   = randrange(0, SWITCH_WIDTH)
        random_site = self.domains[randrange(0,100)]

        self.random_site = random_site

        return (match(switch=random_switch, domain=random_site) >> fwd(random_port))

    def generate_bgp_rule(self):
        random_switch = randrange(0, SWITCH_WIDTH + 1)
        random_port   = randrange(0, SWITCH_WIDTH)
        random_AS = self.ases[randrange(0,len(self.ases))]

        return (match(switch=random_switch, AS=random_AS) >> fwd(random_port))

    def install_new_rule(self):
        self.logger.warning("BEGINNING OF install_new_rule")
        self.dnsme._install_new_rule(self.random_site, "192.168.1.100")

def main():
    return LargeTest()

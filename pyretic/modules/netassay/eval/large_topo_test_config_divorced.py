from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *
#from pyretic.core.language import union
from pyretic.modules.netassay.eval.divorce import *
from pyretic.modules.netassay.assaymcm import *
import logging
from random import randrange

from pyretic.modules.netassay.me.dns.dnsme import DNSMetadataEngine
from pyretic.modules.netassay.lib.py_timer import py_timer as Timer

DOMAIN_LIST = "pyretic/modules/netassay/test/alexa-top-100-2014-12-03.txt"
SWITCH_WIDTH = 10
RULES_TOTAL = 1000 

def get_list_of_domains():
    f = open(DOMAIN_LIST, 'r')
    domain_list = []
    for line in f:
        domain_list.append(line.strip())
    f.close()
    return domain_list
    
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

class LargeTest(object):
    def __init__(self):
        self.logger = logging.getLogger('netassay.test')


        # Topology components
        self.switch_names = get_list_of_switches(SWITCH_WIDTH + 1)
        self.host_names   = get_list_of_hosts(SWITCH_WIDTH * SWITCH_WIDTH)
        self.root_switch_name = self.switch_names[0]
        self.domains = get_list_of_domains()
        
        self.assay_mcm = AssayMainControlModule.get_instance()
        self.dnsme = DNSMetadataEngine.get_instance()

        # RootSwitch gets no rules
        # Each of the children switches gets RULES_PER_SWITCH rules.

        self.list_of_rules = []        
        for i in range(RULES_TOTAL):
            r = self.generate_a_rule()
            logging.getLogger("netassay.evaluation").critical("RULE " + str(i))
            self.list_of_rules.append(r)

#        self.logger.warning("STARTING TIMER install_new_rule")
#        self.update_timer = Timer(30, self.install_new_rule)
#        self.update_timer.start()

        logging.getLogger("netassay.evaluation").critical("SETUP COMPLETE")
        self.update_policy()

        
        
#        print self.policy

    def update_policy(self):
        self.policy = self.assay_mcm.get_assay_ruleset() + union(self.list_of_rules)
#        self.policy = self.assay_mcm.get_assay_ruleset() + disjoint(self.list_of_rules)



    def generate_a_rule(self):
        random_switch = randrange(0, SWITCH_WIDTH + 1)
        random_port   = randrange(0, SWITCH_WIDTH)
        random_site = self.domains[randrange(0,100)]

        self.random_site = random_site

        return (match(switch=random_switch, domain=random_site) >> fwd(random_port))

    def install_new_rule(self):
        self.logger.warning("BEGINNING OF install_new_rule")
        self.dnsme._install_new_rule(self.random_site, "192.168.1.100")

def main():
    return LargeTest()

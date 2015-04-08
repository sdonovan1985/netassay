from pyretic.modules.netassay.assaymcm import *
from pyretic.modules.netassay.eval.divorce import *
from random import randrange
import logging
import pprint


logger = logging.getLogger('netassay.evaluation2')
assay_mcm = AssayMainControlModule.get_instance()

DOMAIN_LIST = "pyretic/modules/netassay/test/alexa-top-100-2014-12-03.txt"
AS_LIST = "pyretic/modules/netassay/test/ribs-with-routes.txt"
SWITCH_WIDTH = 10

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
    print "AS list: " + str(as_list)
    return as_list

def generate_a_rule(domains, ases):
    rand_rule = randrange(0, 4)
    rand_rule = 0
    if rand_rule == 1:
        print "generating bgp rule"
        return generate_bgp_rule(ases)
    else:
        print "generating dns rule"
        return generate_dns_rule(domains)

def generate_dns_rule(domains):
    random_switch = randrange(0, SWITCH_WIDTH + 1)
    random_port   = randrange(0, SWITCH_WIDTH)
    random_site = domains[randrange(0,100)]
    
    retval = match(domain=random_site)
    return retval

def generate_bgp_rule(ases):
    random_switch = randrange(0, SWITCH_WIDTH + 1)
    random_port   = randrange(0, SWITCH_WIDTH)
    random_AS = ases[randrange(1,len(ases))]

    retval = match(AS=random_AS)
    return retval



list_of_rules = []
number_of_rules = 100
domains  = get_list_of_domains()
ases = get_list_of_ases()
pp = pprint.PrettyPrinter(indent=4)


for x in range(0, number_of_rules):
    rule = generate_a_rule(domains, ases)
    print "RULE %d:" % x
    pp.pprint(repr(rule))
    list_of_rules.append(rule)
    

logger.critical("SETUP COMPLETE")

from pyretic.modules.netassay.assaymcm import *
from pyretic.modules.netassay.eval.divorce import *
from random import randrange
from time import sleep
import logging
import pprint
import threading

from pyretic.modules.netassay.me.bgp.bgpsocketclient import *


logger = logging.getLogger('netassay.evaluation2')
assay_mcm = AssayMainControlModule.get_instance()

DOMAIN_LIST = "pyretic/modules/netassay/test/alexa-top-1000-2015-03-05.txt"

def get_list_of_domains():
    f = open(DOMAIN_LIST, 'r')
    domain_list = []
    for line in f:
        domain_list.append(line.strip())
    f.close()
    return domain_list


list_of_rules = []
domains = get_list_of_domains()
pp = pprint.PrettyPrinter(indent=4)


for x in range(0, len(domains)):
#for x in range(0, number_of_rules):
    selected_domain = domains[x]
    rule = match(domain=selected_domain)
    print "RULE %d:" % x
    pp.pprint(repr(rule))
    list_of_rules.append(rule)

    
assay_mcm.init_complete()
logger.critical("SETUP COMPLETE")


# wait for 10 minutes so that DNS updates come in.
sleep(10*60)

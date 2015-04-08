from pyretic.modules.netassay.assaymcm import *
from pyretic.modules.netassay.eval.divorce import *
from time import sleep
from random import randrange
import logging
import pprint


logger = logging.getLogger('netassay.evaluation2')
assay_mcm = AssayMainControlModule.get_instance()

AS_LIST = "pyretic/modules/netassay/test/ribs-with-routes.txt"
SWITCH_WIDTH = 10

def get_list_of_ases():
    f = open(AS_LIST, 'r')
    as_list = []
    for line in f:
        as_list.append(line.strip())
    f.close()
    print "AS list: " + str(as_list)
    return as_list


list_of_rules = []
number_of_rules = 1
ases = get_list_of_ases()
pp = pprint.PrettyPrinter(indent=4)


#for x in range(0, len(ases)):
#for x in range(0, number_of_rules):
#    selected_as = ases[x]
#    rule = match(AS=selected_as)
#    print "RULE %d:" % x
#    pp.pprint(repr(rule))
#    list_of_rules.append(rule)

rule = match(AS=ases[2])
pp.pprint(repr(rule))
list_of_rules.append(rule)

#logger.critical("MEMOIZATION")

#for x in range(0, len(ases)):
#for x in range(0, number_of_rules):
#    selected_as = ases[x]
#    rule = match(AS=selected_as)
#    print "MEMOIZED RULE %d:" % x
#    pp.pprint(repr(rule))
#    list_of_rules.append(rule)
    
assay_mcm.init_complete()
logger.critical("SETUP COMPLETE")

# Wait for 10 minutes, so it can get new routes pushed in.
sleep(10*60)

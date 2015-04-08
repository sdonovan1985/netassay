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
number_of_rules = 100
ases = get_list_of_ases()
pp = pprint.PrettyPrinter(indent=4)


for x in range(0, len(ases)):
#for x in range(0, number_of_rules):
    selected_as = ases[x]
    rule = match(AS=selected_as)
    print "RULE %d:" % x
    pp.pprint(repr(rule))
    del(rule)
#    list_of_rules.append(rule)

    
assay_mcm.init_complete()
logger.critical("SETUP COMPLETE")



FILENAME   = '/home/mininet/bgptools/update.snip.txt'
SERVERNAME = '127.0.0.1'
SERVERPORT = 12345
SLEEPMULTIPLIER = 0.5
push_updates = push_updates(FILENAME)
push_thread = threading.Thread(target=push_updates.execute)

push_thread.start()
push_thread.join()


from bgpoversocket import BGPQueryHandler
from time import sleep

class RegisteredAS:

    def __init__(self, asn, handler):
        self.asn = asn
        self.handler = handler

        self.handler.register_for_update_AS(self.handle_AS_update, asn)
        self.handler.register_for_remove_AS(self.handle_AS_update, asn)
        
        prefixes = self.handler.query_from_AS(self.asn)
        print "ASN " + str(self.asn) + " starts with " + str(len(prefixes)) + " prefixes."
#        for prefix in prefixes:
#            print "AS Init   with " + str(self.asn) + " " + prefix

    def handle_AS_update(prefix):
        print "AS Update  for " + str(self.asn) + " " + prefix

    def handle_AS_update(prefix):
        print "AS Removal for " + str(self.asn) + " " + prefix


handler = BGPQueryHandler()

list_of_registered = []
list_of_registered.append(RegisteredAS(647, handler))

sleep(20*60)

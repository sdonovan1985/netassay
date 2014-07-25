# Copyright 2014 -  Sean Donovan
# Based off of https://github.com/shahifaqeer/dnsclassifier. Modified
# to work with Pyretic.

from ryu.lib.packet.dns import dns
from ryu.lib import addrconv
from mapper import Mapper
from pyretic.modules.netassay.me.dns.dnsentry import DNSClassifierEntry as Entry

# need hooks for passing in DNS packets
#    Parsing out different types
#    adding to database function - helper
# need callback functions (?)
#    Expiry of known DNS entry
# need to convert TTLs to end-of-life timeouts
# printing out of current database
# querying by IP (string)
# prepopulating db from a file?

# Database dictionary of dictionaries:
#    Primary key - IP address string - returns the dictionary associated with IP
#    Secondary keys
#        record types?
#        'ttl' - TTL value from the packet
#        'expiry' - actual time off of expiration - 
#                   upon hitting, delete/move to "expired" list
#        'classification'
#

class DNSClassifierException(Exception):
    pass

class DNSClassifier:
    def __init__(self):
        #may want to enhance this with a pre-load file to prepopulate the DB
        self.db = {}                   # dictionary of DNSClassifierEntrys
        self.mapper = Mapper()
        self.new_callbacks = []        # For each new entry
        self.update_callbacks = []     # For each time an entry is updated
        self.all_callbacks = []        # When entry is updated or new
        self.class_callbacks = {}      # Dictionary of lists of callbacks per
                                       # classification

    def parse_new_DNS(self, packet):
        # Only look at responses with 'No error' reply code
        dns_parsed = dns.parser(packet)
        if (dns_parsed.qr and dns_parsed.rcode == 0000):
            # skip the questions...
            # we don't care about authorities
            # we care about answers
            # we care about additional - could be some goodies in there
            for resp in (dns_parsed.answers + dns_parsed.additional):
                # save off the ttl, classification, calculate expiry time
                # Name of item that's being saved, 
                if (resp.qtype == dns.rr.A_TYPE):
                    classification = self.mapper.searchType(resp.name)
                    addr = addrconv.ipv4.bin_to_text(resp.rddata)
                    
                    if addr not in self.db.keys():
                        self.db[addr] =  Entry(addr, list(), classification,
                                               resp.ttl)
                        self.db[addr].names.append(resp.name)
                        for callback in self.new_callbacks:
                            callback(addr, self.db[addr])
                        if classification in self.class_callbacks.keys():
                            for callback in self.class_callbacks[classification]:
                                callback(addr, self.db[addr])
                    else:
                        self.db[addr].update_expiry(resp.ttl)
                        old_class = self.db[addr].classification
                        self.db[addr].classification = classification

                        if resp.name not in self.db[addr].names:
                            self.db[addr].names.append(resp.name)
                        for callback in self.update_callbacks:
                            callback(addr, self.db[addr])
                        if old_class != classification:
                            if classification in self.class_callbacks.keys():
                                for callback in self.class_callbacks[classification]:
                                    callback(addr, self.db[addr])

                    for callback in self.all_callbacks:
                        callback(addr, self.db[addr])

                elif (resp.qtype == dns.rr.AAAA_TYPE):
                    #placeholder
                    print "Found a AAAA"
                elif (resp.qtype == dns.rr.CNAME_TYPE):
                    #placeholder
                    print "Found a CNAME!"
                elif (resp.qtype == dns.rr.MX_TYPE):
                    #placeholder
                    print "Found an MX!"

    def _clean_expiry_full(self):
        # Loop through everything to check for expired DNS entries
        for key in self.db.keys():
            entry = self.db[key]
            if entry.is_expired():
                del self.db[key]

    def clean_expired(self):
        self._clean_expiry_full()
        
    def print_entries(self):
        for key in self.db.keys():
            self.db[key].print_entry()

    def set_new_callback(self, cb):
        if cb not in self.new_callbacks:
            self.new_callbacks.append(cb)

    def remove_new_callback(self, cb):
        self.new_callbacks.remove(cb)

    def set_update_callback(self, cb):
        if cb not in self.update_callbacks:
            self.update_callbacks.append(cb)

    def remove_update_callback(self, cb):
        self.update_callbacks.remove(cb)

    #TODO: classication change callback?

    def set_all_callback(self, cb):
        if cb not in self.update_callbacks:
            self.all_callbacks.append(cb)

    def remove_all_callback(self, cb):
        self.all_callbacks.remove(cb)

    def set_classification_callback(self, cb, classification):
        print "set_classification_callback: " + str(cb)
        print "classification:              " + str(classification)
        if classification not in self.class_callbacks.keys():
            self.class_callbacks[classification] = list()
        if cb not in self.class_callbacks[classification]:
            self.class_callbacks[classification].append(cb)

    def remove_classification_callback(self, cb, classification):
        if classification not in self.class_callbacks.keys():
            return
        self.class_callbacks[classification].remove(cb)

    def find_by_ip(self, addr):
        """Returns the entry specified by the ip 'addr' if it exists
        """
        if addr in self.db.keys():
            return self.db[addr]
        return None

    def get_classification(self, IP):
        """Returns the classification for the entry specified by the ip 'addr'
           if it exists
        """
        if addr in self.db.keys():
            return self.db[addr].classification
        return None

    def find_by_classification(self, classification):
        """Returns a dictionary of database entries from a particular category  
           Dictionary will be ipaddr:dbentry
        """
        retdict = {}
        for key in self.db.keys():
            if classification == self.db[key].classification:
                retdict[key] = self.db[key]
        return retdict

    def find_by_name(self, name):
        """Returns a dictionary of database entries for a particular webname
           Dictionary will be ipaddr:dbentry
        """
        retdict = {}
        for key in self.db.keys():
            for nameval in self.db[key].names:
                if nameval == name:
                    retdict[key] = self.db[key]
                    continue # don't need to look at any more of the names
        return retdict

    def has(self, ipaddr):
        """Returns true if we have a record for a particular IP address.
           Returns fase if we don't have an active record for a particular
           IP address.
        """
        if ipaddr not in self.db.keys():
            return false        
        return self.db[ipaddr].is_expired()


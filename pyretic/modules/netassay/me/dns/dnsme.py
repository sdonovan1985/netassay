# Copyright 2014 - Sean Donovan
# DNS Metadata Engine

import logging

from dnsclassifier.dnsclassify import *
from dnsentry import DNSClassifierEntry as DNSEntry
from pyretic.modules.netassay.assayrule import *
from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *


class DNSMetadataEngineException(Exception):
    pass

class DNSMetadataEngine:
    INSTANCE = None        
    # Singleton! should be initialized by the MCM only!
    
    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists!")
        self.classifier = DNSClassifier()
        self.entries = []
        self.logger = logging.getLogger('netassay.DNSME')

        self.logger.debug("DNSMetadataEngine.__init__(): finished")

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            logging.getLogger('netassay.DNSME').info("DNSMetadataEngine.get_instance(): Initializing DNSMetadataEngine")
            cls.INSTANCE = DNSMetadataEngine()
        return cls.INSTANCE
    
    def get_forwarding_rules(self):
        """
        This gets the forwarding rules that the DNS Classifier needs to work.
        """
        self.logger.info("DNSMetadataEngine.get_forwarding_rules(): called")
        dnspkts = packets(None, ['srcmac'])
        self.offset = 42 #FIXME! THIS ONLY WORKS WITH IPv4
        dnspkts.register_callback(self._dns_parse_cb)

        dns_inbound = match(srcport = 53) >> dnspkts
        dns_outbound = match(dstport = 53) >> dnspkts

        return dns_inbound + dns_outbound

    def _dns_parse_cb(self, pkt):
        self.logger.info("DNSMetadataEngine._dns_parse_cb(): called")
        self.classifier.parse_new_DNS(pkt['raw'][self.offset:])
        #self.classifier.print_entries()
        
    def new_rule(self, rule):
        self.logger.info("DNSMetadataEngine.new_rule(): called")
        self.entries.append(DNSMetadataEntry(self.classifier, self, rule))

    

class DNSMetadataEntry:
    def __init__(self, classifier, engine, rule ):
        logging.getLogger('netassay.DNSMetadataEntry').info("DNSMetadataEntry.__init__(): called")
        self.classifier = classifier
        self.engine = engine
        self.rule = rule
        self.logger = logging.getLogger('netassay.DNSMetadataEntry')
        
        #register for all the callbacks necessary
        if self.rule.type == AssayRule.CLASSIFICATION:
            classifier.set_classification_callback(
                self.handle_classification_callback,
                self.rule.value)
        else:
            classifier.set_new_callback(self.handle_new_entry_callback)
            #FIXME: classification change
#            classifier.

    def handle_expiration_callback(self, addr, entry):
        self.logger.info("DNSMetadataEntry.handle_expiration_callback(): called with " + addr)
        #need to remove the rules that was generated by the particular DNSEntry
        self.rule.remove_rule(match(srcip=IPAddr(addr)))
        self.rule.remove_rule(match(dstip=IPAddr(addr)))

    def handle_new_entry_callback(self, addr, entry):
        self.logger.info("DNSMetadataEntry.handle_new_entry_callback(): called with " + addr)
        if self.rule.type == AssayRule.CLASSIFICATION:
            if entry.classification == self.rule.value:
                self.logger.debug("    Rule type: CLASSIFICATION")
                self.rule.add_rule(match(srcip=IPAddr(addr)))
                self.rule.add_rule(match(dstip=IPAddr(addr)))
                #SPD FIXME TTL TURNED OFF FOR TESTING entry.register_timeout_callback(self.handle_expiration_callback)

        elif self.rule.type == AssayRule.AS:
            self.logger.debug("    Rule type: AS")
            print "WE DON'T HANDLE AS RULES>"
            raise DNSMetadataEngineException("WE DON'T HANDLE AS RULES")
        elif self.rule.type == AssayRule.DNS_NAME:
            self.logger.debug("    Rule type: DNS_NAME")
            for name in entry.names:
                if name == self.rule.value:
                    self.rule.add_rule(match(srcip=IPAddr(addr)))
                    self.rule.add_rule(match(dstip=IPAddr(addr)))
                    self.logger.debug("    New rule for " + name)
                    #SPD FIXME TTL TURNED OFFF FOR TESTING entry.register_timeout_callback(self.handle_expiration_callback)

    def handle_classification_callback(self, addr, entry):
        # This should only be registered for if you care about a particular 
        # class, so it's blindly adding a rule for the particular entry.
        self.logger.info("DNSMetadataEntry.handle_classification_callback(): called with " + addr)
        self.rule.add_rule(match(srcip=IPAddr(addr)))
        self.rule.add_rule(match(dstip=IPAddr(addr)))
        entry.register_timeout_callback(self.handle_expiration_callback)

    

# Copyright 2014 - Sean Donovan
# DNS Metadata Engine

ACTIVE_MAPPING = True

import logging

from dnsclassifier.dnsclassify import *
from dnsentry import DNSClassifierEntry as DNSEntry
from pyretic.modules.netassay.assayrule import *
from pyretic.modules.netassay.netassaymatch import *
from pyretic.modules.netassay.me.metadataengine import *
from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *

if ACTIVE_MAPPING == True:
    from dns import resolver, exception
    from pyretic.modules.netassay.lib.py_timer import py_timer as Timer


class DNSMetadataEngineException(Exception):
    pass

class DNSMetadataEngine(MetadataEngine):
    def __init__(self):
        super(DNSMetadataEngine, self).__init__(DNSClassifier(), 
                                                DNSMetadataEntry)

        # Register the different actions this ME can handle
        RegisteredMatchActions.register('domain', matchURL)
        RegisteredMatchActions.register('class', matchClass)

    def __del__(self):
        # Clean up timer, lest we cause other problems...
        self.logger.debug("__del__ called.")
        if ACTIVE_MAPPING == True:
            if self._active_timer is not None:
                self._active_timer.cancel()
                self._active_timer.join()

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

        dns_inbound = Match(dict(srcport = 53)) >> dnspkts
        dns_outbound = Match(dict(dstport = 53)) >> dnspkts

        return dns_inbound + dns_outbound

    def _dns_parse_cb(self, pkt):
        self.logger.info("DNSMetadataEngine._dns_parse_cb(): called")
        self.data_source.parse_new_DNS(pkt['raw'][self.offset:])
        #self.data_source.print_entries()

    

class DNSMetadataEntry(MetadataEntry):
    def __init__(self, data_source, engine, rule):
        super(DNSMetadataEntry, self).__init__(data_source, engine, rule)
        
        #register for all the callbacks necessary
        if self.rule.type == AssayRule.CLASSIFICATION:
            self.data_source.set_classification_callback(
                self.handle_classification_callback,
                self.rule.value)
        else:
            self.data_source.set_new_callback(self.handle_new_entry_callback)
            #FIXME: classification change
            if ACTIVE_MAPPING == True:
                self._active_timer = None
                self._active_results = []
                self._active_get_mapping()
                

    def handle_expiration_callback(self, addr, entry):
        self.logger.info("DNSMetadataEntry.handle_expiration_callback(): called with " + addr)
        #need to remove the rules that was generated by the particular DNSEntry
        self.rule.remove_rule(Match(dict(srcip=IPAddr(addr))))
        self.rule.remove_rule(Match(dict(dstip=IPAddr(addr))))

    def handle_new_entry_callback(self, addr, entry):
        self.logger.info("DNSMetadataEntry.handle_new_entry_callback(): called with " + addr)
        if self.rule.type == AssayRule.CLASSIFICATION:
            if entry.classification == self.rule.value:
                self.logger.debug("    Rule type: CLASSIFICATION")
                self.rule.add_rule(Match(dict(srcip=IPAddr(addr))))
                self.rule.add_rule(Match(dict(dstip=IPAddr(addr))))
                entry.register_timeout_callback(self.handle_expiration_callback)

        elif self.rule.type == AssayRule.AS:
            self.logger.debug("    Rule type: AS")
            print "WE DON'T HANDLE AS RULES>"
            raise DNSMetadataEngineException("WE DON'T HANDLE AS RULES")
        elif self.rule.type == AssayRule.DNS_NAME:
            self.logger.debug("    Rule type: DNS_NAME")
            for name in entry.names:
                if name == self.rule.value:
                    self.rule.add_rule(Match(dict(srcip=IPAddr(addr))))
                    self.rule.add_rule(Match(dict(dstip=IPAddr(addr))))
                    self.logger.debug("    New rule for " + name)
                    entry.register_timeout_callback(self.handle_expiration_callback)

    def handle_classification_callback(self, addr, entry):
        # This should only be registered for if you care about a particular 
        # class, so it's blindly adding a rule for the particular entry.
        self.logger.info("DNSMetadataEntry.handle_classification_callback(): called with " + addr)
        self.rule.add_rule(Match(dict(srcip=IPAddr(addr))))
        self.rule.add_rule(Match(dict(dstip=IPAddr(addr))))
        entry.register_timeout_callback(self.handle_expiration_callback)

    def _active_get_mapping_expired(self):
        #self.logger.debug("_active_get_mapping_expired() called " + str(self._active_timer.is_alive()))
        self._active_timer.cancel()
        self._active_get_mapping()

    def _active_get_mapping(self):
        # Anly working on A record now
        try:
            results = resolver.query(self.rule.value, 'A')
            ttl = results.ttl

            self._active_timer = Timer(ttl, self._active_get_mapping_expired)
            self._active_timer.start()
            new_active_results = []
        
            # These two reduce churn: only adds things that weren't there from the 
            # previous pass, only deletes things that aren't there from this pass.
        
            # Add new addresses
            for addr in results:
                new_active_results.append(addr)
                if addr not in self._active_results:
                    self.rule.add_rule(Match(dict(srcip=IPAddr(str(addr)))))
                    self.rule.add_rule(Match(dict(dstip=IPAddr(str(addr)))))

            # Remove old addresses
            for addr in self._active_results:
                if addr not in results:
                    self.rule.remove_rule(Match(dict(srcip=IPAddr(str(addr)))))
                    self.rule.remove_rule(Match(dict(dstip=IPAddr(str(addr)))))

            self._active_results = new_active_results
        except (resolver.NoAnswer, exception.Timeout):
            self.logger.info("Could not query for " + self.rule.value + ". Trying again in 30 seconds.")
            self._active_timer = Timer(30, self._active_get_mapping_expired)
            self._active_timer.start()
            self._active_results = []
        

#--------------------------------------
# NetAssayMatch subclasses
#--------------------------------------

class matchURL(NetAssayMatch):
    """
    matches IPs related to the specified URL.
    """
    def __init__(self, url, matchaction):
        logging.getLogger('netassay.matchURL').info("matchURL.__init__(): called")
        metadata_engine = DNSMetadataEngine.get_instance()
        ruletype = AssayRule.DNS_NAME
        rulevalue = url
        super(matchURL, self).__init__(metadata_engine, ruletype, rulevalue, matchaction)

class matchClass(NetAssayMatch):
    """
    matches IPs related to the specified class of URLs.
    """
    def __init__(self, classification, matchaction):
        logging.getLogger('netassay.matchClass').info("matchURL.__init__(): called")
        metadata_engine = DNSMetadataEngine.get_instance()
        ruletype = AssayRule.CLASSIFICATION
        rulevalue = classification
        super(matchClass, self).__init__(metadata_engine, ruletype, rulevalue, matchaction)

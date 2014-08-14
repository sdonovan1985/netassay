# Copyright 2014 - Sean Donovan
# Defines the NetAssayMatch class and its children, as well as the Main Control
# Module (MCM). This is the primary file users import.

import logging

from pyretic.core.language import DynamicFilter
from pyretic.modules.netassay.assayrule import *
from pyretic.modules.netassay.me.dns.dnsme import *
from pyretic.modules.netassay.me.bgp.bgpme import *

class MainControlModuleException(Exception):
    pass

# All the new matchXXXX policies should inherit from here. They are all very
# similar, so there is tremendous reuse of code. 
# This is based on match from pyretic.core.langauge
class NetAssayMatch(DynamicFilter):
    def __init__(self, metadata_engine, ruletype, rulevalue):
        super(NetAssayMatch,self).__init__()
        loggername = "netassay." + self.__class__.__name__
        logging.getLogger(loggername).info("__init__(): called")
        self.logger = logging.getLogger(loggername)
        # probably should verify that the URL is vaid...
        self.me = metadata_engine 
        self.assayrule = AssayRule(ruletype, rulevalue)
        self.assayrule.set_update_callback(self.update_policy)
        self.me.new_rule(self.assayrule)
        self._classifier = self.generate_classifier()
        # Just in case there was some initialized values in the rule, 
        # actually use them:
        self.assayrule.finish_rule_group()

    def update_policy(self):
        listofrules = self.assayrule.get_list_of_rules()
        count = len(listofrules)
        if count == 0:
            self.policy = drop
        else:
            new_policy = union(listofrules)
            self.policy = new_policy
            
    

#    def eval(self, pkt):
#        for rule in self.assayrule.get_list_of_rules():
#            if rule.eval(pkt) == pkt:
#                return pkt
#        return set()

    def __repr__(self):
        retval = self.__class__.__name__ + ": " + self.assayrule.value
        for rule in self.assayrule.get_list_of_rules():
            retval = retval + "\n   " + str(rule)
        return retval

    def generate_classifier(self):
        return self.policy.compile()


    def __eq__(self, other):
        """
        Equality testing
        We don't actually care if the list of rules in the assayrule are the same,
        we just care about the type and values of the rules.
        """
        return (isinstance(other, type(self)) and 
                self.assayrule.type == other.assayrule.type and
                self.assayrule.value == other.assayrule.value)

    def intersect(self, pol):
        self.logger.debug("Intersect called")
        
        if pol == identity:
            return self
        elif pol == drop:
            return drop
        elif 0 == len(self.assayrule.get_list_of_rules()):
            return drop                          
        elif not (isinstance(pol, NetAssayMatch) or
                  isinstance(pol, Match)):
            raise TypeError(str(pol.__class__.__name__) + ":" + str(pol))

        current_min = identity
        if isinstance(pol, NetAssayMatch):
            if 0 == len(pol.assayrule.get_list_of_rules()):
                return drop
            
            for rule in pol.assayrule.get_list_of_rules():
                if current_min == None:
                    current_min = rule
                    continue
                current_min = current_min.intersect(rule)
        else:
            current_min = pol

        
        for rule in self.assayrule.get_list_of_rules():
            current_min = current_min.intersect(rule)

        self.logger.debug("current_min = " + str(current_min))
        return current_min


#    def __and__(self, pol):
#        raise MainControlModuleException(self.__class__.__name__+":__and__")

    def covers(self, other):
        if (other == self):
            return True
        # FIXME: Go through all the rules in the rule list and see if it would cover
        # This should not return false positives. What is 'covered' may change
        # may not matter much, as this will be run again when there's a policy update.
        # See remove_shadowed_cover_single() in core/classifier.py
        
        return False




class matchAS(NetAssayMatch):
    """
    matches IP prefixes related to the specified AS.
    """
    def __init__(self, asnum):
        logging.getLogger('netassay.matchAS').info("matchAS.__init__(): called")
        metadata_engine = BGPMetadataEngine.get_instance()
        ruletype = AssayRule.AS
        rulevalue = asnum
        super(matchAS, self).__init__(metadata_engine, ruletype, rulevalue)

class matchASPath(NetAssayMatch):
    """
    matches IP prefixes related to the specified AS.
    """
    def __init__(self, asnum):
        logging.getLogger('netassay.matchASPath').info("matchASPath.__init__(): called")
        metadata_engine = BGPMetadataEngine.get_instance()
        ruletype = AssayRule.AS_IN_PATH
        rulevalue = asnum
        super(matchASPath, self).__init__(metadata_engine, ruletype, rulevalue)

class matchURL(NetAssayMatch):
    """
    matches IPs related to the specified URL.
    """
    def __init__(self, url):
        logging.getLogger('netassay.matchURL').info("matchURL.__init__(): called")
        metadata_engine = DNSMetadataEngine.get_instance()
        ruletype = AssayRule.DNS_NAME
        rulevalue = url
        super(matchURL, self).__init__(metadata_engine, ruletype, rulevalue)

class matchClass(NetAssayMatch):
    """
    matches IPs related to the specified class of URLs.
    """
    def __init__(self, classification):
        logging.getLogger('netassay.matchClass').info("matchURL.__init__(): called")
        metadata_engine = DNSMetadataEngine.get_instance()
        ruletype = AssayRule.CLASSIFICATION
        rulevalue = classification
        super(matchClass, self).__init__(metadata_engine, ruletype, rulevalue)


#--------------------------------------
# MAIN CONTROL MODULE - MCM
#--------------------------------------
class AssayMainControlModule:
    INSTANCE = None
    # Singleton! should be initialized once by the overall control program!

    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists!")

        #Basic setup
        self.setup_logger()

        self.logger.info("AssayMCM.__init__(): called") 

        #DME setup
        self.dnsme = DNSMetadataEngine.get_instance() 
        self.dnsme_rules = self.dnsme.get_forwarding_rules()

        #BME setup
        self.bgpme = BGPMetadataEngine.get_instance()
        self.bgpme_rules = self.bgpme.get_forwarding_rules() #Doesn't have any...

        #General information
        self.logger.info("AssayMainControlModule Initialized!")

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = AssayMainControlModule()
        return cls.INSTANCE

    def setup_logger(self):
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        logfile = logging.FileHandler('netassay.log')
        logfile.setLevel(logging.DEBUG)
        logfile.setFormatter(formatter)
        self.logger = logging.getLogger('netassay')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(console)
        self.logger.addHandler(logfile)

    def set_update_policy_callback(self, cb):
        self.logger.info("AssayMCM:set_update_policy_callback(): called")
        self.logger.debug("    callback: " + str(cb))

    def get_assay_ruleset(self):
        """
        This should be called by the update_policy() routine to get any rules 
        that are specific to the MCM and it's children.
        In particular, this adds rules to redirect DNS response packets to the
        """
        self.logger.info("AssayMCM:get_assay_ruleset(): called")
        # Just keep adding on further rulesets as needed
        return self.dnsme_rules

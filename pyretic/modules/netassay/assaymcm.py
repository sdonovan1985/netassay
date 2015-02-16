# Copyright 2014 - Sean Donovan
# Defines the Main Control Module (MCM). This is the primary file users import.

import logging

from pyretic.modules.netassay.me.dns.dnsme import DNSMetadataEngine
from pyretic.modules.netassay.me.bgp.bgpme import BGPMetadataEngine
from pyretic.modules.netassay.rulelimiter import RuleLimiter

class MainControlModuleException(Exception):
    pass


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

    def init_complete(self):
        rl = RuleLimiter.get_instance()
        rl.start_delay()

    def setup_logger(self):
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
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

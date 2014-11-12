# Copyright 2014 - Sean Donovan
# BGP Metadata Engine - Based on the DNS Metadata Engine

import logging


from bgpqueries import BGPQueryHandler as BGPHandler
from pyretic.modules.netassay.assayrule import *
from pyretic.modules.netassay.netassaymatch import *
from pyretic.lib.corelib import *
from pyretic.lib.std import *
from pyretic.lib.query import *


class BGPMetadataEngineException(Exception):
    pass

class BGPMetadataEngine:
    INSTANCE = None        
    # Singleton! should be initialized by the MCM only!
    
    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists!")
        self.bgp_source = BGPHandler()
        self.entries = []
        self.logger = logging.getLogger('netassay.BGPME')

        # Register the different actions this ME can handle
        RegisteredMatchActions.register('AS', matchAS)
        RegisteredMatchActions.register('ASPath', matchASPath)

        self.logger.debug("BGPMetadataEngine.__init__(): finished")

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            logging.getLogger('netassay.BGPME').info("BGPMetadataEngine.get_instance(): Initializing BGPMetadataEngine")
            cls.INSTANCE = BGPMetadataEngine()
        return cls.INSTANCE
    
    def get_forwarding_rules(self):
        """
        This gets the forwarding rules that the BGP Classifier needs to work.
        """
        self.logger.info("BGPMetadataEngine.get_forwarding_rules(): called")

        return identity

    def new_rule(self, rule):
        self.logger.info("BGPMetadataEngine.new_rule(): called")
        self.entries.append(BGPMetadataEntry(self.bgp_source, self, rule))

    

class BGPMetadataEntry:
    def __init__(self, bgp_source, engine, rule ):
        logging.getLogger('netassay.BGPMetadataEntry').info("BGPMetadataEntry.__init__(): called")
        self.bgp_source = bgp_source
        self.engine = engine
        self.rule = rule
        self.logger = logging.getLogger('netassay.BGPMetadataEntry')
        
        #register for all the callbacks necessary
        if self.rule.type == AssayRule.AS:
            bgp_source.register_for_AS(
                self.handle_AS_callback,
                str(self.rule.value))
        elif self.rule.type == AssayRule.AS_IN_PATH:
            bgp_source.register_for_in_path(
                self.handle_AS_callback,
                str(self.rule.value))

        #setup based on initial BGP data
        if self.rule.type == AssayRule.AS:
            new_prefixes = self.bgp_source.query_from_AS(self.rule.value)
            for prefix in new_prefixes:
                self.rule.add_rule(Match(dict(srcip=IPPrefix(prefix))))
                self.rule.add_rule(Match(dict(dstip=IPPrefix(prefix))))
        elif self.rule.type == AssayRule.AS_IN_PATH:
            new_prefixes = self.bgp_source.query_in_path(self.rule.value)
            for prefix in new_prefixes:
                self.rule.add_rule(Match(dict(srcip=IPPrefix(prefix))))
                self.rule.add_rule(Match(dict(dstip=IPPrefix(prefix))))

        #TODO: need to handle withdrawals!

    def handle_AS_callback(self, prefix):
        self.logger.info("BGPMetatdataEntry.handle_AS_callback(): called with prfix " + prefix)
        self.rule.add_rule(Match(dict(srcip=IPPrefix(prefix))))
        self.rule.add_rule(Match(dict(dstip=IPPrefix(prefix))))


#--------------------------------------
# NetAssayMatch subclasses
#--------------------------------------

class matchAS(NetAssayMatch):
    """
    matches IP prefixes related to the specified AS.
    """
    def __init__(self, asnum, matchaction):
        logging.getLogger('netassay.matchAS').info("matchAS.__init__(): called")
        metadata_engine = BGPMetadataEngine.get_instance()
        ruletype = AssayRule.AS
        rulevalue = asnum
        super(matchAS, self).__init__(metadata_engine, ruletype, rulevalue, matchaction)

class matchASPath(NetAssayMatch):
    """
    matches IP prefixes related to the specified AS.
    """
    def __init__(self, asnum, matchaction):
        logging.getLogger('netassay.matchASPath').info("matchASPath.__init__(): called")
        metadata_engine = BGPMetadataEngine.get_instance()
        ruletype = AssayRule.AS_IN_PATH
        rulevalue = asnum
        super(matchASPath, self).__init__(metadata_engine, ruletype, rulevalue, matchaction)

# Copyright 2014 - Sean Donovan
# Defines the NetAssayMatch class

import logging

from pyretic.core.language import DynamicFilter, drop, union
#from pyretic.core.language import DynamicFilter, drop, parallel
from pyretic.modules.netassay.assayrule import *


# All the new matchXXXX policies should inherit from here. They are all very
# similar, so there is tremendous reuse of code. 
# This is based on match from pyretic.core.langauge

class NetAssayMatch(DynamicFilter):
    def __init__(self, metadata_engine, ruletype, rulevalue, matchaction):
        super(NetAssayMatch,self).__init__()
        loggername = "netassay." + self.__class__.__name__
        logging.getLogger(loggername).info("__init__(): called")
        self.logger = logging.getLogger(loggername)
        # probably should verify that the URL is vaid...
        self.me = metadata_engine 
        self.matchaction = matchaction
        self.assayrule = AssayRule(ruletype, rulevalue)
        self.assayrule.set_update_callback(self.update_policy)
        self.me.new_rule(self.assayrule)
        self._classifier = self.generate_classifier()

    def update_policy(self):
        listofrules = self.assayrule.get_list_of_rules()
        count = len(listofrules)
        if count == 0:
            self.policy = drop
        else:
            new_policy = union(listofrules)
#            new_policy = parallel(listofrules)
            self.policy = new_policy

        self.matchaction.children_update()

#    def eval(self, pkt):
#        for rule in self.assayrule.get_list_of_rules():
#            if rule.eval(pkt) == pkt:
#                return pkt
#        return set()

    def __repr__(self):
        retval = self.__class__.__name__ + ": " + str(self.assayrule.value)
#        for rule in self.assayrule.get_list_of_rules():
#            retval = retval + "\n   " + str(rule)
        return retval

    def generate_classifier(self):
        self.logger.debug("generate_classifier called")
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

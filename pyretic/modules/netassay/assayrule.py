# Copyright 2014 - Sean Donovan
# This defines rules for NetAssay.

import logging

class AssayRule:
    # Ruletypes!
    CLASSIFICATION = 1
    AS             = 2
    AS_IN_PATH     = 3
    DNS_NAME       = 4
    
    classtypes = [CLASSIFICATION, AS, AS_IN_PATH, DNS_NAME]

    def __init__(self, ruletype, value, rule_update_cbs=[]):
        logging.getLogger('netassay.AssayRule').info("AssayRule.__init__(): called")
        self.logger = logging.getLogger('netassay.AssayRule')
        self.type = ruletype
        self.value = value
        self.update_callbacks = rule_update_cbs

        self.logger.debug("   self.type  = " + str(ruletype))
        self.logger.debug("   self.value = " + value)

        #Rules should be proper pyretic rules
        #The _rule_list is composed in parallel to get the policy of this rule
        #This allows for FAR easier manipulation of the rules that are active.
        self._rule_list = []  

    def set_update_callback(self, cb):
        #these callbacks take an AssayRule as input
        self.update_callbacks.append(cb)

    def add_rule(self, newrule):
        # Does not check to see if it's a duplicate rule, as this allows the 
        # same rule to be installed for different reasons, and they can be 
        # removed individually.
        self._rule_list.append(newrule)
        self._update_rules()

    def add_rule_group(self, newrule):
        # Does not check to see if it's a duplicate rule, as this allows the 
        # same rule to be installed for different reasons, and they can be 
        # removed individually.
        self._rule_list.append(newrule)

    def finish_rule_group(self):
        self._update_rules()
        
    def has_rule(self, newrule):
        return newrule in self._rule_list

    def remove_rule(self, newrule):
        self._rule_list.remove(newrule)
        self._update_rules()           
    
    def remove_rule_group(self, newrule):
        self._rule_list.remove(newrule)

    def _update_rules(self):
        for cb in self.update_callbacks:
            self.logger.debug("calling " + str(cb))
            cb()

    def get_list_of_rules(self):
        return self._rule_list

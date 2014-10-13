# Copyright 2014 - Sean Donovan
# This defines rules for NetAssay.

import logging
from ipaddr import IPv4Network
from pyretic.core.language import Match


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

        # Rules should be proper pyretic rules
        # _raw_xxx_rules is the naive set of rules that are manipulated. When 
        # self.get_list_of_rules() is called, self._rule_list is populated 
        # without any redundant rules.
        # The _rule_list is composed in parallel to get the policy of this rule
        # This allows for FAR easier manipulation of the rules that are active.
        self._raw_srcmac_rules = []
        self._raw_dstmac_rules = []
        self._raw_srcip_rules = []
        self._raw_dstip_rules = []
        self._raw_srcport_rules = []
        self._raw_dstport_rules = []
        self._raw_protocol_rules = []
        self._raw_other_rules = []
        self._rule_list = []


    def set_update_callback(self, cb):
        # These callbacks take an AssayRule as input
        self.update_callbacks.append(cb)

    def add_rule(self, newrule):
        # Shortcut function. Likely the most commonly used one.
        self.add_rule_group(newrule)
        self._update_rules()

    def add_rule_group(self, newrule):
        # Does not check to see if it's a duplicate rule, as this allows the 
        # same rule to be installed for different reasons, and they can be 
        # removed individually.
        if isinstance(newrule, Match):
            #FIXME: Can this optimize over multiple items?
            if len(newrule.map.keys()) == 1:
                key = newrule.map.keys()[0] # get the key of the only value
                if (key == 'srcmac'):
                    self._raw_srcmac_rules.append(newrule)
                elif (key == 'dstmac'):
                    self._raw_dstmac_rules.append(newrule)
                elif (key == 'srcip'):
                    self._raw_srcip_rules.append(newrule)
                elif (key == 'dstip'):
                    self._raw_dstip_rules.append(newrule)
                elif (key == 'protocol'):
                    self._raw_protocol_rules.append(newrule)
                else:
                    self._raw_other_rules.append(newrule)
            else:
                self._raw_other_rules.append(newrule)
        else:
            self._raw_other_rules.append(newrule)

        # FIXME: Kick off a timer just in case the group isn't finished correctly?

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
        # check if rules have changed
        temp_rule_list = self._generate_list_of_rules()
        # If they're the same, do nothing
        if set(temp_rule_list) == set(self._rule_list):
            self.logger.debug("_update_rules: No changes in rule list")
        else:
            # if they're different, call the callbacks
            self._rule_list = temp_rule_list
            for cb in self.update_callbacks:
                self.logger.debug("_update_rules: calling " + str(cb))
                cb()

    def _generate_list_of_rules(self):
        # This generates teh list of rules and returns them This allows us
        # to check to see if there's a difference between versions
        temp_rule_list = []
        
        # Append non-optimized rules, remove dupes
        for rule in self._raw_other_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)
        for rule in self._raw_protocol_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)
        for rule in self._raw_srcmac_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)
        for rule in self._raw_dstmac_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)
        for rule in self._raw_srcport_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)
        for rule in self._raw_dstport_rules:
            if rule not in temp_rule_list:
                temp_rule_list.append(rule)

        # Optimized rules 
        # ipaddr documentation: https://code.google.com/p/ipaddr-py/wiki/Using3144
        # 
        def optimize_ip(rule_list, ip_rule_list, src_or_dst):
            temp_ip_rules = sorted(ip_rule_list, key=lambda ad: ad.map[src_or_dst].prefixlen)
            for rule in temp_ip_rules:
                # +1 is to skip the current rule...
                for interior_rule in temp_ip_rules[temp_ip_rules.index(rule)+1:]:
                    if interior_rule.map[src_or_dst] in rule.map[src_or_dst]:
                        temp_ip_rules.remove(interior_rule)
            for rule in temp_ip_rules:
                if rule not in rule_list:
                    rule_list.append(rule)
        
        optimize_ip(temp_rule_list, self._raw_srcip_rules, 'srcip')
        optimize_ip(temp_rule_list, self._raw_dstip_rules, 'dstip')



        return temp_rule_list

    def get_list_of_rules(self):
        self._rule_list = self._generate_list_of_rules()
        return self._rule_list




    def _display_for_testing(self):
        if len(self._raw_srcmac_rules) > 0:
            print "_raw_srcmac_rules:"
            for rule in self._raw_srcmac_rules:
                print "    " + str(rule)
            print ""
        
        if len(self._raw_dstmac_rules) > 0:
            print "_raw_dstmac_rules:"
            for rule in self._raw_dstmac_rules:
                print "    " + str(rule)
            print ""

        if len(self._raw_srcip_rules) > 0:
            print "_raw_srcip_rules:"
            for rule in self._raw_srcip_rules:
                print "    " + str(rule)
            print ""
        
        if len(self._raw_dstip_rules) > 0:
            print "_raw_dstip_rules:"
            for rule in self._raw_dstip_rules:
                print "    " + str(rule)
            print ""

        if len(self._raw_srcport_rules) > 0:
            print "_raw_srcport_rules:"
            for rule in self._raw_srcport_rules:
                print "    " + str(rule)
            print ""
        
        if len(self._raw_dstport_rules) > 0:
            print "_raw_dstport_rules:"
            for rule in self._raw_dstport_rules:
                print "    " + str(rule)
            print ""

        if len(self._raw_protocol_rules) > 0:
            print "_raw_protocol_rules:"
            for rule in self._raw_protocol_rules:
                print "    " + str(rule)
            print ""

        if len(self._raw_other_rules) > 0:
            print "_raw_other_rules:"
            for rule in self._raw_other_rules:
                print "    " + str(rule)
            print ""

        if len(self._rule_list) > 0:
            print "_rule_list"
            for rule in self._rule_list:
                print "    " + str(rule)
            print ""

# Unit tests to verify that optimizations do, in fact, work.
if __name__ == "__main__":
    
    from pyretic.core.network import IPAddr

    # Remove duplicates test
    dupe = AssayRule(AssayRule.DNS_NAME, 'dummy')
    dupe.add_rule(Match(dict(srcip=IPAddr("1.2.3.4"))))
    dupe.add_rule(Match(dict(srcip=IPAddr("1.2.3.4"))))
    dupe.add_rule(Match(dict(dstip=IPAddr("1.2.3.4"))))
    dupe.add_rule(Match(dict(srcmac="aa:bb:cc:dd:ee:ff")))
    dupe.add_rule(Match(dict(srcmac="aa:bb:cc:dd:ee:ff")))

    print "DUPLICATES TEST BEGIN"
    dupe._display_for_testing()
    print "DUPLICATES TEST END"
    print ""
    


    # IP Optimization
    optimization = AssayRule(AssayRule.DNS_NAME, 'dummy')
    optimization.add_rule(Match(dict(srcip=IPAddr("1.2.3.4"))))
    optimization.add_rule(Match(dict(srcip=IPv4Network("1.2.3.0/24"))))

    optimization.add_rule(Match(dict(srcip=IPv4Network("2.3.4.0/24"))))
    optimization.add_rule(Match(dict(srcip=IPv4Network("2.3.0.0/16"))))


    print "IP OPTIMIZATION TEST BEGIN"
    optimization._display_for_testing()
    print "IP OPTIMIZATION TEST END"

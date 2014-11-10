# Copyright 2014 - Sean Donovan
# This defines rules for NetAssay.

import logging
from ipaddr import IPv4Network, CollapseAddrList
from pyretic.core.language import Match, basic_headers, tagging_headers


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
                elif (key == 'srcport'):
                    self._raw_srcport_rules.append(newrule)
                elif (key == 'dstport'):
                    self._raw_dstport_rules.append(newrule)
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
        # In expected order of being true. Please rearrange as appropriate.
        return ((newrule in self._raw_srcip_rules) |
                (newrule in self._raw_dstip_rules) |
                (newrule in self._raw_srcmac_rules) |
                (newrule in self._raw_dstmac_rules) |
                (newrule in self._raw_srcport_rules) |
                (newrule in self._raw_dstport_rules) |
                (newrule in self._raw_protocol_rules) |
                (newrule in self._raw_other_rules))

    def remove_rule(self, newrule):
        # Shortcut function. Likely the most commonly used one.
        self.remove_rule_group(newrule)
        self._update_rules()           
    
    def remove_rule_group(self, newrule):
        # See has_rule for ordering decision.
        if newrule in self._raw_srcip_rules:
            self._raw_srcip_rules.remove(newrule)
        elif newrule in self._raw_dstip_rules:
            self._raw_dstip_rules.remove(newrule)
        elif newrule in self._raw_srcmac_rules:
            self._raw_srcmac_rules.remove(newrule)
        elif newrule in self._raw_dstmac_rules:
            self._raw_dstmac_rules.remove(newrule)
        elif newrule in self._raw_srcport_rules:
            self._raw_srcport_rules.remove(newrule)
        elif newrule in self._raw_dstport_rules:
            self._raw_dstport_rules.remove(newrule)
        elif newrule in self._raw_protocol_rules:
            self._raw_protocol_rules.remove(newrule)
        elif newrule in self._raw_other_rules:
            self._raw_other_rules.remove(newrule)


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

#        for rule in self._raw_other_rules:
#            if rule not in temp_rule_list:
#                temp_rule_list.append(rule)


        # Optimized rules 
        # ipaddr documentation: https://code.google.com/p/ipaddr-py/wiki/Using3144
        def optimize_ip(rule_list, ip_rule_list, src_or_dst):
            to_remove_list = []
            temp_ip_rules = sorted(ip_rule_list, key=lambda ad: ad.map[src_or_dst].prefixlen)
            for rule in temp_ip_rules:
                # +1 is to skip the current rule...
                for interior_rule in temp_ip_rules[temp_ip_rules.index(rule)+1:]:
                    if interior_rule.map[src_or_dst] in rule.map[src_or_dst]:
                        to_remove_list.append(interior_rule)
                        break

            for rule in to_remove_list:
                temp_ip_rules.remove(rule)

            for rule in temp_ip_rules:
                if rule not in rule_list:
                    rule_list.append(rule)

        # This is a replacement for optimize_ip(), but I'm leaving the other
        # just in case the old one is faster.
        def optimize_ip_prefix(rule_list, ip_rule_list, src_or_dst):
            prefix_list = []
            for rule in ip_rule_list:
                prefix_list.append(rule.map[src_or_dst])

            for prefix in CollapseAddrList(prefix_list):
                rule_list.append(Match({src_or_dst: prefix}))           
            

#        optimize_ip(temp_rule_list, self._raw_srcip_rules, 'srcip')
#        optimize_ip(temp_rule_list, self._raw_dstip_rules, 'dstip')
        optimize_ip_prefix(temp_rule_list, self._raw_srcip_rules, 'srcip')
        optimize_ip_prefix(temp_rule_list, self._raw_dstip_rules, 'dstip')


        # Optimizing others - function may be useful outside of here.
        def optimize_others(rule_list, other_rule_list):
            headers =  ['srcmac','dstmac','srcport','dstport',
                        'ethtype','protocol','tos']
            ips = ['srcip','dstip']

            temp_other_rules = list(other_rule_list)

            # Separate out the IP related rules
            temp_srcip_rules = []
            temp_dstip_rules = []
            to_remove_list = []

            # First pass is pretty easy, doesn't handle IP addresses
            for rule in temp_other_rules:
                for header in headers:
                    if header in rule.map.keys():
                        to_check = Match({header : rule.map[header]})
                        if to_check in rule_list:
                            to_remove_list.append(rule)
                            break
            for rule in to_remove_list:
                temp_other_rules.remove(rule)


            # Second pass handles IPs. These are different, only because they
            # can easily be subsumed by prefixes.
            for rule in temp_other_rules:
                if 'srcip' in rule.map.keys():
                    temp_srcip_rules.append(rule)
                elif 'dstip' in rule.map.keys():
                    temp_srcip_rules.append(rule)
            for rule in temp_srcip_rules:
                temp_other_rules.remove(rule)
            for rule in temp_dstip_rules:
                temp_other_rules.remove(rule)


            temp_srcip_rules = sorted(temp_srcip_rules, key=lambda ad: ad.map['srcip'].prefixlen)
            temp_dstip_rules = sorted(temp_dstip_rules, key=lambda ad: ad.map['dstip'].prefixlen)

            to_remove_list = []
            for rule in temp_srcip_rules:
                for existing_rule in rule_list:
                    if 'srcip' in existing_rule.map.keys():
                        if rule.map['srcip'] in existing_rule.map['srcip']:
                            to_remove_list.append(rule)
                            break

            for rule in to_remove_list:
                temp_srcip_rules.remove(rule)

            to_remove_list = []
            for rule in temp_dstip_rules:
                for existing_rule in rule_list:
                    if 'dstip' in existing_rule.map.keys():
                        if rule.map['dstip'] in existing_rule.map['dstip']:
                            to_remove_list.append(rule)
                            break
            for rule in to_remove_list:
                temp_dstip_rules.remove(rule)



            for rule in temp_other_rules:
                if rule not in rule_list:
                    rule_list.append(rule)
            for rule in temp_srcip_rules:
                if rule not in rule_list:
                    rule_list.append(rule)
            for rule in temp_dstip_rules:
                if rule not in rule_list:
                    rule_list.append(rule)

        optimize_others(temp_rule_list, self._raw_other_rules)

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
    dupe.add_rule_group(Match(dict(srcip=IPAddr("1.2.3.4"))))
    dupe.add_rule_group(Match(dict(srcip=IPAddr("1.2.3.4"))))
    dupe.add_rule_group(Match(dict(dstip=IPAddr("1.2.3.4"))))
    dupe.add_rule_group(Match(dict(srcmac="aa:bb:cc:dd:ee:ff")))
    dupe.add_rule_group(Match(dict(srcmac="aa:bb:cc:dd:ee:ff")))


    print "DUPLICATES TEST BEGIN"
    dupe.finish_rule_group()
    dupe._display_for_testing()
    print "DUPLICATES TEST END"
    print ""
    
    # IP Optimization
    optimization = AssayRule(AssayRule.DNS_NAME, 'dummy')
    optimization.add_rule_group(Match(dict(srcip=IPAddr("1.2.3.4"))))
    optimization.add_rule_group(Match(dict(srcip=IPv4Network("1.2.3.0/24"))))

    optimization.add_rule_group(Match(dict(srcip=IPv4Network("2.3.4.0/24"))))
    optimization.add_rule_group(Match(dict(srcip=IPv4Network("2.3.0.0/16"))))

    optimization.add_rule_group(Match(dict(srcip=IPv4Network("3.2.0.0/16"))))
    optimization.add_rule_group(Match(dict(srcip=IPv4Network("3.3.0.0/16"))))

    optimization.add_rule_group(Match(dict(srcip=IPv4Network("4.2.0.0/16"))))
    optimization.add_rule_group(Match(dict(srcip=IPv4Network("4.3.0.0/16"))))
    optimization.add_rule_group(Match(dict(srcip=IPv4Network("4.3.4.0/24"))))


    print "IP OPTIMIZATION TEST BEGIN"
    optimization.finish_rule_group()
    optimization._display_for_testing()
    print "IP OPTIMIZATION TEST END"
    print ""


    # Others optimization
    others = AssayRule(AssayRule.DNS_NAME, 'dummy')
    others.add_rule_group(Match(dict(srcip=IPAddr("1.2.3.4"))))
    others.add_rule_group(Match(dict(srcip=IPAddr("1.2.3.4"),srcport='1234')))

    others.add_rule_group(Match(dict(srcip=IPAddr("2.3.4.5"))))
    others.add_rule_group(Match(dict(srcport='2345')))
    others.add_rule_group(Match(dict(srcip=IPAddr("2.3.4.5"),srcport='2345')))

    others.add_rule_group(Match(dict(srcip=IPv4Network("3.4.5.0/16"))))
    others.add_rule_group(Match(dict(srcip=IPAddr("3.4.5.6"),srcport='2345')))


    print "OTHERS OPTIMIZATION TEST BEGIN"
    others.finish_rule_group()
    others._display_for_testing()
    print "OTHERS OPTIMIZATION TEST END"

# Copyright 2014 - Sean Donovan
# Defines the NetAssayWindow class
# NetAssayWindow keeps track of all the filtering policies that are used to
# get information needed to filter by windows. For instance, if we wanted to 
# know which IP address have visited cnn.com in the past hour, we'd need to
# get copies of connections opened to cnn.com. NetAssayWindow would keep track
# of this.

import logging

from pyretic.core.language import DynamicPolicy, match, Match, drop, disjoint
from pyretic.modules.netassay.netassaymatch import NetAssayMatch
from pyretic.lib.query import *
from pyretic.modules.netassay.lib.py_timer import py_timer as Timer
from ryu.lib import addrconv
from datetime import datetime, timedelta

class NetAssayWindow: 
    INSTANCE = None

    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists!")

        self.list_of_forwarding_rules = []

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = NetAssayWindow()
        return cls.INSTANCE

    def get_forwarding_rules(self):
        return disjoint(self.list_of_forwarding_rules)

    def register_forwarding_rule(self, rule):
        self.list_of_forwarding_rules.append(rule)
    
    def deregister_forwarding_rule(self, rule):
        self.list_of_forwarding_rules.remove(rule)
        

class visited(DynamicFilter):
    '''
    Returns match statments for all the IP addresses that have visited whatever
    match action is defined by kwargs.
    '''
    def __init__(self, time_window, **kwargs):
        super(visited,self).__init__()
        loggername = "netassay." + self.__class__.__name__
        logging.getLogger(loggername).info("__init__(): called")
        self.logger = logging.getLogger(loggername)
        self.naw = NetAssayWindow.get_instance()

        self.time_window = time_window
        self.kwargs_filter = match(**kwargs)
        
        self.visit_list = []
        self.timer = None

        self.important_pkts = packets(1, ['srcmac', 'dstmac', 'srcip', 'dstip', 'srcport', 'dstport', 'protocol'])
        self.important_pkts.register_callback(self._pkt_callback)
        self.registered_rule = self.kwargs_filter >> self.important_pkts

        self.naw.register_forwarding_rule(self.registered_rule)
    
    def __del__(self):
        if self.timer != None:
            self.timer.cancel()
        self.naw.deregister_forwaring_rule(self.registered_rule)


    def _pkt_callback(self, pkt):
        ''' 
        If IP already is in the visit list, update the time. 
        If IP not in the visit list, add to visit list with new timestamp and
        call update_policy().
        '''

        # Figure out which IP is in the registered filter right now
        # FIXME: THIS IS VERY DIRTY. It's looking through the match() action,
        # then through the Match() and NetAssayMatch() actions, extract their
        # IP address that are involved... Possible problems.
        def list_of_ips(match_action):
            ip_list = []
            if match_action._traditional_match is not None:
                if ('srcip' in match_action._traditional_match.map.keys()):
                    ip_list.append(match_action._traditional_match.map['srcip'])
                if ('dstip' in match_action._traditional_match.map.keys()):
                    ip_list.append(match_action._traditional_match.map['dstip'])
            if match_action._netassay_match is not None:
                ip_list.append(
                    match_action._netassay_match.assayrule._raw_srcip_rules)
                ip_list.append(
                    match_action._netassay_match.assayrule._raw_dstip_rules)

        ips = list_of_ips(self.kwargs_filter)
        ipaddr = None
        if pkt['dstip'] in ips:
            ipaddr = pkt['dstip']
        elif pkt['srcip'] in ips:
            ipaddr = pkt['srcip']
        # END OF FIXME

        # Build up the dict to lookup the pkt, include timestamp
        new_pkt = {}
        new_pkt['ip'] = ipaddr
        new_pkt['timestamp'] = datetime.now() + timedelta(seconds=self.timewindow)

        # Policy is updated whenever a new entry is added to the list
        # Timer is updated whenever the first entry in the visit_list is changed
        need_to_update_policy = False 
        need_to_update_timer  = False
        if self._in_visit_list(new_pkt):
            need_to_update_timer = self._remove_from_visit_list(new_pkt)
        else:
            need_to_update_policy = True
        self.visit_list.append(new_pkt)

        if need_to_update_timer:
            self._restart_timer
        if need_to_update_policy:
            self.update_policy()

    def _age_out(self):
        '''
        Once something hits the timelime in self.time_window, remove it from
        the visit list and call _restart_timer() and update_policy().
        '''
        if self.timer != None:
            self.timer.cancel()

        if (len(self.visit_list) > 1):
            self.visit_list = self.visit_list[1:]
            self._restart_timer()
        else:
            self.visit_list = []
        self.update_policy()


    def _restart_timer(self):
        '''
        Restarts the timer. This is likely due to an update to the visit_list.
        Look at the first entry to the visit_list, get a timedelta, and send it 
        to the timer.
        '''
        if self.timer != None:
            self.timer.cancel()

        delta = self.visit_list[0]['timestamp'] - datetime.now()

        self.timer = Timer(delta.total_seconds(), self._age_out)
        self.timer.start()

    def update_policy(self):
        '''
        When there is a change in the visit list (addition or subtraction),
        update the policy that's being returned.
        '''
        list_of_rules = []

        for entry in self.visit_list:
            list_of_rules.append(Match({'srcip' : entry['ip']}))
            list_of_rules.append(Match({'dstip' : entry['ip']}))

        count = len(list_of_rules)
        if count == 0:
            self.policy = drop
        else:
            new_policy = union(list_of_rules)
            self.policy = new_policy

    def __repr__(self):
        retval = self.__class__.__name__ + ":"
        retval = retval + "\n    Window: " + str(self.time_window)
        retval = retval + "\n    " + str(self.kwargs_filter)

    def _in_visit_list(self, new_pkt):
        for entry in self.visit_list:
            if (entry['ip'] == new_pkt['ip']):
                return True
        # If it's not in the visit list, return False)
        return False        

    def _remove_from_visit_list(self, new_pkt):
        '''
        Returns whether or not an update to the timer is needed.
        This occurs when the first item in the list is removed, as it was what 
        the timer was based on.
        '''
        update_needed = True
        for entry in self.visit_list:
            if (entry['ip'] == new_pkt['ip']):
                self.visit_list.remove(entry)
                return update_needed
            update_needed = False

    def generate_classifier(self):
        self.logger.debug("generate_classifier called")
        self.policy.compile()    

    def __eq__(self, other):
        return (isinstance(other, type(self)) and
                self.kwargs_filter == other.kwargs_filter)


    def intersect(self, pol):
        self.logger.debug("Intersect called")
        
        if pol == identity:
            return self
        elif pol == drop:
            return drop
        elif 0 == len(self.visit_list):
            return drop
        #FIXME - netassaymatch.py line 78
        
        return pol.intersect(self.policy())

    def covers(self, other):
        # FIXME: Stolen from NetAssayMatch. May need to update.
        if (other == self):
            return True
        return False
                          
    
    

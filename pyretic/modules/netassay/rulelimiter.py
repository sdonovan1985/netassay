# Copyright 2014 - Sean Donovan
# This is a global tracking mechanism that tracks all changes by AssayRules and
# tells them when to install rules.

import logging
from pyretic.modules.netassay.lib.py_timer import py_timer as Timer

class RuleLimiter:
    INSTANCE = None

    # TIMEOUT how often to update the list.
    # DELAY_MULTIPLIER is the damping parameter
    # COUNTS are the number of historical counts to keep track of. 
    # Tracks a total of rules within TIMEOUT * (COUNTS + 1) seconds
    TIMEOUT = 0.1
    DELAY_MULTIPLIER = 0.01
    COUNTS = 9

    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists")
        logging.getLogger('netassay.RuleLimiter').info("RuleLimiter.__init__(): called")
        self.logger = logging.getLogger('netassay.RuleLimiter')

        self._logged_counts = [0] * self.COUNTS
        self._current_count = 0
        self._timer = None

        # Start the timer to get count rates
        self._reset_timer()
        
    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = RuleLimiter()
        return cls.INSTANCE

    def get_delay(self):
        '''
        Whenever a new rule comes in, this is called. 
            It returns 0 if the rule should be installed immediately.
            It returns a delay in fraction of a second.
        '''
        delay = sum(self._logged_counts) + self._current_count
        self._current_count = self._current_count + 1
#        self.logger.debug("DELAY -------- " + str(delay * self.DELAY_MULTIPLIER) + "   " + str(self._logged_counts))
        return delay * self.DELAY_MULTIPLIER
            
    def _reset_timer(self):
        '''
        Initializes the timer
        '''
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        self._timer = Timer(self.TIMEOUT, self._update_counts)
#        self.logger.debug("_reset_timer now!")
        self._timer.start()

    def _update_counts(self):
#        self.logger.debug("_update_counts now! counts " + str(self._current_count) + " old: " + str(self._logged_counts))
        self._logged_counts = self._logged_counts[0:self.COUNTS-1]
        self._logged_counts.insert(0, self._current_count)
        self._current_count = 0
        self._reset_timer()

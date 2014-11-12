# Copyright 2014 - Sean Donovan
# This is a global tracking mechanism that tracks all changes by AssayRules and
# tells them when to install rules.

import logging

class RuleLimiter:
    INSTANCE = None

    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists")
        logging.getLogger('netassay.RuleLimiter').info("RuleLimiter.__init__(): called")
        self.logger = logging.getLogger('netassay.RuleLimiter')

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
        return 0.01
            

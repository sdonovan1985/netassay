# This is from another of my projects located:
# https://github.com/sdonovan1985/py-timer

# Copyright 2014 Sean Donovan
# List-based timer that only has one timer active at a time. When a new timer 
# request comes in, the timer will insert into the list at the appropriate 
# location. If it's to pop soonest, it will stop the current timer, and start a
# timer for the newest time. This has only one timer outstanding at a time, 
# rather than starting a timer for each one.
# 
# This should be used by using the following import statement:
#     from py_timer import py_timer as Timer
# This will remap Timer to the new timer class. 

import logging
from datetime import datetime, timedelta
from threading import Timer, Lock
import pprint

class py_timer_manager:
    INSTANCE = None
    
    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("Instance already exists!")

        self.list_of_inactive_timers = []
        self.list_of_active_timers = []
        self.thread_timer = None
        self.timerlist_lock = Lock()

    @classmethod
    def get_instance(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = py_timer_manager()
        return cls.INSTANCE
    
    def insert_into_list(self, timer):
        # New inactive timer
        self.list_of_inactive_timers.append(timer)

    def start_timer(self, timer):
        # Move a timer from the inactive list
        first = False
        
        self.list_of_inactive_timers.remove(timer)
        timer.calculate_expiration()
        
        # Insert based on time to expire. O(n) time.
        if len(self.list_of_active_timers) == 0:
            self.list_of_active_timers.insert(0, timer)
            first = True
        else:
            inserted = False
            for x in range(len(self.list_of_active_timers)):
                if self.list_of_active_timers[x].expiration > timer.expiration:
                    self.list_of_active_timers.insert(x, timer)
                    inserted = True
                    if x == 0:
                        first = True
                    break
            if inserted == False:
                self.list_of_active_timers.append(timer)
        
        # If the timer is the next to expire, stop the running timer
        if first == True:
            if self.thread_timer is not None:
                self.thread_timer.cancel()
        
            # Call _restart_timer()
            self._restart_timer()

    def is_timer_alive(self, timer):
        return (timer in self.list_of_active_timers)

    def remove_from_list(self, timer):
        if timer in self.list_of_inactive_timers:
            self.list_of_inactive_timers.remove(timer)
        elif timer in self.list_of_active_timers:
            # If it's the first in the list_of_active_timers, need to do extra
            if self.list_of_active_timers[0] == timer:
                self.thread_timer.cancel()
                self.list_of_active_timers.remove(timer)
                self._restart_timer()
            else:
                self.list_of_active_timers.remove(timer)
        # else: trying to cancel an already cancelled timer shouldn't blow up.

    def _restart_timer(self):
        ''' 
        This is what happens when things expire, the timer needs to be stopped
        due to removal of entries, or insertion of new entries at the beginning
        of the list_of_active_timers, etc. Pretty much the go-to function.
        '''
        with self.timerlist_lock:
            if self.thread_timer is not None:
                self.thread_timer.cancel()

            # Call back anything that's expired
            now = datetime.now()
            entries_to_remove = []
            for entry in self.list_of_active_timers:
                if entry.expiration <= now:
                    entries_to_remove.append(entry)
                    entry.call_function()
            for entry in entries_to_remove:
                    self.list_of_active_timers.remove(entry)

        
            # Start the first timer that's not expired
            if len(self.list_of_active_timers) != 0:
                delta = self.list_of_active_timers[0].expiration - now
                self.thread_timer = Timer(delta.total_seconds(), 
                                          self._restart_timer)
                # Set the daemon flag: If the main program dies, this will die too
                # prevents the case where a 3 day long timer for a long lived DNS
                # entry keeps the program running for ages.
                self.thread_timer.daemon = True
                try:
                    self.thread_timer.start()
                except RuntimeError:
                    # Don't worry about this one.
                    return


class py_timer:
    def __init__(self, interval, function, args=[], kwargs={}):
        ''' 
        In order to behave like the current threading.Timer class, use the same
        interface. the py_timer is mostly a tracking structure, while 
        py_timer_manager (above) works the timer magic.
        interval, function, args[], kwargs{}
        '''
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self.expiration = None

        # Get the instance of the py_timer_manager, insert into list
        self.manager = py_timer_manager.get_instance()
        self.manager.insert_into_list(self)

    def calculate_expiration(self):
        self.expiration = datetime.now() + timedelta(seconds=self.interval)

    def start(self):
        self.manager.start_timer(self)

    def cancel(self):
        self.manager.remove_from_list(self)
    
    def is_alive(self):
        self.manager.is_timer_alive(self)
    
    def call_function(self):
        ''' Calls the expiration function. Lots of splatting. '''
        if (len(self.args) == 0):
                pass
        if (len(self.kwargs) == 0):
                pass

        if ((len(self.args) == 0) and len(self.kwargs) == 0):
            self.function()
        elif ((len(self.args) != 0) and len(self.kwargs) == 0):
            self.function(*self.args)
        elif ((len(self.args) == 0) and len(self.kwargs) != 0):
            self.function(**self.kwargs)
        else:
            self.function(*self.args, **self.kwargs)

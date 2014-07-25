from datetime import datetime, timedelta
from threading import Timer


# Creating a new entry takes at least 4 parameters.
#   IP    - The IP address (as a string!) of the website
#   names - a list of website names (url/uri) associated with the IP address
#   classification - the type of site that this is. It's currently a string.
#   ttl   - Time to live, which is a field in the DNS frame. It's the number of 
#           seconds that the entry is valid for
# There is one optional parameter.
#   expiry - This is the time, as a datetime, that the entry expires. If it is
#            None (the default), the expiry time will be now + ttl seconds.
#
# It has 3 public methods:
#   print_entry()   - This prints the entry with an offset (that's is a string) 
#                     and can be anything from spaces to text.
#   is_expired()    - This returns if the entry is expired or not. By default,
#                     this is checked based on the current time.
#   update_expiry() - Pass in a new TTL, and the TTL and new expiry will be set
#   register_timeout_callback() - takes a function of the form func(addr,entry) 
#                     where 'addr' is the IP address of the entry and 'entry' 
#                     will be the the entry that's expiring.
class DNSClassifierEntry:
    def __init__(self, IP, names, classification, ttl, expiry=None):
        self.IP = IP
        self.names = names
        self.classification = classification
        self.ttl = ttl
        if expiry is datetime:
            self.expiry = expiry
        else:
            self.expiry = datetime.now() + timedelta(seconds=ttl)

        # callbacks! 
        self.timeout_callbacks = []
        self.timer = None

    def __del__(self):
        if self.timer is not None:
            self.timer.cancel()
    
    def print_entry(self, offset=""):
        names_str = ""
        for name in self.names:
            names_str = names_str + name + " "
        if (self.is_expired()):
            expired = "Expired"
        else:
            expired = "Not expired"

        print offset + self.IP
        print offset + names_str
        print offset + str(self.ttl)
        print offset + self.classification
        print offset + str(self.expiry)
        print offset + expired

    def is_expired(self, expiry=None):
        if expiry is datetime:
            expiration_time = expiry
        else:
            expiration_time = datetime.now()

        return self.expiry < expiration_time
    
    def update_expiry(self, ttl):
        self.ttl = ttl
        self.expiry = datetime.now() + timedelta(seconds=ttl)
        if self.timer is not None:
            self.timer.cancel()
            self._set_and_start_timer()
    
    def register_timeout_callback(self, func):
        if func not in self.timeout_callbacks:
            self.timeout_callbacks.append(func) 
        if self.timer is None and not self.is_expired():
            self._set_and_start_timer()

    def _call_callbacks(self):
        #This is called when it expires.
        for cb in self.timeout_callbacks:
            cb(self.ip, self)

    def _set_and_start_timer(self):
        time_to_go = self.expiry - datetime.now()
        self.timer = Timer(time_to_go.total_seconds(), self._call_callbacks)
        self.timer.start()

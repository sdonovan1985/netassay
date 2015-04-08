
class Policy(object):
    def compile(self):
        return self

    def __or__(self, pol):
        return union([self, pol])

    def __and__(self, pol):
        return intersection([self,pol])

    def __rshift__(self, pol):
        return sequential([self,pol])

class drop(Policy):
    def __init__(self):
        pass

    def __repr__(self):
        return "drop"

class fwd(Policy):
    def __init__(self,port):
        self.port = port

    def __repr__(self):
        return "fwd " + repr(self.port)
    


class DynamicFilter(Policy):
    def __init__(self, policy=drop):
        self._policy = policy

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, policy):
        prev_policy = self._policy
        self._policy = policy

    def __repr__(self):
        return "[DynamicFilter]\n%s" % repr(self.policy)

class union(Policy):
    def __init__(self, policies=[]):
        self.policies = policies

    def __new__(self, policies=[]):
        self.policies = policies

    def __repr__(self):
        return "union: " + repr(self.policies)

class intersection(Policy):
    def __init__(self, policies=[]):
        self.policies = policies

    def __new__(self, policies=[]):
        self.policies = policies

    def __repr__(self):
        return "intersection: " + repr(self.policies)

class sequential(Policy):
    def __init__(self, policies=[]):
        self.policies = policies

    def __new__(self, policies=[]):
        self.policies = policies

    def __repr__(self):
        return "sequential: " + repr(self.policies)


class disjoint(Policy):
    def __init__(self, policies=[]):
        self.policies = policies

    def __new__(self, policies=[]):
        self.policies = policies
        
    def __repr__(self):
        return "disjoint: " + repr(self.policies)


class Match(Policy):
    def __init__(self, map_dict):
        self.map = map_dict

    def __repr__(self):
        return "match: " + repr(self.map)



#This is from language.py
class RegisteredMatchActionsException(Exception):
    """
    UPDATED FOR NETASSAY
    """
    pass

class RegisteredMatchActions2(object):
    """
    UPDATED FOR NETASSAY
    The class that handles the particular attribute must take as its only 
    parameter in __init__ the value that it's being set to in the match class.

    Example:
       match(domain='example.com') 
    The handler for 'domain' matching, say matchDomain, would be initialized as
    follows:
       matchDomain('example.com')
    """
    INSTANCE = None
    _registered_matches = {}

    def init(self):
        print "RegisteredMatchActions - INIT"

    @classmethod
    def register(cls, attribute, handler):
        """
        Registers new classes to handle new attributes.
        attribute in the above example is 'domain'
        handler in the above example is the class matchDomain
        """
        if cls.INSTANCE == None:
            cls.INSTANCE = RegisteredMatchActions2()
        inst = cls.INSTANCE
        inst._registered_matches[attribute] = handler
        print "attribute - " + str(attribute)
        print "handler   - " + str(handler)

    @classmethod
    def lookup(cls, attribute):
        if cls.INSTANCE == None:
            cls.INSTANCE = RegisteredMatchActions2()
        inst = cls.INSTANCE
        if attribute not in inst._registered_matches.keys():
            # This is normal. Everything that returns this should be handled by 
            # the Match class
            # FIXME - Is this always true?
            raise RegisteredMatchActionsException(
                str(attribute) + " not registered")
        return inst._registered_matches[attribute]

    @classmethod
    def exists(cls, attribute):
        if cls.INSTANCE == None:
            cls.INSTANCE = RegisteredMatchActions2()
        inst = cls.INSTANCE
        return (attribute in inst._registered_matches.keys())
            

class match(DynamicFilter):

    def __init__(self, *args, **kwargs):


        super(match,self).__init__()

        self._traditional_match = None
        self._netassay_match    = None

        map_dict = dict(*args, **kwargs)
        
        traditional_match_params = {}
        netassay_match_params    = {}

        # Sort out the traditional and netassay params
        for attribute in map_dict.keys():
            if RegisteredMatchActions2.exists(attribute):
                netassay_match_params[attribute] = map_dict[attribute]
            else:
                traditional_match_params[attribute] = map_dict[attribute]

        # get the values full
        if len(traditional_match_params.keys()) != 0:
            self._traditional_match = Match(traditional_match_params)
            
        if len(netassay_match_params.keys()) != 0:
            for attribute in netassay_match_params.keys():
                if self._netassay_match is None:
                    self._netassay_match = (RegisteredMatchActions2.lookup(attribute))(netassay_match_params[attribute], self)

        self.children_update()

    def children_update(self):
        self.policy = drop

        if ((self._traditional_match is not None) and
            (self._netassay_match is None)):
            self.policy = self._traditional_match
        elif ((self._traditional_match is None) and
              (self._netassay_match is not None)):
            self.policy = self._netassay_match
        elif ((self._traditional_match is not None) and
              (self._netassay_match is not None)):
            self.policy = self._traditional_match >> self._netassay_match
        else:
            drop
        #self._classifier = self.generate_classifier
#        print self

    def __repr__(self):
        return "match: " + repr(self.policy)


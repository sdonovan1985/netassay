
################################################################################
# The Pyretic Project                                                          #
# frenetic-lang.org/pyretic                                                    #
# author: Joshua Reich (jreich@cs.princeton.edu)                               #
# author: Christopher Monsanto (chris@monsan.to)                               #
# author: Cole Schlesinger (cschlesi@cs.princeton.edu)                         #
################################################################################
# Licensed to the Pyretic Project by one or more contributors. See the         #
# NOTICES file distributed with this work for additional information           #
# regarding copyright and ownership. The Pyretic Project licenses this         #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################

# This module is designed for import *.
import functools
import itertools
import struct
import time
from ipaddr import IPv4Network
from bitarray import bitarray
import copy

from pyretic.core import util
from pyretic.core.network import *
from pyretic.core.classifier import Rule, Classifier
from pyretic.core.util import frozendict, singleton

from multiprocessing import Condition
from multiprocessing import Process
from multiprocessing import Manager
from multiprocessing import cpu_count
from multiprocessing import Queue


NO_CACHE=False
compile_debug = False
use_disjoint_cache = True
use_parallel_cache = True
use_sequential_cache = True

manager = Manager()
disjoint_cache_shr = manager.dict()

disjoint_cache={}
parallel_cache={}
sequential_cache={}


basic_headers = ["srcmac", "dstmac", "srcip", "dstip", "tos", "srcport", "dstport",
                 "ethtype", "protocol"]
tagging_headers = ["vlan_id", "vlan_pcp"]
native_headers = basic_headers + tagging_headers
location_headers = ["switch", "inport", "outport"]
compilable_headers = native_headers + location_headers
content_headers = [ "raw", "header_len", "payload_len"]


################################################################################
# Policy Language                                                              #
################################################################################

class Policy(object):
    """
    Top-level abstract class for policies.
    All Pyretic policies have methods for

    - evaluating on a single packet.
    - compilation to a switch Classifier
    """
    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        raise NotImplementedError

    def invalidate_classifier(self):
        self._classifier = None

    def compile(self):
        """
        Produce a Classifier for this policy

        :rtype: Classifier
        """
        if NO_CACHE: 
            self._classifier = self.generate_classifier()
        return self._classifier

    def __add__(self, pol):
        """
        The parallel composition operator.

        :param pol: the Policy to the right of the operator
        :type pol: Policy
        :rtype: Parallel
        """
        if isinstance(pol,parallel):
            return parallel([self] + pol.policies)
        else:
            return parallel([self, pol])

    def __rshift__(self, other):
        """
        The sequential composition operator.

        :param pol: the Policy to the right of the operator
        :type pol: Policy
        :rtype: Sequential
        """
        if isinstance(other,sequential):
            return sequential([self] + other.policies)
        else:
            return sequential([self, other])

    def __eq__(self, other):
        """Syntactic equality."""
        raise NotImplementedError

    def __ne__(self,other):
        """Syntactic inequality."""
        return not (self == other)

    def name(self):
        return self.__class__.__name__

    def __repr__(self):
        return "%s : %d" % (self.name(),id(self))


class Filter(Policy):
    """
    Abstact class for filter policies.
    A filter Policy will always either 

    - pass packets through unchanged
    - drop them

    No packets will ever be modified by a Filter.
    """
    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        raise NotImplementedError

    def __or__(self, pol):
        """
        The Boolean OR operator.

        :param pol: the filter Policy to the right of the operator
        :type pol: Filter
        :rtype: Union
        """
        if isinstance(pol,Filter):
            return union([self, pol])
        else:
            raise TypeError

    def __and__(self, pol):
        """
        The Boolean AND operator.

        :param pol: the filter Policy to the right of the operator
        :type pol: Filter
        :rtype: Intersection
        """
        if isinstance(pol,Filter):
            return intersection([self, pol])
        else:
            raise TypeError

    def __sub__(self, pol):
        """
        The Boolean subtraction operator.

        :param pol: the filter Policy to the right of the operator
        :type pol: Filter
        :rtype: Difference
        """
        if isinstance(pol,Filter):
            return difference(self, pol)
        else:
            raise TypeError

    def __invert__(self):
        """
        The Boolean negation operator.

        :param pol: the filter Policy to the right of the operator
        :type pol: Filter
        :rtype: negate
        """
        return negate([self])


class Singleton(Filter):
    """Abstract policy from which Singletons descend"""

    _classifier = None

    def compile(self):
        """
        Produce a Classifier for this policy

        :rtype: Classifier
        """
        if NO_CACHE: 
            self.__class__._classifier = self.generate_classifier()
        if self.__class__._classifier is None:
            self.__class__._classifier = self.generate_classifier()
        return self.__class__._classifier

    def generate_classifier(self):
        return Classifier([Rule(identity, {self})])


@singleton
class identity(Singleton):
    """The identity policy, leaves all packets unchanged."""
    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        return {pkt}

    def intersect(self, other):
        return other

    def covers(self, other):
        return True

    def __eq__(self, other):
        return ( id(self) == id(other)
            or ( isinstance(other, Match) and len(other.map) == 0) )

    def __repr__(self):
        return "identity"

passthrough = identity   # Imperative alias
true = identity          # Logic alias
all_packets = identity   # Matching alias


@singleton
class drop(Singleton):
    """The drop policy, produces the empty set of packets."""
    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        return set()

    def generate_classifier(self):
        return Classifier([Rule(identity,set())])

    def intersect(self, other):
        return self

    def covers(self, other):
        return False

    def __eq__(self, other):
        return id(self) == id(other)

    def __repr__(self):
        return "drop"

none = drop
false = drop             # Logic alias
no_packets = drop        # Matching alias


@singleton
class Controller(Singleton):
    def eval(self, pkt):
        return set()

    def __eq__(self, other):
        return id(self) == id(other)

    def __repr__(self):
        return "Controller"
    

class Match(Filter):
    """
    Match on all specified fields.
    Matched packets are kept, non-matched packets are dropped.

    :param *args: field matches in argument format
    :param **kwargs: field matches in keyword-argument format
    """
    def __init__(self, map_dict):

        def _get_processed_map(map_dict):
            for field in ['srcip', 'dstip']:
                try:
                    val = map_dict[field]
                    map_dict.update({field: util.string_to_network(val)})
                except KeyError:
                    pass
            return map_dict

        self.map = util.frozendict(_get_processed_map(map_dict))
        self._classifier = self.generate_classifier()
        super(Match,self).__init__()

    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """

        for field, pattern in self.map.iteritems():
            try:
                v = pkt[field]
                if not field in ['srcip', 'dstip']:
                    if pattern is None or pattern != v:
                        return set()
                else:
                    v = util.string_to_IP(v)
                    if pattern is None or not v in pattern:
                        return set()
            except Exception, e:
                if pattern is not None:
                    return set()
        return {pkt}

    def generate_classifier(self):
        r1 = Rule(self,{identity})
        r2 = Rule(identity,set())
        return Classifier([r1, r2])

    def __eq__(self, other):
        return ( (isinstance(other, Match) and self.map == other.map)
            or (other == identity and len(self.map) == 0) )

    def intersect(self, pol):
        #### NETASSAY WORKAROUND ####
        from pyretic.modules.netassay.netassaymatch import NetAssayMatch
        #### END NETASSAY WORKAROUND ####
        
        def _intersect_ip(ipfx, opfx):
            most_specific = None
            if ipfx in opfx:
                most_specific = ipfx
            elif opfx in ipfx:
                most_specific = opfx
            else:
                most_specific = None
            return most_specific

        if pol == identity:
            return self
        elif pol == drop:
            return drop
        #### NETASSAY WORKAROUND ####
        elif isinstance(pol,NetAssayMatch):
            return pol.intersect(self)
        #### END NETASSAY WORKAROUND ####
        elif not isinstance(pol,Match):
            raise TypeError(str(pol.__class__.__name__) + ":" +str(pol))
        fs1 = set(self.map.keys())
        fs2 = set(pol.map.keys())
        shared = fs1 & fs2
        most_specific_src = None
        most_specific_dst = None

        for f in shared:
            if (f=='srcip'):
                most_specific_src = _intersect_ip(self.map[f], pol.map[f])
                if most_specific_src is None:
                    return drop
            elif (f=='dstip'):
                most_specific_dst = _intersect_ip(self.map[f], pol.map[f])
                if most_specific_dst is None:
                    return drop
            elif (self.map[f] != pol.map[f]):
                return drop

        d = self.map.update(pol.map)

        if most_specific_src is not None:
            d = d.update({'srcip' : most_specific_src})
        if most_specific_dst is not None:
            d = d.update({'dstip' : most_specific_dst})

        return Match(dict(**d))

    def __and__(self,pol):
        if isinstance(pol,Match):
            return self.intersect(pol)
        else:
            return super(Match,self).__and__(pol)

    ### hash : unit -> int
    def __hash__(self):
        return hash(self.map)

    def covers(self,other):
        # Return identity if self matches every packet that other matches (and maybe more).
        # eg. if other is specific on any field that self lacks.
        if other == identity and len(self.map.keys()) > 0:
            return False
        elif other == identity:
            return True
        elif other == drop:
            return True
        if set(self.map.keys()) - set(other.map.keys()):
            return False
        for (f,v) in self.map.items():
            other_v = other.map[f]
            if (f=='srcip' or f=='dstip'):
                if v != other_v:
                    if not other_v in v:
                        return False
            elif v != other_v:
                return False
        return True

    def __repr__(self):
        return "Match: %s" % ' '.join(map(str,self.map.items()))


class modify(Policy):
    """
    Modify on all specified fields to specified values.

    :param *args: field assignments in argument format
    :param **kwargs: field assignments in keyword-argument format
    """
    ### init : List (String * FieldVal) -> List KeywordArg -> unit
    def __init__(self, *args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            raise TypeError
        self.map = dict(*args, **kwargs)
        self.has_virtual_headers = not \
            reduce(lambda acc, f:
                       acc and (f in compilable_headers),
                   self.map.keys(),
                   True)
        self._classifier = self.generate_classifier()
        super(modify,self).__init__()

    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        return {pkt.modifymany(self.map)}

    def generate_classifier(self):
        if self.has_virtual_headers:
            r = Rule(identity,{Controller})
        else:
            r = Rule(identity,{self})
        return Classifier([r])

    def __repr__(self):
        return "modify: %s" % ' '.join(map(str,self.map.items()))

    def __eq__(self, other):
        return ( isinstance(other, modify)
           and (self.map == other.map) )


# FIXME: Srinivas =).
class Query(Filter):
    """
    Abstract class representing a data structure
    into which packets (conceptually) go and with which callbacks can register.
    """
    ### init : unit -> unit
    def __init__(self):
        from multiprocessing import Lock
        self.callbacks = []
        self.bucket = set()
        self.bucket_lock = Lock()
        super(Query,self).__init__()

    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        with self.bucket_lock:
            self.bucket.add(pkt)
        return set()
        
    ### register_callback : (Packet -> X) -> unit
    def register_callback(self, fn):
        self.callbacks.append(fn)

    def __repr__(self):
        return "Query"


class FwdBucket(Query):
    """
    Class for registering callbacks on individual packets sent to
    the controller.
    """
    def __init__(self):
        self._classifier = self.generate_classifier()
        super(FwdBucket,self).__init__()

    def generate_classifier(self):
        return Classifier([Rule(identity,{Controller})])

    def apply(self):
        with self.bucket_lock:
            for pkt in self.bucket:
                for callback in self.callbacks:
                    callback(pkt)
            self.bucket.clear()
    
    def __repr__(self):
        return "FwdBucket"

    def __eq__(self, other):
        # TODO: if buckets eventually have names, equality should
        # be on names.
        return isinstance(other, FwdBucket)


class CountBucket(Query):
    """
    Class for registering callbacks on counts of packets sent to
    the controller.
    """
    def __init__(self):
        super(CountBucket, self).__init__()
        self.matches = set([])
        self.runtime_stats_query_fun = None
        self.outstanding_switches = []
        self.packet_count = 0
        self.byte_count = 0
        self.packet_count_persistent = 0
        self.byte_count_persistent = 0
        self.in_update_cv = Condition()
        self.in_update = False
        self._classifier = self.generate_classifier()
        
    def __repr__(self):
        return "CountBucket"

    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        return set()

    def generate_classifier(self):
        return Classifier([Rule(identity,{self})])

    def apply(self):
        with self.bucket_lock:
            for pkt in self.bucket:
                self.packet_count_persistent += 1
                self.byte_count_persistent += pkt['header_len'] + pkt['payload_len']
            self.bucket.clear()

    def start_update(self):
        """
        Use a condition variable to mediate access to bucket state as it is
        being updated.

        Why condition variables and not locks? The main reason is that the state
        update doesn't happen in just a single function call here, since the
        runtime processes the classifier rule by rule and buckets may be touched
        in arbitrary order depending on the policy. They're not all updated in a
        single function call. In that case,

        (1) Holding locks *across* function calls seems dangerous and
        non-modular (in my opinion), since we need to be aware of this across a
        large function, and acquiring locks in different orders at different
        points in the code can result in tricky deadlocks (there is another lock
        involved in protecting bucket updates in runtime).

        (2) The "with" semantics in python is clean, and splitting that into
        lock.acquire() and lock.release() calls results in possibly replicated
        failure handling code that is boilerplate.

        """
        with self.in_update_cv:
            self.in_update = True
            self.matches = set([])
            self.runtime_stats_query_fun = None
            self.outstanding_switches = []

    def finish_update(self):
        with self.in_update_cv:
            self.in_update = False
            self.in_update_cv.notify_all()
        
    def add_match(self, m):
        """
        Add a match m to list of classifier rules to be queried for
        counts.
        """
        if not m in self.matches:
            self.matches.add(m)

    def add_pull_stats(self, fun):
        """
        Point to function that issues stats queries in the
        runtime.
        """
        if not self.runtime_stats_query_fun:
            self.runtime_stats_query_fun = fun

    def pull_stats(self):
        """Issue stats queries from the runtime"""
        queries_issued = False
        with self.in_update_cv:
            while self.in_update: # ensure buckets not updated concurrently
                self.in_update_cv.wait()
            if not self.runtime_stats_query_fun is None:
                self.outstanding_switches = []
                queries_issued = True
                self.runtime_stats_query_fun()
        # If no queries were issued, then no matches, so just call userland
        # registered callback routines
        if not queries_issued:
            self.packet_count = self.packet_count_persistent
            self.byte_count = self.byte_count_persistent
            for f in self.callbacks:
                f([self.packet_count, self.byte_count])

    def add_outstanding_switch_query(self,switch):
        self.outstanding_switches.append(switch)

    def handle_flow_stats_reply(self,switch,flow_stats):
        """
        Given a flow_stats_reply from switch s, collect only those
        counts which are relevant to this bucket.

        Very simple processing for now: just collect all packet and
        byte counts from rules that have a match that is in the set of
        matches this bucket is interested in.
        """
        def stat_in_bucket(flow_stat, s):
            table_match = Match(dict(f['match']).intersect(match(switch=s)))
            network_match = Match(dict(f['match']))
            if table_match in self.matches or network_match in self.matches:
                return True
            return False

        with self.in_update_cv:
            while self.in_update:
                self.in_update_cv.wait()
            self.packet_count = self.packet_count_persistent
            self.byte_count = self.byte_count_persistent
            if switch in self.outstanding_switches:
                for f in flow_stats:
                    if 'match' in f:
                        if stat_in_bucket(f, switch):
                            self.packet_count += f['packet_count']
                            self.byte_count   += f['byte_count']
                self.outstanding_switches.remove(switch)
        # If have all necessary data, call user-land registered callbacks
        if not self.outstanding_switches:
            for f in self.callbacks:
                f([self.packet_count, self.byte_count])

    def __eq__(self, other):
        # TODO: if buckets eventually have names, equality should
        # be on names.
        return isinstance(other, CountBucket)

################################################################################
# Combinator Policies                                                          #
################################################################################

class CombinatorPolicy(Policy):
    """
    Abstract class for policy combinators.

    :param policies: the policies to be combined.
    :type policies: list Policy
    """
    ### init : List Policy -> unit
    def __init__(self, policies=[]):
        self.policies = list(policies)
        self._classifier = None
        super(CombinatorPolicy,self).__init__()

    def compile(self):
        """
        Produce a Classifier for this policy

        :rtype: Classifier
        """
        if NO_CACHE: 
            self._classifier = self.generate_classifier()
        if not self._classifier:
            self._classifier = self.generate_classifier()
        return self._classifier

    def __repr__(self):
        return "%s:\n%s" % (self.name(),util.repr_plus(self.policies))

    def __eq__(self, other):
        return ( self.__class__ == other.__class__
           and   self.policies == other.policies )


class negate(CombinatorPolicy,Filter):
    """
    Combinator that negates the input policy.

    :param policies: the policies to be negated.
    :type policies: list Filter
    """
    def eval(self, pkt):
        """
        evaluate this policy on a single packet

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        if self.policies[0].eval(pkt):
            return set()
        else:
            return {pkt}

    def generate_classifier(self):
        inner_classifier = self.policies[0].compile()
        return ~inner_classifier


class parallel(CombinatorPolicy):
    """
    Combinator for several policies in parallel.

    :param policies: the policies to be combined.
    :type policies: list Policy
    """
    def __new__(self, policies=[]):
        # Hackety hack.
        if len(policies) == 0:
            return drop
        else:
            rv = super(parallel, self).__new__(parallel, policies)
            rv.__init__(policies)
            return rv

    def __init__(self, policies=[]):
        if len(policies) == 0:
            raise TypeError
        super(parallel, self).__init__(policies)

    def __add__(self, pol):
        if isinstance(pol,parallel):
            return parallel(self.policies + pol.policies)
        else:
            return parallel(self.policies + [pol])

    def eval(self, pkt):
        """
        evaluates to the set union of the evaluation
        of self.policies on pkt

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        output = set()
        for policy in self.policies:
            output |= policy.eval(pkt)
        return output

    def generate_classifier(self):
        """
        Adapted from the SDX modification for caching found:
        https://github.com/sdn-ixp/sdx-platform-optimized/blob/sigcomm/pyretic/core/language.py
        """

        if use_parallel_cache == True:
            classifier_temp=[]
            
            for policy1 in self.policies:
                hash1 = policy1.__repr__()
                
                if hash1 in parallel_cache:
                    out = parallel_cache[hash1]
                    classifier_temp.append(out)
                else:
                    out = policy1.compile()
                    classifier_temp.append(out)
                    parallel_cache[hash1] = out


            if len(self.policies) == 0:  # EMPTY PARALLEL IS A DROP
                return drop.compile()
            classifiers = classifier_temp
        else:
            if len(self.policies) == 0:  # EMPTY PARALLEL IS A DROP
                return drop.compile()
            classifiers = map(lambda p: p.compile(), self.policies)

        out = reduce(lambda acc, c: acc + c, classifiers)
        return out
    

class disjoint(CombinatorPolicy):
    """
    Combinator for several disjoint policies.

    :param policies: the policies to be combined.
    :type policies: list Policy
    """
    def __new__(self, policies=[]):
        # Hackety hack.
        if len(policies) == 0:
            return identity
        else:
            rv = super(disjoint, self).__new__(disjoint, policies)
            rv.__init__(policies)
            return rv

    def __init__(self, policies=[]):
        if len(policies) == 0:
            raise TypeError
        super(disjoint, self).__init__(policies)
        
    def eval(self, pkt):
        """
        evaluates to the set union of the evaluation
        of self.policies on pkt

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        # Very similar to Parallel, only difference that it will only have one output pkt.
        # Todo: Assert that it return only one packet as output
        output = set()
        for policy in self.policies:
            output |= (policy.eval(pkt))
        #print self.policies, pkt
        
        #print output
        return output
    
#    def compile(self, do_mp=False):
    def generate_classifier(self, do_mp=False):
        """
        Produce a Classifier for this policy

        :rtype: Classifier
        """
        #print "lower policies: ",self.lower
        if compile_debug==True: 
            print "Disjoint Policies compiler called: ",len(self.policies)
        start=time.time()
   
        # Make sure that there are policies to compile
        assert(len(self.policies) > 0)
        aggr_rules=[]
        last_rule=None       

        ## Processes will store return values here (Synchronized with lock)
        job_returns = Queue()
        last_rule_entry = manager.list()
        last_rule_entry.append(None)
        from multiprocessing import Lock
        djLock = Lock()

        global disjoint_cache 
        # Processes list
        jobs = []

#        from multiprocessing import Pool
        from multiprocessing import cpu_count
#        pool = Pool(processes=cpu_count())    
        do_multi_process = do_mp


        # Spawn processes based on number of CPUs
        if do_multi_process is True:
            start_time = time.time()
            if len(self.policies) < 1000:
                batch = 1000
            else: 
                batch = len(self.policies) / cpu_count()
            nProc = len(self.policies) / batch
            last_end = 0
            for n in range(nProc):
                start = n*batch
                end = (n+1)*batch
                last_end = end
                policy_list = self.policies[start:end]
                
                p=Process(target=self.mp_for_each_policy,\
                          args=(djLock,policy_list,job_returns,disjoint_cache_shr,last_rule_entry))
                p.start()
                jobs.append(p)


            # Wait until done
#            for j in jobs:
#                j.join()
            while job_returns.qsize()!=nProc:
                continue

            disjoint_cache = copy.deepcopy(disjoint_cache_shr)

            # Create aggr_rules from all returned lists
            while not job_returns.empty():
                try:
                    elem = job_returns.get()
                    aggr_rules+=elem
                except:
                    print 'Exception'
 
            # Remaining   
            if len(self.policies)-nProc*batch <= 0:
                policy_list = self.policies[last_end:(len(self.policies)-nProc*batch)]
                this_aggr_list, last_rule = self.do_each_sequentially(policy_list)

                this_aggr_list+=last_rule
                aggr_rules+=str(this_aggr_list)

            else:
                if last_rule_entry[0] != None:        
                    aggr_rules+=str(last_rule_entry[0])
  
        else:
            start_time = time.time()
            aggr_rules, last_rule = self.do_each_sequentially(self.policies)
            aggr_rules+=last_rule 

        if compile_debug==True: 
            print "Time to compile disjoint policies: ",time.time()-start_time
        start_time=time.time()
        classifiers=aggr_rules  
 
        #print "Cache state: ", disjoint_cache    
        return classifiers

    def do_each_sequentially_for_mp(self,policy_list,disjoint_cache_shr,djLock):
        aggr_rules = []
        tmp_rule_list = []
        last_rule = [None,]
        print "Policy List Length:",len(policy_list)
        for policy in policy_list:
            start1 = time.time()
            tmp_rule_list = []
            
            if use_disjoint_cache:
                hash_d = policy.__repr__()
                if hash_d in disjoint_cache_shr:
                    tmp_rules=disjoint_cache_shr[hash_d]
#                    print 'HIT'
                else:
#                    print 'MISS in MP'
                    tmp_rules=policy.compile().rules
                    disjoint_cache_shr[hash_d]=str(tmp_rules)
            else:                      
                tmp_rules=policy.compile().rules  
                                                
            last_rule=[tmp_rules[len(tmp_rules)-1]]
            
            ctr = 0
            for obj in tmp_rules:
                
                if ctr == len(tmp_rules)-1:
                    break
                else:
                    tmp_rule_list.append(obj)
                    ctr += 1
                    
            aggr_rules+=tmp_rule_list                 
#            print 'Time!!!:',time.time() - start1

        return aggr_rules,last_rule


    def do_each_sequentially(self,policy_list):
        aggr_rules = []
        tmp_rule_list = []
        last_rule = [None,]
        print "Policy List Length SP:",len(policy_list)
        for policy in policy_list:
            start1 = time.time()
            tmp_rule_list = []
            
            if use_disjoint_cache:
                hash_d = policy.__repr__()
                if hash_d in disjoint_cache:
                    tmp_rules=disjoint_cache[hash_d]
                else:
#                    print 'MISS in SP'
                    tmp_rules=policy.compile().rules
                    disjoint_cache[hash_d]=tmp_rules  
            else:                      
                tmp_rules=policy.compile().rules  
                                                
            last_rule=[tmp_rules[len(tmp_rules)-1]]
            
            ctr = 0
            for obj in tmp_rules:
                
                if ctr == len(tmp_rules)-1:
                    break
                else:
                    tmp_rule_list.append(obj)
                    ctr += 1
                    
            aggr_rules+=tmp_rule_list                 
#            print 'Time!!!:',time.time() - start1

        return aggr_rules,last_rule

    def mp_for_each_policy(self, djLock,policy_list,job_returns,disjoint_cache_shr,last_rule_entry):
        
        this_aggr_list,last_rule = self.do_each_sequentially_for_mp(policy_list,disjoint_cache_shr,djLock)

        job_returns.put(str(this_aggr_list))
        last_rule_entry[0] = str(last_rule)

#        with djLock:
#            job_returns.put(str(this_aggr_list))
#            last_rule_entry[0] = str(last_rule)
#            pass
 


class union(parallel,Filter):
    """
    Combinator for several filter policies in parallel.

    :param policies: the policies to be combined.
    :type policies: list Filter
    """
    def __new__(self, policies=[]):
        # Hackety hack.
        if len(policies) == 0:
            return drop
        else:
            rv = super(parallel, self).__new__(union, policies)
            rv.__init__(policies)
            return rv

    def __init__(self, policies=[]):
        if len(policies) == 0:
            raise TypeError
        super(union, self).__init__(policies)

    ### or : Filter -> Filter
    def __or__(self, pol):
        if isinstance(pol,union):
            return union(self.policies + pol.policies)
        elif isinstance(pol,Filter):
            return union(self.policies + [pol])
        else:
            raise TypeError


class sequential(CombinatorPolicy):
    """
    Combinator for several policies in sequence.

    :param policies: the policies to be combined.
    :type policies: list Policy
    """
    def __new__(self, policies=[]):
        # Hackety hack.
        if len(policies) == 0:
            return identity
        else:
            rv = super(sequential, self).__new__(sequential, policies)
            rv.__init__(policies)
            return rv

    def __init__(self, policies=[]):
        if len(policies) == 0:
            raise TypeError
        super(sequential, self).__init__(policies)

    def __rshift__(self, pol):
        if isinstance(pol,sequential):
            return sequential(self.policies + pol.policies)
        else:
            return sequential(self.policies + [pol])

    def eval(self, pkt):
        """
        evaluates to the set union of each policy in 
        self.policies on each packet in the output of the 
        previous.  The first policy in self.policies is 
        evaled on pkt.

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        prev_output = {pkt}
        output = prev_output
        for policy in self.policies:
            if not prev_output:
                return set()
            if policy == identity:
                continue
            if policy == drop:
                return set()
            output = set()
            for p in prev_output:
                output |= policy.eval(p)
            prev_output = output
        return output

    def generate_classifier(self):
        """
        Adapted from the SDX modification for caching found:
        https://github.com/sdn-ixp/sdx-platform-optimized/blob/sigcomm/pyretic/core/language.py
        """

        if use_sequential_cache == True:
            classifier_temp = []
            
            for policy1 in self.policies:
                hash1 = policy1.__repr__()

                if hash1 in sequential_cache:
                    out = sequential_cache[hash1]
                    classifier_temp.append(out)
                else:
                    out = policy1.compile()
                    classifier_temp.append(out)
                    sequential_cache[hash1] = out

            assert(len(self.policies) > 0)
            classifiers = classifier_temp

        else:
            assert(len(self.policies) > 0)
            classifiers = map(lambda p: p.compile(),self.policies)

        for c in classifiers:
            assert(c is not None)
        out = reduce(lambda acc, c: acc >> c, classifiers)
        return out
        

class intersection(sequential,Filter):
    """
    Combinator for several filter policies in sequence.

    :param policies: the policies to be combined.
    :type policies: list Filter
    """
    def __new__(self, policies=[]):
        # Hackety hack.
        if len(policies) == 0:
            return identity
        else:
            rv = super(sequential, self).__new__(intersection, policies)
            rv.__init__(policies)
            return rv

    def __init__(self, policies=[]):
        if len(policies) == 0:
            raise TypeError
        super(intersection, self).__init__(policies)

    ### and : Filter -> Filter
    def __and__(self, pol):
        if isinstance(pol,intersection):
            return intersection(self.policies + pol.policies)
        elif isinstance(pol,Filter):
            return intersection(self.policies + [pol])
        else:
            raise TypeError


################################################################################
# Derived Policies                                                             #
################################################################################

class DerivedPolicy(Policy):
    """
    Abstract class for a policy derived from another policy.

    :param policy: the internal policy (assigned to self.policy)
    :type policy: Policy
    """
    def __init__(self, policy=identity):
        self.policy = policy
        self._classifier = None
        super(DerivedPolicy,self).__init__()

    def eval(self, pkt):
        """
        evaluates to the output of self.policy.

        :param pkt: the packet on which to be evaluated
        :type pkt: Packet
        :rtype: set Packet
        """
        return self.policy.eval(pkt)

    def compile(self):
        """
        Produce a Classifier for this policy

        :rtype: Classifier
        """
        if NO_CACHE: 
            self._classifier = self.generate_classifier()
        if not self._classifier:
            self._classifier = self.generate_classifier()
        return self._classifier

    def generate_classifier(self):
        return self.policy.compile()

    def __repr__(self):
        return "[DerivedPolicy]\n%s" % repr(self.policy)

    def __eq__(self, other):
        return ( self.__class__ == other.__class__
           and ( self.policy == other.policy ) )


class difference(DerivedPolicy,Filter):
    """
    The difference between two filter policies..

    :param f1: the minuend
    :type f1: Filter
    :param f2: the subtrahend
    :type f2: Filter
    """
    def __init__(self, f1, f2):
       self.f1 = f1
       self.f2 = f2
       super(difference,self).__init__(~f2 & f1)

    def __repr__(self):
        return "difference:\n%s" % util.repr_plus([self.f1,self.f2])


class if_(DerivedPolicy):
    """
    if pred holds, t_branch, otherwise f_branch.

    :param pred: the predicate
    :type pred: Filter
    :param t_branch: the true branch policy
    :type pred: Policy
    :param f_branch: the false branch policy
    :type pred: Policy
    """
    def __init__(self, pred, t_branch, f_branch=identity):
        self.pred = pred
        self.t_branch = t_branch
        self.f_branch = f_branch
        super(if_,self).__init__((self.pred >> self.t_branch) +
                                 ((~self.pred) >> self.f_branch))

    def eval(self, pkt):
        if self.pred.eval(pkt):
            return self.t_branch.eval(pkt)
        else:
            return self.f_branch.eval(pkt)

    def __repr__(self):
        return "if\n%s\nthen\n%s\nelse\n%s" % (util.repr_plus([self.pred]),
                                               util.repr_plus([self.t_branch]),
                                               util.repr_plus([self.f_branch]))


class fwd(DerivedPolicy):
    """
    fwd out a specified port.

    :param outport: the port on which to forward.
    :type outport: int
    """
    def __init__(self, outport):
        self.outport = outport
        super(fwd,self).__init__(modify(outport=self.outport))

    def __repr__(self):
        return "fwd %s" % self.outport


class xfwd(DerivedPolicy):
    """
    fwd out a specified port, unless the packet came in on that same port.
    (Semantically equivalent to OpenFlow's forward action

    :param outport: the port on which to forward.
    :type outport: int
    """
    def __init__(self, outport):
        self.outport = outport
        super(xfwd,self).__init__((~Match(dict(inport=outport))) >> fwd(outport))

    def __repr__(self):
        return "xfwd %s" % self.outport


################################################################################
# Dynamic Policies                                                             #
################################################################################

class DynamicPolicy(DerivedPolicy):
    """
    Abstact class for dynamic policies.
    The behavior of a dynamic policy changes each time self.policy is reassigned.
    """
    ### init : unit -> unit
    def __init__(self,policy=drop):
        self._policy = policy
        self.notify = None
        self._classifier = None
        super(DerivedPolicy,self).__init__()

    def set_network(self, network):
        pass

    def attach(self,notify):
        self.notify = notify

    def detach(self):
        self.notify = None

    def changed(self):
        if self.notify:
            self.notify(self)

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, policy):
        prev_policy = self._policy
        self._policy = policy
        self.changed()

    def __repr__(self):
        return "[DynamicPolicy]\n%s" % repr(self.policy)


class DynamicFilter(DynamicPolicy,Filter):
    """
    Abstact class for dynamic filter policies.
    The behavior of a dynamic filter policy changes each time self.policy is reassigned.
    """
    pass


class flood(DynamicPolicy):
    """
    Policy that floods packets on a minimum spanning tree, recalculated
    every time the network is updated (set_network).
    """
    def __init__(self):
        self.mst = None
        super(flood,self).__init__()

    def set_network(self, network):
        changed = False
        if not network is None:
            updated_mst = Topology.minimum_spanning_tree(network.topology)
            if not self.mst is None:
                if self.mst != updated_mst:
                    self.mst = updated_mst
                    changed = True
            else:
                self.mst = updated_mst
                changed = True
        if changed:
            self.policy = parallel([
                    Match(dict(switch=switch)) >>
                        parallel(map(xfwd,attrs['ports'].keys()))
                    for switch,attrs in self.mst.nodes(data=True)])

    def __repr__(self):
        try:
            return "flood on:\n%s" % self.mst
        except:
            return "flood"


class ingress_network(DynamicFilter):
    """
    Returns True if a packet is located at a (switch,inport) pair entering
    the network, False otherwise.
    """
    def __init__(self):
        self.egresses = None
        super(ingress_network,self).__init__()

    def set_network(self, network):
        updated_egresses = network.topology.egress_locations()
        if not self.egresses == updated_egresses:
            self.egresses = updated_egresses
            self.policy = parallel([Match(dict(switch=l.switch,
                                       inport=l.port_no))
                                 for l in self.egresses])

    def __repr__(self):
        return "ingress_network"


class egress_network(DynamicFilter):
    """
    Returns True if a packet is located at a (switch,outport) pair leaving
    the network, False otherwise.
    """
    def __init__(self):
        self.egresses = None
        super(egress_network,self).__init__()

    def set_network(self, network):
        updated_egresses = network.topology.egress_locations()
        if not self.egresses == updated_egresses:
            self.egresses = updated_egresses
            self.policy = parallel([Match(dict(switch=l.switch,
                                       outport=l.port_no))
                                 for l in self.egresses])

    def __repr__(self):
        return "egress_network"




# Begin NETASSAY code
class RegisteredMatchActionsException(Exception):
    """
    UPDATED FOR NETASSAY
    """
    pass

@singleton
class RegisteredMatchActions(Singleton):
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

    _registered_matches = {}

    def register(self, attribute, handler):
        """
        Registers new classes to handle new attributes.
        attribute in the above example is 'domain'
        handler in the above example is the class matchDomain
        """
        self._registered_matches[attribute] = handler

    def lookup(self, attribute):
        if attribute not in self._registered_matches.keys():
            # This is normal. Everything that returns this should be handled by 
            # the Match class
            # FIXME - Is this always true?
            raise RegisteredMatchActionsException(
                str(attribute) + " not registered")
        return self._registered_matches[attribute]

    def exists(self, attribute):
        return (attribute in self._registered_matches.keys())
            

class match(DynamicFilter):
    """
    UPDATED FOR NETASSAY
    Replaces old match action, which is now in the Match class.
    Combines match and NetAssayMatch actions

    Much of the combination logic is based on sequential and intersection 
    classes above.
    Some of the other logic is based on Match and Filter. 
    """

    def __init__(self, *args, **kwargs):

        super(match,self).__init__()

        self._traditional_match = None
        self._netassay_match    = None

        map_dict = dict(*args, **kwargs)
        
        traditional_match_params = {}
        netassay_match_params    = {}

        # Sort out the traditional and netassay params
        for attribute in map_dict.keys():
            if RegisteredMatchActions.exists(attribute):
                netassay_match_params[attribute] = map_dict[attribute]
            else:
                traditional_match_params[attribute] = map_dict[attribute]

        # get the values full
        if len(traditional_match_params.keys()) != 0:
            self._traditional_match = Match(traditional_match_params)
            
        if len(netassay_match_params.keys()) != 0:
            for attribute in netassay_match_params.keys():
                if self._netassay_match is None:
                    self._netassay_match = (RegisteredMatchActions.lookup(attribute))(netassay_match_params[attribute], self)

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
        print self

    def __repr__(self):
        return self.policy.__repr__()

            
    

class match_old(DynamicFilter):#, DerivedPolicy):
    """
    UPDATED FOR NETASSAY
    Replaces old match action, which is now in the Match class.
    Combines match and NetAssayMatch actions

    Much of the combination logic is based on sequential and intersection 
    classes above.
    Some of the other logic is based on Match and Filter. 
    """
    def __init__(self, *args, **kwargs):
        
        # Need to split the traditional match actions from the new 
        # NetAssay-based actions
        self._traditional_match = None
        self._netassay_match = None

        map_dict = dict(*args, **kwargs)
        super(match,self).__init__()

        netassay_match_map = {}
        traditional_match_map = {}

        for attribute in map_dict.keys():
            if RegisteredMatchActions.exists(attribute):
                netassay_match_map[attribute] = map_dict[attribute]
            else:
                traditional_match_map[attribute] = map_dict[attribute]

        if len(traditional_match_map.keys()) != 0:
            # we have a traditional match to deal with. Cache a copy
            self._traditional_match = Match(traditional_match_map)

        if len(netassay_match_map.keys()) != 0:
            # build up and cache a copy of the netassay related things.
            new_netassay_match = None
            for attribute in netassay_match_map.keys():
                if new_netassay_match != None:
                    new_netassay_match = new_netassay_match >> (RegisteredMatchActions.lookup(attribute))(netassay_match_map[attribute], self)
                else:
                    new_netassay_match = (RegisteredMatchActions.lookup(attribute))(netassay_match_map[attribute], self)
            self._netassay_match = new_netassay_match
        
        self.children_update()

    def children_update(self):
        if self._traditional_match != None and self._netassay_match != None:
            self.policy = self._traditional_match >> self._netassay_match
        elif self._traditional_match == None and self._netassay_match != None:
            self.policy = self._netassay_match
        elif self._traditional_match != None and self._netassay_match == None:
            self.policy = self._traditional_match
        self._classifier = self.generate_classifier()

    def eval(self, pkt):
        return self.policy.eval(pkt)

    def __eq__(self, other):
        return self.policy.__eq__(other)
    
    def intersect(self, pol):
        return  self.policy.intersect(pol)

    def __and__(self, pol):
        return self.policy.__and__(pol)

#    def __hash__(self, pol):
#        return self.policy.__hash__(pol)

    def __repr__(self):
        return self.policy.__repr__()
    
#    def compile(self):
#        """
#        Produce a Classifier for this policy
#
#        :rtype: Classifier
#        """
#        if NO_CACHE: 
#            self._classifier = self.generate_classifier()
#        if not self._classifier:
#            self._classifier = self.generate_classifier()
#        return self._classifier

# End NETASSAY code        


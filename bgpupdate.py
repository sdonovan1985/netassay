class BGPUpdate:
    
    WITHDRAWAL = 1
    UPDATE     = 2

    def __init__(self, src_as, aspath, next_hop, network, updatetype=None):
        self.src_as = src_as
        self.aspath = aspath
        self.next_hop = next_hop
        self.network = network
        self.type = updatetype

    def equivalent(self, other):
        if ((other.src_as == self.src_as) and 
            (other.aspath == self.aspath) and
            (other.next_hop == self.next_hop) and
            (other.network == self.network)):
            return True
        return False

    def __str__(self):
        returnstr = "    src_as   : " + str(self.src_as) + "\n"
        returnstr = returnstr + "    aspath   : " + str(self.aspath)   + "\n"
        returnstr = returnstr + "    next_hop : " + str(self.next_hop) + "\n"
        returnstr = returnstr + "    network  : " + str(self.network)  + "\n"
        returnstr = returnstr + "    type     : " + str(self.type)     + "\n"
        return returnstr

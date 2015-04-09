from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import custom
from mininet.node import RemoteController
from nat import *

# Run this seperately, and before, running the Pyretic control program.
# It is a simple topology, nothing more. Requires an external control
# program.
#
# sudo python pcap_server_topo


# Topology to be instantiated in Mininet
class MNTopo(Topo):
    "Mininet test topology"

    def __init__(self, cpu=.1, max_queue_size=None, **params):
        '''
              +----+ 3   1               
Internet +----+ s1 +------+ PCAP_server
              ++--++                   
               |  |2  1                  
              1|  +---+ h1             
               |                       
               +--+ h2                 
                 1
        '''
        print "1"
        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hostConfig = {'cpu': cpu}
        linkConfig = {'bw': 10, 'delay': '1ms', 'loss': 0,
                      'max_queue_size': max_queue_size }
        print "2"
        # Hosts and switches
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', **hostConfig)
        h2 = self.addHost('h2', **hostConfig)
        PCAP_server = self.addHost('p1', **hostConfig)
        print "3"

        # Wire switches

        # Wire hosts
        self.addLink(s1, h1, 1, 1, **linkConfig)
        self.addLink(s1, h2, 2, 1, **linkConfig)
        self.addLink(s1, PCAP_server, 3, 1, **linkConfig)
        print "4"

if __name__ == '__main__':
    print "Entry"
    topo = MNTopo()
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController)
    print "created topology"
    rootnode = connectToInternet(net, switch='s1')
    print "connectToInternet returned"

    CLI(net)
    stopNAT(rootnode)
    net.stop()

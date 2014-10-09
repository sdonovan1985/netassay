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
# sudo python test_assay_topo.py

# Topology to be instantiated in Mininet
class MNTopo(Topo):
    "Mininet test topology"

    def __init__(self, cpu=.1, max_queue_size=None, **params):
        '''
                          +--+
                      +---+s3+---+
                    1 |   +--+   | 1 Slow Link
             3  +--+--+          +----+--+   3
 Internet+------+s1|                  |s2+-------+h1
                +--+--+          +----+--+
                    2 |   +--+   | 2
                      +---+s4+---+
                          +--+

    The links going via s3 and s4 are due to a flaw/bug/bad design in Mininet:
https://mailman.stanford.edu/pipermail/mininet-discuss/2014-February/003976.html
        '''

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hostConfig = {'cpu': cpu}
        fastLinkConfig = {'bw': 10, 'delay': '1ms', 'loss': 0,
                   'max_queue_size': max_queue_size }
        slowLinkConfig = {'bw': 10, 'delay': '100ms', 'loss': 0,
                   'max_queue_size': max_queue_size }

        # Hosts and switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        h1 = self.addHost('h1', **hostConfig)


        # There are multiple links between s1 and s2, a fast and a slow path

        # Wire switches
        self.addLink(s1, s3, port1=1, **slowLinkConfig)
        self.addLink(s1, s4, port1=2, **fastLinkConfig)
        self.addLink(s2, s3, port1=1, **slowLinkConfig)
        self.addLink(s2, s4, port1=2, **fastLinkConfig)

        # Wire host
        self.addLink(s2, h1, 3, 1, **fastLinkConfig)

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

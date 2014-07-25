from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import custom
from mininet.node import RemoteController
from nat import *

# Run this seperately, and before, running the Pyretic control program.
# It is a simple topology, nothing more. Requires an external control
# program.

# Topology to be instantiated in Mininet
class MNTopo(Topo):
    "Mininet test topology"

    def __init__(self, cpu=.1, max_queue_size=None, **params):

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hostConfig = {'cpu': cpu}
        linkConfig = {'bw': 10, 'delay': '1ms', 'loss': 0,
                   'max_queue_size': max_queue_size }

        # Hosts and switches
        s1 = self.addSwitch('s1')
        sender = self.addHost('sender', **hostConfig)
        receiver = self.addHost('receiver', **hostConfig)

        # Wire receiver
        self.addLink(receiver, s1, **linkConfig)

        # Wire sender
        self.addLink(sender, s1, **linkConfig)

if __name__ == '__main__':
    print "Entry"
    topo = MNTopo()
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController)
    print "created topology"
    rootnode = connectToInternet(net)
    print "connectToInternet returned"

    CLI(net)
    stopNAT(rootnode)
    net.stop()

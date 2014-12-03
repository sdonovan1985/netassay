from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import custom
from mininet.node import RemoteController
from nat import *

SWITCH_WIDTH = 10

class LargeTopo(Topo):

    def __init__(self, cpu=.01, max_queue_size=None, **params):

        Topo.__init__(self, **params)


        hostConfig = {'cpu': cpu}
        ethConfig  = {'bw': 10, 'delay': '1ms', 'loss': 0,
                      'max_queue_size': max_queue_size}

        self.switch_names = get_list_of_switches(SWITCH_WIDTH + 1)
        self.host_names   = get_list_of_hosts(SWITCH_WIDTH * SWITCH_WIDTH)

        # Create the root
        self.root_switch = self.addSwitch(self.switch_names[0])
        self.root_switch_name = self.switch_names[0]
        
        # Add the rest of the switches:
        self.leaf_switches = []
        node_index = 0
        for sw in self.switch_names[1:]:
            current_sw = self.addSwitch(sw)
            self.addLink(self.root_switch, current_sw, **ethConfig)
            self.leaf_switches.append(current_sw)
            
            # Add nodes to switches
            for index in range(node_index, node_index + SWITCH_WIDTH):
                host = self.addHost(self.host_names[index], **hostConfig)
                self.addLink(current_sw, host, **ethConfig)
            node_index += SWITCH_WIDTH
        

def get_list_of_hosts(num):
    host_list = []
    for i in range(0,num):
        host_list.append("h%i" % i)
    return host_list

def get_list_of_switches(num):
    switch_list = []
    for i in range(0,num):
        switch_list.append("s%i" % i)
    return switch_list


if __name__ == '__main__':
    print "Entry"
    topo = LargeTopo()
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController)
    print "Created topology"
    rootnode = connectToInternet(net, switch=topo.root_switch_name)
    print "connectToInternet returned"

    CLI(net)
    stopNAT(rootnode)
    net.stop()

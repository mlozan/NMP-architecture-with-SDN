from mininet.topo import Topo
from mininet.link import TCLink

class QoETopo(Topo):
    def build(self):
        # --- Hosts (h1 -> h2 is the monitored QoE flow) ---
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')

        # --- Switches ---
        s1 = self.addSwitch('s1')   # left edge switch
        s3 = self.addSwitch('s3')   # Path A core switch (short path)
        s2 = self.addSwitch('s2')   # Path B core switch 1 (long path)
        s5 = self.addSwitch('s5')   # Path B core switch 2 (long path)
        s4 = self.addSwitch('s4')   # right edge switch

        # --- Host links ---
        self.addLink(h1, s1, cls=TCLink, bw=100)
        self.addLink(s4, h2, cls=TCLink, bw=100)

        # --- Path A: s1 -> s3 -> s4 (2 hops, shortest, default ONOS path) ---
        # netem applied here to simulate congestion
        self.addLink(s1, s3, cls=TCLink, bw=10)   # s1-eth2
        self.addLink(s3, s4, cls=TCLink, bw=10)

        # --- Path B: s1 -> s2 -> s5 -> s4 (3 hops, alternate path) ---
        # netem applied here when Path B congestion is simulated
        self.addLink(s1, s2, cls=TCLink, bw=10)   # s1-eth3
        self.addLink(s2, s5, cls=TCLink, bw=10)
        self.addLink(s5, s4, cls=TCLink, bw=10)

# Register topology so Mininet can load it by name
topos = {'qoe': (lambda: QoETopo())}

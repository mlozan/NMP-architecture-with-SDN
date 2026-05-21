from mininet.topo import Topo

class QoETopo(Topo):
    def build(self):
        # --- Priority hosts (h1 → h2 is the monitored QoE flow) ---
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')

        # --- Background traffic hosts ---
        h3 = self.addHost('h3', ip='10.0.0.3/24')   # iperf sender, left side
        h4 = self.addHost('h4', ip='10.0.0.4/24')   # iperf sender, left side
        h5 = self.addHost('h5', ip='10.0.0.5/24')   # iperf receiver, right side
        h6 = self.addHost('h6', ip='10.0.0.6/24')   # iperf receiver, right side

        # --- Switches ---
        s1 = self.addSwitch('s1')   # left edge switch
        s3 = self.addSwitch('s3')   # Path A core switch (short path)
        s2 = self.addSwitch('s2')   # Path B core switch 1 (long path)
        s5 = self.addSwitch('s5')   # Path B core switch 2 (long path)
        s4 = self.addSwitch('s4')   # right edge switch

        # --- Priority flow links ---
        self.addLink(h1, s1)        # s1 port 1 → h1
        self.addLink(s4, h2)

        # --- Path A: s1 → s3 → s4 (2 hops, shortest, default ONOS path) ---
        # s1 port 2 → s3  (PORT_PATH_A = '2' in MATLAB)
        # Background iperf also uses this path → saturates it → QoE drops
        self.addLink(s1, s3, bw=10)
        self.addLink(s3, s4, bw=10)

        # --- Path B: s1 → s2 → s5 → s4 (3 hops, longer, free for rerouting) ---
        # s1 port 3 → s2
        self.addLink(s1, s2, bw=10)
        self.addLink(s2, s5, bw=10)
        self.addLink(s5, s4, bw=10)

        # --- Cross link between core switches (mesh connectivity) ---
        self.addLink(s2, s3, bw=10)

        # --- Background hosts (high bandwidth, not the bottleneck) ---
        self.addLink(h3, s1, bw=100)
        self.addLink(h4, s1, bw=100)
        self.addLink(h5, s4, bw=100)
        self.addLink(h6, s4, bw=100)

# Register topology so Mininet can load it by name
topos = {'qoe': (lambda: QoETopo())}

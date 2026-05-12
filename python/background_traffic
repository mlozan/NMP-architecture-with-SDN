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
        s1 = self.addSwitch('s1')   # left aggregation switch
        s2 = self.addSwitch('s2')   # Path A (upper)
        s3 = self.addSwitch('s3')   # Path B (lower)
        s4 = self.addSwitch('s4')   # right aggregation switch

        # --- Priority flow links ---
        self.addLink(h1, s1)
        self.addLink(s4, h2)

        # --- Two paths between s1 and s4 (shared with background traffic) ---
        self.addLink(s1, s2)        # Path A: s1 → s2 → s4
        self.addLink(s2, s4)
        self.addLink(s1, s3)        # Path B: s1 → s3 → s4
        self.addLink(s3, s4)

        # --- Background hosts connect to aggregation switches ---
        # h3, h4 on the left (s1); h5, h6 on the right (s4)
        # Their iperf traffic traverses s1→s2→s4 or s1→s3→s4,
        # competing with the h1→h2 priority flow
        self.addLink(h3, s1)
        self.addLink(h4, s1)
        self.addLink(h5, s4)
        self.addLink(h6, s4)

# Register topology so Mininet can load it by name
topos = {'qoe': (lambda: QoETopo())}

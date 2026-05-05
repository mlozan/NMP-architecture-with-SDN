from mininet.topo import Topo

class QoETopo(Topo):
    def build(self):
        # Add hosts with fixed IPs
        h1 = self.addHost('h1', ip='10.0.0.1')
        h2 = self.addHost('h2', ip='10.0.0.2')

        # Add three switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Connect hosts and switches (defines the two paths)
        self.addLink(h1, s1)
        self.addLink(s1, s2)   # Path A
        self.addLink(s2, h2)
        self.addLink(s1, s3)   # Path B
        self.addLink(s3, h2)

# Register topology so Mininet can find it by name
topos = {'qoe': (lambda: QoETopo())}

#!/usr/bin/env python3
"""
traffic_controller.py — run from the Mininet CLI
Automatically cycles through congestion phases to test QoE-based rerouting.
Starts iperf servers on h5/h6, then alternates between congestion levels.
 
Usage (from Mininet CLI):
    mininet> py exec(open('/path/to/traffic_controller.py').read())
"""
 
import time
import subprocess
 
# --- Configuration ---
H5_IP = "10.0.0.5"
H6_IP = "10.0.0.6"
DURATION = 99999  # iperf duration (killed manually between phases)
 
# Congestion phases: (label, bw_h3, bw_h4, duration_seconds)
# Total load = bw_h3 + bw_h4 on the shared 10Mbps links
PHASES = [
    ("No congestion",      "0M",    "0M",    30),   # baseline — no background traffic
    ("Light congestion",   "3M",    "3M",    60),   # 6M/10M — mild QoE degradation
    ("Medium congestion",  "4M",    "4M",    60),   # 8M/10M — noticeable degradation
    ("Heavy congestion",   "4.5M",  "4.5M",  60),   # 9M/10M — should trigger rerouting
    ("No congestion",      "0M",    "0M",    30),   # recovery period
    ("Medium congestion",  "4M",    "4M",    60),   # repeat medium
    ("Heavy congestion",   "4.5M",  "4.5M",  60),   # repeat heavy
    ("No congestion",      "0M",    "0M",    30),   # final recovery
]
 
 
def run_on_host(net, host_name, cmd):
    """Run a command on a Mininet host."""
    host = net.get(host_name)
    host.cmd(cmd)
 
 
def kill_iperf(net):
    """Kill all iperf client processes on h3 and h4."""
    for h in ['h3', 'h4']:
        net.get(h).cmd('kill %iperf 2>/dev/null; pkill -f iperf 2>/dev/null')
 
 
def start_servers(net):
    """Start iperf UDP servers on h5 and h6."""
    print("[traffic] Starting iperf servers on h5 and h6...")
    net.get('h5').cmd('pkill iperf 2>/dev/null; iperf -s -u -D')
    net.get('h6').cmd('pkill iperf 2>/dev/null; iperf -s -u -D')
    time.sleep(1)
    print("[traffic] Servers ready.")
 
 
def run_phases(net):
    """Cycle through congestion phases."""
    start_servers(net)
 
    print("\n[traffic] Starting congestion cycle...\n")
    print(f"{'Phase':<25} {'Load':<12} {'Duration':>8}")
    print("-" * 48)
 
    for label, bw_h3, bw_h4, duration in PHASES:
        # Kill any existing iperf clients first
        kill_iperf(net)
        time.sleep(0.5)
 
        if bw_h3 == "0M":
            print(f"[{label:<23}]  {'idle':<12}  {duration:>5}s  — no background traffic")
        else:
            total_bw = int(bw_h3[:-1]) + int(bw_h4[:-1])
            print(f"[{label:<23}]  {total_bw}M/10M total  {duration:>5}s")
 
            # Start iperf clients
            net.get('h3').cmd(f'iperf -c {H5_IP} -u -b {bw_h3} -t {DURATION} &')
            net.get('h4').cmd(f'iperf -c {H6_IP} -u -b {bw_h4} -t {DURATION} &')
 
        # Wait for the phase duration
        for remaining in range(duration, 0, -10):
            time.sleep(min(10, remaining))
            print(f"  ... {remaining}s remaining in phase [{label}]")
 
    # Clean up
    kill_iperf(net)
    print("\n[traffic] Congestion cycle complete. All iperf clients stopped.")
 
 
# --- Entry point when called from Mininet CLI ---
# mininet> py exec(open('/path/to/traffic_controller.py').read())
# This makes run_phases(net) available to call immediately after
run_phases(net)

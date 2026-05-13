#!/usr/bin/env python3
"""
traffic_controller.py — run from a VM terminal (NOT from Mininet CLI)
Uses mnexec to run iperf commands inside Mininet host namespaces.
Also sets up QoS rules via ovs-ofctl/ovs-vsctl before starting traffic.

Usage:
    sudo python3 traffic_controller.py

Requirements:
    - Mininet must already be running with topo_qoe
    - Run as root (sudo)
"""

import subprocess
import time
import os

# --- Configuration ---
H5_IP = "10.0.0.5"
H6_IP = "10.0.0.6"
DURATION = 99999

LINK_BW  = 10_000_000   # 10 Mbps in bps
HIGH_BW  =  9_000_000   #  9 Mbps guaranteed for priority traffic

# Congestion phases: (label, bw_h3, bw_h4, duration_seconds)
PHASES = [
    ("No congestion",     "0M",    "0M",    30),
    ("Light congestion",  "3M",    "3M",    60),
    ("Medium congestion", "4M",    "4M",    60),
    ("Heavy congestion",  "4.5M",  "4.5M",  60),
    ("No congestion",     "0M",    "0M",    30),
    ("Medium congestion", "4M",    "4M",    60),
    ("Heavy congestion",  "4.5M",  "4.5M",  60),
    ("No congestion",     "0M",    "0M",    30),
]

# ---------------------------------------------------------------------------
# QoS Setup
# ---------------------------------------------------------------------------

def run_cmd(cmd, check=True):
    """Run a shell command and return its stdout. Prints errors but never crashes."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"  [WARN] cmd returned {result.returncode}: {cmd}")
        if result.stderr:
            print(f"         {result.stderr.strip()}")
    return result.stdout.strip()

def setup_qos():
    """
    Mirrors qos_setup.sh:
      1. Force background traffic (DSCP 0) through Path A (s1→s2).
      2. Create HTB QoS queues on s1-eth2 and s2-eth2.
      3. Map DSCP 46 → Queue 0 (high priority) and DSCP 0 → Queue 1 (low priority).
    """
    print("=== QoS Setup for Mininet QoE Topology ===\n")

    # ------------------------------------------------------------------
    # Step 1: Force background traffic through Path A (s1→s2)
    # ------------------------------------------------------------------
    print("[1/3] Forcing background traffic through Path A (s1→s2)...")
    run_cmd("ovs-ofctl add-flow s1 'priority=100,ip,nw_tos=0,actions=set_queue:1,output:2'")
    print("      Background traffic (DSCP 0) locked to s1→s2")
    print("      Path B (s1→s3) stays free for rerouting\n")

    # ------------------------------------------------------------------
    # Step 2: Create QoS queues on s1-eth2 and s2-eth2
    # ------------------------------------------------------------------
    print("[2/3] Creating QoS queues...")

    # Clean existing QoS/Queue objects
    run_cmd("ovs-vsctl clear port s1-eth2 qos", check=False)
    run_cmd("ovs-vsctl clear port s2-eth2 qos", check=False)
    run_cmd("ovs-vsctl --all destroy QoS",       check=False)
    run_cmd("ovs-vsctl --all destroy Queue",     check=False)

    # --- s1-eth2 ---
    q0_s1  = run_cmd(f"ovs-vsctl create Queue "
                     f"other-config:min-rate={HIGH_BW} "
                     f"other-config:max-rate={LINK_BW}")
    q1_s1  = run_cmd(f"ovs-vsctl create Queue "
                     f"other-config:min-rate=0 "
                     f"other-config:max-rate={LINK_BW}")
    qos_s1 = run_cmd(f"ovs-vsctl create QoS type=linux-htb "
                     f"queues:0={q0_s1} queues:1={q1_s1} "
                     f"other-config:max-rate={LINK_BW}")
    run_cmd(f"ovs-vsctl set port s1-eth2 qos={qos_s1}")
    print("      s1-eth2: Q0=high priority (9 Mbps), Q1=low priority")

    # --- s2-eth2 ---
    q0_s2  = run_cmd(f"ovs-vsctl create Queue "
                     f"other-config:min-rate={HIGH_BW} "
                     f"other-config:max-rate={LINK_BW}")
    q1_s2  = run_cmd(f"ovs-vsctl create Queue "
                     f"other-config:min-rate=0 "
                     f"other-config:max-rate={LINK_BW}")
    qos_s2 = run_cmd(f"ovs-vsctl create QoS type=linux-htb "
                     f"queues:0={q0_s2} queues:1={q1_s2} "
                     f"other-config:max-rate={LINK_BW}")
    run_cmd(f"ovs-vsctl set port s2-eth2 qos={qos_s2}")
    print("      s2-eth2: Q0=high priority (9 Mbps), Q1=low priority\n")

    # ------------------------------------------------------------------
    # Step 3: Map DSCP → queues via OpenFlow rules
    # ------------------------------------------------------------------
    print("[3/3] Mapping DSCP → queues...")

    # s1: DSCP 46 (tos=184) → Queue 0, normal forwarding
    run_cmd("ovs-ofctl add-flow s1 'priority=200,ip,nw_tos=184,actions=set_queue:0,normal'")
    # s1: DSCP 0  (tos=0)   → Queue 1, forced via port 2 (s2)
    run_cmd("ovs-ofctl add-flow s1 'priority=100,ip,nw_tos=0,actions=set_queue:1,output:2'")
    # s2: DSCP 46 → Queue 0
    run_cmd("ovs-ofctl add-flow s2 'priority=200,ip,nw_tos=184,actions=set_queue:0,normal'")
    # s2: DSCP 0  → Queue 1
    run_cmd("ovs-ofctl add-flow s2 'priority=100,ip,nw_tos=0,actions=set_queue:1,normal'")

    print("      DSCP 46 (tos=184) → Queue 0 (9 Mbps guaranteed)")
    print("      DSCP 0  (tos=0)   → Queue 1 (dropped first under congestion)\n")

    print("=== QoS Setup Complete ===\n")
    print("Background traffic : always via Path A (s1→s2→s4), saturates the link")
    print("Priority traffic   : via Path A initially, MATLAB reroutes to Path B when QoE drops")
    print("Path B             : free and available for rerouting\n")
    print("Verify with:")
    print("  ovs-ofctl dump-flows s1")
    print("  ovs-vsctl list QoS\n")
    print("Undo with:")
    print("  sudo bash qos_teardown.sh\n")

# ---------------------------------------------------------------------------
# Mininet host helpers
# ---------------------------------------------------------------------------

def get_pid(host_name):
    """Get the PID of a Mininet host process to use with mnexec."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', f'mininet:{host_name}'],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')
        pid = lines[0].strip()
        if pid:
            return pid
        # Fallback: try finding via ip netns
        result2 = subprocess.run(
            ['ip', 'netns', 'pids', host_name],
            capture_output=True, text=True
        )
        pid2 = result2.stdout.strip().split('\n')[0].strip()
        return pid2 if pid2 else None
    except Exception:
        return None


def run_in_host(host_name, cmd, background=False):
    """Run a command inside a Mininet host namespace using mnexec."""
    pid = get_pid(host_name)
    if not pid:
        print(f"[ERROR] Could not find PID for {host_name}")
        return

    full_cmd = f"mnexec -a {pid} {cmd}"
    if background:
        full_cmd += " &"
        os.system(full_cmd)
    else:
        subprocess.run(full_cmd, shell=True, capture_output=True)

# ---------------------------------------------------------------------------
# Traffic helpers
# ---------------------------------------------------------------------------

def kill_iperf_clients():
    """Kill iperf clients on h3 and h4."""
    for host in ['h3', 'h4']:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill -f iperf 2>/dev/null")
    print("[traffic] iperf clients stopped.")


def start_servers():
    """Start iperf UDP servers on h5 and h6."""
    print("[traffic] Starting iperf servers on h5 and h6...")
    for host, ip in [('h5', H5_IP), ('h6', H6_IP)]:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill iperf 2>/dev/null")
            os.system(f"mnexec -a {pid} iperf -s -u -D")
        else:
            print(f"[ERROR] Could not find {host}")
    time.sleep(1)
    print("[traffic] Servers ready.")


def start_clients(bw_h3, bw_h4):
    """Start iperf UDP clients on h3 and h4."""
    pid_h3 = get_pid('h3')
    pid_h4 = get_pid('h4')
    if pid_h3:
        os.system(f"mnexec -a {pid_h3} iperf -c {H5_IP} -u -b {bw_h3} -t {DURATION} &")
    if pid_h4:
        os.system(f"mnexec -a {pid_h4} iperf -c {H6_IP} -u -b {bw_h4} -t {DURATION} &")

# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------

def run_phases():
    start_servers()
    print("\n[traffic] Starting congestion cycle...\n")
    print(f"{'Phase':<25} {'Load':<12} {'Duration':>8}")
    print("-" * 50)

    for label, bw_h3, bw_h4, duration in PHASES:
        kill_iperf_clients()
        time.sleep(0.5)

        if bw_h3 == "0M":
            print(f"[{label:<23}]  {'idle':<12}  {duration:>5}s")
        else:
            total = float(bw_h3[:-1]) + float(bw_h4[:-1])
            print(f"[{label:<23}]  {total:.1f}M/10M      {duration:>5}s")
            start_clients(bw_h3, bw_h4)

        for remaining in range(duration, 0, -10):
            time.sleep(min(10, remaining))
            print(f"  ... {remaining}s remaining [{label}]")

    kill_iperf_clients()
    print("\n[traffic] Cycle complete.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[ERROR] Run as root: sudo python3 traffic_controller.py")
        exit(1)

    setup_qos()   # <-- QoS rules applied before any traffic starts
    run_phases()

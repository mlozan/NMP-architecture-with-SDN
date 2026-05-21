#!/usr/bin/env python3
"""
background_traffic.py
=====================
Generates phased background UDP traffic between h3→h5 and h4→h6 to saturate
Path A (s1→s3→s4), triggering QoE degradation and ONOS rerouting.

Run directly from the VM (no need to enter the Mininet CLI):
    sudo python3 background_traffic.py

Requirements:
  - Mininet must already be running with topo_qoe.py
  - iperf (v2) must be installed on the VM  <-- NOT iperf3
  - Must be run with sudo (required for mnexec to enter host namespaces)

Traffic phases (cycled once):
  1. No congestion    0 + 0   Mbps   30 s
  2. Light            3 + 3   Mbps   60 s
  3. Medium           5 + 5   Mbps   60 s
  4. Heavy            9.5+9.5 Mbps   60 s
  5. No congestion    0 + 0   Mbps   30 s
"""

import subprocess
import time
import os

# ─── Configuration ────────────────────────────────────────────────────────────
H5_IP    = "10.0.0.5"
H6_IP    = "10.0.0.6"
DURATION = 99999        # iperf client duration (s) — effectively infinite per phase

# Congestion phases: (label, bw_h3, bw_h4, phase_duration_s)
PHASES = [
    ("No congestion",     "0M",   "0M",    30),
    ("Light congestion",  "3M",   "3M",    60),
    ("Medium congestion", "5M",   "5M",    60),
    ("Heavy congestion",  "9.5M", "9.5M",  60),
    ("No congestion",     "0M",   "0M",    30),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_pid(hostname):
    """
    Returns the PID of the process running inside the network namespace of the
    given Mininet host. Mininet names its processes as 'mininet:<hostname>'.
    """
    result = subprocess.run(
        ["pgrep", "-f", f"mininet:{hostname}"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split("\n")
    return lines[0].strip() if lines and lines[0] else None

def run_in_host(hostname, cmd, background=False):
    """
    Runs a shell command inside the network namespace of a Mininet host.
    Uses mnexec -a <pid> to attach to the host's namespace.
    If background=True the command is launched with & (fire-and-forget).
    """
    pid = get_pid(hostname)
    if not pid:
        print(f"[ERROR] No PID found for host '{hostname}'. Is Mininet running?")
        return
    full = f"mnexec -a {pid} {cmd}"
    if background:
        os.system(full + " &")
    else:
        subprocess.run(full, shell=True)

# ─── Traffic control ──────────────────────────────────────────────────────────

def kill_clients():
    """Kill iperf client processes on h3 and h4."""
    for host in ["h3", "h4"]:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill -f iperf 2>/dev/null")

def start_servers():
    """
    Start iperf v2 UDP servers on h5 and h6 in daemon mode (-D).
    Kills any existing iperf instances first.
    """
    print("[traffic] Starting iperf servers on h5 and h6...")
    for host in ["h5", "h6"]:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill iperf 2>/dev/null")
            os.system(f"mnexec -a {pid} iperf -s -u -D")   # UDP server, daemonized
    time.sleep(1)   # give servers time to bind before clients connect

def start_clients(bw_h3, bw_h4):
    """
    Launch iperf v2 UDP clients on h3 and h4.
    h3 → h5, h4 → h6, both on Path A — combined load saturates the link.
    """
    pid_h3 = get_pid("h3")
    pid_h4 = get_pid("h4")
    if pid_h3:
        os.system(f"mnexec -a {pid_h3} iperf -c {H5_IP} -u -b {bw_h3} -t {DURATION} &")
    if pid_h4:
        os.system(f"mnexec -a {pid_h4} iperf -c {H6_IP} -u -b {bw_h4} -t {DURATION} &")

# ─── Phase runner ─────────────────────────────────────────────────────────────

def run_phases():
    """Cycle through all congestion phases, printing progress every 10 s."""
    start_servers()
    print("\n[traffic] Starting congestion cycle...\n")

    for label, bw_h3, bw_h4, phase_dur in PHASES:
        kill_clients()
        time.sleep(0.5)

        if bw_h3 == "0M":
            print(f"[{label}] idle for {phase_dur}s")
        else:
            total = float(bw_h3[:-1]) + float(bw_h4[:-1])
            print(f"[{label}] load {total}M / 10M for {phase_dur}s")
            start_clients(bw_h3, bw_h4)

        # Count down, printing a heartbeat every 10 s
        for remaining in range(phase_dur, 0, -10):
            time.sleep(min(10, remaining))
            print(f"  ... {remaining}s remaining")

    kill_clients()
    print("\n[traffic] All phases complete.")

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[ERROR] This script must be run with sudo.")
        exit(1)
    run_phases()

#!/usr/bin/env python3
"""
traffic_controller.py — run from a VM terminal (NOT from Mininet CLI)
Uses mnexec to run iperf commands inside Mininet host namespaces.

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
    except:
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
    run_phases()

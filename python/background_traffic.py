#!/usr/bin/env python3
"""
background_traffic.py
=====================
Generates background UDP traffic between h3→h5 and h4→h6 to saturate
Path A (s1→s3→s4), causing QoE degradation on the monitored h1→h2 flow.

Run directly from the VM (no need to enter the Mininet CLI):
    sudo python3 background_traffic.py

Requirements:
  - Mininet must already be running with topo_qoe.py
  - iperf3 must be installed on the VM
  - Must be run with sudo (required for mnexec to enter host namespaces)
"""

import subprocess
import time
import signal
import sys
import os

# ─── Configuration ────────────────────────────────────────────────────────────
IPERF_DURATION  = 9999       # seconds (~infinite; press Ctrl+C to stop)
BANDWIDTH_MBPS  = "9M"       # UDP bandwidth per flow (~9 Mbps on a 10 Mbps link)
IPERF_PORT_H5   = 5201       # iperf3 server port on h5
IPERF_PORT_H6   = 5202       # iperf3 server port on h6
IP_H5           = "10.0.0.5"
IP_H6           = "10.0.0.6"

# ─── Helpers: locate Mininet host namespace ───────────────────────────────────

def get_host_pid(hostname):
    """
    Returns the PID of the process running inside the network namespace of the
    given Mininet host. Mininet names its host processes as 'mininet:<hostname>'.
    """
    try:
        result = subprocess.check_output(
            ["pgrep", "-f", f"mininet:{hostname}"],
            text=True
        ).strip()
        pids = result.splitlines()
        if not pids:
            raise RuntimeError(f"No process found for mininet:{hostname}")
        return int(pids[0])
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"Host '{hostname}' not found. "
            "Is Mininet running with topo_qoe.py?"
        )

def run_in_host(hostname, cmd, background=True):
    """
    Runs a command inside the network namespace of a Mininet host using mnexec.
    If background=True, launches the process in the background and returns the
    Popen object so it can be terminated later.
    """
    pid = get_host_pid(hostname)
    full_cmd = ["mnexec", "-a", str(pid)] + cmd
    if background:
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    else:
        subprocess.run(full_cmd, check=False)
        return None

# ─── Main logic ───────────────────────────────────────────────────────────────

procs = []   # track background processes so they can be cleaned up on exit

def start_servers():
    """Start iperf3 servers on h5 and h6."""
    print("[BG] Killing any existing iperf3 instances on h5 and h6...")
    run_in_host("h5", ["pkill", "-f", "iperf3"], background=False)
    run_in_host("h6", ["pkill", "-f", "iperf3"], background=False)
    time.sleep(0.5)

    print(f"[BG] Starting iperf3 server on h5 (port {IPERF_PORT_H5})...")
    p1 = run_in_host("h5", [
        "iperf3", "-s", "-p", str(IPERF_PORT_H5),
        "--logfile", "/tmp/iperf_server_h5.log"
    ])
    procs.append(p1)

    print(f"[BG] Starting iperf3 server on h6 (port {IPERF_PORT_H6})...")
    p2 = run_in_host("h6", [
        "iperf3", "-s", "-p", str(IPERF_PORT_H6),
        "--logfile", "/tmp/iperf_server_h6.log"
    ])
    procs.append(p2)

    time.sleep(1)   # wait for servers to be ready before launching clients

def start_clients():
    """Launch UDP iperf3 clients from h3→h5 and h4→h6."""
    print(f"[BG] UDP client h3 → h5 ({IP_H5}:{IPERF_PORT_H5})  bw={BANDWIDTH_MBPS}")
    p3 = run_in_host("h3", [
        "iperf3",
        "-c", IP_H5,
        "-p", str(IPERF_PORT_H5),
        "-u",                        # UDP mode
        "-b", BANDWIDTH_MBPS,
        "-t", str(IPERF_DURATION),
        "--logfile", "/tmp/iperf_client_h3.log"
    ])
    procs.append(p3)

    print(f"[BG] UDP client h4 → h6 ({IP_H6}:{IPERF_PORT_H6})  bw={BANDWIDTH_MBPS}")
    p4 = run_in_host("h4", [
        "iperf3",
        "-c", IP_H6,
        "-p", str(IPERF_PORT_H6),
        "-u",                        # UDP mode
        "-b", BANDWIDTH_MBPS,
        "-t", str(IPERF_DURATION),
        "--logfile", "/tmp/iperf_client_h4.log"
    ])
    procs.append(p4)

def stop_all(signum=None, frame=None):
    """Gracefully stop all iperf3 processes on Ctrl+C or SIGTERM."""
    print("\n[BG] Stopping background traffic...")

    # Terminate tracked Popen objects
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass

    # Also pkill inside each namespace in case any process became orphaned
    for host in ["h3", "h4", "h5", "h6"]:
        try:
            run_in_host(host, ["pkill", "-f", "iperf3"], background=False)
        except Exception:
            pass

    print("[BG] Background traffic stopped.")
    sys.exit(0)

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[ERROR] This script must be run with sudo.")
        sys.exit(1)

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT,  stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    print("=" * 50)
    print(" Background Traffic Generator (VM mode)")
    print("=" * 50)

    try:
        start_servers()
        start_clients()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print("\n[BG] Traffic active. Logs at /tmp/iperf_client_h*.log")
    print("[BG] Press Ctrl+C to stop.\n")

    # Keep the script alive so Ctrl+C can trigger the signal handler
    while True:
        time.sleep(1)

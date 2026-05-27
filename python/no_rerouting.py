#!/usr/bin/env python3
"""
experiment1_no_rerouting.py
============================
Experiment 1 for TFM — Baseline: QoE degradation WITHOUT rerouting.

Timeline:
  0s  – 60s  : No background traffic  → QoE should be high (baseline)
  60s – 180s : iperf traffic at 9 Mbps saturates Path A → QoE degrades

How to run
----------
1. Make sure ONOS is running and has loaded your topology.
2. Start Mininet in a separate terminal:
       sudo mn --custom topo.py --topo qoe --controller remote,ip=192.168.56.101,port=6653
3. In MATLAB: open qoe_monitor.m and SET REROUTING_ENABLED = false  (see note below)
4. In the Mininet CLI, run metrics_h1.py on h1:
       mininet> h1 python3 metrics_h1.py &
5. On the VM host, run udp_sender.py:
       python3 udp_sender.py &
6. Run this script on the VM host (needs root for Mininet API or run via Mininet CLI):
       sudo python3 experiment1_no_rerouting.py

NOTE — disabling rerouting in MATLAB
--------------------------------------
In qoe_monitor.m, add this constant at the top of the CONFIGURATION section:
    REROUTING_ENABLED = false;
Then wrap the rerouting block like this:
    if REROUTING_ENABLED
        if QoE < QOE_THRESHOLD && cooldown_ok
            ...
        end
    end
This way you can switch between Experiment 1 (false) and Experiment 2 (true)
with a single flag, keeping both experiments identical in every other way.

Topology reminder
-----------------
  h3 (10.0.0.3) --> s1 --> [Path A: s3] --> s4 --> h5 (10.0.0.5)   background iperf
  h4 (10.0.0.4) --> s1 --> [Path A: s3] --> s4 --> h6 (10.0.0.6)   background iperf
  h1 (10.0.0.1) --> s1 --> [Path A: s3] --> s4 --> h2 (10.0.0.2)   QoE flow (monitored)
"""

import subprocess
import time
import sys
import os
import signal

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S   = 60    # seconds with no background traffic
PHASE_CONGESTION_S = 120   # seconds with iperf running
IPERF_BW_MBPS      = 9     # Mbps — saturates the 10 Mbps Path A links

# iperf3 targets (receivers on the right side of the topology)
IPERF_TARGETS = [
    {"sender": "h3", "receiver": "h5", "receiver_ip": "10.0.0.5"},
    {"sender": "h4", "receiver": "h6", "receiver_ip": "10.0.0.6"},
]

# Log file — written on the VM, readable from anywhere
LOG_FILE = "/tmp/experiment1_log.txt"

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    """Print with timestamp and write to log file."""
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_on_host(host_name, cmd, background=False):
    """
    Run a shell command on a Mininet host using 'mnexec'.
    mnexec -a <pid> runs in the host's network namespace.

    For simplicity this uses 'ip netns exec' which works when
    Mininet has created named namespaces (requires --no-cli or
    running from within the Mininet Python API).

    Alternative: pipe commands into the Mininet CLI via stdin.
    """
    full_cmd = f"mnexec -a $(pgrep -f 'mininet:{host_name}' | head -1) {cmd}"
    if background:
        full_cmd += " &"
    return subprocess.Popen(full_cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)


def start_iperf_servers():
    """Start iperf3 servers on h5 and h6 (receivers)."""
    log("Starting iperf3 servers on h5 and h6...")
    for t in IPERF_TARGETS:
        receiver = t["receiver"]
        proc = run_on_host(receiver, "iperf3 -s -D")   # -D = daemon mode
        time.sleep(0.5)
        log(f"  iperf3 server started on {receiver}")


def start_iperf_clients():
    """Start iperf3 clients on h3 and h4 (senders) — runs for PHASE_CONGESTION_S."""
    log(f"Starting iperf3 clients (h3->h5, h4->h6) at {IPERF_BW_MBPS} Mbps each...")
    procs = []
    for t in IPERF_TARGETS:
        sender   = t["sender"]
        recv_ip  = t["receiver_ip"]
        duration = PHASE_CONGESTION_S
        cmd = (f"iperf3 -c {recv_ip} "
               f"-b {IPERF_BW_MBPS}M "
               f"-t {duration} "
               f"-u "           # UDP — more realistic for audio/media traffic
               f"--dscp 0 "     # Best-effort DSCP — lower priority than QoE flow
               f"-i 5")         # report every 5s
        proc = run_on_host(sender, cmd, background=True)
        procs.append(proc)
        log(f"  iperf3 client started: {sender} -> {recv_ip}")
    return procs


def stop_iperf_servers():
    """Kill iperf3 server processes."""
    log("Stopping iperf3 servers...")
    subprocess.run("pkill -f 'iperf3 -s'", shell=True)


# ── Alternative: Mininet CLI pipe mode ────────────────────────────────────────
# If mnexec is not available, you can run the experiment by piping
# commands directly to the Mininet CLI. Use this function instead:

def run_via_mininet_cli():
    """
    Prints the exact commands to paste into the Mininet CLI.
    Use this if you prefer to run the experiment semi-manually.
    """
    print("\n" + "="*60)
    print("MANUAL MODE — paste these commands into the Mininet CLI")
    print("="*60)
    print()
    print("# Step 1 — start iperf3 servers on receivers (do this first)")
    print("mininet> h5 iperf3 -s &")
    print("mininet> h6 iperf3 -s &")
    print()
    print("# Step 2 — wait for MATLAB to show stable QoE (about 60s)")
    print("#          then paste the next two lines:")
    print()
    print(f"mininet> h3 iperf3 -c 10.0.0.5 -b {IPERF_BW_MBPS}M -t {PHASE_CONGESTION_S} -u --dscp 0 -i 5 &")
    print(f"mininet> h4 iperf3 -c 10.0.0.6 -b {IPERF_BW_MBPS}M -t {PHASE_CONGESTION_S} -u --dscp 0 -i 5 &")
    print()
    print("# Step 3 — note the exact time you pasted step 2 for your thesis")
    print("# Step 4 — after 120s, kill iperf clients:")
    print("mininet> h3 kill %1")
    print("mininet> h4 kill %1")
    print()
    print("="*60 + "\n")


# ── Main experiment flow ───────────────────────────────────────────────────────

def main():
    # Clear log
    with open(LOG_FILE, "w") as f:
        f.write(f"Experiment 1 — Baseline without rerouting\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Baseline phase: {PHASE_BASELINE_S}s\n")
        f.write(f"Congestion phase: {PHASE_CONGESTION_S}s at {IPERF_BW_MBPS} Mbps\n")
        f.write("-" * 50 + "\n\n")

    log("="*55)
    log("EXPERIMENT 1 — Baseline: QoE degradation without rerouting")
    log("="*55)
    log(f"Baseline phase : {PHASE_BASELINE_S}s  (no background traffic)")
    log(f"Congestion phase: {PHASE_CONGESTION_S}s  (iperf @ {IPERF_BW_MBPS} Mbps)")
    log("")
    log("Make sure:")
    log("  1. ONOS is running")
    log("  2. Mininet is running with your topology")
    log("  3. metrics_h1.py is running on h1")
    log("  4. udp_sender.py is running on the VM")
    log("  5. MATLAB qoe_monitor.m is open with REROUTING_ENABLED = false")
    log("")

    # Check if user wants CLI mode (safer, no mnexec dependency)
    print("Choose mode:")
    print("  1 = Automatic (uses mnexec — requires root + Mininet running)")
    print("  2 = Manual CLI instructions (recommended for most setups)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        run_via_mininet_cli()
        log("Manual CLI instructions printed. Run the experiment manually.")
        log(f"Remember to mark t=0 (baseline start) and t={PHASE_BASELINE_S}s (congestion start) in your notes.")
        return

    # ── Automatic mode ──
    log("\n[PHASE 1] Baseline — no background traffic")
    log(f"  Duration: {PHASE_BASELINE_S}s")
    log("  MATLAB should show QoE stable and high. Let it record...")

    start_iperf_servers()

    # Wait for baseline
    for remaining in range(PHASE_BASELINE_S, 0, -10):
        log(f"  Baseline: {remaining}s remaining...")
        time.sleep(10)

    # ── Phase 2: congestion ──
    log(f"\n[PHASE 2] Congestion starts NOW — iperf @ {IPERF_BW_MBPS} Mbps")
    log("  Watch QoE drop in MATLAB plots.")
    log(f"  Duration: {PHASE_CONGESTION_S}s")

    iperf_procs = start_iperf_clients()

    # Wait for congestion phase
    for remaining in range(PHASE_CONGESTION_S, 0, -10):
        log(f"  Congestion: {remaining}s remaining...")
        time.sleep(10)

    # ── End ──
    log("\n[END] Experiment 1 complete.")
    log("  iperf clients should have stopped automatically (fixed duration).")
    stop_iperf_servers()

    log("")
    log("="*55)
    log("NEXT STEPS:")
    log("  1. Save the MATLAB figure (File > Save As > .fig and .png)")
    log("  2. Export the MATLAB workspace (save('exp1_results.mat'))")
    log(f"  3. Check the log at {LOG_FILE}")
    log("  4. Run Experiment 2 with REROUTING_ENABLED = true")
    log("="*55)


if __name__ == "__main__":
    main()

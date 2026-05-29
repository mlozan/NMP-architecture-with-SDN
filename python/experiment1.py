#!/usr/bin/env python3
"""
experiment1_no_rerouting.py
============================
Experiment 1 for TFM — Baseline: QoE degradation WITHOUT rerouting.

Timeline:
  0s  –  60s : No background traffic  → QoE stable and high (baseline)
  60s – 180s : iperf UDP at 100 Mbps saturates Path A → QoE degrades

How to run
----------
1. Start ONOS:
       sudo docker run -d --name onos \
         -p 192.168.56.102:8181:8181 \
         -p 192.168.56.102:6653:6653 \
         -p 192.168.56.102:6640:6640 \
         -p 127.0.0.1:8101:8101 \
         onosproject/onos:2.7.0

2. Start Mininet in a separate terminal:
       sudo mn --custom topo_qoe.py --topo qoe \
           --controller remote,ip=192.168.56.102,port=6653 \
           --switch ovsk,protocols=OpenFlow13

3. In the Mininet CLI, start metrics_h1.py on h1:
       mininet> h1 python3 metrics_h1.py &

4. In a separate terminal, start metrics_vm.py:
       python3 metrics_vm.py

5. In MATLAB: open qoe_monitor.m with REROUTING_ENABLED = false and press Run.

6. Run this script:
       sudo python3 experiment1_no_rerouting.py

Topology reminder
-----------------
  h3 (10.0.0.3) --> s1 --> [Path A: s3] --> s4 --> h5 (10.0.0.5)   background iperf
  h4 (10.0.0.4) --> s1 --> [Path A: s3] --> s4 --> h6 (10.0.0.6)   background iperf
  h1 (10.0.0.1) --> s1 --> [Path A: s3] --> s4 --> h2 (10.0.0.2)   QoE flow (monitored)
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S   = 60    # seconds with no background traffic
PHASE_CONGESTION_S = 120   # seconds with iperf running

# 100 Mbps per flow — high enough to saturate regardless of OVS bw enforcement
# Two flows (h3->h5 and h4->h6) = 200 Mbps total on Path A
IPERF_BW_MBPS = 100

IPERF_TARGETS = [
    {"sender": "h3", "receiver": "h5", "receiver_ip": "10.0.0.5"},
    {"sender": "h4", "receiver": "h6", "receiver_ip": "10.0.0.6"},
]

LOG_FILE = "/tmp/experiment1_log.txt"

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_on_host(host_name, cmd, background=False):
    """
    Run a command inside a Mininet host's network namespace using mnexec.
    Finds the host process by matching 'mininet:<host_name>' in the process list.
    """
    pid_cmd = f"pgrep -f 'mininet:{host_name}' | head -1"
    pid_result = subprocess.run(pid_cmd, shell=True, capture_output=True, text=True)
    pid = pid_result.stdout.strip()

    if not pid:
        log(f"  [WARN] Could not find PID for {host_name} — is Mininet running?")
        return None

    full_cmd = f"mnexec -a {pid} {cmd}"
    if background:
        return subprocess.Popen(full_cmd, shell=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    else:
        return subprocess.run(full_cmd, shell=True,
                              capture_output=True, text=True)


def start_iperf_servers():
    """Start iperf3 servers on h5 and h6."""
    log("Starting iperf3 servers on h5 and h6...")
    for t in IPERF_TARGETS:
        proc = run_on_host(t["receiver"], "iperf3 -s", background=True)
        if proc:
            log(f"  iperf3 server started on {t['receiver']}")
        time.sleep(0.5)


def start_iperf_clients():
    """Start iperf3 clients on h3 and h4 at IPERF_BW_MBPS each."""
    log(f"Starting iperf3 clients at {IPERF_BW_MBPS} Mbps each "
        f"({IPERF_BW_MBPS * 2} Mbps total on Path A)...")
    procs = []
    for t in IPERF_TARGETS:
        cmd = (f"iperf3 -c {t['receiver_ip']} "
               f"-b {IPERF_BW_MBPS}M "
               f"-t {PHASE_CONGESTION_S} "
               f"-u "        # UDP — realistic for media traffic
               f"--dscp 0 "  # best-effort, lower priority than QoE flow DSCP=46
               f"-i 5")      # report every 5s
        proc = run_on_host(t["sender"], cmd, background=True)
        if proc:
            procs.append(proc)
            log(f"  iperf3 client started: {t['sender']} -> {t['receiver_ip']}")
    return procs


def stop_iperf():
    """Kill all iperf3 processes inside Mininet namespaces."""
    log("Stopping all iperf3 processes...")
    subprocess.run("pkill -f 'iperf3'", shell=True)


def print_manual_commands():
    """Print the exact commands to paste into the Mininet CLI manually."""
    bw = IPERF_BW_MBPS
    dur = PHASE_CONGESTION_S
    print("\n" + "=" * 62)
    print("  MANUAL MODE — paste into the Mininet CLI")
    print("=" * 62)
    print()
    print("# ── STEP 1: start iperf servers (do this now) ──────────────")
    print("mininet> h5 iperf3 -s &")
    print("mininet> h6 iperf3 -s &")
    print()
    print(f"# ── STEP 2: wait {PHASE_BASELINE_S}s of baseline in MATLAB ─────────────")
    print(f"# Then call mark_congestion_start() in MATLAB command window,")
    print(f"# and immediately paste the next two lines:")
    print()
    print(f"mininet> h3 iperf3 -c 10.0.0.5 -b {bw}M -t {dur} -u --dscp 0 -i 5 &")
    print(f"mininet> h4 iperf3 -c 10.0.0.6 -b {bw}M -t {dur} -u --dscp 0 -i 5 &")
    print()
    print(f"# ── STEP 3: wait {dur}s — watch QoE drop in MATLAB ──────────")
    print()
    print("# ── STEP 4: clean up ───────────────────────────────────────")
    print("mininet> h3 kill %1 2>/dev/null; h4 kill %1 2>/dev/null")
    print("mininet> h5 kill %1 2>/dev/null; h6 kill %1 2>/dev/null")
    print()
    print("=" * 62 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    with open(LOG_FILE, "w") as f:
        f.write("Experiment 1 — Baseline without rerouting\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Baseline: {PHASE_BASELINE_S}s | "
                f"Congestion: {PHASE_CONGESTION_S}s @ {IPERF_BW_MBPS} Mbps x2\n")
        f.write("-" * 50 + "\n\n")

    log("=" * 62)
    log("EXPERIMENT 1 — QoE degradation WITHOUT rerouting")
    log("=" * 62)
    log(f"Baseline  : {PHASE_BASELINE_S}s  (no background traffic)")
    log(f"Congestion: {PHASE_CONGESTION_S}s  "
        f"(iperf UDP @ {IPERF_BW_MBPS} Mbps x2 = {IPERF_BW_MBPS*2} Mbps total)")
    log("")
    log("Prerequisites:")
    log("  [1] ONOS running at 192.168.56.102:8181")
    log("  [2] Mininet running with topo_qoe.py")
    log("  [3] metrics_h1.py running on h1")
    log("  [4] metrics_vm.py running on the VM")
    log("  [5] MATLAB running with REROUTING_ENABLED = false")
    log("")

    print("Choose mode:")
    print("  1 = Automatic (uses mnexec — run as sudo)")
    print("  2 = Manual   (prints commands to paste in Mininet CLI)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        print_manual_commands()
        log("Manual commands printed.")
        log("Remember: call mark_congestion_start() in MATLAB when you launch iperf.")
        return

    # ── Automatic mode ──────────────────────────────────────────────────────

    log("\n[PHASE 1] Baseline — no background traffic")
    log(f"  Waiting {PHASE_BASELINE_S}s — MATLAB should show stable high QoE...")

    start_iperf_servers()

    for remaining in range(PHASE_BASELINE_S, 0, -10):
        log(f"  Baseline: {remaining}s remaining...")
        time.sleep(10)

    log(f"\n[PHASE 2] Congestion starts NOW")
    log(f"  Launching iperf @ {IPERF_BW_MBPS} Mbps x2 on Path A...")
    log("  >>> Call mark_congestion_start() in MATLAB command window NOW <<<")

    start_iperf_clients()

    for remaining in range(PHASE_CONGESTION_S, 0, -10):
        log(f"  Congestion: {remaining}s remaining...")
        time.sleep(10)

    log("\n[END] Congestion phase complete. iperf clients have stopped (fixed duration).")
    stop_iperf()

    log("")
    log("=" * 62)
    log("NEXT STEPS:")
    log("  1. Press Ctrl+C in MATLAB to stop the monitor")
    log("  2. In MATLAB command window, run:")
    log("       save('exp1_Bolero.mat', 'log_t','log_delay','log_jitter',")
    log("            'log_loss','log_D','log_qoe','log_path','congestion_time',")
    log("            'SONG_NAME','L_max','QOE_THRESHOLD','REROUTING_ENABLED');")
    log("       exportgraphics(fig, 'exp1_Bolero.png', 'Resolution', 300);")
    log("  3. Repeat for Master Blaster and Yellow Submarine")
    log("  4. Run Experiment 2 with REROUTING_ENABLED = true")
    log("=" * 62)


if __name__ == "__main__":
    main()

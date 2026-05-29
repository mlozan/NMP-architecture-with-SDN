#!/usr/bin/env python3
"""
experiment1_no_rerouting.py
============================
Experiment 1 for TFM — Baseline: QoE degradation WITHOUT rerouting.

Three congestion phases on Path A (s1->s3->s4, bottleneck = 10 Mbps):

  0s  –  60s : No load          → QoE ~1.0  (Excellent)
  60s – 120s : Medium-high load → QoE ~0.5-0.7  (Fair/Poor)
  120s– 180s : Heavy load       → QoE ~0.0  (Unacceptable)

Background traffic uses iperf3 UDP from h3->h5 and h4->h6 over Path A.
The QoE flow (h1->h2 ICMP DSCP=46) shares the same bottleneck links.

How to run
----------
1. Start ONOS:
       sudo docker run -d --name onos \
         -p 192.168.56.102:8181:8181 \
         -p 192.168.56.102:6653:6653 \
         -p 192.168.56.102:6640:6640 \
         -p 127.0.0.1:8101:8101 \
         onosproject/onos:2.7.0

2. Start Mininet (use updated topo_qoe.py with TCLink):
       sudo mn --custom topo_qoe.py --topo qoe \
           --controller remote,ip=192.168.56.102,port=6653 \
           --switch ovsk,protocols=OpenFlow13

3. In Mininet CLI:
       mininet> h1 python3 metrics_h1.py &

4. In a separate terminal:
       python3 metrics_vm.py

5. In MATLAB: open qoe_monitor.m with REROUTING_ENABLED = false, press Run.

6. Run this script:
       sudo python3 experiment1_no_rerouting.py
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────

PHASE_BASELINE_S = 60     # no load
PHASE_MEDIUM_S   = 60     # medium-high congestion
PHASE_HEAVY_S    = 60     # heavy congestion

# Bandwidth per iperf flow (two flows total: h3->h5 and h4->h6)
# Path A bottleneck = 10 Mbps
# Medium: 2 x 4 Mbps = 8 Mbps total  → leaves ~2 Mbps for QoE flow → some degradation
# Heavy:  2 x 9 Mbps = 18 Mbps total → saturates completely → heavy degradation
BW_MEDIUM_MBPS = 4
BW_HEAVY_MBPS  = 9

IPERF_TARGETS = [
    {"sender": "h3", "receiver": "h5", "receiver_ip": "10.0.0.5"},
    {"sender": "h4", "receiver": "h6", "receiver_ip": "10.0.0.6"},
]

LOG_FILE   = "/tmp/experiment1_log.txt"
PHASE_FILE = "/tmp/phase.txt"   # read by MATLAB to draw phase markers automatically

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def write_phase(phase):
    """Write current phase to file so MATLAB detects it automatically."""
    with open(PHASE_FILE, 'w') as f:
        f.write(phase)

def get_host_pid(host_name):
    """Find the PID of a Mininet host process by name."""
    result = subprocess.run(
        f"pgrep -f 'mininet:{host_name}' | head -1",
        shell=True, capture_output=True, text=True)
    pid = result.stdout.strip()
    if not pid:
        log(f"  [WARN] PID not found for {host_name} — is Mininet running?")
    return pid


def run_on_host(host_name, cmd, background=False):
    """Run a command inside a Mininet host's network namespace via mnexec."""
    pid = get_host_pid(host_name)
    if not pid:
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
    """Start iperf3 servers on h5 and h6 (receivers)."""
    log("Starting iperf3 servers on h5 and h6...")
    for t in IPERF_TARGETS:
        proc = run_on_host(t["receiver"], "iperf3 -s", background=True)
        if proc:
            log(f"  Server started on {t['receiver']}")
        time.sleep(0.3)


def start_iperf_clients(bw_mbps, duration_s, label):
    """Start iperf3 clients at bw_mbps on both senders."""
    log(f"  Launching iperf: {bw_mbps} Mbps x2 = {bw_mbps*2} Mbps total [{label}]")
    for t in IPERF_TARGETS:
        cmd = (f"iperf3 -c {t['receiver_ip']} "
               f"-b {bw_mbps}M "
               f"-t {duration_s} "
               f"-u "
               f"--dscp 0 "
               f"-i 10")
        proc = run_on_host(t["sender"], cmd, background=True)
        if proc:
            log(f"    {t['sender']} -> {t['receiver_ip']}  ({bw_mbps} Mbps, {duration_s}s)")


def stop_iperf_clients():
    """Kill iperf3 client processes inside Mininet namespaces."""
    for t in IPERF_TARGETS:
        pid = get_host_pid(t["sender"])
        if pid:
            subprocess.run(f"mnexec -a {pid} pkill -f 'iperf3 -c'",
                           shell=True, capture_output=True)
    log("  iperf clients stopped.")


def stop_iperf_servers():
    """Kill iperf3 server processes."""
    for t in IPERF_TARGETS:
        pid = get_host_pid(t["receiver"])
        if pid:
            subprocess.run(f"mnexec -a {pid} pkill -f 'iperf3 -s'",
                           shell=True, capture_output=True)
    log("  iperf servers stopped.")


def print_manual_commands():
    """Print commands to paste manually into the Mininet CLI."""
    bm  = BW_MEDIUM_MBPS
    bh  = BW_HEAVY_MBPS
    pm  = PHASE_MEDIUM_S
    ph  = PHASE_HEAVY_S

    print("\n" + "=" * 64)
    print("  MANUAL MODE — paste into the Mininet CLI")
    print("=" * 64)
    print()
    print("# ── SETUP: start iperf servers ──────────────────────────────")
    print("mininet> h5 iperf3 -s &")
    print("mininet> h6 iperf3 -s &")
    print()
    print(f"# ── PHASE 1: no load ({PHASE_BASELINE_S}s) ──────────────────────────────")
    print(f"#   Wait {PHASE_BASELINE_S}s — QoE should be ~1.0 (Excellent)")
    print(f"#   Call mark_congestion_start() in MATLAB when ready to proceed")
    print()
    print(f"# ── PHASE 2: medium-high congestion ({pm}s) ───────────────────")
    print(f"#   First write the phase signal so MATLAB marks it:")
    print(f"#   $ echo medium > /tmp/phase.txt")
    print(f"#   {bm} Mbps x2 = {bm*2} Mbps total on Path A (bottleneck 10 Mbps)")
    print(f"mininet> h3 iperf3 -c 10.0.0.5 -b {bm}M -t {pm} -u --dscp 0 -i 10 &")
    print(f"mininet> h4 iperf3 -c 10.0.0.6 -b {bm}M -t {pm} -u --dscp 0 -i 10 &")
    print(f"#   Wait {pm}s — QoE should degrade to Fair/Poor")
    print()
    print(f"# ── PHASE 3: heavy congestion ({ph}s) ────────────────────────")
    print(f"#   First write the phase signal so MATLAB marks it:")
    print(f"#   $ echo heavy > /tmp/phase.txt")
    print(f"#   {bh} Mbps x2 = {bh*2} Mbps total — fully saturates Path A")
    print(f"mininet> h3 iperf3 -c 10.0.0.5 -b {bh}M -t {ph} -u --dscp 0 -i 10 &")
    print(f"mininet> h4 iperf3 -c 10.0.0.6 -b {bh}M -t {ph} -u --dscp 0 -i 10 &")
    print(f"#   Wait {ph}s — QoE should drop to Unacceptable")
    print()
    print("# ── CLEANUP ─────────────────────────────────────────────────")
    print("mininet> h3 kill %1 2>/dev/null")
    print("mininet> h4 kill %1 2>/dev/null")
    print("mininet> h5 kill %1 2>/dev/null")
    print("mininet> h6 kill %1 2>/dev/null")
    print()
    print("=" * 64 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    total_s = PHASE_BASELINE_S + PHASE_MEDIUM_S + PHASE_HEAVY_S

    with open(LOG_FILE, "w") as f:
        f.write("Experiment 1 — Baseline without rerouting\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Phase 1 (no load):    {PHASE_BASELINE_S}s\n")
        f.write(f"Phase 2 (medium):     {PHASE_MEDIUM_S}s @ {BW_MEDIUM_MBPS} Mbps x2\n")
        f.write(f"Phase 3 (heavy):      {PHASE_HEAVY_S}s  @ {BW_HEAVY_MBPS} Mbps x2\n")
        f.write(f"Total duration:       {total_s}s\n")
        f.write("-" * 50 + "\n\n")

    log("=" * 64)
    log("EXPERIMENT 1 — QoE degradation WITHOUT rerouting")
    log("=" * 64)
    log(f"  Phase 1 — No load:           {PHASE_BASELINE_S}s")
    log(f"  Phase 2 — Medium-high load:  {PHASE_MEDIUM_S}s  "
        f"({BW_MEDIUM_MBPS} Mbps x2 = {BW_MEDIUM_MBPS*2} Mbps)")
    log(f"  Phase 3 — Heavy load:        {PHASE_HEAVY_S}s  "
        f"({BW_HEAVY_MBPS} Mbps x2 = {BW_HEAVY_MBPS*2} Mbps)")
    log(f"  Total: {total_s}s")
    log("")
    log("Prerequisites:")
    log("  [1] ONOS running at 192.168.56.102:8181")
    log("  [2] Mininet running with updated topo_qoe.py (TCLink)")
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
        return

    # ── Automatic mode ──────────────────────────────────────────────────────

    start_iperf_servers()
    time.sleep(1)

    # Phase 1 — no load
    log("")
    write_phase('none')
    log("=" * 64)
    log(f"[PHASE 1] No load — {PHASE_BASELINE_S}s")
    log("  QoE expected: ~1.0 (Excellent)")
    log("  MATLAB will detect phase automatically from /tmp/phase.txt")
    log("=" * 64)
    for remaining in range(PHASE_BASELINE_S, 0, -10):
        log(f"  Phase 1: {remaining}s remaining...")
        time.sleep(10)

    # Phase 2 — medium-high
    log("")
    write_phase('medium')
    log("=" * 64)
    log(f"[PHASE 2] Medium-high congestion — {PHASE_MEDIUM_S}s")
    log(f"  Load: {BW_MEDIUM_MBPS} Mbps x2 = {BW_MEDIUM_MBPS*2} Mbps "
        f"(bottleneck = 10 Mbps)")
    log("  QoE expected: Fair / Poor")
    log("=" * 64)
    start_iperf_clients(BW_MEDIUM_MBPS, PHASE_MEDIUM_S, "medium-high")
    for remaining in range(PHASE_MEDIUM_S, 0, -10):
        log(f"  Phase 2: {remaining}s remaining...")
        time.sleep(10)
    stop_iperf_clients()
    time.sleep(2)   # brief gap between phases so the transition is visible in MATLAB

    # Phase 3 — heavy
    log("")
    write_phase('heavy')
    log("=" * 64)
    log(f"[PHASE 3] Heavy congestion — {PHASE_HEAVY_S}s")
    log(f"  Load: {BW_HEAVY_MBPS} Mbps x2 = {BW_HEAVY_MBPS*2} Mbps "
        f"(fully saturates Path A)")
    log("  QoE expected: Poor / Unacceptable")
    log("=" * 64)
    start_iperf_clients(BW_HEAVY_MBPS, PHASE_HEAVY_S, "heavy")
    for remaining in range(PHASE_HEAVY_S, 0, -10):
        log(f"  Phase 3: {remaining}s remaining...")
        time.sleep(10)
    stop_iperf_clients()

    # Cleanup
    stop_iperf_servers()

    log("")
    log("=" * 64)
    log("[END] Experiment 1 complete.")
    log("")
    log("NEXT STEPS — run in MATLAB command window:")
    log("  save('exp1_Bolero.mat', 'log_t','log_delay','log_jitter',")
    log("       'log_loss','log_D','log_qoe','log_path','congestion_time',")
    log("       'SONG_NAME','L_max','QOE_THRESHOLD','REROUTING_ENABLED');")
    log("  exportgraphics(fig, 'exp1_Bolero.png', 'Resolution', 300);")
    log("")
    log("Then repeat for Master Blaster and Yellow Submarine.")
    log("=" * 64)


if __name__ == "__main__":
    main()


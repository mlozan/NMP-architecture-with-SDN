#!/usr/bin/env python3
"""
experiment2_rerouting.py
=========================
Experiment 2 for TFM — Same as Experiment 1 but WITH rerouting active.

Timeline:
  0s  –  60s : No load          → QoE ~1.0  (baseline)
  60s – 120s : Heavy congestion → QoE drops below 0.6 → MATLAB reroutes to Path B
  120s– 125s : iperf stops      → Path B is free → QoE recovers above threshold
  125s– 180s : Recovery         → QoE stable on Path B

Key point:
  iperf is stopped ~5s after the rerouting window opens so that Path B
  is free when MATLAB switches the flow. This is documented in the thesis
  as a controlled experimental condition.

How to run
----------
1. ONOS running
2. Mininet running with topo_qoe.py (TCLink version)
3. mininet> h1 python3 metrics_h1.py &
4. python3 metrics_vm.py
5. MATLAB: REROUTING_ENABLED = true, press Run, select same song as Exp 1
6. sudo python3 experiment2_rerouting.py
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S   = 60    # no load — QoE stable ~1.0
PHASE_MEDIUM_S     = 30    # medium congestion — QoE starts degrading
PHASE_HEAVY_S      = 25    # heavy congestion — QoE drops below 0.6
                           # total congestion = 55s, iperf stops at ~115s
                           # cooldown = 30s → rerouting fires at ~85-115s
                           # iperf already stopped → Path B is free → QoE recovers
PHASE_RECOVERY_S   = 65    # iperf stopped — MATLAB reroutes — QoE recovers on Path B

BW_MEDIUM_MBPS = 4         # medium: 2x4 = 8 Mbps — some degradation
BW_HEAVY_MBPS  = 9         # heavy:  2x9 = 18 Mbps — QoE drops to 0

IPERF_TARGETS = [
    {"sender": "h3", "receiver": "h5", "receiver_ip": "10.0.0.5"},
    {"sender": "h4", "receiver": "h6", "receiver_ip": "10.0.0.6"},
]

LOG_FILE = "/tmp/experiment2_log.txt"

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_host_pid(host_name):
    result = subprocess.run(
        f"pgrep -f 'mininet:{host_name}' | head -1",
        shell=True, capture_output=True, text=True)
    pid = result.stdout.strip()
    if not pid:
        log(f"  [WARN] PID not found for {host_name}")
    return pid


def run_on_host(host_name, cmd, background=False):
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
    log("Starting iperf3 servers on h5 and h6...")
    for t in IPERF_TARGETS:
        proc = run_on_host(t["receiver"], "iperf3 -s", background=True)
        if proc:
            log(f"  Server on {t['receiver']}")
        time.sleep(0.3)


def start_iperf_clients(bw_mbps, duration_s=9999):
    log(f"Starting iperf3 clients @ {bw_mbps} Mbps x2...")
    for t in IPERF_TARGETS:
        cmd = (f"iperf3 -c {t['receiver_ip']} "
               f"-b {bw_mbps}M "
               f"-t {duration_s} "
               f"-u --dscp 0 -i 10")
        proc = run_on_host(t["sender"], cmd, background=True)
        if proc:
            log(f"  {t['sender']} -> {t['receiver_ip']}")


def stop_iperf_clients():
    log("Stopping iperf3 clients — Path B is now free for rerouting...")
    for t in IPERF_TARGETS:
        pid = get_host_pid(t["sender"])
        if pid:
            subprocess.run(f"mnexec -a {pid} pkill -f 'iperf3 -c'",
                           shell=True, capture_output=True)
    log("  iperf clients stopped.")


def stop_iperf_servers():
    for t in IPERF_TARGETS:
        pid = get_host_pid(t["receiver"])
        if pid:
            subprocess.run(f"mnexec -a {pid} pkill -f 'iperf3 -s'",
                           shell=True, capture_output=True)
    log("  iperf servers stopped.")


def print_manual_commands():
    bw = IPERF_BW_MBPS
    print("\n" + "=" * 62)
    print("  MANUAL MODE — paste into the Mininet CLI")
    print("=" * 62)
    print()
    print("# ── SETUP ───────────────────────────────────────────────────")
    print("mininet> h5 iperf3 -s &")
    print("mininet> h6 iperf3 -s &")
    print()
    print(f"# ── PHASE 1: baseline ({PHASE_BASELINE_S}s) ─────────────────────────────")
    print(f"#   Wait {PHASE_BASELINE_S}s — QoE ~1.0")
    print()
    print(f"# ── PHASE 2: heavy congestion ({PHASE_HEAVY_S}s) ────────────────────────")
    print(f"#   {bw} Mbps x2 = {bw*2} Mbps — saturates Path A")
    print(f"#   MATLAB will detect QoE < 0.6 and reroute automatically")
    print(f"mininet> h3 iperf3 -c 10.0.0.5 -b {bw}M -t 9999 -u --dscp 0 -i 10 &")
    print(f"mininet> h4 iperf3 -c 10.0.0.6 -b {bw}M -t 9999 -u --dscp 0 -i 10 &")
    print()
    print(f"# ── PHASE 3: stop iperf when MATLAB reroutes ────────────────")
    print(f"#   Watch MATLAB terminal — when you see:")
    print(f"#   '>>> Path B active. Flows flushed — ONOS recomputing...'")
    print(f"#   immediately run:")
    print("mininet> h3 kill %1 2>/dev/null")
    print("mininet> h4 kill %1 2>/dev/null")
    print(f"#   QoE should recover above 0.6 on Path B")
    print()
    print("=" * 62 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    total_s = PHASE_BASELINE_S + PHASE_MEDIUM_S + PHASE_HEAVY_S + PHASE_RECOVERY_S

    with open(LOG_FILE, "w") as f:
        f.write("Experiment 2 — WITH rerouting\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Phase 1 (baseline):   {PHASE_BASELINE_S}s\n")
        f.write(f"Phase 2 (medium):     {PHASE_MEDIUM_S}s @ {BW_MEDIUM_MBPS} Mbps x2\n")
        f.write(f"Phase 3 (heavy):      {PHASE_HEAVY_S}s @ {BW_HEAVY_MBPS} Mbps x2\n")
        f.write(f"Phase 4 (recovery):   {PHASE_RECOVERY_S}s (iperf stopped)\n")
        f.write(f"Total: {total_s}s\n")
        f.write("-" * 50 + "\n\n")

    log("=" * 62)
    log("EXPERIMENT 2 — QoE recovery WITH rerouting")
    log("=" * 62)
    log(f"  Phase 1 — Baseline:    {PHASE_BASELINE_S}s  (no load)")
    log(f"  Phase 2 — Medium:      {PHASE_MEDIUM_S}s  ({BW_MEDIUM_MBPS} Mbps x2 = {BW_MEDIUM_MBPS*2} Mbps)")
    log(f"  Phase 3 — Heavy:       {PHASE_HEAVY_S}s  ({BW_HEAVY_MBPS} Mbps x2 = {BW_HEAVY_MBPS*2} Mbps)")
    log(f"  Phase 4 — Recovery:    {PHASE_RECOVERY_S}s  (iperf stopped, QoE recovers)")
    log(f"  Total: {total_s}s")
    log("")
    log("Prerequisites:")
    log("  [1] ONOS running at 192.168.56.102:8181")
    log("  [2] Mininet running with topo_qoe.py (TCLink)")
    log("  [3] metrics_h1.py running on h1")
    log("  [4] metrics_vm.py running on VM")
    log("  [5] MATLAB running with REROUTING_ENABLED = true")
    log("")

    print("Choose mode:")
    print("  1 = Automatic (uses mnexec — run as sudo)")
    print("  2 = Manual   (prints commands to paste in Mininet CLI)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        print_manual_commands()
        return

    # ── Automatic mode ──────────────────────────────────────────────────────

    start_iperf_servers()
    time.sleep(1)

    # Phase 1 — baseline
    log("")
    log("=" * 62)
    log(f"[PHASE 1] Baseline — {PHASE_BASELINE_S}s — no load")
    log("  QoE expected: ~1.0 (Excellent)")
    log("=" * 62)
    for remaining in range(PHASE_BASELINE_S, 0, -10):
        log(f"  Baseline: {remaining}s remaining...")
        time.sleep(10)

    # Phase 2 — medium congestion
    log("")
    log("=" * 62)
    log(f"[PHASE 2] Medium congestion — {PHASE_MEDIUM_S}s")
    log(f"  Load: {BW_MEDIUM_MBPS} Mbps x2 = {BW_MEDIUM_MBPS*2} Mbps on Path A")
    log("  QoE starts degrading")
    log("=" * 62)
    start_iperf_clients(BW_MEDIUM_MBPS, 9999)
    for remaining in range(PHASE_MEDIUM_S, 0, -5):
        log(f"  Medium: {remaining}s remaining...")
        time.sleep(5)

    # Phase 3 — heavy congestion
    log("")
    log("=" * 62)
    log(f"[PHASE 3] Heavy congestion — {PHASE_HEAVY_S}s")
    log(f"  Load: {BW_HEAVY_MBPS} Mbps x2 = {BW_HEAVY_MBPS*2} Mbps on Path A")
    log("  QoE will drop below 0.6 — MATLAB will reroute automatically")
    log("=" * 62)
    stop_iperf_clients()
    time.sleep(1)
    start_iperf_clients(BW_HEAVY_MBPS, 9999)
    for remaining in range(PHASE_HEAVY_S, 0, -5):
        log(f"  Heavy: {remaining}s remaining...")
        time.sleep(5)

    # Stop iperf — Path B must be free for recovery
    log("")
    log("=" * 62)
    log("[PHASE 4] iperf stopped — Path B is free")
    log("  MATLAB will detect QoE < 0.6 and reroute to Path B")
    log("  With Path B free, QoE should recover above 0.6")
    log("=" * 62)
    stop_iperf_clients()

    for remaining in range(PHASE_RECOVERY_S, 0, -10):
        log(f"  Recovery: {remaining}s remaining...")
        time.sleep(10)

    stop_iperf_servers()

    log("")
    log("=" * 62)
    log("[END] Experiment 2 complete.")
    log("")
    log("NEXT STEPS — run in MATLAB command window:")
    log("  song_safe = strrep(SONG_NAME, ' ', '_');")
    log("  xlim(ax1,[0,max(log_t)]); xlim(ax2,[0,max(log_t)]); xlim(ax3,[0,max(log_t)]);")
    log("  exportgraphics(fig, sprintf('exp2_%s.png', song_safe), 'Resolution', 300);")
    log("  T = table(log_t', log_delay', log_jitter', log_loss'*100, log_D', log_qoe',")
    log("      'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});")
    log("  writetable(T, sprintf('exp2_%s.xlsx', song_safe));")
    log("=" * 62)


if __name__ == "__main__":
    main()

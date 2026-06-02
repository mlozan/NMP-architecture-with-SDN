#!/usr/bin/env python3
"""
experiment1_no_rerouting.py
============================
Experiment 1 for TFM — Baseline: QoE degradation WITHOUT rerouting.

Uses tc netem to inject delay and packet loss directly on the s1->s3 link
(Path A bottleneck). This guarantees QoE degradation regardless of OVS
bandwidth enforcement.

Timeline:
  0s  –  60s : No impairment      → QoE ~1.0  (Excellent)
  60s – 120s : Medium impairment  → QoE ~0.5-0.7  (Fair/Poor)
  120s– 180s : Heavy impairment   → QoE ~0.0  (Unacceptable)

Network conditions applied on s1-eth2 (s1 -> s3, Path A):
  Medium: delay 20ms jitter 5ms  loss 2%
  Heavy:  delay 50ms jitter 10ms loss 5%

How to run
----------
1. ONOS running
2. Mininet running with topo_qoe.py
3. mininet> h1 python3 metrics_h1.py &
4. python3 metrics_vm.py
5. MATLAB: REROUTING_ENABLED = false, press Run, select song
6. sudo python3 experiment1_no_rerouting.py
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S = 60
PHASE_MEDIUM_S   = 60
PHASE_HEAVY_S    = 60

# Network impairment applied on s1-eth2 (s1 → s3, Path A)
# Medium: noticeable degradation, QoE drops to Fair/Poor
MEDIUM_DELAY_MS  = 20
MEDIUM_JITTER_MS = 5
MEDIUM_LOSS_PCT  = 2

# Heavy: severe degradation, QoE drops to Unacceptable
HEAVY_DELAY_MS   = 50
HEAVY_JITTER_MS  = 10
HEAVY_LOSS_PCT   = 5

# Interface on s1 facing s3 (Path A)
# Verify with: mininet> s1 tc qdisc show
S1_IFACE = 's1-eth2'

LOG_FILE = "/tmp/experiment1_log.txt"

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_switch_pid(switch_name):
    result = subprocess.run(
        f"pgrep -f 'mininet:{switch_name}' | head -1",
        shell=True, capture_output=True, text=True)
    pid = result.stdout.strip()
    if not pid:
        log(f"  [WARN] PID not found for {switch_name}")
    return pid


def apply_netem(delay_ms, jitter_ms, loss_pct):
    """Apply tc netem impairment on s1-eth2 (Path A bottleneck)."""
    pid = get_switch_pid('s1')
    if not pid:
        log("  [ERROR] Could not find s1 — is Mininet running?")
        return False

    # Delete existing qdisc first (ignore error if none exists)
    subprocess.run(
        f"mnexec -a {pid} tc qdisc del dev {S1_IFACE} root 2>/dev/null",
        shell=True)

    cmd = (f"mnexec -a {pid} tc qdisc add dev {S1_IFACE} root netem "
           f"delay {delay_ms}ms {jitter_ms}ms "
           f"loss {loss_pct}%")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        log(f"  netem applied: delay={delay_ms}ms jitter={jitter_ms}ms loss={loss_pct}%")
        return True
    else:
        log(f"  [ERROR] netem failed: {result.stderr.strip()}")
        return False


def clear_netem():
    """Remove tc netem from s1-eth2."""
    pid = get_switch_pid('s1')
    if not pid:
        return
    cmd = f"mnexec -a {pid} tc qdisc del dev {S1_IFACE} root 2>/dev/null"
    subprocess.run(cmd, shell=True)
    log(f"  netem cleared on {S1_IFACE}")


def print_manual_commands():
    print("\n" + "=" * 62)
    print("  MANUAL MODE — paste into the Mininet CLI")
    print("=" * 62)
    print()
    print(f"# ── PHASE 1: baseline ({PHASE_BASELINE_S}s) ─────────────────────────────")
    print(f"#   No impairment — QoE ~1.0")
    print()
    print(f"# ── PHASE 2: medium impairment ({PHASE_MEDIUM_S}s) ───────────────────────")
    print(f"mininet> s1 tc qdisc add dev s1-eth2 root netem delay {MEDIUM_DELAY_MS}ms {MEDIUM_JITTER_MS}ms loss {MEDIUM_LOSS_PCT}%")
    print(f"#   Wait {PHASE_MEDIUM_S}s — QoE should drop to Fair/Poor")
    print()
    print(f"# ── PHASE 3: heavy impairment ({PHASE_HEAVY_S}s) ─────────────────────────")
    print(f"mininet> s1 tc qdisc change dev s1-eth2 root netem delay {HEAVY_DELAY_MS}ms {HEAVY_JITTER_MS}ms loss {HEAVY_LOSS_PCT}%")
    print(f"#   Wait {PHASE_HEAVY_S}s — QoE should drop to Unacceptable")
    print()
    print("# ── CLEANUP ─────────────────────────────────────────────────")
    print("mininet> s1 tc qdisc del dev s1-eth2 root")
    print()
    print("=" * 62 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    total_s = PHASE_BASELINE_S + PHASE_MEDIUM_S + PHASE_HEAVY_S

    with open(LOG_FILE, "w") as f:
        f.write("Experiment 1 — Baseline without rerouting (netem)\n")
        f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Phase 1 (baseline): {PHASE_BASELINE_S}s — no impairment\n")
        f.write(f"Phase 2 (medium):   {PHASE_MEDIUM_S}s — {MEDIUM_DELAY_MS}ms delay {MEDIUM_LOSS_PCT}% loss\n")
        f.write(f"Phase 3 (heavy):    {PHASE_HEAVY_S}s — {HEAVY_DELAY_MS}ms delay {HEAVY_LOSS_PCT}% loss\n")
        f.write(f"Total: {total_s}s\n")
        f.write("-" * 50 + "\n\n")

    log("=" * 62)
    log("EXPERIMENT 1 — QoE degradation WITHOUT rerouting")
    log("=" * 62)
    log(f"  Phase 1 — Baseline: {PHASE_BASELINE_S}s  (no impairment)")
    log(f"  Phase 2 — Medium:   {PHASE_MEDIUM_S}s  "
        f"(delay={MEDIUM_DELAY_MS}ms jitter={MEDIUM_JITTER_MS}ms loss={MEDIUM_LOSS_PCT}%)")
    log(f"  Phase 3 — Heavy:    {PHASE_HEAVY_S}s  "
        f"(delay={HEAVY_DELAY_MS}ms jitter={HEAVY_JITTER_MS}ms loss={HEAVY_LOSS_PCT}%)")
    log(f"  Total: {total_s}s")
    log(f"  Interface: {S1_IFACE}")
    log("")
    log("Prerequisites:")
    log("  [1] ONOS running at 192.168.56.102:8181")
    log("  [2] Mininet running with topo_qoe.py")
    log("  [3] metrics_h1.py running on h1")
    log("  [4] metrics_vm.py running on VM")
    log("  [5] MATLAB running with REROUTING_ENABLED = false")
    log("")

    print("Choose mode:")
    print("  1 = Automatic (uses mnexec — run as sudo)")
    print("  2 = Manual   (prints commands to paste in Mininet CLI)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        print_manual_commands()
        return

    # ── Automatic mode ──────────────────────────────────────────────────────

    # Make sure netem is clean at start
    clear_netem()

    # Phase 1 — baseline
    log("")
    log("=" * 62)
    log(f"[PHASE 1] Baseline — {PHASE_BASELINE_S}s — no impairment")
    log("  QoE expected: ~1.0 (Excellent)")
    log("=" * 62)
    for remaining in range(PHASE_BASELINE_S, 0, -10):
        log(f"  Baseline: {remaining}s remaining...")
        time.sleep(10)

    # Phase 2 — medium impairment
    log("")
    log("=" * 62)
    log(f"[PHASE 2] Medium impairment — {PHASE_MEDIUM_S}s")
    log(f"  delay={MEDIUM_DELAY_MS}ms jitter={MEDIUM_JITTER_MS}ms loss={MEDIUM_LOSS_PCT}%")
    log("  QoE expected: Fair / Poor")
    log("=" * 62)
    apply_netem(MEDIUM_DELAY_MS, MEDIUM_JITTER_MS, MEDIUM_LOSS_PCT)
    for remaining in range(PHASE_MEDIUM_S, 0, -10):
        log(f"  Medium: {remaining}s remaining...")
        time.sleep(10)

    # Phase 3 — heavy impairment
    log("")
    log("=" * 62)
    log(f"[PHASE 3] Heavy impairment — {PHASE_HEAVY_S}s")
    log(f"  delay={HEAVY_DELAY_MS}ms jitter={HEAVY_JITTER_MS}ms loss={HEAVY_LOSS_PCT}%")
    log("  QoE expected: Unacceptable")
    log("=" * 62)
    apply_netem(HEAVY_DELAY_MS, HEAVY_JITTER_MS, HEAVY_LOSS_PCT)
    for remaining in range(PHASE_HEAVY_S, 0, -10):
        log(f"  Heavy: {remaining}s remaining...")
        time.sleep(10)

    # Cleanup
    clear_netem()

    log("")
    log("=" * 62)
    log("[END] Experiment 1 complete.")
    log("")
    log("NEXT STEPS — run in MATLAB command window:")
    log("  song_safe = strrep(SONG_NAME, ' ', '_');")
    log("  xlim(ax1,[0,max(log_t)]); xlim(ax2,[0,max(log_t)]); xlim(ax3,[0,max(log_t)]);")
    log("  exportgraphics(fig, sprintf('exp1_%s.png', song_safe), 'Resolution', 300);")
    log("  T = table(log_t', log_delay', log_jitter', log_loss'*100, log_D', log_qoe',")
    log("      'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});")
    log("  writetable(T, sprintf('exp1_%s.xlsx', song_safe));")
    log("=" * 62)


if __name__ == "__main__":
    main()

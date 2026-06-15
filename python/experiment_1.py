#!/usr/bin/env python3
"""
experiment_1.py
============================
Experiment 1 — Baseline: QoE degradation WITHOUT rerouting.

Same structure as Experiment 2 but REROUTING_ENABLED = false in MATLAB.
Uses tc netem on s1-eth2 (Path A) to inject delay and loss.

Timeline:
  0s  –  30s : Baseline          → QoE ~1.0
  30s –  90s : Medium impairment → QoE degrades (Fair/Poor)
  90s – 120s : Heavy impairment  → QoE drops to Unacceptable
  120s– 150s : Full recovery     → netem cleared → QoE ~1.0

Path A impairment applied on s1-eth2 (s1 → s3)
No rerouting — QoE stays degraded until netem is cleared
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S = 30
PHASE_MEDIUM_S   = 60
PHASE_HEAVY_S    = 30
PHASE_CLEAN_S    = 30

# Path A impairment — same values as Experiment 2 for comparability
MEDIUM_DELAY_MS  = 5
MEDIUM_JITTER_MS = 1
MEDIUM_LOSS_PCT  = 0

HEAVY_DELAY_MS   = 15
HEAVY_JITTER_MS  = 3
HEAVY_LOSS_PCT   = 5

S1_IFACE_A = 's1-eth2'   # s1 -> s3 (Path A)
LOG_FILE   = '/tmp/experiment1_log.txt'

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def get_pid():
    r = subprocess.run(
        "pgrep -f 'mininet:s1' | grep -v pgrep | head -1",
        shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def tc(pid, cmd):
    """Run a tc command inside s1 namespace."""
    full = f'mnexec -a {pid} {cmd}'
    r = subprocess.run(full, shell=True, capture_output=True, text=True)
    return r.returncode, r.stderr.strip()


def apply_netem(pid, iface, delay_ms, jitter_ms, loss_pct):
    tc(pid, f'tc qdisc del dev {iface} root 2>/dev/null')
    ret, err = tc(pid, f'tc qdisc add dev {iface} root netem '
                       f'delay {delay_ms}ms {jitter_ms}ms loss {loss_pct}%')
    if ret == 0:
        r = subprocess.run(f'mnexec -a {pid} tc qdisc show dev {iface}',
                           shell=True, capture_output=True, text=True)
        log(f'  {iface}: {r.stdout.strip()}')
    else:
        log(f'  [ERROR] {iface}: {err}')


def clear_netem(pid, iface):
    tc(pid, f'tc qdisc del dev {iface} root 2>/dev/null')
    log(f'  {iface}: cleared')


def wait(seconds, label):
    for remaining in range(seconds, 0, -10):
        log(f'  {label}: {remaining}s remaining...')
        time.sleep(min(10, remaining))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    total = PHASE_BASELINE_S + PHASE_MEDIUM_S + PHASE_HEAVY_S + PHASE_CLEAN_S

    with open(LOG_FILE, 'w') as f:
        f.write('Experiment 1 — WITHOUT rerouting\n')
        f.write(f'Started: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Total: {total}s\n\n')

    log('=' * 62)
    log('EXPERIMENT 1 — WITHOUT rerouting (baseline)')
    log('=' * 62)
    log(f'  Phase 1 Baseline:  {PHASE_BASELINE_S}s — no impairment')
    log(f'  Phase 2 Medium:    {PHASE_MEDIUM_S}s  — {MEDIUM_DELAY_MS}ms {MEDIUM_LOSS_PCT}%')
    log(f'  Phase 3 Heavy:     {PHASE_HEAVY_S}s  — {HEAVY_DELAY_MS}ms {HEAVY_LOSS_PCT}%')
    log(f'  Phase 4 Recovery:  {PHASE_CLEAN_S}s  — netem cleared')
    log(f'  Total: {total}s')
    log('')
    log('Prerequisites:')
    log('  [1] ONOS running at 192.168.56.102:8181')
    log('  [2] Mininet running with topo_qoe.py')
    log('  [3] metrics_h1.py running on h1')
    log('  [4] metrics_vm.py running on VM')
    log('  [5] MATLAB running with REROUTING_ENABLED = false')
    log('')

    pid = get_pid()
    if not pid:
        log('[ERROR] s1 PID not found — is Mininet running?')
        return
    log(f'  s1 PID: {pid}')

    # Clean start
    clear_netem(pid, S1_IFACE_A)

    # ── Phase 1: Baseline ──────────────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 1] Baseline — {PHASE_BASELINE_S}s — no impairment')
    log('  QoE ~1.0 (Excellent)')
    log('=' * 62)
    wait(PHASE_BASELINE_S, 'Baseline')

    # ── Phase 2: Medium impairment ─────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 2] Medium impairment — {PHASE_MEDIUM_S}s')
    log(f'  Path A: {MEDIUM_DELAY_MS}ms {MEDIUM_LOSS_PCT}%')
    log('  QoE expected: Fair / Poor')
    log('  No rerouting — QoE stays degraded')
    log('=' * 62)
    apply_netem(pid, S1_IFACE_A, MEDIUM_DELAY_MS, MEDIUM_JITTER_MS, MEDIUM_LOSS_PCT)
    wait(PHASE_MEDIUM_S, 'Medium')

    # ── Phase 3: Heavy impairment ──────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 3] Heavy impairment — {PHASE_HEAVY_S}s')
    log(f'  Path A: {HEAVY_DELAY_MS}ms {HEAVY_LOSS_PCT}%')
    log('  QoE expected: Unacceptable')
    log('  No rerouting — QoE stays at 0')
    log('=' * 62)
    apply_netem(pid, S1_IFACE_A, HEAVY_DELAY_MS, HEAVY_JITTER_MS, HEAVY_LOSS_PCT)
    wait(PHASE_HEAVY_S, 'Heavy')

    # ── Phase 4: Full recovery ─────────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 4] Full recovery — {PHASE_CLEAN_S}s — netem cleared')
    log('  QoE returns to ~1.0 (Excellent)')
    log('=' * 62)
    clear_netem(pid, S1_IFACE_A)
    wait(PHASE_CLEAN_S, 'Recovery')

    log('')
    log('=' * 62)
    log('[END] Experiment 1 complete.')
    log('')
    log('NEXT STEPS — run in MATLAB command window:')
    log("  song_safe = strrep(SONG_NAME, ' ', '_');")
    log('  xlim(ax1,[0,max(log_t)]); xlim(ax2,[0,max(log_t)]); xlim(ax3,[0,max(log_t)]);')
    log("  exportgraphics(fig, sprintf('exp1_%s.png', song_safe), 'Resolution', 300);")
    log("  T = table(log_t', log_delay', log_jitter', log_loss'*100, log_D', log_qoe',")
    log("      'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});")
    log("  writetable(T, sprintf('exp1_%s.xlsx', song_safe));")
    log('=' * 62)


if __name__ == '__main__':
    main()

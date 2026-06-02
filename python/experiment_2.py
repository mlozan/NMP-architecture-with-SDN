#!/usr/bin/env python3
"""
experiment2_rerouting.py
=========================
Experiment 2 — WITH rerouting active.

Timeline:
  0s  –  30s : Baseline           → QoE ~1.0
  30s –  90s : Medium A + Light B → QoE degrades on Path A
  90s – 120s : Heavy A + Light B  → QoE < 0.6 → MATLAB reroutes to Path B
  120s– 180s : Clear A + Light B  → QoE recovers on Path B
  180s– 210s : Full recovery      → Both paths clean → QoE ~1.0

Path A impairment applied on s1-eth2 (s1 → s3)
Path B impairment applied on s1-eth3 (s1 → s2) — very light, just visible
"""

import subprocess
import time

# ── Configuration ──────────────────────────────────────────────────────────────
PHASE_BASELINE_S = 30
PHASE_MEDIUM_S   = 60
PHASE_HEAVY_S    = 30
PHASE_RECOVERY_S = 30   # same as Experiment 1 clean phase

# Path A impairment
MEDIUM_DELAY_MS  = 5
MEDIUM_JITTER_MS = 1
MEDIUM_LOSS_PCT  = 0

HEAVY_DELAY_MS   = 15
HEAVY_JITTER_MS  = 3
HEAVY_LOSS_PCT   = 5

# Path B impairment — very light, always present from phase 2 onwards
PATHB_DELAY_MS   = 3
PATHB_JITTER_MS  = 1
PATHB_LOSS_PCT   = 0

S1_IFACE_A = 's1-eth2'
S1_IFACE_B = 's1-eth3'
LOG_FILE   = '/tmp/experiment2_log.txt'

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
        # Verify
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
    total = PHASE_BASELINE_S + PHASE_MEDIUM_S + PHASE_HEAVY_S + \
            PHASE_RECOVERY_S

    with open(LOG_FILE, 'w') as f:
        f.write(f'Experiment 2 — WITH rerouting\n')
        f.write(f'Started: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Total: {total}s\n\n')

    log('=' * 62)
    log('EXPERIMENT 2 — WITH rerouting')
    log('=' * 62)
    log(f'  Phase 1 Baseline:   {PHASE_BASELINE_S}s — no impairment')
    log(f'  Phase 2 Medium:     {PHASE_MEDIUM_S}s  — A:{MEDIUM_DELAY_MS}ms {MEDIUM_LOSS_PCT}%  B:{PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}%')
    log(f'  Phase 3 Heavy:      {PHASE_HEAVY_S}s  — A:{HEAVY_DELAY_MS}ms {HEAVY_LOSS_PCT}%  B:{PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}%')
    log(f'  Phase 4 Recovery:   {PHASE_RECOVERY_S}s — A:clean  B:{PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}% — MATLAB reroutes — QoE recovers')
    log(f'  Total: {total}s')
    log('')

    pid = get_pid()
    if not pid:
        log('[ERROR] s1 PID not found — is Mininet running?')
        return
    log(f'  s1 PID: {pid}')

    # Clean start
    clear_netem(pid, S1_IFACE_A)
    clear_netem(pid, S1_IFACE_B)

    # ── Phase 1: Baseline ──────────────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 1] Baseline — {PHASE_BASELINE_S}s — no impairment')
    log('  QoE ~1.0 (Excellent)')
    log('=' * 62)
    wait(PHASE_BASELINE_S, 'Baseline')

    # ── Phase 2: Medium A + Light B ────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 2] Medium Path A + Light Path B — {PHASE_MEDIUM_S}s')
    log(f'  Path A: {MEDIUM_DELAY_MS}ms {MEDIUM_LOSS_PCT}%  |  Path B: {PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}%')
    log('  QoE expected: Fair / Poor')
    log('=' * 62)
    apply_netem(pid, S1_IFACE_A, MEDIUM_DELAY_MS, MEDIUM_JITTER_MS, MEDIUM_LOSS_PCT)
    apply_netem(pid, S1_IFACE_B, PATHB_DELAY_MS,  PATHB_JITTER_MS,  PATHB_LOSS_PCT)
    wait(PHASE_MEDIUM_S, 'Medium')

    # ── Phase 3: Heavy A + Light B ─────────────────────────────────────────
    log('')
    log('=' * 62)
    log(f'[PHASE 3] Heavy Path A + Light Path B — {PHASE_HEAVY_S}s')
    log(f'  Path A: {HEAVY_DELAY_MS}ms {HEAVY_LOSS_PCT}%  |  Path B: {PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}%')
    log('  QoE drops < 0.6 — MATLAB reroutes to Path B')
    log('=' * 62)
    apply_netem(pid, S1_IFACE_A, HEAVY_DELAY_MS, HEAVY_JITTER_MS, HEAVY_LOSS_PCT)
    # Path B stays the same — no need to re-apply
    wait(PHASE_HEAVY_S, 'Heavy')

    # ── Phase 4: Clear A + Light B (same duration as Exp1 clean phase) ──────
    log('')
    log('=' * 62)
    log(f'[PHASE 4] Path A cleared + Light Path B — {PHASE_RECOVERY_S}s')
    log(f'  Path A: clean  |  Path B: {PATHB_DELAY_MS}ms {PATHB_LOSS_PCT}%')
    log('  MATLAB reroutes to Path B — QoE recovers')
    log('  Same duration as Experiment 1 Phase 4 for direct comparison')
    log('=' * 62)
    clear_netem(pid, S1_IFACE_A)
    clear_netem(pid, S1_IFACE_B)
    wait(PHASE_RECOVERY_S, 'Recovery')

    log('')
    log('=' * 62)
    log('[END] Experiment 2 complete.')
    log('')
    log('NEXT STEPS — run in MATLAB command window:')
    log("  song_safe = strrep(SONG_NAME, ' ', '_');")
    log('  xlim(ax1,[0,max(log_t)]); xlim(ax2,[0,max(log_t)]); xlim(ax3,[0,max(log_t)]);')
    log("  exportgraphics(fig, sprintf('exp2_%s.png', song_safe), 'Resolution', 300);")
    log("  T = table(log_t', log_delay', log_jitter', log_loss'*100, log_D', log_qoe',")
    log("      'VariableNames', {'Time_s','Delay_ms','Jitter_ms','Loss_pct','D_ms','QoE'});")
    log("  writetable(T, sprintf('exp2_%s.xlsx', song_safe));")
    log('=' * 62)


if __name__ == '__main__':
    main()

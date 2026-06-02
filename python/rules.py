#!/usr/bin/env python3
"""
install_flow_rules.py
======================
Installs static DSCP-based flow rules on ONOS before running Experiment 2.

Flow rule logic on s1:
  - DSCP=0  (iperf background) → always Path A (port 2 → s3)
  - DSCP=46 (QoE flow)         → Path A by default (port 2 → s3)
                                  Path B on rerouting (port 3 → s2) ← changed by MATLAB

Same rules are mirrored on s4 for the return path:
  - s4 port facing s3 → h2
  - s4 port facing s5 → h2 (for Path B return)

Run this ONCE after Mininet is up and before starting qoe_monitor.m:
    python3 install_flow_rules.py

Then run qoe_monitor.m normally. When rerouting triggers, MATLAB will
call update_qoe_path.py to switch only the QoE flow to Path B.
"""

import requests
import json
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
ONOS_BASE  = 'http://192.168.56.102:8181/onos/v1'
ONOS_USER  = 'onos'
ONOS_PASS  = 'rocks'

# Switch IDs
S1_ID = 'of:0000000000000001'
S4_ID = 'of:0000000000000004'

# s1 ports
S1_PORT_H1    = 1   # h1 connected to s1
S1_PORT_PATH_A = 2  # s1 → s3 (Path A)
S1_PORT_PATH_B = 3  # s1 → s2 (Path B)

# s4 ports (check with: curl -u onos:rocks http://192.168.56.102:8181/onos/v1/devices/of:0000000000000004/ports)
S4_PORT_PATH_A = 2  # s4 ← s3 (Path A return)
S4_PORT_PATH_B = 3  # s4 ← s5 (Path B return)
S4_PORT_H2     = 1  # h2 connected to s4

DSCP_QOE  = 46   # Expedited Forwarding — QoE flow
DSCP_IPERF = 0   # Best effort — background iperf

PRIORITY_DSCP   = 40000   # higher than default ONOS rules
PRIORITY_DEFAULT = 10000

# ── Helpers ────────────────────────────────────────────────────────────────────

def post_flow(device_id, flow):
    # ONOS 2.7 expects each flow posted individually without the 'flows' wrapper
    url = f'{ONOS_BASE}/flows/{device_id}'
    r = requests.post(url,
                      auth=(ONOS_USER, ONOS_PASS),
                      headers={'Content-Type': 'application/json'},
                      data=json.dumps(flow))
    if r.status_code in (200, 201):
        print(f'  [OK] Flow installed on {device_id}')
    else:
        print(f'  [ERROR] {r.status_code}: {r.text}')


def delete_all_flows(device_id):
    url = f'{ONOS_BASE}/flows/{device_id}'
    r = requests.delete(url, auth=(ONOS_USER, ONOS_PASS))
    print(f'  Cleared flows on {device_id}: {r.status_code}')


def make_flow(device_id, priority, in_port, dscp, out_port, permanent=True):
    """Build an ONOS flow rule matching in_port + DSCP, forwarding to out_port."""
    return {
        'priority': int(priority),
        'isPermanent': permanent,
        'deviceId': str(device_id),
        'tableId': 0,
        'treatment': {
            'instructions': [{'type': 'OUTPUT', 'port': str(out_port)}],
            'deferred': []
        },
        'selector': {
            'criteria': [
                {'type': 'ETH_TYPE', 'ethType': '0x0800'},
                {'type': 'IN_PORT',  'port': str(in_port)},
                {'type': 'IP_DSCP',  'ipDscp': int(dscp)}
            ]
        }
    }


def make_flow_out_only(device_id, priority, in_port, out_port, permanent=True):
    """Build a flow rule matching only in_port (no DSCP), forwarding to out_port."""
    return {
        'priority': int(priority),
        'isPermanent': permanent,
        'deviceId': str(device_id),
        'tableId': 0,
        'treatment': {
            'instructions': [{'type': 'OUTPUT', 'port': str(out_port)}],
            'deferred': []
        },
        'selector': {
            'criteria': [
                {'type': 'IN_PORT', 'port': str(in_port)}
            ]
        }
    }

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('=' * 55)
    print('Installing DSCP-based flow rules on ONOS')
    print('=' * 55)
    print()

    # Clear existing flows on s1 and s4
    print('Clearing existing flows...')
    delete_all_flows(S1_ID)
    delete_all_flows(S4_ID)
    print()

    # ── s1: forward rules (h1 side → network) ──────────────────────────────

    print('Installing s1 forward rules...')

    # DSCP=46 (QoE) from h1 → Path A (default, will be changed on rerouting)
    post_flow(S1_ID, make_flow(
        S1_ID, PRIORITY_DSCP,
        in_port=S1_PORT_H1, dscp=DSCP_QOE,
        out_port=S1_PORT_PATH_A))

    # DSCP=0 (iperf) from h1 side → always Path A (permanent, never changes)
    post_flow(S1_ID, make_flow(
        S1_ID, PRIORITY_DSCP,
        in_port=S1_PORT_H1, dscp=DSCP_IPERF,
        out_port=S1_PORT_PATH_A))

    # ── s1: return rules (network → h1) ────────────────────────────────────

    print('Installing s1 return rules...')

    # Return from Path A (s3 → s1 → h1)
    post_flow(S1_ID, make_flow_out_only(
        S1_ID, PRIORITY_DEFAULT,
        in_port=S1_PORT_PATH_A,
        out_port=S1_PORT_H1))

    # Return from Path B (s2 → s1 → h1)
    post_flow(S1_ID, make_flow_out_only(
        S1_ID, PRIORITY_DEFAULT,
        in_port=S1_PORT_PATH_B,
        out_port=S1_PORT_H1))

    # ── s4: forward rules (network → h2) ───────────────────────────────────

    print('Installing s4 rules...')

    # Arriving from Path A → h2
    post_flow(S4_ID, make_flow_out_only(
        S4_ID, PRIORITY_DEFAULT,
        in_port=S4_PORT_PATH_A,
        out_port=S4_PORT_H2))

    # Arriving from Path B → h2
    post_flow(S4_ID, make_flow_out_only(
        S4_ID, PRIORITY_DEFAULT,
        in_port=S4_PORT_PATH_B,
        out_port=S4_PORT_H2))

    print()
    print('=' * 55)
    print('Done. Flow rules installed.')
    print()
    print('Default routing:')
    print(f'  QoE  (DSCP=46): h1 → s1 port {S1_PORT_PATH_A} → Path A → h2')
    print(f'  iperf (DSCP=0): h1 → s1 port {S1_PORT_PATH_A} → Path A → h2')
    print()
    print('On rerouting, MATLAB will call:')
    print('  update_qoe_path.py --path B   (switches QoE to port 3 → Path B)')
    print('  update_qoe_path.py --path A   (restores QoE to port 2 → Path A)')
    print()
    print('The iperf flow (DSCP=0) ALWAYS stays on Path A.')
    print('=' * 55)


if __name__ == '__main__':
    main()

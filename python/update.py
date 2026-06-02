#!/usr/bin/env python3
"""
update_qoe_path.py
===================
Called by MATLAB (via system()) to switch the QoE flow between Path A and Path B.
Only modifies the DSCP=46 rule on s1 — the iperf DSCP=0 rule is never touched.

Usage:
    python3 update_qoe_path.py --path B   # switch QoE to Path B (s1 port 3)
    python3 update_qoe_path.py --path A   # restore QoE to Path A (s1 port 2)
"""

import requests
import json
import sys

ONOS_BASE = 'http://192.168.56.102:8181/onos/v1'
ONOS_USER = 'onos'
ONOS_PASS = 'rocks'

S1_ID          = 'of:0000000000000001'
S1_PORT_H1     = 1
S1_PORT_PATH_A = 2
S1_PORT_PATH_B = 3
DSCP_QOE       = 46
PRIORITY_DSCP  = 40000


def delete_qoe_flow():
    """Delete the existing QoE flow rule on s1."""
    # Get all flows on s1
    url = f'{ONOS_BASE}/flows/{S1_ID}'
    r = requests.get(url, auth=(ONOS_USER, ONOS_PASS))
    if r.status_code != 200:
        print(f'[ERROR] Could not get flows: {r.status_code}')
        return

    flows = r.json().get('flows', [])
    for flow in flows:
        criteria = flow.get('selector', {}).get('criteria', [])
        has_qoe_dscp  = any(c.get('type') == 'IP_DSCP' and c.get('ipDscp') == DSCP_QOE
                            for c in criteria)
        has_in_port_h1 = any(c.get('type') == 'IN_PORT' and str(c.get('port')) == str(S1_PORT_H1)
                              for c in criteria)
        if has_qoe_dscp and has_in_port_h1:
            flow_id = flow.get('id')
            del_url = f'{ONOS_BASE}/flows/{S1_ID}/{flow_id}'
            dr = requests.delete(del_url, auth=(ONOS_USER, ONOS_PASS))
            print(f'  Deleted QoE flow {flow_id}: {dr.status_code}')


def install_qoe_flow(out_port):
    """Install QoE flow rule on s1 pointing to out_port."""
    flow = {
        'priority': int(PRIORITY_DSCP),
        'isPermanent': True,
        'deviceId': str(S1_ID),
        'tableId': 0,
        'treatment': {
            'instructions': [{'type': 'OUTPUT', 'port': str(out_port)}],
            'deferred': []
        },
        'selector': {
            'criteria': [
                {'type': 'ETH_TYPE', 'ethType': '0x0800'},
                {'type': 'IN_PORT',  'port': str(S1_PORT_H1)},
                {'type': 'IP_DSCP',  'ipDscp': int(DSCP_QOE)}
            ]
        }
    }
    url = f'{ONOS_BASE}/flows/{S1_ID}'
    r = requests.post(url,
                      auth=(ONOS_USER, ONOS_PASS),
                      headers={'Content-Type': 'application/json'},
                      data=json.dumps(flow))
    if r.status_code in (200, 201):
        print(f'  [OK] QoE flow installed → port {out_port}')
    else:
        print(f'  [ERROR] {r.status_code}: {r.text}')
        sys.exit(1)


def main():
    if len(sys.argv) < 3 or sys.argv[1] != '--path':
        print('Usage: python3 update_qoe_path.py --path A|B')
        sys.exit(1)

    path = sys.argv[2].upper()
    if path not in ('A', 'B'):
        print('Path must be A or B')
        sys.exit(1)

    out_port = S1_PORT_PATH_A if path == 'A' else S1_PORT_PATH_B
    print(f'Switching QoE flow to Path {path} (port {out_port})...')
    delete_qoe_flow()
    install_qoe_flow(out_port)
    print(f'Done. QoE → Path {path}. iperf → Path A (unchanged).')


if __name__ == '__main__':
    main()

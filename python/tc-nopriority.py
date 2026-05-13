#!/usr/bin/env python3

import subprocess
import time
import os

H5_IP = "10.0.0.5"
H6_IP = "10.0.0.6"
DURATION = 99999

LINK_BW = 10_000_000  # 10 Mbps

PHASES = [
    ("No congestion",     "0M",   "0M",   30),
    ("Light congestion",  "3M",   "3M",   60),
    ("Medium congestion", "5M",   "5M",   60),
    ("Heavy congestion",  "9.5M", "9.5M", 60),
    ("No congestion",     "0M",   "0M",   30),
]

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, capture_output=True)

def get_pid(host_name):
    result = subprocess.run(
        ['pgrep', '-f', f'mininet:{host_name}'],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split('\n')
    return lines[0].strip() if lines and lines[0] else None


def run_in_host(host, cmd, background=False):
    pid = get_pid(host)
    if not pid:
        print(f"[ERROR] No PID for {host}")
        return
    full = f"mnexec -a {pid} {cmd}"
    if background:
        os.system(full + " &")
    else:
        subprocess.run(full, shell=True)


def kill_iperf():
    for host in ['h3', 'h4']:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill -f iperf 2>/dev/null")


def start_servers():
    print("[traffic] Starting servers...")
    for host in ['h5', 'h6']:
        pid = get_pid(host)
        if pid:
            os.system(f"mnexec -a {pid} pkill iperf 2>/dev/null")
            os.system(f"mnexec -a {pid} iperf -s -u -D")
    time.sleep(1)


def start_clients(bw_h3, bw_h4):
    pid_h3 = get_pid('h3')
    pid_h4 = get_pid('h4')

    if pid_h3:
        os.system(f"mnexec -a {pid_h3} iperf -c {H5_IP} -u -b {bw_h3} -t {DURATION} &")

    if pid_h4:
        os.system(f"mnexec -a {pid_h4} iperf -c {H6_IP} -u -b {bw_h4} -t {DURATION} &")


def run_phases():
    start_servers()

    print("\n[traffic] Starting congestion cycle...\n")

    for label, bw_h3, bw_h4, duration in PHASES:
        kill_iperf()
        time.sleep(0.5)

        if bw_h3 == "0M":
            print(f"[{label}] idle {duration}s")
        else:
            total = float(bw_h3[:-1]) + float(bw_h4[:-1])
            print(f"[{label}] load {total}M/10M for {duration}s")
            start_clients(bw_h3, bw_h4)

        for remaining in range(duration, 0, -10):
            time.sleep(min(10, remaining))
            print(f"  ... {remaining}s remaining")


    kill_iperf()
    print("\n[traffic] Done.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run with sudo")
        exit(1)

    run_phases()

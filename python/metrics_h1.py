#!/usr/bin/env python3
"""
metrics_h1.py — runs on h1 inside Mininet
Sends DSCP-marked pings to h2 and writes latency/jitter/loss to a shared file.
The UDP sender script on the VM reads this file and forwards metrics to MATLAB.
"""

import os
import re
import time
import statistics

# --- Configuration ---
TARGET_IP  = "10.0.0.2"    # h2
PING_COUNT = 10             # packets per measurement round
PING_INTERVAL = 0.1         # seconds between pings (0.1 = 100ms)
                            # Default ping interval is 1s — too slow: the OS
                            # scheduler and OVS queues change state between
                            # packets, producing artificially high jitter.
                            # 100ms keeps consecutive RTTs comparable.
DSCP_VALUE = 46             # Expedited Forwarding (EF) — highest priority
LOG_FILE   = "/tmp/metrics.txt"

# DSCP 46 sets the TOS byte to 46<<2 = 184 (EF PHB)
# ping -Q sets the DSCP field in the IP header
# ping -i sets the interval between packets (requires root for < 0.2s)
PING_CMD = f"ping -c {PING_COUNT} -i {PING_INTERVAL} -Q {DSCP_VALUE} {TARGET_IP}"

print(f"[metrics_h1] Starting — target={TARGET_IP}  DSCP={DSCP_VALUE}  "
      f"count={PING_COUNT}  interval={PING_INTERVAL}s")

while True:
    output = os.popen(PING_CMD).read()

    # Extract individual RTT values from "time=X.XXX ms" lines
    rtt_values = [float(x) for x in re.findall(r"time=([\d.]+)", output)]

    if len(rtt_values) == 0:
        # No replies — use worst-case fallback values
        delay  = 50.0
        jitter = 5.0
        loss   = 1.0
        print(f"[metrics_h1] No replies — using fallback values")
    else:
        # Average delay across all successful pings
        delay = sum(rtt_values) / len(rtt_values)

        if len(rtt_values) > 1:
            diffs = [abs(rtt_values[i+1] - rtt_values[i])
                     for i in range(len(rtt_values) - 1)]
            # Median is robust against the 1-2 outlier spikes that
            # a mean would amplify into a falsely high jitter reading.
            jitter = statistics.median(diffs)
        else:
            jitter = 0.0

        # Packet loss as a fraction [0.0 – 1.0]
        loss = round((PING_COUNT - len(rtt_values)) / PING_COUNT, 2)

    # Atomic write: write to temp file then rename to avoid race conditions
    tmp = LOG_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(f"{delay} {jitter} {loss}")
    os.rename(tmp, LOG_FILE)

    print(f"[metrics_h1] delay={delay:.3f}ms  jitter={jitter:.3f}ms  loss={loss:.2f}")

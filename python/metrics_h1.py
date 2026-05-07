import os
import time
import re

LOG_FILE = "/tmp/metrics.txt"
PING_COUNT = 10  # number of packets per measurement round

while True:
    # Send PING_COUNT pings and capture full output
    output = os.popen(f"ping -c {PING_COUNT} 10.0.0.2").read()

    # Extract all individual RTT values from output
    # ping prints one "time=X ms" per successful reply
    rtt_values = [float(x) for x in re.findall(r"time=([\d.]+)", output)]

    if len(rtt_values) == 0:
        # No replies at all, assume worst case
        delay  = 50.0
        jitter = 5.0
        loss   = 1.0
    else:
        # Average delay across all successful pings
        delay = sum(rtt_values) / len(rtt_values)

        # Real jitter: average of absolute differences between consecutive RTTs
        # e.g. RTTs=[10, 13, 11] → diffs=[3, 2] → jitter=2.5
        if len(rtt_values) > 1:
            diffs = [abs(rtt_values[i+1] - rtt_values[i]) for i in range(len(rtt_values)-1)]
            jitter = sum(diffs) / len(diffs)
        else:
            jitter = 0.0

        # Real packet loss ratio: packets lost / packets sent
        loss = round((PING_COUNT - len(rtt_values)) / PING_COUNT, 2)

    # Write metrics to shared file
    with open(LOG_FILE, "w") as f:
        f.write(f"{delay} {jitter} {loss}")

    print(f"h1 wrote: delay={delay:.3f} jitter={jitter:.3f} loss={loss:.2f}")
    time.sleep(1)

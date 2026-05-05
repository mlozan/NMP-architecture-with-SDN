import os
import time
import re

LOG_FILE = "/tmp/metrics.txt"

while True:
    # Ping h2 3 times and capture the full output
    output = os.popen("ping -c 3 10.0.0.2").read()

    # Default delay in case ping fails
    delay = 50

    # Extract RTT from ping output (e.g. "time=12.3 ms")
    match = re.search(r"time=([\d.]+)", output)
    if match:
        delay = float(match.group(1))

    # Approximate jitter as 10% of delay (no direct measurement)
    jitter = delay * 0.1

    # Loss is binary: 0.0 if no packets lost, 1.0 if any lost
    loss = 0.0 if "0% packet loss" in output else 1.0

    # Write metrics to shared file
    with open(LOG_FILE, "w") as f:
        f.write(f"{delay} {jitter} {loss}")

    print("h1 wrote:", delay, jitter, loss)
    time.sleep(1)

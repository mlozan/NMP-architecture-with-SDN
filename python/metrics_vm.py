import time
from socket import *

MATLAB_IP = "192.168.56.1"   # Host machine IP (where MATLAB runs)
PORT = 5006
LOG_FILE = "/tmp/metrics.txt"

sock = socket(AF_INET, SOCK_DGRAM)

while True:
    try:
        # Read the latest metrics written by h1
        with open(LOG_FILE, "r") as f:
            data = f.read().strip()

        if data:
            print("VM sending:", data)
            # Send metrics as a UTF-8 encoded UDP packet to MATLAB
            sock.sendto(data.encode(), (MATLAB_IP, PORT))
    except:
        pass  # Silently skip if file is not available yet

    time.sleep(1)

#!/usr/bin/env python3
from scapy.all import IP, ICMP, sr1
import socket, json, time, signal, sys

VM_IP       = "172.17.0.1"    # docker0 — accesible desde h1
VM_PORT     = 5005
INTERVAL    = 1.0
DST_IP      = "10.0.0.2"
SRC_IP      = "10.0.0.1"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def handler(sig, frame):
    print("\nStopped.")
    sock.close()
    sys.exit(0)

signal.signal(signal.SIGINT, handler)

prev_rtt = None
seq = 0

print(f"Starting measurement to {DST_IP}...")

while True:
    packet = IP(src=SRC_IP, dst=DST_IP) / ICMP(seq=seq)

    t0 = time.perf_counter()
    reply = sr1(packet, timeout=2, verbose=0)
    t1 = time.perf_counter()

    if reply and reply.haslayer(ICMP) and reply[ICMP].type == 0:
        rtt    = (t1 - t0) * 1000
        jitter = abs(rtt - prev_rtt) if prev_rtt is not None else 0.0
        lost   = 0
        prev_rtt = rtt
    else:
        rtt      = None
        jitter   = 0.0
        lost     = 1
        prev_rtt = None

    payload = json.dumps({
        "timestamp":  round(time.time(), 3),
        "latency_ms": round(rtt, 3) if rtt else None,
        "jitter_ms":  round(jitter, 3),
        "lost":       lost,
        "seq":        seq
    })

    try:
        sock.sendto(payload.encode(), (VM_IP, VM_PORT))
    except Exception as e:
        print(f"UDP error: {e}")

    print(f"[seq={seq}] latency={rtt:.2f}ms  jitter={jitter:.2f}ms  lost={lost}"
          if rtt else f"[seq={seq}] LOST")

    seq += 1
    time.sleep(INTERVAL)

#!/usr/bin/env python3
from scapy.all import IP, ICMP, sr1
import socket, json, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

MATLAB_IP   = "127.0.0.1"
MATLAB_PORT = 5005
INTERVAL    = 1.0
DST_IP      = "10.0.0.2"
SRC_IP      = "10.0.0.1"
HTTP_PORT   = 8080

latest = {}

# Servidor HTTP simple
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(latest).encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open("dashboard.html", "rb") as f:
                self.wfile.write(f.read())
    def log_message(self, *args):
        pass  # silencia logs del servidor

def run_server():
    HTTPServer(("0.0.0.0", HTTP_PORT), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()
print(f"Dashboard at http://localhost:{HTTP_PORT}")

# Loop de medición
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
prev_rtt = None
seq = 0

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

    latest.update({
        "timestamp":  round(time.time(), 3),
        "latency_ms": round(rtt, 3) if rtt else None,
        "jitter_ms":  round(jitter, 3),
        "lost":       lost,
        "seq":        seq
    })

    sock.sendto(json.dumps(latest).encode(), (MATLAB_IP, MATLAB_PORT))
    print(f"[seq={seq}] latency={rtt:.2f}ms  jitter={jitter:.2f}ms" 
          if rtt else f"[seq={seq}] LOST")

    seq += 1
    time.sleep(INTERVAL)

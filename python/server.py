#!/usr/bin/env python3
import socket, json, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

HTTP_PORT    = 8080
UDP_PORT     = 5005
MATLAB_IP    = "192.168.56.1"
MATLAB_PORT  = 5006

latest  = {}
history = []
MAX_HISTORY = 120

forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "latest":  latest,
                "history": history
            }).encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open("dashboard.html", "rb") as f:
                self.wfile.write(f.read())
    def log_message(self, *args):
        pass

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"Listening on UDP {UDP_PORT}...")
    while True:
        data, _ = sock.recvfrom(1024)
        m = json.loads(data.decode())
        latest.update(m)
        history.append(m)
        if len(history) > MAX_HISTORY:
            history.pop(0)
        # Reenviar a MATLAB en Windows
        try:
            forward_sock.sendto(data, (MATLAB_IP, MATLAB_PORT))
        except Exception as e:
            print(f"Forward error: {e}")

threading.Thread(target=udp_listener, daemon=True).start()
print(f"Dashboard at http://localhost:{HTTP_PORT}")
print(f"Forwarding to MATLAB at {MATLAB_IP}:{MATLAB_PORT}")
HTTPServer(("0.0.0.0", HTTP_PORT), Handler).serve_forever()

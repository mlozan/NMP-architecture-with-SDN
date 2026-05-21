#!/usr/bin/env python3
"""
background_traffic.py
Genera tráfico de fondo entre h3→h5 y h4→h6 para saturar Path A (s1→s3→s4).
Ejecutar desde la CLI de Mininet:
    mininet> py exec(open('background_traffic.py').read())
O bien lanzar los servidores/clientes manualmente por separado.
"""

import subprocess
import time
import threading
import sys

# ─── Configuración ───────────────────────────────────────────────────────────
IPERF_DURATION   = 9999      # segundos (prácticamente infinito; Ctrl+C para parar)
BANDWIDTH_MBPS   = "9M"      # ancho de banda por flujo UDP (~9 Mbps sobre enlace de 10 Mbps)
UDP_BUFFER_SIZE  = "1M"      # buffer UDP
IPERF_PORT_H5    = 5201      # puerto servidor en h5
IPERF_PORT_H6    = 5202      # puerto servidor en h6
IP_H5            = "10.0.0.5"
IP_H6            = "10.0.0.6"

# ─── Utilidades ──────────────────────────────────────────────────────────────

def run_server(host, port, label):
    """Arranca iperf3 en modo servidor en el host indicado."""
    cmd = f"iperf3 -s -p {port} -D --logfile /tmp/iperf_server_{label}.log"
    print(f"[{label}] Servidor iperf3 escuchando en puerto {port}")
    host.cmd(cmd)

def run_client(host, target_ip, port, bw, duration, label):
    """Lanza iperf3 en modo cliente UDP desde el host indicado."""
    cmd = (
        f"iperf3 -c {target_ip} -p {port} "
        f"-u -b {bw} "
        f"-t {duration} "
        f"--length {UDP_BUFFER_SIZE} "
        f"--logfile /tmp/iperf_client_{label}.log &"
    )
    print(f"[{label}] Cliente iperf3 → {target_ip}:{port}  bw={bw}  dur={duration}s")
    host.cmd(cmd)

# ─── Función principal ────────────────────────────────────────────────────────

def start_background_traffic(net):
    """
    Recibe el objeto net de Mininet y lanza el tráfico de fondo.
    Uso:
        from background_traffic import start_background_traffic
        start_background_traffic(net)
    """
    h3 = net.get('h3')
    h4 = net.get('h4')
    h5 = net.get('h5')
    h6 = net.get('h6')

    print("\n[BG] Iniciando servidores iperf3 en h5 y h6...")
    # Matar instancias previas por si acaso
    h5.cmd("pkill -f iperf3; sleep 0.5")
    h6.cmd("pkill -f iperf3; sleep 0.5")

    # Arrancar servidores en background
    h5.cmd(f"iperf3 -s -p {IPERF_PORT_H5} -D --logfile /tmp/iperf_server_h5.log")
    h6.cmd(f"iperf3 -s -p {IPERF_PORT_H6} -D --logfile /tmp/iperf_server_h6.log")
    time.sleep(1)  # Esperar a que los servidores estén listos

    print("[BG] Lanzando clientes UDP h3→h5 y h4→h6...")
    # Flujo 1: h3 → h5  (satura Path A junto con el flujo h1→h2)
    h3.cmd(
        f"iperf3 -c {IP_H5} -p {IPERF_PORT_H5} "
        f"-u -b {BANDWIDTH_MBPS} -t {IPERF_DURATION} "
        f"--length {UDP_BUFFER_SIZE} "
        f"--logfile /tmp/iperf_client_h3.log &"
    )
    # Flujo 2: h4 → h6  (añade más carga)
    h4.cmd(
        f"iperf3 -c {IP_H6} -p {IPERF_PORT_H6} "
        f"-u -b {BANDWIDTH_MBPS} -t {IPERF_DURATION} "
        f"--length {UDP_BUFFER_SIZE} "
        f"--logfile /tmp/iperf_client_h4.log &"
    )

    print("[BG] Tráfico de fondo activo. Logs en /tmp/iperf_client_h*.log")
    print("[BG] Para detener: h3.cmd('pkill -f iperf3'); h4.cmd('pkill -f iperf3')\n")


def stop_background_traffic(net):
    """Detiene todos los procesos iperf3 en los hosts de background."""
    for name in ['h3', 'h4', 'h5', 'h6']:
        net.get(name).cmd("pkill -f iperf3")
    print("[BG] Tráfico de fondo detenido.")


# ─── Uso directo desde CLI de Mininet ────────────────────────────────────────
# Si se ejecuta con: mininet> py exec(open('background_traffic.py').read())
# el objeto 'net' ya existe en el namespace de Mininet.

if __name__ == '__main__' or 'net' in dir():
    try:
        start_background_traffic(net)
    except NameError:
        print("Ejecuta este script desde dentro de Mininet CLI:")
        print("  mininet> py exec(open('background_traffic.py').read())")

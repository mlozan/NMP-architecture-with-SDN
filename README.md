# NMP-SDN QoE-Based Adaptive Routing System

This project integrates **Mininet + ONOS + MATLAB** to simulate an SDN environment with real-time QoE monitoring and adaptive routing based on network conditions.

---

## Overview

The system dynamically:
- Measures network metrics (delay, jitter, packet loss)
- Computes QoE in real time
- Detects degradation
- Triggers rerouting via ONOS
- Updates flow rules automatically

---

## 🧰 Prerequisites

- Ubuntu/Linux system (recommended)
- MATLAB installed
- Git installed
- Docker installed
- Python 3 installed

---

## ⚙️ 1. Install Mininet

```bash
sudo apt update
sudo apt install mininet -y
```

## 🐳 2. Install and Start ONOS (Docker)

First time: 
```bash
sudo apt install docker.io -y
sudo systemctl start docker

sudo docker pull onosproject/onos:2.7.0

sudo docker run -d --name onos \
-p 8181:8181 \
-p 6653:6653 \
-p 8101:8101 \
onosproject/onos:2.7.0
```

```bash
docker run -p 192.168.56.102:8181:8181 onosproject/onos
```

## 🔐 3. Access ONOS CLI
```bash
ssh -o HostKeyAlgorithms=+ssh-rsa \
-o PubkeyAcceptedAlgorithms=+ssh-rsa \
-p 8101 onos@localhost
```

## 📦 4. Activate ONOS Applications
```bash
app activate org.onosproject.openflow
app activate org.onosproject.fwd
app activate org.onosproject.proxyarp
app activate org.onosproject.hostprovider
```


## 🌐 5. Launch Mininet Topology
```bash
sudo mn --custom topo_qoe.py --topo qoe \
--controller=remote,ip=192.168.56.101,port=6653 \
--switch ovs,protocols=OpenFlow13
```


## 📊 6. Run Network Monitoring (Mininet)
```bash
mininet> h1 python3 metrics_h1.py
```

## 📡 7. Forward Metrics from VM
```bash
python3 metrics_vm.py
```


## 📉 8. Run QoE Controller in MATLAB
```bash
qoe3
```


## ⚡ 9. Optional Network Degradation Test
```bash
python3 degrade.py
```


## 🔍 10. Monitor ONOS in Real Time
```bash
curl --user onos:rocks http://localhost:8181/onos/v1/flows | jq
curl --user onos:rocks http://localhost:8181/onos/v1/devices | jq
curl --user onos:rocks http://localhost:8181/onos/v1/links | jq
```


## 🌐 11. ONOS Web UI
```bash
http://192.168.56.101:8181/onos/ui







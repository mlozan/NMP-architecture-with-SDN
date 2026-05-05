import time
import subprocess

def degrade_link(interface, delay, jitter, loss):
    cmd = f'tc qdisc add dev {interface} root netem delay {delay} jitter {jitter} loss {loss}'
    subprocess.run(cmd.split())
    print(f"*** Link {interface} degraded")

def restore_link(interface):
    cmd = f'tc qdisc del dev {interface} root'
    subprocess.run(cmd.split())
    print(f"*** Link {interface} restored")

if __name__ == '__main__':
    print("Waiting 30 seconds before degrading Path A...")
    time.sleep(30)
    degrade_link('s1-eth2', '80ms', '20ms', '10%')
    time.sleep(60)
    restore_link('s1-eth2')
    

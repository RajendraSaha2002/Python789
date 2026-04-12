import socket
import json
import time
import random
import threading

JAVA_HOST = '127.0.0.1'
JAVA_PORT = 8080

# Track the physical status of our simulated grid nodes
nodes_status = {1: "ONLINE", 2: "ONLINE", 3: "ONLINE"}


def listen_for_scada_commands(sock):
    """Listens for automated defense commands from the Java MTU"""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data: break

            if "TRIP_BREAKER" in data:
                # Java IDS detected an attack and ordered an isolation
                target_node = int(data.split(":")[1].strip())
                nodes_status[target_node] = "ISOLATED"
                print(f"\n[BLUE TEAM RESPONSE] Breaker tripped for Node {target_node}! Disconnecting from grid.\n")
        except:
            break


def run_edge_nodes():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((JAVA_HOST, JAVA_PORT))
        print("[RTU] Connected to Master Command Center.")

        # Start a background thread to listen for Kill Commands from Java
        threading.Thread(target=listen_for_scada_commands, args=(s,), daemon=True).start()

        while True:
            for node_id, status in nodes_status.items():
                if status == "ISOLATED":
                    continue  # Do not send data for islanded nodes

                # 1. Generate normal physics telemetry (230V, 50Hz)
                voltage = random.uniform(228.0, 232.0)
                freq = random.uniform(49.9, 50.1)
                load = random.uniform(500.0, 800.0)

                # 2. Red Team Attack Engine: Randomly inject False Data (FDI Attack)
                # We simulate an attacker falsifying a massive voltage drop to crash the automated systems
                if random.random() < 0.05:  # 5% chance of attack per tick
                    print(f"[RED TEAM] Injecting FDI Payload (Voltage Drop) into Node {node_id}...")
                    voltage = voltage * 0.75  # Drops voltage to ~172V (Highly anomalous)

                # 3. Transmit telemetry to Java Command Center
                payload = {
                    "node_id": node_id,
                    "voltage": round(voltage, 2),
                    "frequency": round(freq, 2),
                    "load_kw": round(load, 2)
                }

                s.sendall((json.dumps(payload) + '\n').encode('utf-8'))

            time.sleep(1.5)  # Simulate telemetry polling interval

    except ConnectionRefusedError:
        print("[ERROR] Cannot connect to Java MTU. Is the Command Center running?")


if __name__ == "__main__":
    print("--- Starting Project BLACKOUT Edge Nodes & Attack Simulator ---")
    run_edge_nodes()
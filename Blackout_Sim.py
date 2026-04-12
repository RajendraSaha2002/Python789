import socket
import json
import time
import random
import threading
import sys

JAVA_HOST = '127.0.0.1'
JAVA_PORT = 5050

# Global Grid State
grid_nodes = {
    "Substation_A": {"voltage": 220.0, "frequency": 50.0, "load": 500.0, "status": "CLOSED"},
    "Substation_B": {"voltage": 220.0, "frequency": 50.0, "load": 480.0, "status": "CLOSED"}
}

system_active = True


def c2_listener(sock):
    """Background thread to ingest commands from the Java Command Center"""
    global system_active
    while system_active:
        try:
            data = sock.recv(1024).decode('utf-8').strip()
            if not data:
                break

            print(f"\n[RECEIVED FROM C2] {data}")

            if data == "EMERGENCY_SHUTDOWN":
                print("[SYSTEM] Emergency Shutdown Initiated! Halting simulation.")
                system_active = False
                sys.exit(0)

            elif data.startswith("SAFE_MODE:"):
                target = data.split(":")[1]
                if target in grid_nodes:
                    grid_nodes[target]["status"] = "ISOLATED"
                    grid_nodes[target]["voltage"] = 0.0  # Breaker tripped
                    print(f"[HARDWARE] {target} Breaker Tripped. Node Isolated.\n")

        except ConnectionAbortedError:
            break


def run_simulation():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((JAVA_HOST, JAVA_PORT))
        print("[NETWORK] Connected to Java MTU on Port 5050")

        # Start C2 listener thread
        threading.Thread(target=c2_listener, args=(s,), daemon=True).start()

        tick = 0
        while system_active:
            tick += 1
            for name, data in grid_nodes.items():
                if data["status"] == "ISOLATED":
                    continue  # Stop sending data if Java isolated this node

                # Generate normal physics variance
                data["voltage"] = round(random.uniform(218.0, 222.0), 2)
                data["frequency"] = round(random.uniform(49.95, 50.05), 2)
                data["load"] = round(random.uniform(490.0, 520.0), 2)

                # --- RED TEAM ATTACK ENGINE ---
                # Attack 1: MitM Attack (Falsifying voltage to 0 while breaker is CLOSED)
                if tick % 25 == 0 and name == "Substation_B":
                    print(f"[ATTACK ENGINE] Injecting MitM Voltage Drop on {name}...")
                    data["voltage"] = 0.0

                # Attack 2: Slow Load Escalation Trick
                if tick % 35 == 0 and name == "Substation_A":
                    print(f"[ATTACK ENGINE] Injecting Load Spike on {name}...")
                    data["load"] = 1500.0

                # Package and Transmit (Mimicking pyzmq publish)
                payload = {
                    "substation": name,
                    "voltage": data["voltage"],
                    "frequency": data["frequency"],
                    "load": data["load"],
                    "status": data["status"]
                }

                # Append newline so Java's readLine() detects the end of the packet
                packet = json.dumps(payload) + '\n'
                s.sendall(packet.encode('utf-8'))

            time.sleep(1.0)  # 1-second telemetry interval

    except ConnectionRefusedError:
        print("[FATAL] Could not connect. Ensure Java C2 is running first!")


if __name__ == "__main__":
    print("--- Project BLACKOUT: Grid Sim & Attack Engine ---")
    run_simulation()
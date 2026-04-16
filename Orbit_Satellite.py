import socket
import json
import time
import threading
import random
import hmac
import hashlib

GCS_HOST = '127.0.0.1'
GCS_PORT = 8888
SECRET_KEY = b"ORBIT_TOP_SECRET_HMAC_KEY"


def verify_signature(cmd, signature):
    """Verifies the HMAC-SHA256 signature sent by Java"""
    expected_mac = hmac.new(SECRET_KEY, cmd.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_mac, signature)


def satellite_telemetry_loop(sock):
    """Simulates normal satellite physics and downlink"""
    print("[SATELLITE] Commencing standard telemetry downlink...")
    while True:
        temp = random.uniform(15.0, 25.0)
        sun = random.uniform(80.0, 100.0)
        payload = {"type": "TELEMETRY", "battery": 98.5, "temp": temp, "sun": sun}
        try:
            sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))
        except:
            break
        time.sleep(1)


def satellite_uplink_listener(sock):
    """Listens for commands from Ground Control, checking crypto signatures"""
    sock.settimeout(None)
    f = sock.makefile('r')
    while True:
        line = f.readline()
        if not line: break
        try:
            data = json.loads(line)
            cmd = data.get("cmd")
            sig = data.get("signature")

            if verify_signature(cmd, sig):
                print(f"\n[SATELLITE - SECURE] Executing Authorized Command: {cmd}\n")
            else:
                print(f"\n[SATELLITE - HACKED] Invalid Crypto Signature! Rejecting {cmd}\n")
        except json.JSONDecodeError:
            pass


# ================= RED TEAM ADVERSARY =================

def attack_phantom_command(sock):
    """Scenario: Command Injection (Attempting to force an unapproved DE-ORBIT)"""
    time.sleep(4)
    print("\n[RED TEAM] Injecting Phantom Command: DE-ORBIT...")
    payload = {"type": "INJECT_CMD", "cmd": "DE-ORBIT"}
    sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))

    time.sleep(2)
    print("[RED TEAM] Injecting Authorized Command trigger to test crypto...")
    payload = {"type": "INJECT_CMD", "cmd": "ROTATE_ANTENNA"}
    sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))


def attack_telemetry_hijack(sock):
    """Scenario: Telemetry Spoofing / Sensor Manipulation"""
    time.sleep(8)
    print("\n[RED TEAM] Spoofing Telemetry (0% Battery & Sensor Manipulation)...")
    payload = {"type": "TELEMETRY", "battery": 0.0, "temp": 85.0, "sun": 2.0}
    sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))


def attack_signal_denial(sock):
    """Scenario: DoS (Signal Denial via RF flooding)"""
    time.sleep(12)
    print("\n[RED TEAM] Launching RF Signal Denial (DoS Flood)...")
    payload = {"type": "TELEMETRY", "battery": 99.0, "temp": 20.0, "sun": 90.0}
    encoded = (json.dumps(payload) + '\n').encode('utf-8')
    for _ in range(100):  # Flood the socket
        try:
            sock.sendall(encoded)
            time.sleep(0.01)  # Faster than the Leaky Bucket can drain
        except:
            break


if __name__ == "__main__":
    print("--- ORBIT-SHIELD: SATELLITE & ADVERSARY SIMULATOR ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((GCS_HOST, GCS_PORT))
        print("[NETWORK] RF Link to Ground Station established.")

        # Start Satellite Physics Threads
        threading.Thread(target=satellite_telemetry_loop, args=(s,), daemon=True).start()
        threading.Thread(target=satellite_uplink_listener, args=(s,), daemon=True).start()

        # Start APT Attack Threads
        threading.Thread(target=attack_phantom_command, args=(s,), daemon=True).start()
        threading.Thread(target=attack_telemetry_hijack, args=(s,), daemon=True).start()
        threading.Thread(target=attack_signal_denial, args=(s,), daemon=True).start()

        # Keep main thread alive
        while True: time.sleep(1)

    except ConnectionRefusedError:
        print("[FATAL] Could not connect. Start the Java Ground Station first!")
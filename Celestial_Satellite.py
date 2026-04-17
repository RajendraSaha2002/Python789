import socket
import json
import time
import threading
import random

GCS_IP = '127.0.0.1'
GCS_PORT = 4444
SAT_PORT = 5555
CRYPTO_KEY = b"AEROSPACE_VIGIL_KEY"

# Shared state
satellite_state = {"lat": 0.0, "lon": -180.0, "seq": 1}


def xor_crypt(data: bytes) -> bytes:
    """Native Stream Cipher to match Java (Zero dependencies)"""
    return bytes([b ^ CRYPTO_KEY[i % len(CRYPTO_KEY)] for i, b in enumerate(data)])


def satellite_telemetry_loop(sock):
    """Simulates physical orbit and downlinks via UDP"""
    print("[SATELLITE] UDP Telemetry Downlink Active...")
    while True:
        # Move satellite across the map
        satellite_state["lon"] += 5.0
        if satellite_state["lon"] > 180: satellite_state["lon"] = -180.0
        satellite_state["lat"] = 45.0 * random.uniform(0.9, 1.1)  # Wobbly orbit

        payload = {
            "seq": satellite_state["seq"],
            "lat": round(satellite_state["lat"], 2),
            "lon": round(satellite_state["lon"], 2),
            "alt": 405.0
        }
        json_str = json.dumps(payload)

        # --- ADVERSARY: Bit-Flip Injection (Cosmic Radiation / Tampering) ---
        if random.random() < 0.05:  # 5% chance to corrupt the packet
            print("\n[RED TEAM] Injecting Bit-Flip Corruption into Downlink!")
            json_str = json_str.replace("alt", "al_CORRUPTED_t")  # Breaks Java JSON parser

        # --- ADVERSARY: Signal Jamming ---
        if random.random() < 0.10:  # 10% chance to drop the packet entirely
            print("[RED TEAM] Jamming RF Signal (Dropping packet seq {})".format(satellite_state["seq"]))
            satellite_state["seq"] += 1
            time.sleep(1)
            continue  # Skip sending

        sock.sendto(json_str.encode('utf-8'), (GCS_IP, GCS_PORT))
        satellite_state["seq"] += 1
        time.sleep(1)


def satellite_uplink_listener(sock):
    """Listens for UDP commands and enforces the Custom XOR Crypto"""
    while True:
        data, addr = sock.recvfrom(1024)

        # Determine if data is encrypted based on raw byte inspection (simplified)
        # We try to decrypt it first.
        decrypted_bytes = xor_crypt(data)

        try:
            # Try to parse the decrypted bytes
            payload = json.loads(decrypted_bytes.decode('utf-8'))
            if payload.get("crypto") == "XOR":
                print(f"\n[SAT-SECURE] Valid Encrypted Command Received: {payload.get('cmd')}\n")
                continue
        except:
            pass  # Decryption failed, it might be plaintext

        try:
            # Try to parse as plaintext
            payload = json.loads(data.decode('utf-8'))
            if payload.get("crypto") == "NONE":
                print(f"\n[SAT-DANGER] PLAINTEXT Command Received: {payload.get('cmd')}")
                print("[SAT-DEFENSE] REJECTING Plaintext command due to security policy!\n")
        except:
            print("\n[SAT-ERROR] Unrecognized RF noise received.\n")


def adversary_rogue_uplink(sock):
    """ADVERSARY: Simulates a hacker sending unauthorized commands to the Satellite"""
    while True:
        time.sleep(15)
        print("\n[RED TEAM] Injecting Unauthorized Rogue Command (DEORBIT)...")
        # Attacker sends plaintext because they don't have the AES/XOR key
        rogue_payload = '{"cmd":"DEORBIT","crypto":"NONE"}'
        # Attacker spoofs by sending directly to the Satellite port via loopback
        sock.sendto(rogue_payload.encode('utf-8'), ('127.0.0.1', SAT_PORT))


if __name__ == "__main__":
    print("--- CELESTIAL-VIGIL: Satellite & RF Adversary ---")

    # UDP Socket for Satellite
    sat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sat_sock.bind(('0.0.0.0', SAT_PORT))

    threading.Thread(target=satellite_telemetry_loop, args=(sat_sock,), daemon=True).start()
    threading.Thread(target=satellite_uplink_listener, args=(sat_sock,), daemon=True).start()

    # Attacker uses a separate socket to inject attacks
    attack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    threading.Thread(target=adversary_rogue_uplink, args=(attack_sock,), daemon=True).start()

    while True: time.sleep(1)
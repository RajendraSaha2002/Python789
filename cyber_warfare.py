import psycopg2
import socket
import threading
import time
import random
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'cyber_war_db',
    'port': 5432
}

JAVA_HOST = '127.0.0.1'
JAVA_PORT = 5000


# --- TOOL 1: RED TEAM ATTACK SIMULATOR ---
def run_red_team():
    print("\n[RED TEAM] Attack Console Initialized.")
    print("1. Simulate Normal Traffic (Background Noise)")
    print("2. Launch SSH Brute Force (Port 22 Flooding)")
    print("3. Launch Botnet DDOS (Distributed IPs -> Port 80)")
    choice = input("Select Attack Vector: ")

    if choice == '1':
        print("[RED] Sending normal traffic...")
        while True:
            ip = f"192.168.1.{random.randint(1, 100)}"
            send_log(ip, 80, "GET /index.html HTTP/1.1")
            time.sleep(0.5)

    elif choice == '2':
        target_ip = "10.10.10.5"  # Attacker IP
        print(f"[RED] Launching Brute Force from {target_ip}...")
        for i in range(100):
            send_log(target_ip, 22, f"ssh: login failed for user root (attempt {i})")
            time.sleep(0.05)  # FAST
        print("[RED] Attack Batch Complete.")

    elif choice == '3':
        print("[RED] activating Botnet Swarm...")
        for i in range(60):
            # Generate 60 UNIQUE IPs in 1 second
            bot_ip = f"45.33.{random.randint(1, 255)}.{random.randint(1, 255)}"
            send_log(bot_ip, 80, "GET /admin HTTP/1.1")
            time.sleep(0.02)  # VERY FAST
        print("[RED] Botnet Surge Complete.")


def send_log(ip, port, payload):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((JAVA_HOST, JAVA_PORT))
        # Format: "IP|PORT|PAYLOAD"
        msg = f"{ip}|{port}|{payload}"
        s.sendall(msg.encode('utf-8'))
        s.close()
        print(f" -> Sent: {msg}")
    except ConnectionRefusedError:
        print("[ERROR] Java SIEM is offline. Start BlueTeamSIEM.java first.")
        sys.exit()


# --- TOOL 2: BLUE TEAM HEURISTIC HUNTER ---
def run_blue_team():
    print("\n[BLUE TEAM] Heuristic Engine Online.")
    print("Scanning database for anomalies...")

    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # HEURISTIC 1: Brute Force Detection
            # Logic: Single IP hitting Port 22 > 10 times in last 30 seconds
            cur.execute("""
                        SELECT source_ip, COUNT(*)
                        FROM network_logs
                        WHERE target_port = 22
                          AND classification = 'Analyzing...'
                          AND timestamp
                            > NOW() - INTERVAL '30 seconds'
                        GROUP BY source_ip
                        HAVING COUNT (*) > 10
                        """)
            brute_force_ips = cur.fetchall()

            for ip, count in brute_force_ips:
                print(f"[HUNTER] ALERT: Brute Force detected from {ip} ({count} attempts)")
                cur.execute(
                    "UPDATE network_logs SET classification='BRUTE_FORCE_ATTACK', severity_level=90 WHERE source_ip=%s AND classification='Analyzing...'",
                    (ip,))

            # HEURISTIC 2: Botnet Detection
            # Logic: > 50 DISTINCT IPs hitting Port 80 in last 10 seconds
            cur.execute("""
                        SELECT COUNT(DISTINCT source_ip)
                        FROM network_logs
                        WHERE target_port = 80
                          AND classification = 'Analyzing...'
                          AND timestamp
                            > NOW() - INTERVAL '10 seconds'
                        """)
            unique_ips = cur.fetchone()[0]

            if unique_ips > 30:  # Threshold lowered for demo
                print(f"[HUNTER] ALERT: Botnet Swarm Detected! ({unique_ips} unique hosts)")
                cur.execute(
                    "UPDATE network_logs SET classification='BOTNET_ATTACK_DDOS', severity_level=100 WHERE target_port=80 AND classification='Analyzing...'")

            # Mark rest as CLEAN
            cur.execute(
                "UPDATE network_logs SET classification='CLEAN' WHERE classification='Analyzing...' AND timestamp < NOW() - INTERVAL '1 minute'")

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[ERROR] Engine failure: {e}")

        time.sleep(2)  # Poll every 2 seconds


# --- MENU ---
if __name__ == "__main__":
    print("--- CYBER WARFARE SIMULATION TOOLS ---")
    print("1. Launch Red Team (Attacker)")
    print("2. Launch Blue Team (Hunter Engine)")
    mode = input("Select Mode: ")

    if mode == '1':
        run_red_team()
    elif mode == '2':
        run_blue_team()
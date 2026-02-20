import os
import time
import psycopg2
import hashlib

# DB CONFIG
DB_CONFIG = {"dbname": "postgres", "user": "postgres", "password": "varrie75", "host": "localhost"}

# DIRECTORY TO WATCH (Simulated System Folder)
WATCH_DIR = "./system_binaries"

# CREATE DIR IF NOT EXISTS
if not os.path.exists(WATCH_DIR):
    os.makedirs(WATCH_DIR)

print(f"🛡️ KAVACH-C2 SCANNER ONLINE. Watching: {WATCH_DIR}")


def scan_file(filepath):
    """
    Simulates a YARA scan. In a real scenario, you'd use:
    rules = yara.compile(filepath='rules.yar')
    matches = rules.match(filepath)
    """
    filename = os.path.basename(filepath)

    print(f"Scanning: {filename}...")
    time.sleep(0.5)  # Simulate processing time

    threat_name = None

    # 1. SIMULATED YARA RULE MATCHING
    # If the file is named 'malware.exe' or 'supply_chain_patch.bin'
    if "ransom" in filename.lower() or "malware" in filename.lower():
        threat_name = "RANSOMWARE.RYUK.VARIANT"
    elif "patch" in filename.lower():
        threat_name = "SUPPLY_CHAIN_COMPROMISE"

    if threat_name:
        log_threat("AIR-CMD-ALPHA", filename, threat_name)
    else:
        print(f"✅ CLEAN: {filename}")


def log_threat(node, filename, threat):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print(f"🚨 THREAT DETECTED: {threat} in {filename}")

        # Log to Integrity Table (Triggers SQL Quarantine)
        cur.execute("""
                    INSERT INTO system_integrity_logs (node_id, file_scanned, threat_detected)
                    VALUES (%s, %s, %s)
                    """, (node, filename, threat))

        conn.commit()
        conn.close()
        print(">> ALERT LOGGED TO WORM LEDGER.")

    except Exception as e:
        print(f"DB Error: {e}")


# MAIN LOOP
processed_files = set()

while True:
    # List files in directory
    files = [f for f in os.listdir(WATCH_DIR) if os.path.isfile(os.path.join(WATCH_DIR, f))]

    for f in files:
        if f not in processed_files:
            scan_file(os.path.join(WATCH_DIR, f))
            processed_files.add(f)

    print("--- Scan Cycle Complete. Waiting... ---")
    time.sleep(5)
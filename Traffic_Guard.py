import zmq
import psycopg2
import hashlib
import time
import random

# DB CONFIG (Login as sec_analyst)
DB_CONFIG = {"dbname": "postgres", "user": "sec_analyst", "password": "monitor123", "host": "localhost"}

# ZMQ CONFIG
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")

print("🛡️ VIGILANT-S: TRAFFIC GUARD ONLINE (Port 5556)")


def check_file_integrity(file_data):
    # 1. Generate SHA-256 Hash of the data
    file_hash = hashlib.sha256(file_data.encode()).hexdigest()

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. Check DB for this hash
        query = "SELECT filename_masked FROM digital_fingerprints WHERE file_hash = %s"
        cur.execute(query, (file_hash,))
        result = cur.fetchone()

        if result:
            # MATCH FOUND! SENSITIVE DATA DETECTED!
            filename = result[0]
            print(f"🚨 ALERT: EXFILTRATION DETECTED! File: {filename}")

            # 3. Log to DB
            cur.execute("INSERT INTO access_logs (event_type) VALUES ('EXFILTRATION_BLOCKED')")
            conn.commit()

            # 4. SEND KILL SIGNAL TO JAVA (ZeroMQ)
            # Format: "LOCK_PORT [PORT_ID] [THREAT_NAME]"
            socket.send_string(f"LOCK_PORT 8080 {filename}")
            return True

        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

    return False


# SIMULATION LOOP
while True:
    time.sleep(3)  # Wait 3 seconds between checks

    # Randomly simulate a "User" trying to send data
    if random.choice([True, False]):
        print(">> Scanning Outbound Packet: [Normal Email]...")
        check_file_integrity("Just a normal email body.")
    else:
        print(">> Scanning Outbound Packet: [Sensitive Payload]...")
        # This string matches the hash in the SQL script
        # In a real app, this would be the binary content of a PDF
        check_file_integrity("SECRET_DATA")

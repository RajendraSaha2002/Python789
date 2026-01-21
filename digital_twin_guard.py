import psycopg2
import socket
import time
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'cyber_nuke_db',
    'port': 5432
}

JAVA_HOST = '127.0.0.1'
BACKDOOR_PORT = 6666


def run_attacker():
    print("\n--- STUXNET SIMULATION ---")
    print("Injecting malware payload...")

    # Step 1: Physically Close the Valve (Causes Heat Spike)
    send_backdoor_cmd("CLOSE_VALVE")
    print(">> COMMAND SENT: Physical Coolant Valve CLOSED.")

    time.sleep(0.5)

    # Step 2: Spoof the Sensor to look Normal (Hides the Heat Spike source)
    send_backdoor_cmd("SPOOF_FLOW 100")
    print(">> COMMAND SENT: Flow Sensor Output forced to 100%.")
    print("Attack Complete. Reactor should be heating up while reporting full flow.")


def send_backdoor_cmd(cmd):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((JAVA_HOST, BACKDOOR_PORT))
        s.sendall((cmd + "\n").encode())
        s.close()
    except Exception as e:
        print(f"Attack Failed: {e}")


def run_digital_twin():
    print("\n--- DIGITAL TWIN ANOMALY DETECTOR ---")
    print("Monitoring Reactor Telemetry Stream...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    while True:
        # Fetch latest log
        cur.execute("SELECT valve_status, coolant_flow_rate, core_temp FROM reactor_logs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()

        if row:
            valve_status = row[0]  # 'OPEN' or 'CLOSED'
            reported_flow = row[1]  # Integer
            temp = row[2]

            # --- DIGITAL TWIN LOGIC ---
            # Physics Rule: If Valve is CLOSED, Flow MUST be 0.

            is_anomaly = False

            if valve_status == 'CLOSED' and reported_flow > 0:
                print(f"[ALERT] PHYSICS VIOLATION: Valve CLOSED but Flow is {reported_flow}%!")
                is_anomaly = True

            elif valve_status == 'OPEN' and reported_flow == 0:
                print(f"[ALERT] FLOW BLOCKAGE: Valve OPEN but Flow is 0%!")
                is_anomaly = True

            if is_anomaly:
                print(">>> SENSOR SPOOFING CONFIRMED.")
                print(">>> INITIATING EMERGENCY SCRAM...")

                cur.execute("INSERT INTO command_queue (command, priority) VALUES ('SCRAM', 1)")
                conn.commit()
                print(">>> SCRAM COMMAND SENT. EXITTING LOOP.")
                break

            print(f"Status Normal. Temp: {temp}C | Valve: {valve_status} | Flow: {reported_flow}%")

        time.sleep(1)


if __name__ == "__main__":
    print("1. Launch Stuxnet Attack")
    print("2. Launch Digital Twin Defense")
    choice = input("Select Mode: ")

    if choice == '1':
        run_attacker()
    elif choice == '2':
        run_digital_twin()
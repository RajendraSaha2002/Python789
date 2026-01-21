import socket
import threading
import json
import time
import requests
import random
from datetime import datetime

# --- Configuration ---
BIND_IP = '0.0.0.0'
BIND_PORT = 2222  # We use 2222 to avoid needing Root for port 22
BANNER = b"\n*** WARNING: RESTRICTED ACCESS ***\n*** UNAUTHORIZED ACCESS IS PROHIBITED ***\n*** SCADA CONTROL SYSTEM V4.2 ***\n\n"
LOG_FILE = "evidences.json"

# --- Fake File System (The Deception) ---
FAKE_FS = {
    "reactor_core.conf": "CORE_TEMP_MAX=4000\nCOOLANT_FLOW=ENABLED\nFAILSAFE=ACTIVE",
    "passwords.txt": "admin:Hunter2\nroot:toor\nengineer:123456",
    "network_map.png": "[BINARY DATA CORRUPTED]",
    "readme.msg": "Don't forget to rotate the keys every 24h. -Sysadmin"
}


# --- 1. Intelligence Module (The "Origin Tracer") ---

class IntelGatherer:
    @staticmethod
    def get_ip_info(ip_address):
        """
        Queries a GeoIP API to find the physical location of the hacker.
        """
        # If localhost, simulate a threat for demonstration
        if ip_address in ["127.0.0.1", "localhost"]:
            return {
                "status": "success",
                "country": "Simulated Country (Arstotzka)",
                "city": "Grestin",
                "isp": "Ministry of Information",
                "lat": 0.0,
                "lon": 0.0,
                "query": ip_address
            }

        try:
            # Real lookup
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            return response.json()
        except Exception as e:
            return {"status": "fail", "message": str(e)}


# --- 2. Evidence Logger ---

class EvidenceLocker:
    def __init__(self):
        self.lock = threading.Lock()

    def log_event(self, session_id, event_type, data):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "type": event_type,
            "data": data
        }

        # 1. Print to Console (The War Room View)
        prefix = f"[{event_type.upper()}]"
        print(f"{prefix.ljust(10)} | {data}")

        # 2. Save to File
        with self.lock:
            try:
                with open(LOG_FILE, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"Logging Error: {e}")


# Global Logger Instance
EVIDENCE = EvidenceLocker()


# --- 3. The Honeypot Logic (The Session) ---

class HoneypotSession(threading.Thread):
    def __init__(self, client_sock, address):
        super().__init__()
        self.client = client_sock
        self.ip = address[0]
        self.port = address[1]
        self.session_id = f"SESS-{random.randint(1000, 9999)}"
        self.username = None
        self.prompt = b"$ "

    def run(self):
        # 1. Intel Gathering
        print(f"\n--- NEW CONNECTION DETECTED [{self.session_id}] ---")
        intel = IntelGatherer.get_ip_info(self.ip)

        if intel.get("status") == "success":
            geo_info = f"Origin: {intel.get('city')}, {intel.get('country')} | ISP: {intel.get('isp')}"
            EVIDENCE.log_event(self.session_id, "INTEL", f"INTRUDER IDENTIFIED: {self.ip} -> {geo_info}")
        else:
            EVIDENCE.log_event(self.session_id, "INTEL", f"Connection from {self.ip} (GeoIP Failed)")

        try:
            # 2. Login Simulation
            self.client.send(BANNER)

            # Username
            self.client.send(b"login as: ")
            self.username = self.read_line().strip()
            EVIDENCE.log_event(self.session_id, "AUTH", f"Username attempted: {self.username}")

            # Password (Fake verification - accept anything)
            self.client.send(b"password: ")
            password = self.read_line().strip()  # We don't echo password back
            EVIDENCE.log_event(self.session_id, "AUTH", f"Password attempted: {password}")

            # Simulate processing delay
            time.sleep(1.5)
            self.client.send(b"\nAccess Granted. Welcome to SCADA_CORE_SYSTEM.\n")
            self.client.send(
                b"Last login: " + datetime.now().strftime("%a %b %d %H:%M:%S").encode() + b" from 192.168.1.10\n\n")

            self.prompt = f"{self.username}@scada-node-04:~$ ".encode()

            # 3. Interactive Shell
            while True:
                self.client.send(self.prompt)
                cmd = self.read_line().strip()

                if not cmd: continue

                EVIDENCE.log_event(self.session_id, "SHELL", f"Command: {cmd}")

                response = self.process_command(cmd)
                if response == "EXIT":
                    break

                if response:
                    self.client.send(response + b"\n")

        except Exception as e:
            # Connection lost
            pass
        finally:
            EVIDENCE.log_event(self.session_id, "NET", "Connection Closed.")
            self.client.close()

    def read_line(self):
        """Reads data byte-by-byte until newline."""
        buf = b""
        while True:
            chunk = self.client.recv(1)
            if not chunk: raise ConnectionError("Client disconnected")

            # Handle backspace (simple)
            if chunk == b'\x08' or chunk == b'\x7f':
                if len(buf) > 0:
                    buf = buf[:-1]
                    # Erase char from client terminal
                    self.client.send(b'\x08 \x08')
                continue

            # Echo back to client (like a real terminal)
            # Don't echo if reading password? (Simplified here: we rely on client behavior mostly)
            # Actually, standard telnet/netcat expects echo.
            self.client.send(chunk)

            if chunk == b'\n' or chunk == b'\r':
                return buf.decode('utf-8', errors='ignore')
            buf += chunk

    def process_command(self, cmd):
        """Emulates a Linux shell."""
        parts = cmd.split()
        base = parts[0].lower()

        if base == "ls":
            # List fake files
            files = list(FAKE_FS.keys())
            return ("  ".join(files)).encode()

        elif base == "cat":
            if len(parts) < 2:
                return b"Usage: cat <filename>"
            filename = parts[1]
            if filename in FAKE_FS:
                return FAKE_FS[filename].encode()
            else:
                return f"cat: {filename}: No such file or directory".encode()

        elif base == "pwd":
            return b"/home/admin/secure_storage"

        elif base == "whoami":
            return self.username.encode()

        elif base == "id":
            return b"uid=0(root) gid=0(root) groups=0(root)"

        elif base == "help":
            return b"Available commands: ls, cat, pwd, whoami, id, exit, help"

        elif base == "exit":
            return "EXIT"

        else:
            return f"{base}: command not found".encode()


# --- 4. The Server ---

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((BIND_IP, BIND_PORT))
        server.listen(5)

        print("\n" + "=" * 50)
        print(f"HONEYPOT ACTIVE: {BIND_IP}:{BIND_PORT}")
        print("Waiting for intruders...")
        print("=" * 50 + "\n")

        while True:
            client, addr = server.accept()
            # Spawn a thread for the intruder
            handler = HoneypotSession(client, addr)
            handler.start()

    except KeyboardInterrupt:
        print("\n[!] Shutting down Honeypot.")
    except Exception as e:
        print(f"\n[!] Critical Error: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
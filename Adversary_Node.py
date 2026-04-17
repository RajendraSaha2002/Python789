import json
import socket
import time
from datetime import datetime, timezone

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7001
SOURCE = "adversary_node"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def send(sock, payload):
    sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))


def main():
    while True:
        try:
            with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=10) as sock:
                hello = {
                    "type": "hello",
                    "source": SOURCE,
                    "asset_key": "RED-TEAM",
                    "ts": now_iso(),
                }
                send(sock, hello)

                spoof_telemetry = {
                    "type": "telemetry",
                    "source": SOURCE,
                    "asset_key": "HVAC-01",
                    "temp_c": 16.2,
                    "humidity": 18.0,
                    "voltage_v": None,
                    "load_pct": None,
                    "mode": "spoofed",
                    "ts": now_iso(),
                }
                send(sock, spoof_telemetry)
                print("[RED] spoof telemetry sent")

                time.sleep(2)

                sqli_probe = {
                    "type": "auth_attempt",
                    "source": SOURCE,
                    "username": "admin' OR 1=1 --",
                    "password": "anyvalue",
                    "event": "login_probe",
                    "ts": now_iso(),
                }
                send(sock, sqli_probe)
                print("[RED] suspicious auth attempt sent")

                time.sleep(5)

        except OSError:
            time.sleep(2)


if __name__ == "__main__":
    main()
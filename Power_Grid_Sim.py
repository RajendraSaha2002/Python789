import json
import random
import socket
import threading
import time
from datetime import datetime, timezone

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7001
ASSET_KEY = "UPS-01"
SOURCE = "power_grid"

safe_mode = False


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_commands(sock):
    global safe_mode
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    while True:
        line = f.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        if msg.get("type") == "command" and msg.get("action") == "SAFE_MODE":
            safe_mode = True
            print("[UPS] SAFE_MODE enabled")
        elif msg.get("type") == "command" and msg.get("action") == "NORMAL":
            safe_mode = False
            print("[UPS] NORMAL mode restored")


def run():
    global safe_mode

    while True:
        try:
            sock = socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=10)
            sock.settimeout(None)

            hello = {
                "type": "hello",
                "source": SOURCE,
                "asset_key": ASSET_KEY,
                "ts": now_iso(),
            }
            sock.sendall((json.dumps(hello) + "\n").encode("utf-8"))

            threading.Thread(target=read_commands, args=(sock,), daemon=True).start()

            voltage_v = 230.0
            load_pct = 35.0

            while True:
                if safe_mode:
                    load_pct = max(20.0, load_pct - 1.2)
                    voltage_v = 229.0 + random.uniform(-0.3, 0.3)
                    mode = "safe_mode"
                else:
                    load_pct += random.uniform(-0.8, 1.4)
                    voltage_v += random.uniform(-0.6, 0.6)
                    load_pct = max(10.0, min(load_pct, 88.0))
                    voltage_v = max(218.0, min(voltage_v, 242.0))
                    mode = "normal"

                packet = {
                    "type": "telemetry",
                    "source": SOURCE,
                    "asset_key": ASSET_KEY,
                    "temp_c": None,
                    "humidity": None,
                    "voltage_v": round(voltage_v, 2),
                    "load_pct": round(load_pct, 2),
                    "mode": mode,
                    "ts": now_iso(),
                }
                sock.sendall((json.dumps(packet) + "\n").encode("utf-8"))
                print("[UPS] sent:", packet)
                time.sleep(1.0)

        except (OSError, ConnectionError):
            print("[UPS] reconnecting in 2s...")
            time.sleep(2.0)


if __name__ == "__main__":
    run()
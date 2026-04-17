import json
import random
import socket
import threading
import time
from datetime import datetime, timezone

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7001
ASSET_KEY = "HVAC-01"
SOURCE = "cooling_unit"

safe_mode = False


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_packet(temp_c, humidity, mode):
    return {
        "type": "telemetry",
        "source": SOURCE,
        "asset_key": ASSET_KEY,
        "temp_c": round(temp_c, 2),
        "humidity": round(humidity, 2),
        "voltage_v": None,
        "load_pct": None,
        "mode": mode,
        "ts": now_iso(),
    }


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
            print("[HVAC] SAFE_MODE enabled")
        elif msg.get("type") == "command" and msg.get("action") == "NORMAL":
            safe_mode = False
            print("[HVAC] NORMAL mode restored")


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

            temp_c = 25.0
            humidity = 45.0

            while True:
                if safe_mode:
                    temp_c = max(18.0, temp_c - 0.8)
                    humidity = min(42.0, humidity - 0.3)
                    mode = "safe_mode"
                else:
                    temp_c += random.uniform(0.1, 0.7)
                    humidity += random.uniform(-0.4, 0.6)
                    temp_c = min(temp_c, 36.5)
                    humidity = max(30.0, min(humidity, 60.0))
                    mode = "normal"

                packet = make_packet(temp_c, humidity, mode)
                sock.sendall((json.dumps(packet) + "\n").encode("utf-8"))
                print("[HVAC] sent:", packet)
                time.sleep(1.0)

        except (OSError, ConnectionError):
            print("[HVAC] reconnecting in 2s...")
            time.sleep(2.0)


if __name__ == "__main__":
    run()
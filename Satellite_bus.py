import socket, json, time, random


def run():
    print("[SAT-1] Initializing ADCS Telemetry...")
    # Waits for Java container to boot
    time.sleep(5)

    lat = 0.0
    lon = -180.0

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 9090))

                while True:
                    lon += 2.0
                    if lon > 180: lon = -180
                    lat = 45 * random.uniform(0.95, 1.05)

                    payload = {"lat": lat, "lon": lon}
                    s.sendall((json.dumps(payload) + '\n').encode('utf-8'))
                    time.sleep(1)
        except Exception as e:
            print(f"[SAT-1] Link dropped. Reconnecting... {e}")
            time.sleep(2)


if __name__ == "__main__":
    run()
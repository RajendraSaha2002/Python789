import socket, json, time


def test_docker_isolation():
    """Attempting Command Injection directly to the Postgres Container"""
    print("[RED TEAM] Attempting to bypass Java C2 and hit PostgreSQL directly...")
    try:
        # This WILL fail because port 5432 is not exposed to the python container properly
        # or we lack credentials, proving Docker network isolation works.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('mission_historian', 5432))
        print("[RED TEAM] WARNING: Database is accessible!")
    except:
        print("[RED TEAM] BLOCKED: Docker Network Isolation prevented direct DB access.")


def tle_spoofing_attack():
    print("[RED TEAM] Launching TLE Spoofing Attack on Java C2...")
    time.sleep(10)  # Wait for normal sat to establish orbit

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 9090))
                # Send massive coordinate jumps to trigger the Neon Orange IDS alert
                payload = {"lat": 85.0, "lon": 150.0}
                s.sendall((json.dumps(payload) + '\n').encode('utf-8'))
                time.sleep(1)

                payload = {"lat": -85.0, "lon": -150.0}
                s.sendall((json.dumps(payload) + '\n').encode('utf-8'))
                time.sleep(1)
        except:
            time.sleep(2)


if __name__ == "__main__":
    time.sleep(8)
    test_docker_isolation()
    tle_spoofing_attack()
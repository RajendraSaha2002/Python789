import socket, json, time, random, threading, sys


def listen_for_kill(sock):
    f = sock.makefile('r')
    while True:
        line = f.readline()
        if "SYS_EXIT" in line:
            print("\n[HACKER TERMINAL] C2 Server killed our connection! Evading...")
            sys.exit(0)


def run():
    print("--- ADVANCED PERSISTENT THREAT: CRYPTOJACKING INJECTOR ---")
    time.sleep(3)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 7070))
    threading.Thread(target=listen_for_kill, args=(s,), daemon=True).start()

    print("[ATTACK] Injecting Monero Miner into Idle Node: NODE_02")
    t_ambient = 25.0
    k = 0.8  # Hacker runs unoptimized code, generating more heat!

    while True:
        cpu_load = 99.9  # Maxing out the CPU for mining
        temperature = t_ambient + (k * cpu_load)

        payload = {
            "node_id": "NODE_02",
            "cpu_load": round(cpu_load, 2),
            "temp": round(temperature, 2),
            "proc_id": "xmrig_miner.exe"
        }

        # FIX: Compress the JSON to remove spaces so Java can parse it perfectly!
        compressed_json = json.dumps(payload, separators=(',', ':'))
        s.sendall((compressed_json + '\n').encode('utf-8'))

        time.sleep(1)


if __name__ == "__main__":
    run()
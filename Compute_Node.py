import socket, json, time, random, threading, sys


def listen_for_kill(sock):
    f = sock.makefile('r')
    while True:
        line = f.readline()
        if "SYS_EXIT" in line:
            print("\n[SYSTEM] Remote Kill Command Received! Shutting down process.")
            sys.exit(0)


def run():
    print("--- HPC COMPUTE NODE 01 (AUTHORIZED JOB) ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 7070))
    threading.Thread(target=listen_for_kill, args=(s,), daemon=True).start()

    t_ambient = 25.0
    k = 0.5  # Thermal coefficient

    while True:
        cpu_load = random.uniform(85.0, 95.0)  # Normal high HPC load
        temperature = t_ambient + (k * cpu_load)  # T = T_ambient + k * P_load

        payload = {
            "node_id": "NODE_01",
            "cpu_load": round(cpu_load, 2),
            "temp": round(temperature, 2),
            "proc_id": "physics_sim.exe"
        }

        # FIX: Compress the JSON to remove spaces so Java can parse it perfectly!
        compressed_json = json.dumps(payload, separators=(',', ':'))
        s.sendall((compressed_json + '\n').encode('utf-8'))

        time.sleep(1)


if __name__ == "__main__":
    run()
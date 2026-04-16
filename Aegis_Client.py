import socket
import json
import time
import threading
import random

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9999


def send_packet(payload):
    """Native socket packet injection"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.sendall((json.dumps(payload) + '\n').encode('utf-8'))
    except ConnectionRefusedError:
        pass


def normal_player_sim():
    """Simulates a legitimate player playing by the rules"""
    print("[CLIENT] Normal player logging in...")
    x, y = 0.0, 0.0
    for _ in range(5):
        time.sleep(1.5)  # Normal pacing
        x += random.uniform(1.0, 5.0)  # Moves within legal limits (< 20)
        y += random.uniform(1.0, 5.0)
        send_packet({"player_id": "Player_Normal", "action": "MOVE", "x": x, "y": y})


def teleport_hack_sim():
    """Exploit 1: Packet Manipulation (Teleportation)"""
    print("[RED TEAM] Injecting Modified Packet (Teleport Hack)...")
    time.sleep(2)
    # Jumps 500 units instantly (violates server physics engine)
    send_packet({"player_id": "Player_Hacker", "action": "MOVE", "x": 500.0, "y": 500.0})


def economy_hack_sim():
    """Exploit 2: Memory/API Injection (5000 Gems)"""
    print("[RED TEAM] Exploiting Economy API (Injecting 5000 Gems)...")
    time.sleep(4)
    # Bypasses client UI to directly call an unauthorized gem injection
    send_packet({"player_id": "Player_Hacker", "action": "INJECT_GEMS", "amount": 5000})


def bot_spammer_sim():
    """Exploit 3: Automated Gold Farming Bot"""
    print("[RED TEAM] Launching Bot Spammer (Rate Limit Evasion)...")
    time.sleep(6)
    # Sends 20 actions in less than a second (triggers Bot detection)
    for _ in range(20):
        send_packet({"player_id": "Player_Bot", "action": "MINE"})
        time.sleep(0.01)


def ddos_stress_test():
    """Exploit 4: TCP Connection Flood (DDoS)"""
    print("[RED TEAM] Launching Connection Flood (DDoS)...")
    time.sleep(8)

    def flood():
        for _ in range(50):
            send_packet({"player_id": "NULL", "action": "HANDSHAKE_FLOOD"})

    # Launch 5 concurrent threads blasting the server
    threads = [threading.Thread(target=flood) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()


if __name__ == "__main__":
    print("--- AEGIS-GAMENET ADVERSARY SUITE ---")

    # Run attack vectors concurrently
    threading.Thread(target=normal_player_sim).start()
    threading.Thread(target=teleport_hack_sim).start()
    threading.Thread(target=economy_hack_sim).start()
    threading.Thread(target=bot_spammer_sim).start()
    threading.Thread(target=ddos_stress_test).start()
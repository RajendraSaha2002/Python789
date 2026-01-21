import sys
import socket
import threading
import json
import time
import random
import uuid
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QTextEdit, QGroupBox, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QColor, QFont

from cryptography.fernet import Fernet

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 4444  # Typical Metasploit/C2 port
HEARTBEAT_INTERVAL = 3.0  # Bots ping every 3s
TIMEOUT_THRESHOLD = 8.0  # Mark dead if no ping for 8s


# --- Crypto Engine ---

class CryptoHandler:
    """
    Simulates the shared secret between the Hacker and the Malware.
    """

    def __init__(self):
        # In a real scenario, this key is hardcoded in the malware binary
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data_dict):
        """Encrypts a dictionary payload."""
        json_str = json.dumps(data_dict)
        return self.cipher.encrypt(json_str.encode('utf-8'))

    def decrypt(self, token):
        """Decrypts bytes to a dictionary."""
        try:
            json_bytes = self.cipher.decrypt(token)
            return json.loads(json_bytes.decode('utf-8'))
        except Exception:
            return None


# Shared Key Instance
CRYPTO = CryptoHandler()


# --- Server Logic (The Puppet Master) ---

class C2Server(QThread):
    log_signal = pyqtSignal(str)
    bot_update_signal = pyqtSignal(str, str, float)  # ID, IP, LastSeen

    def __init__(self):
        super().__init__()
        self.running = True
        self.clients = []  # List of socket objects
        self.bot_registry = {}  # {uuid: {'ip': str, 'last_seen': float, 'status': 'ONLINE'}}

    def run(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((HOST, PORT))
        self.server_sock.listen(10)
        self.log_signal.emit(f"[SERVER] Listening on {HOST}:{PORT} (AES-256 Encrypted)")

        while self.running:
            try:
                conn, addr = self.server_sock.accept()
                self.clients.append(conn)
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            except OSError:
                break

    def handle_client(self, conn, addr):
        """Handles incoming traffic from a single bot."""
        bot_id = "UNKNOWN"
        try:
            while self.running:
                # Receive Encrypted Data
                data = conn.recv(4096)
                if not data: break

                # Decrypt
                payload = CRYPTO.decrypt(data)

                if payload:
                    msg_type = payload.get('type')
                    bot_id = payload.get('id')

                    if msg_type == 'HEARTBEAT':
                        # Update Last Seen
                        self.bot_update_signal.emit(bot_id, str(addr), time.time())

                    elif msg_type == 'RESULT':
                        # Bot finished a task
                        status = payload.get('status')
                        self.log_signal.emit(f"[BOT-{bot_id[:4]}] >> {status}")
                else:
                    self.log_signal.emit(f"[SERVER] WARN: Received unreadable/garbage data from {addr}")

        except Exception as e:
            pass
        finally:
            if conn in self.clients: self.clients.remove(conn)
            conn.close()

    def broadcast_command(self, cmd_str):
        """Encrypts and sends a command to ALL connected bots."""
        if not self.clients:
            self.log_signal.emit("[SERVER] No bots connected.")
            return

        payload = {
            'type': 'COMMAND',
            'cmd': cmd_str,
            'timestamp': time.time()
        }
        encrypted_token = CRYPTO.encrypt(payload)

        count = 0
        for client in self.clients:
            try:
                client.send(encrypted_token)
                count += 1
            except:
                pass
        self.log_signal.emit(f"[SERVER] Broadcast '{cmd_str}' sent to {count} bots.")

    def stop(self):
        self.running = False
        if self.server_sock: self.server_sock.close()


# --- Client Logic (The Zombie Bot) ---

class BotClient(QThread):
    """
    Simulates an infected machine.
    Runs in background, maintains persistence, executes commands.
    """
    log_signal = pyqtSignal(str)  # Local debug log for the simulation

    def __init__(self):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.running = True
        self.sock = None
        self.connected = False

    def run(self):
        while self.running:
            try:
                if not self.connected:
                    self.connect_to_c2()

                # Main Loop
                while self.connected and self.running:
                    # 1. Send Heartbeat (Ping)
                    self.send_heartbeat()

                    # 2. Listen for Commands (Non-blocking check would be better,
                    # but for this sim thread, blocking recv with timeout is fine)
                    self.sock.settimeout(HEARTBEAT_INTERVAL)
                    try:
                        data = self.sock.recv(4096)
                        if not data:
                            self.connected = False
                            break

                        # Decrypt Command
                        payload = CRYPTO.decrypt(data)
                        if payload and payload['type'] == 'COMMAND':
                            self.execute_command(payload['cmd'])

                    except socket.timeout:
                        pass  # Just loop back to heartbeat
                    except Exception:
                        self.connected = False

            except Exception as e:
                self.log_signal.emit(f"[BOT-{self.id[:4]}] Connection Err: {e}. Retrying...")
                time.sleep(2)  # Retry delay

    def connect_to_c2(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))
        self.connected = True
        self.log_signal.emit(f"[BOT-{self.id[:4]}] Connected to C2 Server.")

    def send_heartbeat(self):
        payload = {'type': 'HEARTBEAT', 'id': self.id}
        token = CRYPTO.encrypt(payload)
        self.sock.send(token)

    def execute_command(self, cmd_text):
        self.log_signal.emit(f"[BOT-{self.id[:4]}] EXECUTING: {cmd_text}")

        # Simulate work
        time.sleep(0.5)

        # Report Result
        result = {'type': 'RESULT', 'id': self.id, 'status': f"Executed: {cmd_text}"}
        self.sock.send(CRYPTO.encrypt(result))

    def kill(self):
        self.running = False
        if self.sock: self.sock.close()
        self.log_signal.emit(f"[BOT-{self.id[:4]}] TERMINATED.")


# --- Main GUI ---

class C2Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APTV-42 C2 DASHBOARD (SIMULATION)")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: #00FF00; font-family: Consolas; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QTableWidget { background-color: #1a1a1a; gridline-color: #333; color: #DDD; }
            QHeaderView::section { background-color: #333; color: white; }
            QLineEdit { background-color: #222; color: #0F0; border: 1px solid #444; padding: 5px; }
            QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QPushButton:hover { background-color: #444; border: 1px solid #0F0; }
        """)

        self.bots = []  # List of active BotClient threads
        self.bot_db = {}  # {id: {'ip': str, 'last_seen': float}}

        self.server = C2Server()
        self.server.log_signal.connect(self.log_server)
        self.server.bot_update_signal.connect(self.update_bot_status)
        self.server.start()

        self.init_ui()

        # Watchdog Timer (Checks for dead bots)
        self.watchdog = QTimer()
        self.watchdog.timeout.connect(self.check_dead_bots)
        self.watchdog.start(1000)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: SERVER CONTROL ---
        server_panel = QVBoxLayout()

        # 1. Bot Table
        grp_bots = QGroupBox("ACTIVE ZOMBIES (BOTNET)")
        b_layout = QVBoxLayout(grp_bots)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["BOT ID", "IP ADDRESS", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        b_layout.addWidget(self.table)

        server_panel.addWidget(grp_bots)

        # 2. Command Center
        grp_cmd = QGroupBox("COMMAND SHELL")
        c_layout = QVBoxLayout(grp_cmd)

        self.inp_cmd = QLineEdit()
        self.inp_cmd.setPlaceholderText("Enter Command (e.g., DDOS ip=192.168.1.5)")
        self.inp_cmd.returnPressed.connect(self.send_command)
        c_layout.addWidget(self.inp_cmd)

        btn_send = QPushButton("BROADCAST EXECUTE")
        btn_send.setStyleSheet("background-color: #D32F2F; font-weight: bold;")
        btn_send.clicked.connect(self.send_command)
        c_layout.addWidget(btn_send)

        server_panel.addWidget(grp_cmd)

        # 3. Server Log
        self.txt_server_log = QTextEdit()
        self.txt_server_log.setReadOnly(True)
        self.txt_server_log.setStyleSheet("background-color: #000; color: #0F0; font-size: 10px;")
        server_panel.addWidget(self.txt_server_log)

        layout.addLayout(server_panel, 60)

        # --- RIGHT: SIMULATION CONTROL ---
        sim_panel = QVBoxLayout()

        grp_sim = QGroupBox("INFECTION SIMULATOR")
        s_layout = QVBoxLayout(grp_sim)

        btn_spawn = QPushButton("SPAWN NEW BOT")
        btn_spawn.clicked.connect(self.spawn_bot)
        s_layout.addWidget(btn_spawn)

        btn_kill = QPushButton("KILL RANDOM BOT")
        btn_kill.clicked.connect(self.kill_bot)
        s_layout.addWidget(btn_kill)

        sim_panel.addWidget(grp_sim)

        # Global Log (What the bots see)
        grp_global = QGroupBox("GLOBAL TRAFFIC SNIFFER")
        g_layout = QVBoxLayout(grp_global)
        self.txt_global_log = QTextEdit()
        self.txt_global_log.setReadOnly(True)
        self.txt_global_log.setStyleSheet(
            "background-color: #111; color: #AAA; font-family: monospace; font-size: 10px;")
        g_layout.addWidget(self.txt_global_log)

        sim_panel.addWidget(grp_global)

        layout.addLayout(sim_panel, 40)

    # --- Server Logic ---

    def log_server(self, msg):
        self.txt_server_log.append(msg)

    def log_global(self, msg):
        self.txt_global_log.append(msg)

    def send_command(self):
        cmd = self.inp_cmd.text()
        if not cmd: return
        self.server.broadcast_command(cmd)
        self.inp_cmd.clear()

    def update_bot_status(self, bot_id, ip, last_seen):
        # Update Internal DB
        self.bot_db[bot_id] = {'ip': ip, 'last_seen': last_seen, 'status': 'ONLINE'}
        self.refresh_table()

    def check_dead_bots(self):
        now = time.time()
        changed = False
        for bid, data in self.bot_db.items():
            if data['status'] == 'ONLINE':
                if now - data['last_seen'] > TIMEOUT_THRESHOLD:
                    data['status'] = 'OFFLINE'
                    changed = True

        if changed:
            self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for bid, data in self.bot_db.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(bid[:8]))

            # IP
            self.table.setItem(row, 1, QTableWidgetItem(data['ip']))

            # Status
            stat = data['status']
            item = QTableWidgetItem(stat)

            if stat == 'ONLINE':
                item.setForeground(QColor("#00FF00"))
                item.setBackground(QColor("#003300"))
            else:
                item.setForeground(QColor("#555555"))  # Gray
                item.setBackground(QColor("#111111"))

            self.table.setItem(row, 2, item)

    # --- Simulation Logic ---

    def spawn_bot(self):
        bot = BotClient()
        bot.log_signal.connect(self.log_global)
        bot.start()
        self.bots.append(bot)

    def kill_bot(self):
        if self.bots:
            # Find a running bot
            alive = [b for b in self.bots if b.running]
            if alive:
                victim = random.choice(alive)
                victim.kill()
                # We don't remove from list immediately to let logic play out
                self.log_global(f"[SIM] Bot {victim.id[:4]} process killed.")
            else:
                self.log_global("[SIM] No active bots to kill.")

    def closeEvent(self, event):
        self.server.stop()
        for b in self.bots: b.kill()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = C2Dashboard()
    window.show()
    sys.exit(app.exec_())
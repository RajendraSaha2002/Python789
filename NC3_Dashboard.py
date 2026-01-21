import sys
import socket
import threading
import json
import time
import random
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QGridLayout, QFrame, QMessageBox, QGroupBox,
                             QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QColor

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 9999
NUM_SILOS = 10


# --- Security Module (RSA Logic) ---

class SecurityModule:
    def __init__(self):
        # Generate keys for the "Command Authority" (Server)
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def generate_eam(self, content):
        """Creates a digitally signed Emergency Action Message."""
        signature = self.private_key.sign(
            content.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return content, signature.hex()

    def verify_eam(self, content, signature_hex):
        """Verifies the EAM signature."""
        try:
            signature = bytes.fromhex(signature_hex)
            self.public_key.verify(
                signature,
                content.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


# Global Security Instance (Shared for this demo script)
SEC_MOD = SecurityModule()


# --- Network Server (The Silo Controller) ---

class NC3Server(QThread):
    log_signal = pyqtSignal(str)
    silo_update = pyqtSignal(list)
    launch_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.clients = []
        self.votes = {}  # {client_addr: timestamp}
        self.silo_states = ["READY"] * NUM_SILOS

        # Simulate some silo issues
        self.silo_states[2] = "MAINTENANCE"
        self.silo_states[7] = "COMM_LOSS"

    def run(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(5)
        self.log_signal.emit(f"[SERVER] NC3 Logic Engine listening on {PORT}")

        # Start a status heartbeat
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.broadcast_status)
        self.heartbeat_timer.start(2000)

        while self.running:
            try:
                client, addr = server_sock.accept()
                self.clients.append(client)
                threading.Thread(target=self.handle_client, args=(client, addr)).start()
            except OSError:
                break

    def handle_client(self, conn, addr):
        self.log_signal.emit(f"[SERVER] Officer connected: {addr}")
        while True:
            try:
                data = conn.recv(1024)
                if not data: break

                msg = json.loads(data.decode('utf-8'))

                if msg['type'] == 'VOTE_LAUNCH':
                    self.process_vote(addr)
                elif msg['type'] == 'REQUEST_EAM':
                    self.send_eam(conn)

            except Exception as e:
                print(f"Client Error: {e}")
                break

        if conn in self.clients: self.clients.remove(conn)
        conn.close()

    def send_eam(self, conn):
        # Generate a random EAM
        code = f"ALPHA-ZULU-{random.randint(1000, 9999)}"
        content, sig = SEC_MOD.generate_eam(code)

        response = {
            'type': 'EAM_DATA',
            'content': content,
            'signature': sig
        }
        conn.send(json.dumps(response).encode('utf-8'))
        self.log_signal.emit(f"[SERVER] EAM Generated: {code}")

    def process_vote(self, addr):
        now = time.time()
        self.votes[addr] = now
        self.log_signal.emit(f"[SERVER] Vote received from {addr}")

        # Check Two-Person Rule
        # Valid if we have 2 distinct votes within 2 seconds
        valid_votes = 0
        for voter, timestamp in list(self.votes.items()):
            if now - timestamp < 2.0:  # 2 Second Window
                valid_votes += 1
            else:
                del self.votes[voter]  # Remove stale votes

        if valid_votes >= 2:
            self.trigger_launch()
        elif valid_votes == 1:
            self.broadcast({'type': 'ALERT', 'msg': 'PARTIAL AUTHORIZATION RECEIVED. AWAITING SECOND KEY.'})

    def trigger_launch(self):
        self.log_signal.emit("[SERVER] *** CRITICAL: LAUNCH SEQUENCE INITIATED ***")
        self.launch_status.emit("LAUNCHING")
        self.broadcast({'type': 'LAUNCH_CONFIRMED'})

        # Update Silos to firing
        for i in range(len(self.silo_states)):
            if self.silo_states[i] == "READY":
                self.silo_states[i] = "FIRING"
        self.broadcast_status()

    def broadcast_status(self):
        msg = {'type': 'SILO_STATUS', 'states': self.silo_states}
        self.broadcast(msg)

    def broadcast(self, msg_dict):
        data = json.dumps(msg_dict).encode('utf-8')
        for c in self.clients:
            try:
                c.send(data)
            except:
                pass


# --- Client GUI (The Launch Control Center) ---

class SiloWidget(QFrame):
    def __init__(self, silo_id):
        super().__init__()
        self.setFixedSize(80, 100)
        self.setStyleSheet("background-color: #222; border: 1px solid #444;")

        layout = QVBoxLayout(self)

        self.lbl_id = QLabel(f"SILO {silo_id}")
        self.lbl_id.setAlignment(Qt.AlignCenter)
        self.lbl_id.setStyleSheet("color: #AAA; font-size: 10px;")

        self.indicator = QLabel()
        self.indicator.setFixedSize(40, 40)
        self.indicator.setStyleSheet("background-color: #333; border-radius: 20px;")

        self.lbl_status = QLabel("OFFLINE")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #555; font-weight: bold; font-size: 10px;")

        layout.addWidget(self.lbl_id)
        layout.addWidget(self.indicator, 0, Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

    def set_state(self, state):
        colors = {
            "READY": ("#00FF00", "READY"),
            "MAINTENANCE": ("#FF0000", "MAINT"),
            "COMM_LOSS": ("#FFAA00", "NO COMM"),
            "FIRING": ("#FFFFFF", "LAUNCH")
        }
        col, text = colors.get(state, ("#333", "UNKNOWN"))

        self.indicator.setStyleSheet(f"background-color: {col}; border-radius: 20px; border: 2px solid #FFF;")
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 10px;")


class OfficerDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NC3: Launch Control Center - STATION A")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #121212; color: #00FF00; font-family: Consolas;")

        self.client_socket = None
        self.eam_verified = False

        self.init_ui()
        self.connect_to_server()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- HEADER ---
        header = QLabel("STRATEGIC AIR COMMAND // LAUNCH CONTROL CENTER")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #FFFFFF; background-color: #333; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # --- EAM PANEL ---
        eam_group = QGroupBox("EMERGENCY ACTION MESSAGE (EAM) AUTHENTICATION")
        eam_group.setStyleSheet("border: 1px solid #444; margin-top: 10px;")
        eam_layout = QHBoxLayout(eam_group)

        self.input_eam = QLineEdit()
        self.input_eam.setPlaceholderText("WAITING FOR TRANSMISSION...")
        self.input_eam.setReadOnly(True)
        self.input_eam.setStyleSheet("background-color: #000; color: #F0F; font-size: 14px; padding: 5px;")

        self.btn_fetch_eam = QPushButton("RECEIVE EAM")
        self.btn_fetch_eam.setStyleSheet("background-color: #004400; color: white; padding: 8px;")
        self.btn_fetch_eam.clicked.connect(self.request_eam)

        self.btn_verify = QPushButton("VALIDATE SIGNATURE")
        self.btn_verify.setStyleSheet("background-color: #444; color: white; padding: 8px;")
        self.btn_verify.clicked.connect(self.validate_eam)
        self.btn_verify.setEnabled(False)

        eam_layout.addWidget(self.input_eam)
        eam_layout.addWidget(self.btn_fetch_eam)
        eam_layout.addWidget(self.btn_verify)
        main_layout.addWidget(eam_group)

        # --- SILO GRID ---
        grid_group = QGroupBox("SQUADRON STATUS")
        grid_layout = QGridLayout(grid_group)

        self.silo_widgets = []
        for i in range(NUM_SILOS):
            w = SiloWidget(i + 1)
            self.silo_widgets.append(w)
            grid_layout.addWidget(w, i // 5, i % 5)

        main_layout.addWidget(grid_group)

        # --- CONTROLS ---
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet("background-color: #222; border-top: 2px solid #555;")
        ctrl_layout = QHBoxLayout(ctrl_frame)

        # Log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #000; font-size: 10px; border: 1px solid #333;")
        ctrl_layout.addWidget(self.log_area, 2)

        # Launch Section
        launch_layout = QVBoxLayout()

        self.chk_partner = QCheckBox("SIMULATE PARTNER KEY")
        self.chk_partner.setStyleSheet("color: #AAA;")
        launch_layout.addWidget(self.chk_partner)

        self.btn_launch = QPushButton("INITIATE LAUNCH SEQUENCE")
        self.btn_launch.setFixedSize(250, 80)
        self.btn_launch.setStyleSheet("""
            QPushButton { background-color: #550000; color: #555; border: 2px solid #333; font-size: 14px; font-weight: bold; border-radius: 10px; }
        """)
        self.btn_launch.setEnabled(False)
        self.btn_launch.clicked.connect(self.send_vote)

        launch_layout.addWidget(self.btn_launch)
        ctrl_layout.addLayout(launch_layout, 1)

        main_layout.addWidget(ctrl_frame)

        # Logic State
        self.current_eam_content = ""
        self.current_eam_sig = ""

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{ts}] {msg}")

    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            self.log("Connected to NC3 Command Loop.")
        except Exception as e:
            self.log(f"Connection Failed: {e}")

    def listen_to_server(self):
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data: break
                msg = json.loads(data.decode('utf-8'))

                if msg['type'] == 'SILO_STATUS':
                    # Must update GUI from main thread?
                    # PyQt signals handle this implicitly if we emit, but here we are in a thread.
                    # For simplicity in this structure, we rely on Python's GIL or safer: QMetaObject.
                    # But direct call works usually in simple Python threads if careful.
                    # Ideally, use signals. Let's assume direct for brevity, if it crashes, use Signal.
                    QThread.msleep(10)  # Yield
                    self.update_silos_safe(msg['states'])

                elif msg['type'] == 'EAM_DATA':
                    self.current_eam_content = msg['content']
                    self.current_eam_sig = msg['signature']
                    self.input_eam.setText(f"ENCRYPTED: {msg['content']}")
                    self.btn_verify.setEnabled(True)
                    self.btn_verify.setStyleSheet("background-color: #D35400; color: white; padding: 8px;")
                    self.log(f"EAM Received: {msg['content']}")

                elif msg['type'] == 'ALERT':
                    self.log(f"⚠️ ALERT: {msg['msg']}")

                elif msg['type'] == 'LAUNCH_CONFIRMED':
                    self.log("🚀 LAUNCH CONFIRMED. MISSILES AWAY.")
                    self.btn_launch.setStyleSheet("background-color: #FFF; color: #F00; border: 3px solid red;")
                    self.btn_launch.setText("LAUNCH IN PROGRESS")

            except Exception as e:
                print(f"Listen Error: {e}")
                break

    def update_silos_safe(self, states):
        # A tiny hack to update UI from thread.
        # In production, use pyqtSignal.
        class Updater(QThread):
            signal = pyqtSignal(list)

            def run(self): self.signal.emit(states)

        u = Updater()
        u.signal.connect(self._update_silos_gui)
        u.start()
        # Keep ref to avoid GC
        self.updater_ref = u

    def _update_silos_gui(self, states):
        for i, state in enumerate(states):
            self.silo_widgets[i].set_state(state)

    def request_eam(self):
        msg = {'type': 'REQUEST_EAM'}
        self.client_socket.send(json.dumps(msg).encode('utf-8'))

    def validate_eam(self):
        if SEC_MOD.verify_eam(self.current_eam_content, self.current_eam_sig):
            self.eam_verified = True
            self.input_eam.setStyleSheet("background-color: #003300; color: #00FF00; font-size: 14px; padding: 5px;")
            self.input_eam.setText(f"VERIFIED: {self.current_eam_content}")
            self.log("EAM Signature Valid. Launch Keys Unlocked.")

            self.btn_launch.setEnabled(True)
            self.btn_launch.setStyleSheet("""
                QPushButton { background-color: #FF0000; color: #FFF; border: 2px solid #FFF; font-size: 14px; font-weight: bold; border-radius: 10px; }
                QPushButton:hover { background-color: #FF4444; }
                QPushButton:pressed { background-color: #AA0000; }
            """)
        else:
            self.log("CRITICAL: EAM Signature Invalid. Spoofing Attempt.")
            QMessageBox.critical(self, "SECURITY ALERT",
                                 "Message Authentication Failed.\nDigital Signature does not match Command Authority.")

    def send_vote(self):
        msg = {'type': 'VOTE_LAUNCH'}
        self.client_socket.send(json.dumps(msg).encode('utf-8'))
        self.log("Key Turned. Waiting for partner...")
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("KEY TURNED")

        # Simulate Partner?
        if self.chk_partner.isChecked():
            QTimer.singleShot(500, self.simulate_partner_vote)

    def simulate_partner_vote(self):
        # We need a separate socket to pretend to be Officer B
        try:
            sock_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_b.connect((HOST, PORT))
            msg = {'type': 'VOTE_LAUNCH'}
            sock_b.send(json.dumps(msg).encode('utf-8'))
            sock_b.close()
            self.log("(Simulated) Partner Key Turned.")
        except:
            self.log("Partner Simulation Failed.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1. Start Server Logic
    server = NC3Server()
    server.start()

    # 2. Start Client Logic
    # Give server a moment
    QThread.msleep(100)
    window = OfficerDashboard()
    window.show()

    sys.exit(app.exec_())
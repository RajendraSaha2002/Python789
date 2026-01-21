import sys
import os
import time
import base64
import random
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QGroupBox, QFrame, QRadioButton, QButtonGroup,
                             QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# --- Cryptography & Key Management ---

class KeyManager:
    """
    Simulates a synchronized crypto-key system.
    Keys rotate every 60 seconds based on the system clock.
    """
    MASTER_SECRET = b"TOP_SECRET_MILITARY_SEED_V1"

    @staticmethod
    def get_key(offset_minutes=0):
        """
        Generates a deterministic key based on the current minute.
        offset_minutes: 0 = Current, -1 = Previous (Expired), etc.
        """
        # Get current time bucket (1 minute resolution)
        timestamp = int(time.time() / 60) + offset_minutes
        seed = KeyManager.MASTER_SECRET + str(timestamp).encode()

        # Derive a 32-byte URL-safe base64 key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'static_salt',  # In real life, salt is exchanged securely
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(seed))
        return key

    @staticmethod
    def encrypt_response(challenge_text, key):
        f = Fernet(key)
        return f.encrypt(challenge_text.encode())

    @staticmethod
    def decrypt_verify(encrypted_response, original_challenge, key):
        try:
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_response).decode()
            return decrypted == original_challenge
        except Exception:
            return False


# --- GUI Application ---

class IFFSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IFF SYSTEM: MODE 5 ENCRYPTION SIMULATOR")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #e0e0e0; font-family: Consolas; }
            QGroupBox { border: 2px solid #444; margin-top: 10px; font-weight: bold; color: #aaa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QPushButton { font-weight: bold; padding: 8px; border-radius: 4px; }
            QLabel { font-size: 12px; }
        """)

        # State
        self.current_challenge = None
        self.radio_air_gap = None  # Stores the transmitted signal

        self.init_ui()

        # Timer to update key clocks
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clocks)
        self.timer.start(1000)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)

        # --- LEFT PANEL: RADAR OPERATOR (INTERROGATOR) ---
        radar_panel = self.create_radar_ui()
        main_layout.addWidget(radar_panel)

        # --- CENTER: THE AIR GAP (Visualizer) ---
        air_panel = self.create_air_ui()
        main_layout.addWidget(air_panel)

        # --- RIGHT PANEL: PILOT (TRANSPONDER) ---
        pilot_panel = self.create_pilot_ui()
        main_layout.addWidget(pilot_panel)

    def create_radar_ui(self):
        frame = QGroupBox("RADAR STATION (INTERROGATOR)")
        frame.setStyleSheet("QGroupBox { border-color: #0d47a1; color: #64b5f6; }")
        layout = QVBoxLayout(frame)

        # Status Display
        self.lbl_target_status = QLabel("TARGET: UNKNOWN")
        self.lbl_target_status.setAlignment(Qt.AlignCenter)
        self.lbl_target_status.setStyleSheet(
            "background-color: #333; color: #FFF; font-size: 18px; font-weight: bold; padding: 15px; border-radius: 5px;")
        layout.addWidget(self.lbl_target_status)

        # Controls
        btn_interrogate = QPushButton("SEND CHALLENGE (INTERROGATE)")
        btn_interrogate.setStyleSheet("background-color: #0d47a1; color: white;")
        btn_interrogate.clicked.connect(self.send_challenge)
        layout.addWidget(btn_interrogate)

        layout.addStretch()

        # Key Info
        self.lbl_radar_time = QLabel("TIME: 00:00:00")
        layout.addWidget(self.lbl_radar_time)

        self.lbl_radar_key = QLabel("CURRENT KEY HASH: ...")
        self.lbl_radar_key.setStyleSheet("color: #64b5f6;")
        layout.addWidget(self.lbl_radar_key)

        return frame

    def create_air_ui(self):
        frame = QFrame()
        frame.setFixedWidth(200)
        frame.setStyleSheet("background-color: #121212; border-left: 1px dashed #444; border-right: 1px dashed #444;")
        layout = QVBoxLayout(frame)

        lbl = QLabel("RF SPECTRUM\n(AIR GAP)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #555; font-weight: bold;")
        layout.addWidget(lbl)

        self.log_air = QTextEdit()
        self.log_air.setReadOnly(True)
        self.log_air.setStyleSheet("border: none; background: transparent; color: #00FF00; font-size: 10px;")
        layout.addWidget(self.log_air)

        return frame

    def create_pilot_ui(self):
        frame = QGroupBox("AIRCRAFT COCKPIT (TRANSPONDER)")
        frame.setStyleSheet("QGroupBox { border-color: #1b5e20; color: #81c784; }")
        layout = QVBoxLayout(frame)

        # Incoming Display
        layout.addWidget(QLabel("INCOMING CHALLENGE:"))
        self.txt_incoming = QLineEdit()
        self.txt_incoming.setReadOnly(True)
        self.txt_incoming.setPlaceholderText("Waiting for Radar...")
        self.txt_incoming.setStyleSheet("background-color: #000; color: #0F0; border: 1px solid #333; padding: 5px;")
        layout.addWidget(self.txt_incoming)

        # Key Selector
        grp_keys = QGroupBox("ENCRYPTION KEY SELECTOR")
        vbox_keys = QVBoxLayout(grp_keys)

        self.key_group = QButtonGroup(self)

        self.rad_correct = QRadioButton("Valid Key (Current Minute)")
        self.rad_correct.setChecked(True)
        self.rad_expired = QRadioButton("Expired Key (Last Minute)")
        self.rad_wrong = QRadioButton("Corrupted/Wrong Key")

        self.key_group.addButton(self.rad_correct)
        self.key_group.addButton(self.rad_expired)
        self.key_group.addButton(self.rad_wrong)

        vbox_keys.addWidget(self.rad_correct)
        vbox_keys.addWidget(self.rad_expired)
        vbox_keys.addWidget(self.rad_wrong)
        layout.addWidget(grp_keys)

        # Respond Button
        self.btn_respond = QPushButton("TRANSMIT RESPONSE")
        self.btn_respond.setStyleSheet("background-color: #1b5e20; color: white;")
        self.btn_respond.setEnabled(False)
        self.btn_respond.clicked.connect(self.send_response)
        layout.addWidget(self.btn_respond)

        layout.addStretch()

        self.lbl_pilot_time = QLabel("COCKPIT CLOCK: 00:00:00")
        layout.addWidget(self.lbl_pilot_time)

        return frame

    # --- SIMULATION LOGIC ---

    def update_clocks(self):
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        # Update Time Labels
        self.lbl_radar_time.setText(f"SYSTEM TIME: {time_str}")
        self.lbl_pilot_time.setText(f"COCKPIT CLOCK: {time_str}")

        # Update Key Hash Visual (Shows rotation)
        # We only show the first few chars to simulate key ID
        current_key = KeyManager.get_key(0)
        key_hash = str(current_key)[2:10]

        seconds = now.second
        secs_left = 60 - seconds

        self.lbl_radar_key.setText(f"KEY ID: {key_hash}... (ROTATES IN {secs_left}s)")

        if secs_left <= 5:
            self.lbl_radar_key.setStyleSheet("color: #FF5555;")  # Warn about rotation
        else:
            self.lbl_radar_key.setStyleSheet("color: #64b5f6;")

    def log(self, sender, message):
        self.log_air.append(f"[{sender}] {message}")
        # Auto scroll
        self.log_air.verticalScrollBar().setValue(self.log_air.verticalScrollBar().maximum())

    def send_challenge(self):
        # 1. Generate Challenge
        self.current_challenge = f"XC9-{random.randint(1000, 9999)}"

        # 2. Log transmission
        self.log("RADAR", f"Ping: {self.current_challenge}")

        # 3. 'Transmit' to Pilot GUI
        self.txt_incoming.setText(self.current_challenge)
        self.btn_respond.setEnabled(True)

        # 4. Reset Status
        self.lbl_target_status.setText("WAITING FOR REPLY...")
        self.lbl_target_status.setStyleSheet(
            "background-color: #AAAA00; color: black; font-weight: bold; padding: 15px; border-radius: 5px;")

    def send_response(self):
        challenge = self.txt_incoming.text()
        if not challenge: return

        # 1. Select Key based on Pilot Choice
        if self.rad_correct.isChecked():
            key = KeyManager.get_key(0)  # Valid
            status_text = "(Valid Key)"
        elif self.rad_expired.isChecked():
            key = KeyManager.get_key(-1)  # Expired
            status_text = "(Expired Key)"
        else:
            key = Fernet.generate_key()  # Totally random/wrong
            status_text = "(Wrong Key)"

        # 2. Encrypt
        try:
            encrypted_token = KeyManager.encrypt_response(challenge, key)

            # 3. Transmit back
            self.log("PILOT", f"Resp: [ENCRYPTED BLOB] {status_text}")
            self.verify_response(encrypted_token)

            # Disable button to prevent spamming
            self.btn_respond.setEnabled(False)
            self.txt_incoming.clear()

        except Exception as e:
            self.log("PILOT", "Encryption Error")

    def verify_response(self, encrypted_token):
        # Radar uses CURRENT Valid Key to decrypt
        valid_key = KeyManager.get_key(0)

        # Artificial delay for drama
        QTimer.singleShot(800, lambda: self._process_verification(encrypted_token, valid_key))

    def _process_verification(self, token, key):
        is_friend = KeyManager.decrypt_verify(token, self.current_challenge, key)

        if is_friend:
            self.lbl_target_status.setText("IFF MODE 5: FRIENDLY")
            self.lbl_target_status.setStyleSheet("""
                background-color: #1b5e20; 
                color: #FFF; 
                font-size: 18px; 
                font-weight: bold; 
                padding: 15px; 
                border: 2px solid #00FF00;
                border-radius: 5px;
            """)
            self.log("SYS", "Identity Confirmed.")
        else:
            self.lbl_target_status.setText("IFF INVALID: HOSTILE")
            self.lbl_target_status.setStyleSheet("""
                background-color: #b71c1c; 
                color: #FFF; 
                font-size: 18px; 
                font-weight: bold; 
                padding: 15px; 
                border: 2px solid #FF0000;
                border-radius: 5px;
            """)
            self.log("SYS", "Decryption Failed / Key Mismatch.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IFFSimulator()
    window.show()
    sys.exit(app.exec_())
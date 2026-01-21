import sys
import os
import random
import hmac
import hashlib
import time
from datetime import datetime

# --- Third-Party Imports ---
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                                 QLabel, QGroupBox, QSlider, QProgressBar, QCheckBox)
    from PyQt5.QtCore import pyqtSignal, QObject, Qt, QThread
    from PyQt5.QtGui import QFont, QColor, QTextCharFormat
    from cryptography.fernet import Fernet
except ImportError:
    print("CRITICAL ERROR: Missing libraries.")
    print("Please run: pip install PyQt5 cryptography")
    sys.exit(1)


# --- Cryptography & Protocol Engine ---

class CryptoEngine:
    def __init__(self):
        # 1. Key Generation (Simulating a Pre-Shared Key - PSK)
        # Fernet uses AES-128 in CBC mode with PKCS7 padding and HMAC-SHA256
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.signing_key = b"military_grade_signing_key_v1"

    def encrypt(self, plaintext):
        """Encrypts text using AES."""
        if not plaintext: return b""
        return self.cipher.encrypt(plaintext.encode('utf-8'))

    def decrypt(self, token):
        """Decrypts token using AES."""
        try:
            return self.cipher.decrypt(token).decode('utf-8')
        except Exception:
            return None  # Decryption failure

    def sign(self, data):
        """Generates HMAC-SHA256 signature for integrity/auth."""
        return hmac.new(self.signing_key, data, hashlib.sha256).digest()

    def verify(self, data, signature):
        """Verifies HMAC signature to detect tampering/spoofing."""
        expected = hmac.new(self.signing_key, data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)


class FECProtocol:
    """
    Forward Error Correction: Repetition Code (Rate 1/3).
    Each byte is sent 3 times. Receiver votes on the correct byte.
    """

    @staticmethod
    def encode(data_bytes):
        # Repeat every byte 3 times
        encoded = bytearray()
        for b in data_bytes:
            encoded.extend([b, b, b])
        return bytes(encoded)

    @staticmethod
    def decode(encoded_bytes):
        # Majority voting logic
        decoded = bytearray()
        errors_fixed = 0

        for i in range(0, len(encoded_bytes), 3):
            chunk = encoded_bytes[i:i + 3]
            if len(chunk) < 3: break  # Incomplete chunk

            # Count occurrences of each byte in the chunk
            # e.g., b'A', b'A', b'B' -> A wins
            votes = {}
            for byte in chunk:
                votes[byte] = votes.get(byte, 0) + 1

            # Get the winner
            winner = max(votes, key=votes.get)
            decoded.append(winner)

            if len(votes) > 1:
                errors_fixed += 1

        return bytes(decoded), errors_fixed


# --- Network Simulation (The "Air Gap") ---

class NetworkWorker(QThread):
    packet_received = pyqtSignal(dict)
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = []
        self.jamming_intensity = 0  # 0 to 100%
        self.running = True

    def send_packet(self, packet):
        self.queue.append(packet)

    def run(self):
        while self.running:
            if self.queue:
                packet = self.queue.pop(0)
                self.process_transmission(packet)
            time.sleep(0.1)

    def process_transmission(self, packet):
        raw_data = bytearray(packet['payload'])
        is_jammed = False

        # --- JAMMING SIMULATION ---
        # Randomly corrupt bits based on intensity
        if self.jamming_intensity > 0:
            noise_level = self.jamming_intensity / 100.0

            for i in range(len(raw_data)):
                if random.random() < noise_level:
                    # Flip bits or randomize byte
                    raw_data[i] = random.randint(0, 255)
                    is_jammed = True

        packet['payload'] = bytes(raw_data)

        if is_jammed:
            self.log_signal.emit(f"[NETWORK] ⚠️ SIGNAL JAMMED: Packet corrupted in transit.")
        else:
            self.log_signal.emit(f"[NETWORK] ✓ Transmission Clear.")

        # Deliver
        time.sleep(0.5)  # Simulate latency
        self.packet_received.emit(packet)


# --- GUI Application ---

class SecureDataLink(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Tactical Data Link (Link-16 Sim)")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; font-family: Consolas, Monospace;")

        # Core Logic
        self.crypto = CryptoEngine()
        self.network = NetworkWorker()
        self.network.packet_received.connect(self.receive_message)
        self.network.log_signal.connect(self.log_network)
        self.network.start()

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- LEFT: COMMAND POST ---
        self.chat_cmd = self.create_chat_panel("COMMAND POST (HQ)", "cmd")
        layout.addLayout(self.chat_cmd, 1)

        # --- CENTER: NETWORK VISUALIZER ---
        center_panel = QVBoxLayout()
        center_panel.setSpacing(10)

        # Title
        lbl = QLabel("ENCRYPTED CHANNEL")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #fab387;")
        center_panel.addWidget(lbl)

        # Log Window
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setStyleSheet("background-color: #11111b; border: 1px solid #45475a; font-size: 10px;")
        center_panel.addWidget(self.log_window, 2)

        # Jamming Controls
        grp_jam = QGroupBox("Electronic Warfare (Jamming)")
        grp_jam.setStyleSheet("border: 1px solid #f38ba8; margin-top: 10px; padding: 10px;")
        vbox_jam = QVBoxLayout()

        self.slider_jam = QSlider(Qt.Horizontal)
        self.slider_jam.setRange(0, 30)  # Max 30% corruption (repetition code limit)
        self.slider_jam.setValue(0)
        self.slider_jam.valueChanged.connect(self.update_jamming)

        self.lbl_jam = QLabel("Noise Level: 0%")

        vbox_jam.addWidget(self.lbl_jam)
        vbox_jam.addWidget(self.slider_jam)
        grp_jam.setLayout(vbox_jam)
        center_panel.addWidget(grp_jam)

        # FEC Status
        self.chk_fec = QCheckBox("Enable Forward Error Correction (FEC)")
        self.chk_fec.setChecked(True)
        center_panel.addWidget(self.chk_fec)

        center_panel.addStretch()
        layout.addLayout(center_panel, 1)

        # --- RIGHT: FIELD UNIT ---
        self.chat_field = self.create_chat_panel("FIELD UNIT (ALPHA)", "field")
        layout.addLayout(self.chat_field, 1)

    def create_chat_panel(self, title, sender_id):
        layout = QVBoxLayout()

        header = QLabel(title)
        header.setStyleSheet("font-weight: bold; font-size: 16px; background-color: #313244; padding: 5px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        display = QTextEdit()
        display.setReadOnly(True)
        display.setStyleSheet("background-color: #181825; border: none;")
        layout.addWidget(display)

        # Store reference for later updates
        if sender_id == "cmd":
            self.display_cmd = display
        else:
            self.display_field = display

        input_box = QLineEdit()
        input_box.setPlaceholderText("Enter secure message...")
        input_box.setStyleSheet("padding: 8px; background-color: #313244; border: 1px solid #45475a;")
        input_box.returnPressed.connect(lambda: self.send_message(sender_id, input_box))
        layout.addWidget(input_box)

        return layout

    def update_jamming(self):
        val = self.slider_jam.value()
        self.network.jamming_intensity = val
        self.lbl_jam.setText(f"Noise Level: {val}%")

    def log_network(self, msg):
        self.log_window.append(msg)

    def log_msg(self, display, sender, text, color="#cdd6f4"):
        display.append(f"<span style='color:{color}'><b>[{sender}]:</b> {text}</span>")

    # --- SENDING LOGIC ---
    def send_message(self, sender_id, input_widget):
        plaintext = input_widget.text()
        if not plaintext: return

        input_widget.clear()

        # 1. Update Sender Display
        sender_name = "CMD" if sender_id == "cmd" else "ALPHA"
        target_display = self.display_cmd if sender_id == "cmd" else self.display_field
        self.log_msg(target_display, "ME", plaintext, "#a6e3a1")  # Green for self

        self.log_window.append(f"\n--- TRANSMISSION START ({sender_name}) ---")

        # 2. Encrypt (AES)
        encrypted_payload = self.crypto.encrypt(plaintext)
        self.log_window.append(f"1. Encrypting: {len(encrypted_payload)} bytes")

        # 3. Sign (HMAC)
        signature = self.crypto.sign(encrypted_payload)
        self.log_window.append(f"2. Signing: HMAC-SHA256 generated")

        # Combine Payload + Signature
        # Format: [Sig Length (1 byte)][Signature][Payload]
        combined_data = len(signature).to_bytes(1, 'big') + signature + encrypted_payload

        # 4. Encode (FEC)
        if self.chk_fec.isChecked():
            final_payload = FECProtocol.encode(combined_data)
            self.log_window.append(f"3. FEC Encoding: Expanded to {len(final_payload)} bytes (3x redundancy)")
        else:
            final_payload = combined_data
            self.log_window.append(f"3. FEC Disabled: Sending raw bytes")

        # 5. Transmit
        packet = {
            'sender': sender_id,
            'payload': final_payload,
            'fec_enabled': self.chk_fec.isChecked()
        }
        self.network.send_packet(packet)

    # --- RECEIVING LOGIC ---
    def receive_message(self, packet):
        sender_id = packet['sender']
        raw_data = packet['payload']
        target_display = self.display_field if sender_id == "cmd" else self.display_cmd
        sender_name = "CMD" if sender_id == "cmd" else "ALPHA"

        self.log_window.append(f"--- RECEIVING ({sender_name}) ---")

        # 1. Decode FEC
        if packet['fec_enabled']:
            decoded_data, errors = FECProtocol.decode(raw_data)
            self.log_window.append(f"1. FEC Decoding: Corrected {errors} byte errors")
        else:
            decoded_data = raw_data
            self.log_window.append(f"1. FEC Skipped")

        # Parse Data
        try:
            sig_len = decoded_data[0]
            signature = decoded_data[1:1 + sig_len]
            encrypted_payload = decoded_data[1 + sig_len:]
        except IndexError:
            self.log_msg(target_display, "SYS", "PACKET MALFORMED (Data Lost)", "#f38ba8")
            return

        # 2. Verify Signature
        if self.crypto.verify(encrypted_payload, signature):
            self.log_window.append(f"2. Integrity Check: PASSED (Signature Valid)")

            # 3. Decrypt
            plaintext = self.crypto.decrypt(encrypted_payload)
            if plaintext:
                self.log_window.append(f"3. Decryption: SUCCESS")
                self.log_msg(target_display, sender_name, plaintext)
            else:
                self.log_msg(target_display, "SYS", "DECRYPTION FAILED", "#f38ba8")
        else:
            self.log_window.append(f"2. Integrity Check: FAILED (Tampering Detected)")
            self.log_msg(target_display, "SYS", "⚠️ AUTHENTICATION ERROR: INVALID SIGNATURE", "#f38ba8")

    def closeEvent(self, event):
        self.network.running = False
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SecureDataLink()
    window.show()
    sys.exit(app.exec_())
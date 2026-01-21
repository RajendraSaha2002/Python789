import sys
import socket
import threading
import json
import time
import pickle
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                             QLabel, QGroupBox, QFrame)
from PyQt5.QtCore import pyqtSignal, QThread, Qt

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.fernet import Fernet

# --- Configuration ---
HOST = '127.0.0.1'
PORTS = [8001, 8002, 8003]  # The Relay Nodes
DEST_PORT = 8004  # The Final Server


# --- Cryptography Utils ---

class CryptoUtils:
    @staticmethod
    def generate_rsa_keys():
        """Generates Private/Public Key Pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()

        # Serialize Public Key to send to directory
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return private_key, pem_public

    @staticmethod
    def encrypt_layer(payload_bytes, node_public_pem):
        """
        Hybrid Encryption:
        1. Generate temporary AES Key (Fernet).
        2. Encrypt Payload with AES.
        3. Encrypt AES Key with Node's RSA Public Key.
        4. Package: [RSA_Enc_AES_Key_Len (4 bytes)] + [RSA_Enc_AES_Key] + [AES_Enc_Payload]
        """
        # Load RSA Key
        public_key = serialization.load_pem_public_key(node_public_pem)

        # Generate AES Key
        aes_key = Fernet.generate_key()
        cipher_suite = Fernet(aes_key)

        # Encrypt Payload (AES)
        encrypted_payload = cipher_suite.encrypt(payload_bytes)

        # Encrypt AES Key (RSA)
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Pack Format: length_of_key_block (4 bytes int) + encrypted_key + encrypted_payload
        key_len = len(encrypted_aes_key)
        packet = key_len.to_bytes(4, 'big') + encrypted_aes_key + encrypted_payload
        return packet

    @staticmethod
    def decrypt_layer(packet_bytes, private_key):
        """
        Peels one layer of the onion.
        Returns: Decrypted Payload Bytes (which might contain the next onion layer).
        """
        try:
            # 1. Parse Packet
            key_len = int.from_bytes(packet_bytes[:4], 'big')
            encrypted_aes_key = packet_bytes[4: 4 + key_len]
            encrypted_payload = packet_bytes[4 + key_len:]

            # 2. Decrypt AES Key (RSA)
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # 3. Decrypt Payload (AES)
            cipher_suite = Fernet(aes_key)
            decrypted_payload = cipher_suite.decrypt(encrypted_payload)

            return decrypted_payload
        except Exception as e:
            print(f"Decryption Error: {e}")
            return None


# --- Networking Components ---

class NodeServer(QThread):
    """
    A Thread that acts as a Node/Server listening on a TCP port.
    It receives data, peels a layer, and forwards it.
    """
    log_signal = pyqtSignal(str, str)  # node_name, message

    def __init__(self, name, port, is_destination=False):
        super().__init__()
        self.name = name
        self.port = port
        self.is_destination = is_destination
        self.private_key, self.public_key_pem = CryptoUtils.generate_rsa_keys()
        self.running = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((HOST, self.port))
            self.sock.listen(5)
            self.log_signal.emit(self.name, f"Listening on {self.port}...")

            while self.running:
                conn, addr = self.sock.accept()
                threading.Thread(target=self.handle_client, args=(conn,)).start()
        except OSError:
            pass

    def handle_client(self, conn):
        try:
            # Receive Data (Chunks)
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                data += chunk

            self.log_signal.emit(self.name, f"Received {len(data)} bytes encrypted blob.")

            # --- THE PEELING PROCESS ---
            if self.is_destination:
                # Final Hop: The data IS the message
                # Note: In real Tor, the last hop is unencrypted or TLS.
                # Here, we assume the Client encrypted the final payload for the Destination too.
                decrypted = CryptoUtils.decrypt_layer(data, self.private_key)
                if decrypted:
                    msg_text = decrypted.decode('utf-8')
                    self.log_signal.emit(self.name, f"🎉 MESSAGE RECEIVED: '{msg_text}'")
                else:
                    self.log_signal.emit(self.name, "❌ Decryption Failed.")
            else:
                # Intermediate Node: Peels layer to reveal Next Hop + Inner Packet
                decrypted_json_bytes = CryptoUtils.decrypt_layer(data, self.private_key)

                if decrypted_json_bytes:
                    # Parse JSON routing info
                    instructions = pickle.loads(decrypted_json_bytes)
                    next_hop_port = instructions['next_hop']
                    inner_packet = instructions['payload']

                    self.log_signal.emit(self.name, f"Layer Peeled. Next Hop -> Port {next_hop_port}")
                    time.sleep(1)  # Visual delay
                    self.forward_packet(next_hop_port, inner_packet)
                else:
                    self.log_signal.emit(self.name, "❌ Decryption/Routing Error.")

        except Exception as e:
            self.log_signal.emit(self.name, f"Error: {e}")
        finally:
            conn.close()

    def forward_packet(self, next_port, packet):
        try:
            self.log_signal.emit(self.name, f"Forwarding {len(packet)} bytes to {next_port}...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, next_port))
            s.sendall(packet)
            s.close()
        except ConnectionRefusedError:
            self.log_signal.emit(self.name, f"❌ Failed to connect to {next_port}")

    def stop(self):
        self.running = False
        self.sock.close()


# --- GUI Application ---

class OnionRouterSim(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Onion Router Simulator (Tor Logic)")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #1a1a1a; color: #00ff00; font-family: monospace;")

        self.nodes = {}  # Store node threads
        self.init_network()
        self.init_ui()

    def init_network(self):
        # Create Nodes
        node_configs = [
            ("Node A", PORTS[0], False),
            ("Node B", PORTS[1], False),
            ("Node C", PORTS[2], False),
            ("Dest D", DEST_PORT, True)
        ]

        for name, port, is_dest in node_configs:
            node = NodeServer(name, port, is_dest)
            node.log_signal.connect(self.log_event)
            self.nodes[name] = node
            node.start()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        header = QLabel("ONION ROUTING VISUALIZER")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Network Diagram (Status Area)
        diagram_box = QGroupBox("Network Status")
        diagram_layout = QHBoxLayout()
        self.status_labels = {}

        for name in self.nodes.keys():
            lbl = QLabel(f"[{name}]\nListening")
            lbl.setStyleSheet("border: 2px solid #00ff00; border-radius: 5px; padding: 10px; color: white;")
            lbl.setAlignment(Qt.AlignCenter)
            diagram_layout.addWidget(lbl)
            self.status_labels[name] = lbl

            if name != "Dest D":
                arrow = QLabel("-->")
                arrow.setAlignment(Qt.AlignCenter)
                diagram_layout.addWidget(arrow)

        diagram_box.setLayout(diagram_layout)
        layout.addWidget(diagram_box)

        # Logs
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #000; border: 1px solid #333;")
        layout.addWidget(self.log_area)

        # Controls
        ctrl_box = QFrame()
        ctrl_layout = QHBoxLayout(ctrl_box)

        self.input_msg = QLineEdit()
        self.input_msg.setPlaceholderText("Enter secret message...")
        self.input_msg.setStyleSheet("padding: 10px; background-color: #333; color: white;")

        btn_send = QPushButton("ENCRYPT & SEND")
        btn_send.setStyleSheet("background-color: #008800; color: white; padding: 10px; font-weight: bold;")
        btn_send.clicked.connect(self.client_send_message)

        ctrl_layout.addWidget(self.input_msg)
        ctrl_layout.addWidget(btn_send)
        layout.addWidget(ctrl_box)

    def log_event(self, node_name, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] <b>{node_name}:</b> {msg}")

        # Highlight active node visually
        # Reset all
        for name, lbl in self.status_labels.items():
            lbl.setStyleSheet("border: 2px solid #555; color: gray;")

        # Highlight current
        if node_name in self.status_labels:
            self.status_labels[node_name].setStyleSheet(
                "border: 2px solid #00ff00; background-color: #003300; color: white;")

    def client_send_message(self):
        msg = self.input_msg.text()
        if not msg: return
        self.input_msg.clear()

        self.log_area.append(f"\n--- CLIENT: Constructing Onion Packet ---")

        # --- THE ONION CONSTRUCTION (Layering) ---
        # Path: Client -> A -> B -> C -> Dest

        # 1. Layer 4: Final Message for Destination
        # Encrypt message with Destination's Public Key
        dest_pub = self.nodes["Dest D"].public_key_pem
        layer_4 = CryptoUtils.encrypt_layer(msg.encode('utf-8'), dest_pub)
        self.log_area.append("Client: Encrypted Layer 4 (Final Message) for Dest D")

        # 2. Layer 3: Routing for Node C
        # Tells C to send 'layer_4' to Dest D (8004)
        c_payload = {'next_hop': DEST_PORT, 'payload': layer_4}
        c_bytes = pickle.dumps(c_payload)
        c_pub = self.nodes["Node C"].public_key_pem
        layer_3 = CryptoUtils.encrypt_layer(c_bytes, c_pub)
        self.log_area.append("Client: Wrapped in Layer 3 (Routing Info) for Node C")

        # 3. Layer 2: Routing for Node B
        # Tells B to send 'layer_3' to Node C (8003)
        b_payload = {'next_hop': PORTS[2], 'payload': layer_3}
        b_bytes = pickle.dumps(b_payload)
        b_pub = self.nodes["Node B"].public_key_pem
        layer_2 = CryptoUtils.encrypt_layer(b_bytes, b_pub)
        self.log_area.append("Client: Wrapped in Layer 2 (Routing Info) for Node B")

        # 4. Layer 1: Routing for Node A
        # Tells A to send 'layer_2' to Node B (8002)
        a_payload = {'next_hop': PORTS[1], 'payload': layer_2}
        a_bytes = pickle.dumps(a_payload)
        a_pub = self.nodes["Node A"].public_key_pem
        layer_1 = CryptoUtils.encrypt_layer(a_bytes, a_pub)
        self.log_area.append("Client: Wrapped in Layer 1 (Routing Info) for Node A")

        # --- TRANSMIT ---
        self.log_area.append("Client: Sending Onion Packet to Entry Node A...")

        # Connect to Node A and send
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORTS[0]))
            s.sendall(layer_1)
            s.close()
        except Exception as e:
            self.log_area.append(f"Client Error: {e}")

    def closeEvent(self, event):
        # Cleanup threads
        for node in self.nodes.values():
            node.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OnionRouterSim()
    window.show()
    sys.exit(app.exec_())
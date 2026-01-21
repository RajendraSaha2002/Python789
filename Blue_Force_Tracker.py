import sys
import socket
import threading
import json
import time
import random
import math
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QGroupBox, QFrame, QDialog, QFormLayout,
                             QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QGraphicsTextItem, QInputDialog, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPolygonF, QPainter

# --- Configuration ---
HOST = '127.0.0.1'
TCP_PORT = 6000  # For Chat / 9-Lines
UDP_PORT = 6001  # For Position Updates
MAP_SIZE = 800  # 800x800 pixel grid


# --- Networking Core ---

class NetworkManager(QThread):
    chat_received = pyqtSignal(str)
    position_received = pyqtSignal(dict)  # {callsign, x, y, type}

    def __init__(self, mode, callsign):
        super().__init__()
        self.mode = mode  # 'SERVER' or 'CLIENT'
        self.callsign = callsign
        self.running = True
        self.tcp_sock = None
        self.udp_sock = None
        self.clients = []  # TCP Connections (Server only)

    def run(self):
        # Start UDP Listener (Both Server and Client listen for updates in this peer-to-peer sim style,
        # or Server aggregates. For simplicity, Server aggregates and re-broadcasts, or clients listen to broadcast.
        # Let's make the Server the central node for simplicity).

        threading.Thread(target=self.udp_listener, daemon=True).start()

        if self.mode == 'SERVER':
            self.start_tcp_server()
        else:
            self.connect_tcp_client()

    # --- TCP (Chat & Reliable Data) ---

    def start_tcp_server(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind((HOST, TCP_PORT))
        self.tcp_sock.listen(5)
        self.chat_received.emit(f"[SYS] Command Server listening on TCP {TCP_PORT}")

        while self.running:
            try:
                conn, addr = self.tcp_sock.accept()
                self.clients.append(conn)
                threading.Thread(target=self.handle_tcp_client, args=(conn,), daemon=True).start()
            except:
                break

    def handle_tcp_client(self, conn):
        while self.running:
            try:
                data = conn.recv(1024)
                if not data: break
                msg = data.decode('utf-8')
                self.chat_received.emit(msg)
                # Re-broadcast to other clients
                self.broadcast_tcp(msg, exclude=conn)
            except:
                break
        if conn in self.clients: self.clients.remove(conn)

    def connect_tcp_client(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.tcp_sock.connect((HOST, TCP_PORT))
            self.chat_received.emit("[SYS] Connected to Command Net.")
            threading.Thread(target=self.handle_tcp_client, args=(self.tcp_sock,), daemon=True).start()
        except Exception as e:
            self.chat_received.emit(f"[SYS] Connection Failed: {e}")

    def send_chat(self, message):
        full_msg = f"[{self.callsign}] {message}"
        if self.mode == 'SERVER':
            self.chat_received.emit(full_msg)  # Echo locally
            self.broadcast_tcp(full_msg)
        elif self.tcp_sock:
            try:
                self.tcp_sock.send(full_msg.encode('utf-8'))
            except:
                self.chat_received.emit("[SYS] Send Failed.")

    def broadcast_tcp(self, msg, exclude=None):
        for c in self.clients:
            if c != exclude:
                try:
                    c.send(msg.encode('utf-8'))
                except:
                    pass

    # --- UDP (Position Updates) ---

    def udp_listener(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((HOST, UDP_PORT if self.mode == 'SERVER' else UDP_PORT + random.randint(1, 100)))

        # If client, we also need a sending socket to the server
        self.udp_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while self.running:
            try:
                data, addr = self.udp_sock.recvfrom(1024)
                pos_data = json.loads(data.decode('utf-8'))

                # If Server, update map and re-broadcast to others (simplified for now: just update local)
                # In a full BFT, server merges all tracks and sends a 'Common Operational Picture' (COP) back.
                # Here we just visualize incoming beacons.
                self.position_received.emit(pos_data)

            except:
                pass

    def send_position_update(self, x, y, unit_type):
        # Send to Server UDP Port
        payload = json.dumps({
            'callsign': self.callsign,
            'x': x,
            'y': y,
            'type': unit_type
        })
        try:
            # Client sends to Server's known UDP port
            self.udp_sender.sendto(payload.encode('utf-8'), (HOST, UDP_PORT))
        except:
            pass


# --- 9-Line Generator Dialog ---

class NineLineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NATO 9-LINE CAS REQUEST")
        self.resize(400, 500)
        self.setStyleSheet("background-color: #222; color: #EEE; font-family: Consolas;")

        self.generated_text = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_ip = QLineEdit("BRAVO")
        self.inp_heading = QLineEdit("180")
        self.inp_dist = QLineEdit("5.2 KM")
        self.inp_elev = QLineEdit("1200 FT")
        self.inp_desc = QLineEdit("T-72 TANK PLATOON")
        self.inp_loc = QLineEdit("GRID NK 1234 5678")
        self.inp_mark = QLineEdit("WP SMOKE")
        self.inp_friends = QLineEdit("SOUTH 800M")
        self.inp_egress = QLineEdit("NORTH THEN EAST")

        inputs = [self.inp_ip, self.inp_heading, self.inp_dist, self.inp_elev,
                  self.inp_desc, self.inp_loc, self.inp_mark, self.inp_friends, self.inp_egress]

        labels = ["1. IP/BP:", "2. Heading:", "3. Distance:", "4. Target Elev:",
                  "5. Target Desc:", "6. Target Loc:", "7. Type Mark:", "8. Friendlies:", "9. Egress:"]

        for lbl, widget in zip(labels, inputs):
            widget.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 4px;")
            form.addRow(lbl, widget)

        layout.addLayout(form)

        btn_gen = QPushButton("TRANSMIT 9-LINE")
        btn_gen.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; padding: 10px;")
        btn_gen.clicked.connect(self.generate)
        layout.addWidget(btn_gen)

    def generate(self):
        # Format the message
        lines = [
            "*** CAS 9-LINE REQUEST ***",
            f"1. IP/BP: {self.inp_ip.text()}",
            f"2. HDG:   {self.inp_heading.text()}",
            f"3. DIST:  {self.inp_dist.text()}",
            f"4. ELEV:  {self.inp_elev.text()}",
            f"5. DESC:  {self.inp_desc.text()}",
            f"6. LOC:   {self.inp_loc.text()}",
            f"7. MARK:  {self.inp_mark.text()}",
            f"8. FRND:  {self.inp_friends.text()}",
            f"9. EGRS:  {self.inp_egress.text()}",
            "*** END OF LINE ***"
        ]
        self.generated_text = "\n".join(lines)
        self.accept()


# --- Tactical Map Widget ---

class TacticalMap(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(0, 0, MAP_SIZE, MAP_SIZE)
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor("#001100")))  # Dark Radar Green

        # Grid Lines
        pen = QPen(QColor(0, 50, 0), 1, Qt.DashLine)
        for x in range(0, MAP_SIZE, 100):
            self.scene.addLine(x, 0, x, MAP_SIZE, pen)
        for y in range(0, MAP_SIZE, 100):
            self.scene.addLine(0, y, MAP_SIZE, y, pen)

        self.units = {}  # {callsign: graphics_item}

    def update_unit(self, callsign, x, y, u_type):
        # Normalize coordinates if needed, here assuming 0-800 mapping

        if callsign in self.units:
            # Move existing
            item = self.units[callsign]
            item.setPos(x, y)
            # Update label text? (optional)
        else:
            # Create new
            color = Qt.blue if "CMD" in callsign else Qt.cyan
            if "RED" in callsign or "OPFOR" in callsign: color = Qt.red

            # Simple shape
            item = self.scene.addEllipse(0, 0, 10, 10, QPen(Qt.white), QBrush(color))
            item.setPos(x, y)

            # Label
            text = QGraphicsTextItem(callsign)
            text.setDefaultTextColor(Qt.white)
            text.setParentItem(item)
            text.setPos(12, -5)

            self.units[callsign] = item


# --- Main Application ---

class BFTWindow(QMainWindow):
    def __init__(self, mode, callsign):
        super().__init__()
        self.setWindowTitle(f"BLUE FORCE TRACKER - {mode} MODE ({callsign})")
        self.setGeometry(100, 100, 1200, 850)
        self.setStyleSheet("background-color: #1a1a1a; color: #DDD;")

        self.mode = mode
        self.callsign = callsign

        # Local Position State (Client only)
        self.my_x = random.randint(100, 700)
        self.my_y = random.randint(100, 700)
        self.my_dest_x = self.my_x
        self.my_dest_y = self.my_y

        # Network
        self.net = NetworkManager(mode, callsign)
        self.net.chat_received.connect(self.append_chat)
        self.net.position_received.connect(self.update_map_icon)
        self.net.start()

        self.init_ui()

        # Timers
        if mode == 'CLIENT':
            # Position Beacon (UDP)
            self.beacon_timer = QTimer()
            self.beacon_timer.timeout.connect(self.broadcast_position)
            self.beacon_timer.start(500)  # 2 Hz update

            # Movement Simulation logic
            self.move_timer = QTimer()
            self.move_timer.timeout.connect(self.sim_movement)
            self.move_timer.start(50)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # --- LEFT: MAP ---
        map_layout = QVBoxLayout()
        lbl_map = QLabel("TACTICAL DISPLAY (UDP FEED)")
        lbl_map.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        map_layout.addWidget(lbl_map)

        self.map_view = TacticalMap()
        map_layout.addWidget(self.map_view)

        # Movement Controls (Client only)
        if self.mode == 'CLIENT':
            move_group = QGroupBox("NAVIGATION")
            move_layout = QHBoxLayout(move_group)
            btn_move = QPushButton("SET WAYPOINT (RANDOM)")
            btn_move.setStyleSheet("background-color: #444;")
            btn_move.clicked.connect(self.set_random_waypoint)
            move_layout.addWidget(btn_move)
            map_layout.addWidget(move_group)

        main_layout.addLayout(map_layout, 2)

        # --- RIGHT: COMMS ---
        comm_layout = QVBoxLayout()

        # Chat Display
        lbl_chat = QLabel("SECURE CHAT (TCP)")
        lbl_chat.setStyleSheet("font-weight: bold; font-size: 14px; color: #2196F3;")
        comm_layout.addWidget(lbl_chat)

        self.txt_chat = QTextEdit()
        self.txt_chat.setReadOnly(True)
        self.txt_chat.setStyleSheet("background-color: #111; color: #0f0; font-family: Consolas;")
        comm_layout.addWidget(self.txt_chat)

        # 9-Line Button
        btn_9line = QPushButton("GENERATE 9-LINE CAS REQ")
        btn_9line.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; padding: 10px;")
        btn_9line.clicked.connect(self.open_9line)
        comm_layout.addWidget(btn_9line)

        # Input Area
        input_layout = QHBoxLayout()
        self.inp_msg = QLineEdit()
        self.inp_msg.setPlaceholderText("Type message...")
        self.inp_msg.setStyleSheet("background-color: #222; color: white; padding: 8px;")
        self.inp_msg.returnPressed.connect(self.send_chat_msg)

        btn_send = QPushButton("SEND")
        btn_send.clicked.connect(self.send_chat_msg)
        btn_send.setStyleSheet("background-color: #1976D2; color: white; padding: 8px;")

        input_layout.addWidget(self.inp_msg)
        input_layout.addWidget(btn_send)
        comm_layout.addLayout(input_layout)

        main_layout.addLayout(comm_layout, 1)

    # --- Logic ---

    def append_chat(self, msg):
        self.txt_chat.append(msg)

    def send_chat_msg(self):
        msg = self.inp_msg.text()
        if msg:
            self.net.send_chat(msg)
            self.inp_msg.clear()

    def open_9line(self):
        dialog = NineLineDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Send the pre-formatted block
            self.net.send_chat("\n" + dialog.generated_text)

    def update_map_icon(self, data):
        # Update map from UDP packet
        self.map_view.update_unit(data['callsign'], data['x'], data['y'], data['type'])

    # --- Client Movement Simulation ---

    def set_random_waypoint(self):
        self.my_dest_x = random.randint(50, 750)
        self.my_dest_y = random.randint(50, 750)
        self.net.send_chat(f"Moving to Grid {self.my_dest_x // 10}-{self.my_dest_y // 10}")

    def sim_movement(self):
        # Simple lerp towards destination
        dx = self.my_dest_x - self.my_x
        dy = self.my_dest_y - self.my_y
        dist = math.hypot(dx, dy)

        if dist > 2:
            speed = 2
            self.my_x += (dx / dist) * speed
            self.my_y += (dy / dist) * speed

            # Self-update map locally immediately
            self.map_view.update_unit(self.callsign, self.my_x, self.my_y, "JET")

    def broadcast_position(self):
        # Send UDP packet
        self.net.send_position_update(self.my_x, self.my_y, "JET")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Startup Dialog to choose role
    role, ok = QInputDialog.getItem(None, "BFT Login", "Select Role:", ["SERVER (Command)", "CLIENT (Pilot)"], 0, False)

    if ok and role:
        mode = 'SERVER' if 'SERVER' in role else 'CLIENT'

        # Get Callsign
        default_call = "GODFATHER" if mode == 'SERVER' else f"VIPER-{random.randint(1, 9)}"
        callsign, ok2 = QInputDialog.getText(None, "BFT Login", "Enter Callsign:", text=default_call)

        if ok2 and callsign:
            win = BFTWindow(mode, callsign)
            win.show()
            sys.exit(app.exec_())
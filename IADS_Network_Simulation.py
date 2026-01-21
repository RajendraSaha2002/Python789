import sys
import socket
import threading
import json
import time
import random

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLabel, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import pyqtSignal, QThread, Qt

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 5555

# Defense Layers (km)
RANGE_TIER_1 = 100  # S-400 Limit (Handover point)
RANGE_TIER_2 = 15  # Buk-M3 Limit (Handover point)


# --- Network Protocol & Logic ---

class IADSServer(QThread):
    """
    The Central Battle Management Station.
    Listens for connections from Subsystems.
    Receives Radar Tracks.
    Delegates Targets based on Range.
    """
    log_signal = pyqtSignal(str)
    table_signal = pyqtSignal(int, float, str)  # ID, Range, Status

    def __init__(self):
        super().__init__()
        self.running = True
        self.clients = {}  # {system_name: socket_conn}
        self.targets = {}  # {id: {range: float, assigned_to: str}}

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        self.log_signal.emit(f"[IADS CORE] Server listening on {PORT}...")

        while self.running:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(conn,)).start()

    def handle_client(self, conn):
        system_name = "UNKNOWN"
        try:
            # Handshake
            data = conn.recv(1024).decode()
            msg = json.loads(data)

            if msg['type'] == 'REGISTER':
                system_name = msg['name']
                self.clients[system_name] = conn
                self.log_signal.emit(f"[NET] Subsystem Connected: {system_name}")

            elif msg['type'] == 'RADAR_TRACK':
                # Radar is just a data source, not a weapon system
                self.process_track(msg)

            # Listen loop
            while self.running:
                data = conn.recv(1024).decode()
                if not data: break
                # Handle status updates from subsystems if needed

        except Exception as e:
            # Connection lost
            pass
        finally:
            if system_name in self.clients:
                del self.clients[system_name]
            conn.close()

    def process_track(self, track_data):
        t_id = track_data['id']
        t_range = track_data['range']

        # 1. Determine optimal system
        best_system = "NONE"
        if t_range > RANGE_TIER_1:
            best_system = "S-400 Triumph"
        elif t_range > RANGE_TIER_2:
            best_system = "Buk-M3"
        else:
            best_system = "Pantsir-S1"

        # 2. Check State & Perform Handover
        current_assignment = self.targets.get(t_id, {}).get('assigned_to', None)

        status_msg = "TRACKING"

        if current_assignment != best_system:
            # LOGIC: HANDOVER REQUIRED
            if current_assignment:
                self.send_command(current_assignment, "RELEASE", t_id)
                self.log_signal.emit(
                    f"[MANAGER] ⚠️ HANDOVER TGT-{t_id}: {current_assignment} -> {best_system} (Range: {t_range:.1f}km)")
            else:
                self.log_signal.emit(f"[MANAGER] NEW TARGET TGT-{t_id} DETECTED. Assigning to {best_system}.")

            self.send_command(best_system, "ENGAGE", t_id)

            # Update Internal State
            self.targets[t_id] = {'range': t_range, 'assigned_to': best_system}
            status_msg = f"ENGAGED BY {best_system}"
        else:
            # Just update range
            self.targets[t_id]['range'] = t_range
            status_msg = f"ENGAGED BY {best_system}"

        # Update GUI
        self.table_signal.emit(t_id, t_range, best_system)

    def send_command(self, system_name, command, target_id):
        if system_name in self.clients:
            msg = json.dumps({"type": command, "target_id": target_id})
            try:
                self.clients[system_name].send(msg.encode())
            except:
                pass


class SubsystemClient(threading.Thread):
    """
    Simulates a Weapon System (S-400, Buk, Pantsir).
    Connects to Manager, receives 'ENGAGE' or 'RELEASE' commands.
    """

    def __init__(self, name, log_callback):
        super().__init__()
        self.name = name
        self.log_callback = log_callback
        self.sock = None
        self.running = True

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))

            # Register
            reg_msg = json.dumps({"type": "REGISTER", "name": self.name})
            self.sock.send(reg_msg.encode())

            while self.running:
                data = self.sock.recv(1024).decode()
                if not data: break
                msg = json.loads(data)

                if msg['type'] == 'ENGAGE':
                    self.log_callback(f"[{self.name}] >> ACK: Locking Target {msg['target_id']}")
                elif msg['type'] == 'RELEASE':
                    self.log_callback(f"[{self.name}] >> REL: Dropping Target {msg['target_id']} (Handover)")

        except Exception as e:
            self.log_callback(f"[{self.name}] Connection Failed: {e}")


class RadarSimulator(threading.Thread):
    """
    Simulates a Radar feeding tracks to the Manager.
    Generates a target at long range and moves it closer.
    """

    def __init__(self):
        super().__init__()
        self.sock = None
        self.running = True
        self.target_dist = 250.0  # Start at 250km
        self.target_speed = 2.0  # km per tick

    def run(self):
        time.sleep(1)  # Wait for server
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))

            # Register (Dummy)
            reg_msg = json.dumps({"type": "REGISTER", "name": "NEBO-M RADAR"})
            self.sock.send(reg_msg.encode())

            while self.running:
                # Move target
                self.target_dist -= self.target_speed
                if self.target_dist < 0: self.target_dist = 250.0  # Reset loop

                # Send Track Data
                msg = json.dumps({
                    "type": "RADAR_TRACK",
                    "id": 101,
                    "range": self.target_dist,
                    "azimuth": 45
                })
                self.sock.send(msg.encode())

                time.sleep(0.1)  # Update rate
        except:
            pass


# --- GUI Application ---

class IADSDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Integrated Air Defense System (IADS) Manager")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #111; color: #0f0; font-family: monospace; }
            QGroupBox { border: 1px solid #333; color: white; font-weight: bold; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QTextEdit { background-color: #000; border: 1px solid #333; color: #0f0; }
            QTableWidget { background-color: #1a1a1a; color: white; gridline-color: #333; }
            QHeaderView::section { background-color: #333; color: white; }
        """)

        self.init_ui()
        self.start_network()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        header = QLabel("MULTI-TIER DEFENSE NETWORK // NETWORK STATUS: ACTIVE")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #fff; background-color: #222; padding: 5px;")
        layout.addWidget(header)

        # Top: Live Target Table
        grp_targets = QGroupBox("LIVE AIR PICTURE")
        t_layout = QVBoxLayout(grp_targets)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["TRACK ID", "RANGE (KM)", "ASSIGNED UNIT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t_layout.addWidget(self.table)

        layout.addWidget(grp_targets, 40)

        # Middle: Logs
        grp_logs = QGroupBox("DATALINK LOGS")
        l_layout = QHBoxLayout(grp_logs)

        # Server Log
        self.log_server = QTextEdit()
        self.log_server.setReadOnly(True)
        l_layout.addWidget(self.log_server)

        # Subsystem Log
        self.log_subs = QTextEdit()
        self.log_subs.setReadOnly(True)
        l_layout.addWidget(self.log_subs)

        layout.addWidget(grp_logs, 60)

        # Legend
        lbl_legend = QLabel("TIER 1: S-400 (>100km)  |  TIER 2: Buk-M3 (15-100km)  |  TIER 3: Pantsir-S1 (<15km)")
        lbl_legend.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(lbl_legend)

    def start_network(self):
        # 1. Start Server
        self.server = IADSServer()
        self.server.log_signal.connect(self.append_server_log)
        self.server.table_signal.connect(self.update_table)
        self.server.start()

        # 2. Start Subsystems (Clients)
        self.systems = []
        for name in ["S-400 Triumph", "Buk-M3", "Pantsir-S1"]:
            client = SubsystemClient(name, self.append_sub_log)
            client.start()
            self.systems.append(client)

        # 3. Start Radar Feed
        self.radar = RadarSimulator()
        self.radar.start()

    def append_server_log(self, text):
        self.log_server.append(text)

    def append_sub_log(self, text):
        # Use simple mutex logic via Qt signals usually, but direct append
        # from threads needs care. For this simple sim, we emit to a slot.
        # Here we just use a helper to queue it if needed, but QTextEdit is mostly thread-safe in PyQt5 for appends
        self.log_subs.append(text)

    def update_table(self, t_id, t_range, system):
        # Update or Insert Row
        items = self.table.findItems(str(t_id), Qt.MatchExactly)
        if items:
            row = items[0].row()
        else:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t_id)))

        self.table.setItem(row, 1, QTableWidgetItem(f"{t_range:.2f}"))

        # Highlight Logic
        item_sys = QTableWidgetItem(system)
        if system == "S-400 Triumph":
            item_sys.setForeground(QColor("#FF5555"))  # Red
        elif system == "Buk-M3":
            item_sys.setForeground(QColor("#FFAA00"))  # Orange
        else:
            item_sys.setForeground(QColor("#55FFFF"))  # Cyan

        self.table.setItem(row, 2, item_sys)

    def closeEvent(self, event):
        self.server.running = False
        for s in self.systems: s.running = False
        self.radar.running = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IADSDashboard()
    window.show()
    sys.exit(app.exec_())
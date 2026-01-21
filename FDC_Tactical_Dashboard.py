import sys
import socket
import threading
import json
import time
import os
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QGroupBox, QComboBox, QFrame,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QColor

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 5500
LOG_FILE = "mission_logs.txt"


# --- Backend: Logging & Protocol ---

class MissionLogger:
    @staticmethod
    def log(event_type, details):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{event_type}] {details}"

        # Write to file
        try:
            with open(LOG_FILE, "a") as f:
                f.write(entry + "\n")
        except Exception as e:
            print(f"Logging Error: {e}")

        return entry


class MilitaryProtocol:
    @staticmethod
    def format_cff(observer_id, grid, target_desc, method):
        """Formats a Call For Fire into standard message syntax."""
        # Simulated AFATDS / VMF format
        return f"K02.19/CFF/{observer_id}//GRID:{grid}/TGT:{target_desc}/METHOD:{method}//EOM"


# --- Backend: Networking (Server) ---

class FDCServer(QThread):
    new_request = pyqtSignal(dict)
    log_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.server_socket = None

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            self.log_update.emit(MissionLogger.log("SYS", f"FDC Server listening on {PORT}"))

            while self.running:
                client, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client, addr)).start()
        except OSError:
            pass

    def handle_client(self, conn, addr):
        try:
            data = conn.recv(4096).decode('utf-8')
            if data:
                payload = json.loads(data)
                self.new_request.emit(payload)
                self.log_update.emit(
                    MissionLogger.log("NET", f"Received Packet from {payload.get('callsign', 'UNKNOWN')}"))
        except Exception as e:
            print(f"Connection Error: {e}")
        finally:
            conn.close()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()


# --- GUI Component: Battery Status Widget ---

class BatteryWidget(QFrame):
    status_changed = pyqtSignal(str, str)  # battery_name, new_status

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.state = "READY"  # READY, BUSY, RELOADING
        self.ammo = 40

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #222; border: 1px solid #444; border-radius: 5px;")
        self.setFixedSize(150, 180)

        layout = QVBoxLayout(self)

        self.lbl_name = QLabel(name)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFF;")

        self.lbl_status = QLabel("READY")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(
            "background-color: #2E7D32; color: white; font-weight: bold; padding: 5px; border-radius: 3px;")

        self.lbl_ammo = QLabel(f"ROUNDS: {self.ammo}")
        self.lbl_ammo.setStyleSheet("color: #AAA;")
        self.lbl_ammo.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { background: #333; border: none; height: 5px; } QProgressBar::chunk { background: #00bcd4; }")
        self.progress.setValue(0)

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_ammo)
        layout.addWidget(self.progress)

        # Internal Timer for simulation
        self.timer = QTimer()
        self.timer.timeout.connect(self.cycle_logic)
        self.cycle_step = 0

    def fire_mission(self, rounds):
        if self.state != "READY": return False

        self.state = "FIRING"
        self.update_ui_state("#D32F2F", "FIRING")  # Red
        self.ammo -= rounds
        self.lbl_ammo.setText(f"ROUNDS: {self.ammo}")

        # Start Cycle (Simulate Fire -> Reload -> Ready)
        self.cycle_step = 0
        self.timer.start(500)  # Tick every 0.5s
        return True

    def cycle_logic(self):
        self.cycle_step += 10
        self.progress.setValue(self.cycle_step)

        if self.state == "FIRING" and self.cycle_step >= 50:
            self.state = "RELOADING"
            self.update_ui_state("#FBC02D", "RELOADING")  # Yellow

        elif self.state == "RELOADING" and self.cycle_step >= 100:
            self.state = "READY"
            self.update_ui_state("#2E7D32", "READY")  # Green
            self.progress.setValue(0)
            self.timer.stop()
            self.status_changed.emit(self.name, "READY")

    def update_ui_state(self, color, text):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"background-color: {color}; color: #FFF; font-weight: bold; padding: 5px;")


# --- GUI: FDC Main Dashboard ---

class FDCDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FDC TACTICAL COMMAND - MAIN")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; color: #e0e0e0; font-family: Consolas; }
            QLabel { color: #e0e0e0; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; font-weight: bold; color: #4fc3f7; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        """)

        # Logic
        self.pending_missions = []
        self.batteries = {}

        self.init_ui()

        # Start Server
        self.server = FDCServer()
        self.server.new_request.connect(self.incoming_cff)
        self.server.log_update.connect(self.append_log)
        self.server.start()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # HEADER
        header = QLabel("FIRE DIRECTION CENTER (FDC) // BATTALION NET")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; background-color: #0d47a1; color: white; padding: 10px;")
        layout.addWidget(header)

        # MAIN SPLIT
        mid_layout = QHBoxLayout()

        # --- LEFT: MISSION QUEUE ---
        queue_group = QGroupBox("PENDING FIRE MISSIONS")
        q_layout = QVBoxLayout(queue_group)

        self.table_missions = QTableWidget()
        self.table_missions.setColumnCount(4)
        self.table_missions.setHorizontalHeaderLabels(["ID", "Observer", "Grid", "Type"])
        self.table_missions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_missions.setStyleSheet("background-color: #222; color: #eee; border: none;")
        self.table_missions.setSelectionBehavior(QTableWidget.SelectRows)
        q_layout.addWidget(self.table_missions)

        # Assignment Controls
        assign_layout = QHBoxLayout()
        self.combo_battery = QComboBox()
        self.combo_battery.addItems(["ALPHA BTRY", "BRAVO BTRY", "CHARLIE BTRY"])
        self.combo_battery.setStyleSheet("padding: 5px; background: #333; color: white;")

        btn_assign = QPushButton("ASSIGN & FIRE")
        btn_assign.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 8px;")
        btn_assign.clicked.connect(self.execute_mission)

        assign_layout.addWidget(QLabel("Assign To:"))
        assign_layout.addWidget(self.combo_battery)
        assign_layout.addWidget(btn_assign)
        q_layout.addLayout(assign_layout)

        mid_layout.addWidget(queue_group, 60)

        # --- RIGHT: ASSET STATUS ---
        assets_group = QGroupBox("UNIT STATUS")
        a_layout = QVBoxLayout(assets_group)

        # Battery Widgets
        self.batteries["ALPHA BTRY"] = BatteryWidget("ALPHA BTRY")
        self.batteries["BRAVO BTRY"] = BatteryWidget("BRAVO BTRY")
        self.batteries["CHARLIE BTRY"] = BatteryWidget("CHARLIE BTRY")

        a_layout.addWidget(self.batteries["ALPHA BTRY"])
        a_layout.addWidget(self.batteries["BRAVO BTRY"])
        a_layout.addWidget(self.batteries["CHARLIE BTRY"])
        a_layout.addStretch()

        mid_layout.addWidget(assets_group, 40)
        layout.addLayout(mid_layout)

        # LOGGING AREA
        log_group = QGroupBox("DIGITAL TRANSMISSION LOG")
        l_layout = QVBoxLayout(log_group)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #000; color: #00ff00; font-family: Courier; font-size: 11px;")
        l_layout.addWidget(self.txt_log)
        layout.addWidget(log_group)

        # Button to launch Observer
        btn_observer = QPushButton("LAUNCH OBSERVER CLIENT (SIMULATION)")
        btn_observer.setStyleSheet("background-color: #444; color: #AAA; padding: 5px;")
        btn_observer.clicked.connect(self.spawn_observer)
        layout.addWidget(btn_observer)

    def incoming_cff(self, data):
        """Handle incoming data packet from Observer."""
        row = self.table_missions.rowCount()
        self.table_missions.insertRow(row)

        # Store full data in the table item's user data if needed, or just keep a list
        self.pending_missions.append(data)

        self.table_missions.setItem(row, 0, QTableWidgetItem(f"M-{random.randint(100, 999)}"))
        self.table_missions.setItem(row, 1, QTableWidgetItem(data['callsign']))
        self.table_missions.setItem(row, 2, QTableWidgetItem(data['grid']))
        self.table_missions.setItem(row, 3, QTableWidgetItem(data['target']))

        # Format Log String
        log_msg = MilitaryProtocol.format_cff(data['callsign'], data['grid'], data['target'], "FFE")
        self.append_log(f"RX << {log_msg}")

    def execute_mission(self):
        """Assigns selected mission to selected battery."""
        selected_rows = self.table_missions.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Command Error", "No Fire Mission Selected.")
            return

        row_idx = selected_rows[0].row()
        btry_name = self.combo_battery.currentText()
        battery = self.batteries[btry_name]

        # Check Rules of Engagement / Status
        if battery.state != "READY":
            QMessageBox.critical(self, "Asset Unavailable",
                                 f"{btry_name} is currently {battery.state}.\nCannot process fire mission.")
            return

        # Execute
        rounds = 3  # Standard volly
        battery.fire_mission(rounds)

        # Log
        mission_id = self.table_missions.item(row_idx, 0).text()
        self.append_log(f"TX >> CMD: {btry_name} // FIRE MISSION {mission_id} // {rounds} ROUNDS HE // AT MY COMMAND")

        # Remove from Queue
        self.table_missions.removeRow(row_idx)
        self.pending_missions.pop(row_idx)

    def append_log(self, text):
        self.txt_log.append(text)

    def spawn_observer(self):
        # Open the client window
        self.obs_win = ObserverClient()
        self.obs_win.show()

    def closeEvent(self, event):
        self.server.stop()
        event.accept()


import random


# --- GUI: Observer Client (The Forward Observer) ---

class ObserverClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FORWARD OBSERVER - HANDHELD")
        self.setGeometry(1200, 100, 400, 500)
        self.setStyleSheet("""
            QMainWindow { background-color: #263238; color: #eceff1; }
            QLineEdit, QComboBox { padding: 8px; background: #37474f; color: white; border: 1px solid #546e7a; }
            QLabel { font-weight: bold; margin-top: 5px; }
        """)

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("YOUR CALLSIGN:"))
        self.txt_callsign = QLineEdit("VICTOR-1-1")
        layout.addWidget(self.txt_callsign)

        # Target Data
        grp_tgt = QGroupBox("TARGET PACKET")
        t_layout = QVBoxLayout(grp_tgt)

        t_layout.addWidget(QLabel("GRID COORDINATES (MGRS):"))
        self.txt_grid = QLineEdit()
        self.txt_grid.setPlaceholderText("e.g. 12S QT 1234 5678")
        t_layout.addWidget(self.txt_grid)

        t_layout.addWidget(QLabel("TARGET DESCRIPTION:"))
        self.combo_target = QComboBox()
        self.combo_target.addItems(["INFANTRY IN OPEN", "ARMOR COLUMN", "BUNKER", "LIGHT TRUCKS", "SUSPECTED HQ"])
        t_layout.addWidget(self.combo_target)

        t_layout.addWidget(QLabel("METHOD OF ENGAGEMENT:"))
        self.combo_method = QComboBox()
        self.combo_method.addItems(["FIRE FOR EFFECT", "ADJUST FIRE", "SUPPRESSION", "SMOKE SCREEN"])
        t_layout.addWidget(self.combo_method)

        layout.addWidget(grp_tgt)

        # Transmit
        self.btn_send = QPushButton("TRANSMIT CALL FOR FIRE")
        self.btn_send.setStyleSheet(
            "background-color: #ff6f00; color: white; font-weight: bold; padding: 15px; margin-top: 20px;")
        self.btn_send.clicked.connect(self.transmit)
        layout.addWidget(self.btn_send)

        # Quick Fill for testing
        btn_sim = QPushButton("Simulate Laser Rangefinder Data")
        btn_sim.setStyleSheet("background-color: #455a64; color: #aaa; margin-top: 5px;")
        btn_sim.clicked.connect(self.sim_data)
        layout.addWidget(btn_sim)

        layout.addStretch()

    def sim_data(self):
        grids = ["34U CA 123 456", "34U CA 789 012", "34U CB 555 999"]
        self.txt_grid.setText(random.choice(grids))

    def transmit(self):
        payload = {
            'callsign': self.txt_callsign.text(),
            'grid': self.txt_grid.text(),
            'target': self.combo_target.currentText(),
            'method': self.combo_method.currentText(),
            'timestamp': time.time()
        }

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.send(json.dumps(payload).encode('utf-8'))
            s.close()
            QMessageBox.information(self, "SENT", "Digital CFF Packet Transmitted.")
        except Exception as e:
            QMessageBox.critical(self, "COMM ERROR", f"Cannot reach FDC Server.\n{e}")


# --- Main Entry Point ---

if __name__ == "__main__":
    # Ensure clean exit for threads
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)

    # Launch FDC Server Dashboard
    fdc_window = FDCDashboard()
    fdc_window.show()

    sys.exit(app.exec_())
import sys
import json
import math
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QMessageBox, QFrame,
                             QTabWidget, QSplitter, QDialog, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QRadialGradient

# --- Configuration ---
DEFAULT_SCENARIO = "mission_01.json"
RADAR_RANGE_KM = 100.0
UPDATE_INTERVAL_MS = 30  # ~30 FPS


# --- Data Models ---

class ThreatType:
    F16 = "F-16 Fighter"
    CRUISE_MISSILE = "Cruise Missile"
    DRONE = "Kamikaze Drone"
    BOMBER = "Strategic Bomber"

    @staticmethod
    def get_speed(t_type):
        # Arbitrary pixels per second for simulation
        if t_type == ThreatType.F16: return 15.0
        if t_type == ThreatType.CRUISE_MISSILE: return 25.0
        if t_type == ThreatType.DRONE: return 8.0
        if t_type == ThreatType.BOMBER: return 10.0
        return 10.0


# --- PART 1: THE SCENARIO EDITOR ---

class ScenarioEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INSTRUCTOR STATION - SCENARIO EDITOR")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #e0e0e0; font-family: Segoe UI; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; color: #aaa; font-weight: bold; }
            QTableWidget { background-color: #1e1e1e; color: white; gridline-color: #444; border: none; }
            QHeaderView::section { background-color: #333; color: white; padding: 4px; }
            QLineEdit, QComboBox, QSpinBox { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QPushButton { background-color: #0d47a1; color: white; border: none; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton#DeleteBtn { background-color: #c62828; }
            QPushButton#SaveBtn { background-color: #2e7d32; }
        """)

        self.events = []  # List of dicts
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- Left: Input Form ---
        form_panel = QFrame()
        form_panel.setFixedWidth(300)
        form_layout = QVBoxLayout(form_panel)

        lbl_title = QLabel("EVENT CREATOR")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #90caf9;")
        form_layout.addWidget(lbl_title)

        # Inputs
        self.inp_time = QLineEdit()
        self.inp_time.setPlaceholderText("Time (seconds, e.g. 5)")

        self.combo_type = QComboBox()
        self.combo_type.addItems([ThreatType.F16, ThreatType.CRUISE_MISSILE, ThreatType.DRONE, ThreatType.BOMBER])

        self.combo_azimuth = QComboBox()
        self.combo_azimuth.addItems(["North (0°)", "North-East (45°)", "East (90°)", "South-East (135°)",
                                     "South (180°)", "South-West (225°)", "West (270°)", "North-West (315°)"])

        form = QFormLayout()
        form.addRow("Spawn Time (T+):", self.inp_time)
        form.addRow("Threat Type:", self.combo_type)
        form.addRow("Direction:", self.combo_azimuth)
        form_layout.addLayout(form)

        btn_add = QPushButton("ADD EVENT TO TIMELINE")
        btn_add.clicked.connect(self.add_event)
        form_layout.addWidget(btn_add)

        form_layout.addStretch()

        # File Operations
        btn_save = QPushButton("SAVE SCENARIO (JSON)")
        btn_save.setObjectName("SaveBtn")
        btn_save.clicked.connect(self.save_to_json)
        form_layout.addWidget(btn_save)

        btn_load = QPushButton("LOAD SCENARIO")
        btn_load.clicked.connect(self.load_from_json)
        form_layout.addWidget(btn_load)

        layout.addWidget(form_panel)

        # --- Right: Timeline Table ---
        table_panel = QFrame()
        t_layout = QVBoxLayout(table_panel)

        t_layout.addWidget(QLabel("MISSION TIMELINE"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time (s)", "Type", "Azimuth", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t_layout.addWidget(self.table)

        layout.addWidget(table_panel)

    def add_event(self):
        try:
            t = float(self.inp_time.text())
            t_type = self.combo_type.currentText()
            # Parse Azimuth from string "North (0°)" -> 0
            az_str = self.combo_azimuth.currentText()
            az = int(az_str.split('(')[1].replace('°)', ''))

            event = {
                "time": t,
                "type": t_type,
                "azimuth": az,
                "range": RADAR_RANGE_KM  # Start at max range
            }

            self.events.append(event)
            self.events.sort(key=lambda x: x["time"])  # Keep timeline ordered
            self.refresh_table()
            self.inp_time.clear()
            self.inp_time.setFocus()

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Time must be a number.")

    def refresh_table(self):
        self.table.setRowCount(0)
        for i, e in enumerate(self.events):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(e['time'])))
            self.table.setItem(i, 1, QTableWidgetItem(e['type']))
            self.table.setItem(i, 2, QTableWidgetItem(str(e['azimuth']) + "°"))

            btn_del = QPushButton("Delete")
            btn_del.setObjectName("DeleteBtn")
            btn_del.clicked.connect(lambda _, idx=i: self.delete_event(idx))
            self.table.setCellWidget(i, 3, btn_del)

    def delete_event(self, index):
        self.events.pop(index)
        self.refresh_table()

    def save_to_json(self):
        if not self.events: return
        path, _ = QFileDialog.getSaveFileName(self, "Save Scenario", DEFAULT_SCENARIO, "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(self.events, f, indent=4)
            QMessageBox.information(self, "Success", "Scenario saved successfully.")

    def load_from_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Scenario", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    self.events = json.load(f)
                self.refresh_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {e}")


# --- PART 2: THE PLAYER CONSOLE (SIMULATOR) ---

class ActiveThreat:
    def __init__(self, config):
        self.type = config['type']
        self.azimuth_deg = config['azimuth']
        self.range = config['range']  # km
        self.speed = ThreatType.get_speed(self.type)  # km/s (scaled)

        # Convert polar to cartesian for internal logic (normalized 0-1)
        rad = math.radians(self.azimuth_deg - 90)  # Adjust so 0 is North (Up)
        self.dx = math.cos(rad)
        self.dy = math.sin(rad)

        self.spawn_time = config['time']
        self.id = id(self)
        self.is_destroyed = False

    def update(self, dt_seconds):
        # Move closer to center (range 0)
        self.range -= self.speed * dt_seconds
        return self.range <= 0  # Return True if impact (leak)


class RadarScope(QWidget):
    threat_clicked = pyqtSignal(object)  # Emits the threat object

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.active_threats = []
        self.selected_threat = None
        self.scan_line_angle = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 20
        scale_factor = radius / RADAR_RANGE_KM

        # 1. Draw Scope Grid
        painter.setPen(QPen(QColor(0, 50, 0), 1))
        painter.setBrush(QBrush(QColor(0, 20, 0)))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Range Rings
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 100, 0), 1, Qt.DashLine))
        painter.drawEllipse(QPointF(cx, cy), radius * 0.75, radius * 0.75)
        painter.drawEllipse(QPointF(cx, cy), radius * 0.5, radius * 0.5)
        painter.drawEllipse(QPointF(cx, cy), radius * 0.25, radius * 0.25)

        # Crosshairs
        painter.drawLine(int(cx - radius), int(cy), int(cx + radius), int(cy))
        painter.drawLine(int(cx), int(cy - radius), int(cx), int(cy + radius))

        # 2. Draw Sweep Line
        scan_rad = math.radians(self.scan_line_angle)
        sx = cx + math.cos(scan_rad) * radius
        sy = cy + math.sin(scan_rad) * radius

        gradient = QRadialGradient(cx, cy, radius)
        gradient.setColorAt(0, QColor(0, 255, 0, 0))
        gradient.setColorAt(1, QColor(0, 255, 0, 100))  # Fading trail logic would go here

        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.drawLine(QPointF(cx, cy), QPointF(sx, sy))

        # 3. Draw Threats
        for t in self.active_threats:
            if t.is_destroyed: continue

            # Calculate position on screen
            # Azimuth 0 is North (Up). Math: Up is -Y.
            # Angle in logic: 0 = North.
            rad = math.radians(t.azimuth_deg - 90)

            dist_px = t.range * scale_factor
            tx = cx + math.cos(rad) * dist_px
            ty = cy + math.sin(rad) * dist_px

            # Store screen pos for clicking
            t.screen_rect = QRectF(tx - 6, ty - 6, 12, 12)

            # Determine Color
            color = QColor(255, 0, 0)  # Red Hostile
            if t == self.selected_threat:
                color = QColor(255, 255, 0)  # Yellow Selected
                # Draw Lock Box
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(int(tx - 10), int(ty - 10), 20, 20)

                # Draw Info Text
                painter.setPen(color)
                painter.setFont(QFont("Consolas", 10))
                painter.drawText(int(tx + 15), int(ty), f"{t.type}\nR: {t.range:.1f}km")

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)

            # Draw Symbol (Diamond)
            path = [(0, -6), (6, 0), (0, 6), (-6, 0)]
            points = [QPointF(tx + px, ty + py) for px, py in path]
            painter.drawPolygon(*points)

    def mousePressEvent(self, event):
        pos = event.pos()
        clicked = None
        for t in self.active_threats:
            if hasattr(t, 'screen_rect') and t.screen_rect.contains(pos):
                clicked = t
                break

        self.selected_threat = clicked
        self.threat_clicked.emit(clicked)
        self.update()


class SimulatorConsole(QMainWindow):
    def __init__(self, scenario_file):
        super().__init__()
        self.scenario_file = scenario_file
        self.setWindowTitle("STUDENT STATION - AIR DEFENSE CONSOLE")
        self.setGeometry(100, 100, 1024, 768)
        self.setStyleSheet("background-color: #111; color: #0f0; font-family: Consolas;")

        # State
        self.mission_time = 0.0
        self.scenario_queue = []
        self.score_engaged = 0
        self.score_leaked = 0
        self.reaction_times = []

        self.load_scenario()
        self.init_ui()

        # Game Loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_tick)
        self.timer.start(UPDATE_INTERVAL_MS)

    def load_scenario(self):
        try:
            with open(self.scenario_file, 'r') as f:
                self.scenario_queue = json.load(f)
                # Sort just in case
                self.scenario_queue.sort(key=lambda x: x['time'])
        except Exception:
            self.scenario_queue = []  # Empty mission

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Radar
        self.radar = RadarScope()
        self.radar.threat_clicked.connect(self.on_target_select)
        layout.addWidget(self.radar, 70)

        # Controls Panel
        panel = QFrame()
        panel.setStyleSheet("background-color: #222; border-left: 2px solid #0f0;")
        p_layout = QVBoxLayout(panel)

        lbl_header = QLabel("WEAPON CONTROL")
        lbl_header.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        p_layout.addWidget(lbl_header)

        self.lbl_clock = QLabel("MISSION CLOCK: 00:00")
        self.lbl_clock.setStyleSheet("font-size: 16px; color: #aaa;")
        p_layout.addWidget(self.lbl_clock)

        p_layout.addSpacing(20)

        self.lbl_target_info = QLabel("NO TARGET LOCKED")
        self.lbl_target_info.setStyleSheet("border: 1px solid #0f0; padding: 10px; font-size: 14px;")
        p_layout.addWidget(self.lbl_target_info)

        self.btn_engage = QPushButton("ENGAGE TARGET")
        self.btn_engage.setStyleSheet("""
            QPushButton { background-color: #b71c1c; color: white; font-size: 18px; font-weight: bold; padding: 20px; border-radius: 5px; }
            QPushButton:hover { background-color: #d32f2f; }
            QPushButton:disabled { background-color: #333; color: #555; }
        """)
        self.btn_engage.setEnabled(False)
        self.btn_engage.clicked.connect(self.engage_target)
        p_layout.addWidget(self.btn_engage)

        p_layout.addStretch()

        self.lbl_status = QLabel("SYSTEM READY")
        p_layout.addWidget(self.lbl_status)

        layout.addWidget(panel, 30)

    def on_target_select(self, threat):
        if threat:
            self.lbl_target_info.setText(
                f"LOCKED: {threat.type}\nAZIMUTH: {threat.azimuth_deg}°\nRANGE: {threat.range:.1f} KM")
            self.btn_engage.setEnabled(True)
        else:
            self.lbl_target_info.setText("NO TARGET LOCKED")
            self.btn_engage.setEnabled(False)

    def engage_target(self):
        tgt = self.radar.selected_threat
        if tgt and not tgt.is_destroyed:
            # Fire Logic
            tgt.is_destroyed = True

            # Calc Reaction
            react_time = self.mission_time - tgt.spawn_time
            self.reaction_times.append(react_time)

            self.score_engaged += 1
            self.lbl_status.setText(f"SPLASH! TARGET DESTROYED. RT: {react_time:.2f}s")

            # Clear selection
            self.radar.active_threats.remove(tgt)
            self.radar.selected_threat = None
            self.on_target_select(None)
            self.radar.update()

            self.check_mission_end()

    def game_tick(self):
        dt = UPDATE_INTERVAL_MS / 1000.0
        self.mission_time += dt
        self.lbl_clock.setText(f"MISSION CLOCK: {int(self.mission_time // 60):02}:{int(self.mission_time % 60):02}")

        # 1. Spawn Threats
        if self.scenario_queue:
            # Check if it's time for next event
            if self.mission_time >= self.scenario_queue[0]['time']:
                event_data = self.scenario_queue.pop(0)
                new_threat = ActiveThreat(event_data)
                self.radar.active_threats.append(new_threat)
                self.lbl_status.setText(f"WARNING: NEW CONTACT {new_threat.type}")

        # 2. Update Radar Sweep
        self.radar.scan_line_angle = (self.radar.scan_line_angle + 2) % 360

        # 3. Update Threats
        for t in list(self.radar.active_threats):
            leaked = t.update(dt)
            if leaked:
                self.score_leaked += 1
                self.lbl_status.setText("CRITICAL: TARGET LEAKED (IMPACT)")
                self.radar.active_threats.remove(t)
                self.radar.selected_threat = None
                self.on_target_select(None)
                self.check_mission_end()

        self.radar.update()

    def check_mission_end(self):
        # End if queue empty and no threats on screen
        if not self.scenario_queue and not self.radar.active_threats:
            self.timer.stop()
            self.show_aar()

    def show_aar(self):
        avg_rt = sum(self.reaction_times) / len(self.reaction_times) if self.reaction_times else 0
        grade = "FAIL" if self.score_leaked > 0 else "PASS"
        if avg_rt < 3.0 and grade == "PASS": grade = "DISTINCTION"

        report = (
            f"--- AFTER ACTION REPORT ---\n\n"
            f"MISSION RESULT: {grade}\n"
            f"---------------------------\n"
            f"Targets Engaged: {self.score_engaged}\n"
            f"Targets Leaked:  {self.score_leaked}\n"
            f"Avg Reaction Time: {avg_rt:.2f} seconds\n"
        )

        QMessageBox.information(self, "Mission Complete", report)
        self.close()


# --- Launcher ---

class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S-400 SIMULATION SUITE")
        self.setGeometry(400, 300, 400, 300)
        self.setStyleSheet("background-color: #333; color: white;")

        layout = QVBoxLayout(self)

        lbl = QLabel("SELECT MODE")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(lbl)

        btn_editor = QPushButton("INSTRUCTOR (SCENARIO EDITOR)")
        btn_editor.setStyleSheet("background-color: #1565c0; padding: 15px; font-size: 14px;")
        btn_editor.clicked.connect(self.launch_editor)
        layout.addWidget(btn_editor)

        btn_sim = QPushButton("STUDENT (TRAINING CONSOLE)")
        btn_sim.setStyleSheet("background-color: #2e7d32; padding: 15px; font-size: 14px;")
        btn_sim.clicked.connect(self.launch_sim)
        layout.addWidget(btn_sim)

    def launch_editor(self):
        self.editor = ScenarioEditor()
        self.editor.show()
        self.close()

    def launch_sim(self):
        # Ask for file first
        path, _ = QFileDialog.getOpenFileName(self, "Select Mission File", "", "JSON Files (*.json)")
        if path:
            self.sim = SimulatorConsole(path)
            self.sim.show()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create default file if not exists
    if not os.path.exists(DEFAULT_SCENARIO):
        default_data = [
            {"time": 2.0, "type": ThreatType.F16, "azimuth": 0, "range": 100},
            {"time": 6.0, "type": ThreatType.DRONE, "azimuth": 90, "range": 100},
            {"time": 12.0, "type": ThreatType.CRUISE_MISSILE, "azimuth": 270, "range": 100}
        ]
        with open(DEFAULT_SCENARIO, 'w') as f:
            json.dump(default_data, f)

    launcher = LauncherWindow()
    launcher.show()

    sys.exit(app.exec_())
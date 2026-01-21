import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QDial, QFrame,
                             QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QRadialGradient, QPainter, QPen, QBrush

# --- Configuration ---
DB_FILE = "restricted_sectors.json"


# --- 1. The Safety Logic Engine ---

class SafetyInterlock:
    def __init__(self):
        self.zones = []
        self.load_database()

    def load_database(self):
        """Loads no-fire zones from JSON. Creates default if missing."""
        if not os.path.exists(DB_FILE):
            default_zones = [
                {"start": 80, "end": 100, "name": "CITY GENERAL HOSPITAL", "type": "CRITICAL"},
                {"start": 200, "end": 240, "name": "INTL AIRPORT APCH", "type": "AVIATION"},
                {"start": 350, "end": 10, "name": "FRIENDLY COMMS TOWER", "type": "BLUE_FORCE"}
                # Note: 350-10 wraps around 360
            ]
            with open(DB_FILE, 'w') as f:
                json.dump(default_zones, f, indent=4)

        try:
            with open(DB_FILE, 'r') as f:
                self.zones = json.load(f)
        except Exception as e:
            print(f"Database Error: {e}")
            self.zones = []

    def check_safety(self, azimuth):
        """
        Returns (Is_Safe: bool, Reason: str)
        """
        azimuth = azimuth % 360

        for zone in self.zones:
            s = zone['start']
            e = zone['end']

            # Handle wrap-around (e.g., 350 to 10)
            in_zone = False
            if s > e:
                if azimuth >= s or azimuth <= e:
                    in_zone = True
            else:
                if s <= azimuth <= e:
                    in_zone = True

            if in_zone:
                return False, f"RESTRICTED: {zone['name']}"

        return True, "SECTOR CLEAR"


# --- 2. Custom Compass Widget ---

class CompassDial(QWidget):
    angleChanged = pyqtSignal(int)

    def __init__(self, interlock):
        super().__init__()
        self.setFixedSize(300, 300)
        self.angle = 0
        self.interlock = interlock
        self.is_jamming = False

    def set_angle(self, angle):
        self.angle = angle % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 10

        # Background
        painter.setBrush(QBrush(QColor(20, 20, 30)))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        # Draw Restricted Zones (Red Arcs)
        for zone in self.interlock.zones:
            s = zone['start']
            e = zone['end']

            # Qt draws arcs in 1/16th degrees, counter-clockwise from 3 o'clock (0).
            # Compass is clockwise from 12 o'clock (0).
            # Conversion: QtAngle = 90 - CompassAngle

            span = e - s
            if s > e: span = (360 - s) + e

            start_qt = (90 - s) * 16
            span_qt = -span * 16

            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 0, 0, 100), 15))  # Semi-transparent red

            # drawArc(x, y, w, h, startAngle, spanAngle)
            # Adjust radius slightly inward
            r_arc = radius - 15
            painter.drawArc(int(cx - r_arc), int(cy - r_arc), int(r_arc * 2), int(r_arc * 2), int(start_qt),
                            int(span_qt))

        # Draw Current Heading Needle
        painter.translate(cx, cy)
        painter.rotate(self.angle)

        # Color changes if jamming
        color = QColor(0, 255, 0) if not self.is_jamming else QColor(255, 0, 0)
        if self.is_jamming:
            # Draw "Beam"
            beam_grad = QRadialGradient(0, -radius / 2, radius)
            beam_grad.setColorAt(0, QColor(255, 0, 0, 200))
            beam_grad.setColorAt(1, QColor(255, 0, 0, 0))
            painter.setBrush(QBrush(beam_grad))
            painter.setPen(Qt.NoPen)
            # Fan shape
            path = QPainter.drawPolygon
            # Simple triangle beam for viz
            painter.drawPolygon([
                Qt.QPoint(0, 0),
                Qt.QPoint(-20, -int(radius)),
                Qt.QPoint(20, -int(radius))
            ])

        # The physical pointer
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawPolygon([
            Qt.QPoint(0, -int(radius) + 10),
            Qt.QPoint(-10, 10),
            Qt.QPoint(10, 10)
        ])


# --- 3. Main GUI ---

class JammerConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOFT KILL // DIRECTED ENERGY CONTROL")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: #EEE; font-family: Consolas; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { font-size: 14px; }
            QTableWidget { background-color: #222; gridline-color: #444; color: #EEE; }
            QHeaderView::section { background-color: #333; color: white; }
        """)

        self.logic = SafetyInterlock()
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: CONTROLS ---
        ctrl_panel = QWidget()
        ctrl_panel.setFixedWidth(400)
        vbox = QVBoxLayout(ctrl_panel)

        # Header
        lbl_h = QLabel("SYSTEM STATUS: ONLINE")
        lbl_h.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #00FF00; border: 1px solid #00FF00; padding: 10px; background: #002200;")
        lbl_h.setAlignment(Qt.AlignCenter)
        vbox.addWidget(lbl_h)

        # Azimuth Control
        grp_az = QGroupBox("DIRECTOR CONTROL")
        az_layout = QVBoxLayout(grp_az)

        self.lbl_az = QLabel("AZIMUTH: 000°")
        self.lbl_az.setAlignment(Qt.AlignCenter)
        self.lbl_az.setStyleSheet("font-size: 24px; font-weight: bold; color: #00FFFF;")
        az_layout.addWidget(self.lbl_az)

        self.dial = QDial()
        self.dial.setRange(0, 359)
        self.dial.setNotchesVisible(True)
        self.dial.setWrapping(True)
        self.dial.setFixedSize(150, 150)
        self.dial.valueChanged.connect(self.update_azimuth)

        # Center the dial
        h_dial = QHBoxLayout()
        h_dial.addStretch()
        h_dial.addWidget(self.dial)
        h_dial.addStretch()
        az_layout.addLayout(h_dial)

        vbox.addWidget(grp_az)

        # Status Display
        self.lbl_safety = QLabel("SECTOR CLEAR")
        self.lbl_safety.setAlignment(Qt.AlignCenter)
        self.lbl_safety.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #00FF00; background: #222; padding: 10px;")
        vbox.addWidget(self.lbl_safety)

        # FIRE BUTTON
        self.btn_jam = QPushButton("INITIATE JAMMING")
        self.btn_jam.setFixedHeight(100)
        self.btn_jam.setStyleSheet(self.get_btn_style("READY"))
        self.btn_jam.pressed.connect(self.start_jamming)
        self.btn_jam.released.connect(self.stop_jamming)
        vbox.addWidget(self.btn_jam)

        layout.addWidget(ctrl_panel)

        # --- RIGHT: VISUALS & DATA ---
        right_panel = QVBoxLayout()

        # Compass View
        self.compass = CompassDial(self.logic)

        h_comp = QHBoxLayout()
        h_comp.addStretch()
        h_comp.addWidget(self.compass)
        h_comp.addStretch()
        right_panel.addLayout(h_comp)

        # Database View
        grp_db = QGroupBox("RESTRICTED FREQUENCY/AZIMUTH ZONES")
        db_layout = QVBoxLayout(grp_db)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["START", "END", "DESIGNATION"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.populate_table()

        db_layout.addWidget(self.table)
        right_panel.addWidget(grp_db)

        layout.addLayout(right_panel)

    def populate_table(self):
        self.table.setRowCount(0)
        for zone in self.logic.zones:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(f"{zone['start']}°"))
            self.table.setItem(r, 1, QTableWidgetItem(f"{zone['end']}°"))
            self.table.setItem(r, 2, QTableWidgetItem(zone['name']))

    def update_azimuth(self, val):
        self.lbl_az.setText(f"AZIMUTH: {val:03d}°")
        self.compass.set_angle(val)

        # Real-time safety check
        safe, msg = self.logic.check_safety(val)

        if safe:
            self.lbl_safety.setText("SECTOR CLEAR")
            self.lbl_safety.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #00FF00; background: #222; padding: 10px;")
            self.btn_jam.setEnabled(True)
            self.btn_jam.setStyleSheet(self.get_btn_style("READY"))
            self.btn_jam.setText("INITIATE JAMMING")
        else:
            self.lbl_safety.setText(f"SAFETY LOCK: {msg}")
            self.lbl_safety.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #FFF; background: #B71C1C; padding: 10px;")
            self.btn_jam.setEnabled(False)  # Hardware Lockout
            self.btn_jam.setStyleSheet(self.get_btn_style("LOCKED"))
            self.btn_jam.setText("FIRING DISABLED")

    def start_jamming(self):
        # Double Check (Redundancy)
        az = self.dial.value()
        safe, msg = self.logic.check_safety(az)

        if safe:
            self.btn_jam.setText("JAMMING ACTIVE")
            self.btn_jam.setStyleSheet(self.get_btn_style("FIRING"))
            self.compass.is_jamming = True
            self.compass.update()
        else:
            # Should be disabled, but just in case
            self.stop_jamming()

    def stop_jamming(self):
        # Reset text based on current safety
        self.compass.is_jamming = False
        self.compass.update()
        self.update_azimuth(self.dial.value())

    def get_btn_style(self, state):
        if state == "READY":
            return """
                QPushButton {
                    background-color: #333; color: #DDD;
                    border: 2px solid #555; border-radius: 10px;
                    font-size: 20px; font-weight: bold;
                }
                QPushButton:hover { border: 2px solid #00FFFF; color: #FFF; }
            """
        elif state == "FIRING":
            return """
                QPushButton {
                    background-color: #D32F2F; color: #FFF;
                    border: 4px solid #FF0000; border-radius: 10px;
                    font-size: 24px; font-weight: bold;
                }
            """
        elif state == "LOCKED":
            return """
                QPushButton {
                    background-color: #111; color: #555;
                    border: 2px dashed #555; border-radius: 10px;
                    font-size: 20px; font-weight: bold;
                }
            """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JammerConsole()
    window.show()
    sys.exit(app.exec_())
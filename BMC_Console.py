import sys
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGridLayout,
                             QFrame, QGroupBox, QPlainTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette


# --- Custom UI Components ---

class StatusLED(QFrame):
    """A circular status indicator (Green/Red/Yellow)."""

    def __init__(self, label_text):
        super().__init__()
        self.setFixedSize(120, 60)
        self.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.led = QLabel()
        self.led.setFixedSize(20, 20)
        self.led.setStyleSheet("background-color: #333; border-radius: 10px; border: 1px solid #555;")

        self.label = QLabel(label_text)
        self.label.setFont(QFont("Consolas", 10, QFont.Bold))
        self.label.setStyleSheet("color: #AAA;")

        layout.addWidget(self.led)
        layout.addWidget(self.label)
        layout.addStretch()

    def set_status(self, status):
        colors = {
            "ONLINE": "#00FF00",  # Bright Green
            "OFFLINE": "#FF0000",  # Red
            "WARNING": "#FFDD00",  # Yellow
            "STANDBY": "#555555"  # Grey
        }
        col = colors.get(status, "#555")
        # Add a "glow" effect via border
        self.led.setStyleSheet(f"""
            background-color: {col}; 
            border-radius: 10px; 
            border: 2px solid {col};
            box-shadow: 0 0 10px {col};
        """)
        self.label.setText(f"{self.label.text().split(':')[0]}: {status}")
        self.label.setStyleSheet(f"color: {col};")


class MissileCell(QLabel):
    """Visual representation of a single interceptor in the canister."""

    def __init__(self, id):
        super().__init__()
        self.id = id
        self.setFixedSize(30, 60)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: #004400; 
            border: 1px solid #00FF00; 
            border-radius: 4px;
            color: #00FF00;
            font-size: 8px;
        """)
        self.setText(f"M-{id}")
        self.active = True

    def set_spent(self):
        self.active = False
        self.setStyleSheet("""
            background-color: #222; 
            border: 1px solid #444; 
            color: #444;
        """)
        self.setText("EMPTY")

    def reset(self):
        self.active = True
        self.setStyleSheet("""
            background-color: #004400; 
            border: 1px solid #00FF00; 
            color: #00FF00;
        """)
        self.setText(f"M-{self.id}")


# --- Main Console Application ---

class BMCConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IRON DOME // BATTLE MANAGEMENT CONSOLE (BMC)")
        self.setGeometry(100, 100, 1200, 750)

        # Apply Military Dark Theme
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QGroupBox { 
                border: 1px solid #444; 
                margin-top: 10px; 
                font-family: Consolas;
                font-weight: bold;
                color: #888;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { font-family: Consolas; }
            QPushButton { font-family: Consolas; font-weight: bold; }
        """)

        # System State
        self.ammo_count = 20
        self.safety_locked = True  # Default to Safety ON
        self.missile_widgets = []

        self.init_ui()

        # Simulate background system checks
        self.sys_timer = QTimer()
        self.sys_timer.timeout.connect(self.system_heartbeat)
        self.sys_timer.start(2000)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- LEFT COLUMN: STATUS & COMMS ---
        left_panel = QVBoxLayout()

        # 1. System Health
        grp_status = QGroupBox("SYSTEM DIAGNOSTICS")
        status_layout = QVBoxLayout(grp_status)

        self.led_radar = StatusLED("RADAR LINK")
        self.led_comms = StatusLED("BMC UPLINK")
        self.led_launcher = StatusLED("LAUNCHER")
        self.led_power = StatusLED("MAIN POWER")

        status_layout.addWidget(self.led_power)
        status_layout.addWidget(self.led_radar)
        status_layout.addWidget(self.led_comms)
        status_layout.addWidget(self.led_launcher)

        # Initial States
        self.led_power.set_status("ONLINE")
        self.led_radar.set_status("ONLINE")
        self.led_comms.set_status("ONLINE")
        self.led_launcher.set_status("READY")

        left_panel.addWidget(grp_status)

        # 2. Event Log
        grp_log = QGroupBox("TACTICAL LOG")
        log_layout = QVBoxLayout(grp_log)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            background-color: #000; 
            color: #00FF00; 
            border: none; 
            font-family: Consolas; 
            font-size: 10px;
        """)
        log_layout.addWidget(self.log_view)
        left_panel.addWidget(grp_log)

        main_layout.addLayout(left_panel, 30)

        # --- CENTER COLUMN: AMMO & FIRE CONTROL ---
        center_panel = QVBoxLayout()

        # 1. Ammo Grid
        grp_ammo = QGroupBox(f"INTERCEPTOR INVENTORY ({self.ammo_count}/20)")
        self.grp_ammo_ref = grp_ammo  # Keep ref to update title
        ammo_layout = QGridLayout(grp_ammo)
        ammo_layout.setSpacing(5)

        for i in range(20):
            m = MissileCell(i + 1)
            self.missile_widgets.append(m)
            row = i // 5
            col = i % 5
            ammo_layout.addWidget(m, row, col)

        center_panel.addWidget(grp_ammo)

        # 2. Warning Label
        self.lbl_warning = QLabel("SYSTEM READY")
        self.lbl_warning.setAlignment(Qt.AlignCenter)
        self.lbl_warning.setFixedHeight(40)
        self.lbl_warning.setStyleSheet(
            "background-color: #222; color: #555; font-weight: bold; font-size: 16px; border-radius: 5px;")
        center_panel.addWidget(self.lbl_warning)

        # 3. The Big Buttons
        ctrl_layout = QHBoxLayout()

        self.btn_fire = QPushButton("ENGAGE TARGET")
        self.btn_fire.setFixedHeight(80)
        self.btn_fire.setStyleSheet(self.get_fire_style(enabled=False))
        self.btn_fire.clicked.connect(self.fire_mission)

        ctrl_layout.addWidget(self.btn_fire)
        center_panel.addLayout(ctrl_layout)

        # Reload Button (Hidden mostly)
        self.btn_reload = QPushButton("INITIATE RELOAD SEQUENCE")
        self.btn_reload.setStyleSheet("background-color: #444; color: #AAA; padding: 10px;")
        self.btn_reload.clicked.connect(self.reload_ammo)
        center_panel.addWidget(self.btn_reload)

        main_layout.addLayout(center_panel, 40)

        # --- RIGHT COLUMN: SAFETY & OVERRIDE ---
        right_panel = QVBoxLayout()

        grp_safety = QGroupBox("SAFETY INTERLOCKS")
        safety_layout = QVBoxLayout(grp_safety)

        # The Safety Switch
        self.btn_safety = QPushButton("SAFETY: LOCKED")
        self.btn_safety.setCheckable(True)
        self.btn_safety.setChecked(True)  # Start Locked
        self.btn_safety.setFixedHeight(100)
        self.btn_safety.clicked.connect(self.toggle_safety)
        self.update_safety_style()

        safety_layout.addWidget(self.btn_safety)

        info_lbl = QLabel(
            "MAN-IN-THE-LOOP CONTROL\n\nWhen LOCKED, firing circuit is physically broken.\n\nOverride only for imminent threat.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #666; font-size: 11px; margin-top: 10px;")
        safety_layout.addWidget(info_lbl)

        safety_layout.addStretch()
        right_panel.addWidget(grp_safety)

        main_layout.addLayout(right_panel, 30)

    # --- LOGIC ---

    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {message}")

    def system_heartbeat(self):
        # Occasionally simulate a radar flicker for realism
        import random
        if random.random() < 0.1:
            self.led_radar.set_status("WARNING")
            self.log("SYS: Radar Handshake High Latency")
            QTimer.singleShot(1000, lambda: self.led_radar.set_status("ONLINE"))

    def toggle_safety(self):
        self.safety_locked = self.btn_safety.isChecked()

        if self.safety_locked:
            self.btn_safety.setText("SAFETY: LOCKED")
            self.log("OP: Safety Interlock ENGAGED. Firing Disabled.")
            self.lbl_warning.setText("SYSTEM SAFE")
            self.lbl_warning.setStyleSheet("background-color: #222; color: #555; font-weight: bold; font-size: 16px;")
        else:
            self.btn_safety.setText("SAFETY: OVERRIDE\n(ARMED)")
            self.log("OP: *** SAFETY OVERRIDE ACTIVE *** System Armed.")
            self.lbl_warning.setText("⚠️ WEAPONS FREE ⚠️")
            self.lbl_warning.setStyleSheet(
                "background-color: #FF0000; color: #FFF; font-weight: bold; font-size: 16px; border-radius: 5px;")

        self.update_safety_style()
        self.update_fire_button()

    def update_safety_style(self):
        if self.safety_locked:
            # Green/Safe Look
            self.btn_safety.setStyleSheet("""
                QPushButton {
                    background-color: #1b5e20;
                    color: #a5d6a7;
                    border: 2px solid #2e7d32;
                    border-radius: 10px;
                    font-size: 18px;
                }
            """)
        else:
            # Red/Danger Look with Stripes
            self.btn_safety.setStyleSheet("""
                QPushButton {
                    background-color: #b71c1c;
                    color: #FFF;
                    border: 4px solid #ff5252;
                    border-radius: 10px;
                    font-size: 18px;
                }
            """)

    def update_fire_button(self):
        # Fire button is only active if Safety is OFF and Ammo > 0
        is_armed = not self.safety_locked and self.ammo_count > 0
        self.btn_fire.setStyleSheet(self.get_fire_style(enabled=is_armed))
        self.btn_fire.setEnabled(is_armed)

    def get_fire_style(self, enabled):
        if enabled:
            return """
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    font-size: 20px;
                    border: 2px solid #ff5252;
                    border-radius: 5px;
                }
                QPushButton:pressed { background-color: #ff0000; }
            """
        else:
            return """
                QPushButton {
                    background-color: #333;
                    color: #555;
                    font-size: 20px;
                    border: 2px solid #444;
                    border-radius: 5px;
                }
            """

    def fire_mission(self):
        if self.safety_locked:
            self.log("ERR: Firing blocked by Safety Interlock.")
            return

        if self.ammo_count <= 0:
            self.log("ERR: Launcher Empty.")
            return

        # Find first active missile
        for m in self.missile_widgets:
            if m.active:
                m.set_spent()
                self.ammo_count -= 1
                self.log(f"CMD: Tamir Interceptor {m.id} Launched. Tracking...")
                break

        # Update Header
        self.grp_ammo_ref.setTitle(f"INTERCEPTOR INVENTORY ({self.ammo_count}/20)")

        # Check Empty State
        if self.ammo_count == 0:
            self.log("ALERT: MAGAZINE EMPTY. RELOAD REQUIRED.")
            self.lbl_warning.setText("MAGAZINE EMPTY")
            self.lbl_warning.setStyleSheet("background-color: #FFDD00; color: #000;")
            self.update_fire_button()

    def reload_ammo(self):
        if not self.safety_locked:
            self.log("ERR: Cannot reload while Safety Override is active.")
            return

        self.log("MAINT: Reloading canister...")
        self.ammo_count = 20
        self.grp_ammo_ref.setTitle(f"INTERCEPTOR INVENTORY ({self.ammo_count}/20)")
        for m in self.missile_widgets:
            m.reset()
        self.lbl_warning.setText("SYSTEM SAFE")
        self.lbl_warning.setStyleSheet("background-color: #222; color: #555;")
        self.log("MAINT: Reload Complete. 20/20 Ready.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BMCConsole()
    window.show()
    sys.exit(app.exec_())
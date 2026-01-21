import sys
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QMessageBox, QGridLayout, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont, QColor, QPalette

# --- Configuration ---
SCRAMBLE_TIME_SECONDS = 300  # 5 Minutes
LOG_FILE = "scramble_log.txt"

# --- Styles ---
STYLE_IDLE = "color: #555; background-color: #222; border: 2px solid #444;"
STYLE_ACTIVE = "color: #FFF; background-color: #000; border: 2px solid #FFF;"
STYLE_DONE = "color: #000; background-color: #00FF00; border: 2px solid #00FF00; font-weight: bold;"


class ScrambleDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QRA COMMAND DASHBOARD - SECTOR 7")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #1a1a1a;")

        # State
        self.time_remaining = SCRAMBLE_TIME_SECONDS
        self.timer_active = False
        self.current_stage = 0  # 0=Idle, 1=Pilots, 2=Engines, 3=Taxi, 4=Airborne

        self.init_ui()

        # Logic Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_tick)

        # Flasher for Alarm
        self.flash_state = False
        self.flash_timer = QTimer()
        self.flash_timer.timeout.connect(self.flash_ui)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # --- HEADER ---
        self.lbl_status = QLabel("STATUS: STANDBY")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont("Arial Black", 32))
        self.lbl_status.setStyleSheet("color: #00FF00; letter-spacing: 5px;")
        main_layout.addWidget(self.lbl_status)

        # --- THE COUNTDOWN ---
        self.lbl_timer = QLabel("05:00")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        self.lbl_timer.setFont(QFont("Consolas", 120, QFont.Bold))
        self.lbl_timer.setStyleSheet(
            "color: #333; background-color: #111; border: 5px solid #333; border-radius: 20px;")
        main_layout.addWidget(self.lbl_timer)

        # --- CONTROLS (CHECKLIST) ---
        checklist_group = QGroupBox("INTERCEPT SEQUENCE CHECKLIST")
        checklist_group.setStyleSheet("color: #AAA; font-weight: bold; border: 1px solid #444; margin-top: 20px;")
        c_layout = QHBoxLayout(checklist_group)
        c_layout.setContentsMargins(20, 30, 20, 30)
        c_layout.setSpacing(20)

        # Button 1: Pilots
        self.btn_pilots = QPushButton("1. PILOTS IN COCKPIT")
        self.btn_pilots.setFixedSize(200, 100)
        self.btn_pilots.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_pilots.setStyleSheet(STYLE_IDLE)
        self.btn_pilots.setEnabled(False)
        self.btn_pilots.clicked.connect(self.stage_pilots)
        c_layout.addWidget(self.btn_pilots)

        # Button 2: Engines
        self.btn_engines = QPushButton("2. ENGINES START")
        self.btn_engines.setFixedSize(200, 100)
        self.btn_engines.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_engines.setStyleSheet(STYLE_IDLE)
        self.btn_engines.setEnabled(False)
        self.btn_engines.clicked.connect(self.stage_engines)
        c_layout.addWidget(self.btn_engines)

        # Button 3: Taxi
        self.btn_taxi = QPushButton("3. TAXI TO RUNWAY")
        self.btn_taxi.setFixedSize(200, 100)
        self.btn_taxi.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_taxi.setStyleSheet(STYLE_IDLE)
        self.btn_taxi.setEnabled(False)
        self.btn_taxi.clicked.connect(self.stage_taxi)
        c_layout.addWidget(self.btn_taxi)

        # Button 4: Takeoff
        self.btn_takeoff = QPushButton("4. WHEELS UP (COMPLETE)")
        self.btn_takeoff.setFixedSize(200, 100)
        self.btn_takeoff.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_takeoff.setStyleSheet(STYLE_IDLE)
        self.btn_takeoff.setEnabled(False)
        self.btn_takeoff.clicked.connect(self.stage_takeoff)
        c_layout.addWidget(self.btn_takeoff)

        main_layout.addWidget(checklist_group)

        # --- THE BIG BUTTON ---
        self.btn_scramble = QPushButton("INITIATE SCRAMBLE")
        self.btn_scramble.setFixedHeight(80)
        self.btn_scramble.setFont(QFont("Arial Black", 20))
        self.btn_scramble.setStyleSheet("""
            QPushButton { background-color: #B71C1C; color: white; border: 4px solid #FF5252; border-radius: 10px; }
            QPushButton:hover { background-color: #FF0000; }
            QPushButton:pressed { background-color: #550000; border: 4px solid #880000; }
        """)
        self.btn_scramble.clicked.connect(self.start_scramble)
        main_layout.addWidget(self.btn_scramble)

    # --- LOGIC ---

    def start_scramble(self):
        if self.timer_active: return  # Already running

        # Reset State
        self.time_remaining = SCRAMBLE_TIME_SECONDS
        self.current_stage = 1
        self.timer_active = True

        # UI Updates
        self.btn_scramble.setEnabled(False)
        self.btn_scramble.setStyleSheet("background-color: #333; color: #555; border: none;")
        self.btn_scramble.setText("SCRAMBLE IN PROGRESS")

        self.lbl_status.setText("⚠️ ALERT: SCRAMBLE! SCRAMBLE! ⚠️")
        self.lbl_status.setStyleSheet("color: #FF0000; letter-spacing: 5px;")

        # Start Clock
        self.update_clock_display(QColor("#FF0000"))  # Red Start
        self.timer.start(1000)  # 1 second tick

        # Start Alarm Flash
        self.flash_timer.start(500)

        # Unlock Step 1
        self.btn_pilots.setEnabled(True)
        self.btn_pilots.setStyleSheet(STYLE_ACTIVE)

        self.log_event("SCRAMBLE INITIATED")

    def update_tick(self):
        self.time_remaining -= 1

        # Dynamic Color Shift based on urgency/progress
        # We handle specific colors in stage transitions,
        # but here we ensure red if running out of time.
        if self.time_remaining < 60:
            self.lbl_timer.setStyleSheet(
                "color: #FF0000; background-color: #220000; border: 5px solid #FF0000; border-radius: 20px;")

        if self.time_remaining <= 0:
            self.fail_mission()
        else:
            # Refresh text
            mins = self.time_remaining // 60
            secs = self.time_remaining % 60
            self.lbl_timer.setText(f"{mins:02}:{secs:02}")

    def update_clock_display(self, color):
        mins = self.time_remaining // 60
        secs = self.time_remaining % 60
        self.lbl_timer.setText(f"{mins:02}:{secs:02}")
        col_str = color.name()
        self.lbl_timer.setStyleSheet(
            f"color: {col_str}; background-color: #111; border: 5px solid {col_str}; border-radius: 20px;")

    def flash_ui(self):
        # Flash the Header text Red/White
        self.flash_state = not self.flash_state
        if self.flash_state:
            self.lbl_status.setStyleSheet("color: #FF0000; letter-spacing: 5px;")
        else:
            self.lbl_status.setStyleSheet("color: #FFFFFF; letter-spacing: 5px;")

    # --- STAGES ---

    def stage_pilots(self):
        self.btn_pilots.setEnabled(False)
        self.btn_pilots.setStyleSheet(STYLE_DONE)

        # Unlock Next
        self.btn_engines.setEnabled(True)
        self.btn_engines.setStyleSheet(STYLE_ACTIVE)

        # Change Timer visual (Yellow - Progressing)
        self.update_clock_display(QColor("#FFEB3B"))
        self.log_event("Step 1 Complete: Pilots Seated")

    def stage_engines(self):
        self.btn_engines.setEnabled(False)
        self.btn_engines.setStyleSheet(STYLE_DONE)

        # Unlock Next
        self.btn_taxi.setEnabled(True)
        self.btn_taxi.setStyleSheet(STYLE_ACTIVE)

        # Change Timer visual (Orange - Getting Hot)
        self.update_clock_display(QColor("#FF9800"))
        self.log_event("Step 2 Complete: Engines Spooling")

    def stage_taxi(self):
        self.btn_taxi.setEnabled(False)
        self.btn_taxi.setStyleSheet(STYLE_DONE)

        # Unlock Next
        self.btn_takeoff.setEnabled(True)
        self.btn_takeoff.setStyleSheet(STYLE_ACTIVE)

        # Change Timer visual (Light Green - Almost there)
        self.update_clock_display(QColor("#64DD17"))
        self.log_event("Step 3 Complete: Taxiing to Runway")

    def stage_takeoff(self):
        # Stop everything - SUCCESS
        self.timer.stop()
        self.flash_timer.stop()
        self.timer_active = False

        self.btn_takeoff.setEnabled(False)
        self.btn_takeoff.setStyleSheet(STYLE_DONE)

        # Visuals
        self.lbl_status.setText("MISSION ACTIVE: AIRBORNE")
        self.lbl_status.setStyleSheet("color: #00FFFF; letter-spacing: 5px;")

        final_time = SCRAMBLE_TIME_SECONDS - self.time_remaining
        mins = final_time // 60
        secs = final_time % 60
        self.lbl_timer.setText(f"RT: {mins:02}:{secs:02}")
        self.lbl_timer.setStyleSheet(
            "color: #00FFFF; background-color: #003333; border: 5px solid #00FFFF; border-radius: 20px;")

        self.log_event(f"MISSION SUCCESS. Reaction Time: {mins:02}:{secs:02}")

        # Enable reset
        self.btn_scramble.setText("RESET SYSTEM")
        self.btn_scramble.setEnabled(True)
        self.btn_scramble.clicked.disconnect()
        self.btn_scramble.clicked.connect(self.reset_system)

    def fail_mission(self):
        self.timer.stop()
        self.flash_timer.stop()
        self.timer_active = False

        self.lbl_timer.setText("00:00")
        self.lbl_status.setText("!!! MISSION FAILURE !!!")
        self.lbl_status.setStyleSheet("color: #FF0000; font-weight: bold; background-color: #330000;")

        self.log_event("MISSION FAILED: TIMEOUT")

        QMessageBox.critical(self, "FAILURE",
                             "SCRAMBLE TIMEOUT.\nAircraft failed to launch within 5 minutes.\nIncident logged.")

        self.btn_scramble.setText("RESET SYSTEM")
        self.btn_scramble.setEnabled(True)
        self.btn_scramble.clicked.disconnect()
        self.btn_scramble.clicked.connect(self.reset_system)

    def reset_system(self):
        # Reset Logic
        self.btn_scramble.clicked.disconnect()
        self.btn_scramble.clicked.connect(self.start_scramble)
        self.btn_scramble.setText("INITIATE SCRAMBLE")
        self.btn_scramble.setStyleSheet("""
            QPushButton { background-color: #B71C1C; color: white; border: 4px solid #FF5252; border-radius: 10px; }
            QPushButton:hover { background-color: #FF0000; }
        """)

        self.lbl_status.setText("STATUS: STANDBY")
        self.lbl_status.setStyleSheet("color: #00FF00; letter-spacing: 5px; background: transparent;")

        self.lbl_timer.setText("05:00")
        self.lbl_timer.setStyleSheet(
            "color: #333; background-color: #111; border: 5px solid #333; border-radius: 20px;")

        # Reset Buttons
        for btn in [self.btn_pilots, self.btn_engines, self.btn_taxi, self.btn_takeoff]:
            btn.setEnabled(False)
            btn.setStyleSheet(STYLE_IDLE)

    def log_event(self, message):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] {message}\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrambleDashboard()
    window.show()
    sys.exit(app.exec_())
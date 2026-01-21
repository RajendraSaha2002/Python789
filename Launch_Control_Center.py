import sys
import time
import random
from enum import Enum, auto
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGridLayout,
                             QFrame, QMessageBox, QProgressBar, QGroupBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QKeySequence, QFontDatabase


# --- 1. State Machine Architecture ---

class MissionState(Enum):
    OFF = auto()
    IDLE = auto()  # Power On, waiting
    BIT_CHECK = auto()  # Built-in Test running
    READY = auto()  # Systems Green
    ARMED = auto()  # Safety Keys turned
    COUNTDOWN = auto()  # T-minus sequence
    LAUNCHED = auto()  # Success
    ABORTED = auto()  # Failure/Safety trip


# --- 2. Asynchronous Workers ---

class CountdownWorker(QThread):
    """Handles the T-Minus 10s logic without freezing the GUI."""
    tick = pyqtSignal(int)
    finished = pyqtSignal()
    aborted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.t_minus = 10

    def run(self):
        while self.t_minus >= 0 and self.is_running:
            # Simulate random system fault
            if self.t_minus > 0 and random.random() < 0.05:  # 5% chance per tick
                self.is_running = False
                self.aborted.emit("CRITICAL: HYDRAULIC PRESSURE LOSS")
                return

            self.tick.emit(self.t_minus)
            time.sleep(1.0)
            self.t_minus -= 1

        if self.is_running:
            self.finished.emit()

    def abort(self):
        self.is_running = False


class BitWorker(QThread):
    """Simulates the Built-in Test (BIT) sequence."""
    update_led = pyqtSignal(int)  # Index of LED to turn green
    finished = pyqtSignal(bool)  # True = Pass, False = Fail

    def run(self):
        # Check 20 systems
        for i in range(20):
            time.sleep(0.15)  # Simulate check time
            if random.random() < 0.02:  # 2% chance of hardware failure
                self.finished.emit(False)
                return
            self.update_led.emit(i)
        self.finished.emit(True)


# --- 3. GUI Components ---

class LedIndicator(QLabel):
    """Custom 'Physical' LED Widget."""

    def __init__(self, label_text):
        super().__init__()
        self.setFixedSize(100, 40)
        self.label_text = label_text
        self.status = "OFF"
        self.update_style()
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Consolas", 8, QFont.Bold))

    def set_status(self, status):
        # status: "OFF", "RED", "GREEN", "YELLOW"
        self.status = status
        self.update_style()

    def update_style(self):
        color_map = {
            "OFF": "#333",
            "RED": "#D32F2F",
            "GREEN": "#388E3C",
            "YELLOW": "#FBC02D"
        }
        bg = color_map.get(self.status, "#333")
        text_col = "#FFF" if self.status != "OFF" else "#555"

        # CSS Styling for "Glass" LED look
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {text_col};
                border: 2px solid #111;
                border-radius: 5px;
                padding: 2px;
            }}
        """)
        self.setText(self.label_text)


class LaunchControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRATEGIC COMMAND - LAUNCH CONTROL")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #222; color: #EEE;")

        # State
        self.current_state = MissionState.OFF
        self.pressed_keys = set()
        self.leds = []

        # System Names
        self.systems = [
            "MAIN BUS A", "MAIN BUS B", "GUIDANCE", "GYRO STAB",
            "GPS LINK", "TELEM UPLINK", "FUEL PRES", "OXIDIZER",
            "HYDRAULICS", "PYROTECHNICS", "WARHEAD", "FUSING",
            "DOOR HATCH", "RAIL LOCK", "COOLING", "COMM LINK",
            "RADAR ALT", "TARGET LOCK", "WEATHER", "SECURITY"
        ]

        self.init_ui()
        self.change_state(MissionState.OFF)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)

        # --- HEADER ---
        header = QFrame()
        header.setStyleSheet("background-color: #111; border-bottom: 2px solid #444;")
        h_layout = QHBoxLayout(header)

        self.lbl_state = QLabel("SYSTEM OFF")
        self.lbl_state.setFont(QFont("Arial Black", 24))
        self.lbl_state.setStyleSheet("color: #555;")

        self.lbl_timer = QLabel("T-MINUS: 00")
        self.lbl_timer.setFont(QFont("Courier New", 32, QFont.Bold))
        self.lbl_timer.setStyleSheet("color: #D32F2F;")

        h_layout.addWidget(self.lbl_state)
        h_layout.addStretch()
        h_layout.addWidget(self.lbl_timer)
        layout.addWidget(header)

        # --- STATUS PANEL (LED GRID) ---
        grid_frame = QGroupBox("SYSTEM STATUS INDICATORS")
        grid_frame.setStyleSheet("font-weight: bold; border: 1px solid #444; margin-top: 10px;")
        grid_layout = QGridLayout(grid_frame)

        for i, name in enumerate(self.systems):
            led = LedIndicator(name)
            self.leds.append(led)
            row = i // 5
            col = i % 5
            grid_layout.addWidget(led, row, col)

        layout.addWidget(grid_frame)

        # --- CONTROL DECK ---
        controls = QFrame()
        controls.setStyleSheet("background-color: #2A2A2A; border-top: 2px solid #555;")
        c_layout = QHBoxLayout(controls)
        c_layout.setContentsMargins(30, 30, 30, 30)

        # Power Switch
        self.btn_power = QPushButton("MASTER POWER")
        self.btn_power.setCheckable(True)
        self.btn_power.setStyleSheet(self.get_btn_style("grey"))
        self.btn_power.clicked.connect(self.toggle_power)
        c_layout.addWidget(self.btn_power)

        # BIT Button
        self.btn_bit = QPushButton("RUN BIT SEQUENCE")
        self.btn_bit.setStyleSheet(self.get_btn_style("blue"))
        self.btn_bit.clicked.connect(self.run_bit)
        c_layout.addWidget(self.btn_bit)

        # Arm Switch
        self.btn_arm = QPushButton("ARM SYSTEM")
        self.btn_arm.setCheckable(True)
        self.btn_arm.setStyleSheet(self.get_btn_style("orange"))
        self.btn_arm.toggled.connect(self.toggle_arm)
        c_layout.addWidget(self.btn_arm)

        c_layout.addStretch()

        # The Launch Button (Big Red Button)
        self.btn_launch = QPushButton("INITIATE LAUNCH\n(REQ: CTRL + SHIFT)")
        self.btn_launch.setFixedSize(200, 100)
        self.btn_launch.setStyleSheet(self.get_btn_style("red_big"))
        self.btn_launch.clicked.connect(self.attempt_launch)
        c_layout.addWidget(self.btn_launch)

        layout.addWidget(controls)

    def get_btn_style(self, color):
        base = """
            QPushButton {
                border: 2px solid #111;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                color: white;
                padding: 15px;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #555;
            }
        """
        colors = {
            "grey": "background-color: #444;",
            "grey_checked": "background-color: #4CAF50;",
            "blue": "background-color: #1976D2;",
            "orange": "background-color: #FF9800;",
            "orange_checked": "background-color: #D32F2F; border: 3px solid #FFEB3B;",  # Flashing hazard style
            "red_big": "background-color: #B71C1C; font-size: 16px; border-radius: 50px;"
        }

        if color == "red_big":
            return base + colors["red_big"]
        return base + colors[color]

    # --- LOGIC & STATE MACHINE ---

    def change_state(self, new_state):
        self.current_state = new_state
        state_name = new_state.name.replace("_", " ")
        self.lbl_state.setText(f"STATUS: {state_name}")

        # UI Logic based on state
        if new_state == MissionState.OFF:
            self.lbl_state.setStyleSheet("color: #555;")
            self.reset_leds("OFF")
            self.btn_bit.setEnabled(False)
            self.btn_arm.setEnabled(False)
            self.btn_launch.setEnabled(False)

        elif new_state == MissionState.IDLE:
            self.lbl_state.setStyleSheet("color: #FFF;")
            self.reset_leds("RED")  # All systems unchecked
            self.btn_bit.setEnabled(True)
            self.btn_arm.setEnabled(False)
            self.btn_launch.setEnabled(False)

        elif new_state == MissionState.BIT_CHECK:
            self.lbl_state.setStyleSheet("color: #2196F3;")
            self.btn_power.setEnabled(False)
            self.btn_bit.setEnabled(False)

        elif new_state == MissionState.READY:
            self.lbl_state.setStyleSheet("color: #4CAF50;")
            self.btn_power.setEnabled(True)
            self.btn_arm.setEnabled(True)

        elif new_state == MissionState.ARMED:
            self.lbl_state.setStyleSheet("color: #FF9800;")
            self.btn_bit.setEnabled(False)
            self.btn_launch.setEnabled(True)  # Unlocked but requires keys

        elif new_state == MissionState.COUNTDOWN:
            self.lbl_state.setStyleSheet("color: #F44336; font-size: 32px;")
            self.btn_power.setEnabled(False)
            self.btn_arm.setEnabled(False)
            self.btn_launch.setEnabled(False)

        elif new_state == MissionState.LAUNCHED:
            self.lbl_state.setStyleSheet("color: #4CAF50;")
            self.lbl_timer.setText("LAUNCH SUCCESS")
            self.reset_leds("GREEN")

        elif new_state == MissionState.ABORTED:
            self.lbl_state.setStyleSheet("color: #B71C1C;")
            self.reset_leds("RED")
            self.btn_power.setEnabled(True)
            self.btn_power.setChecked(False)  # Force full reset

    # --- ACTIONS ---

    def toggle_power(self, checked):
        if checked:
            self.btn_power.setStyleSheet(self.get_btn_style("grey_checked"))
            self.change_state(MissionState.IDLE)
        else:
            self.btn_power.setStyleSheet(self.get_btn_style("grey"))
            self.change_state(MissionState.OFF)

    def run_bit(self):
        self.change_state(MissionState.BIT_CHECK)
        self.bit_thread = BitWorker()
        self.bit_thread.update_led.connect(self.set_led_green)
        self.bit_thread.finished.connect(self.bit_complete)
        self.bit_thread.start()

    def set_led_green(self, index):
        self.leds[index].set_status("GREEN")

    def bit_complete(self, success):
        if success:
            self.change_state(MissionState.READY)
        else:
            QMessageBox.critical(self, "BIT FAILURE", "Hardware integrity check failed. Restart required.")
            self.change_state(MissionState.IDLE)

    def reset_leds(self, status):
        for led in self.leds:
            led.set_status(status)

    def toggle_arm(self, checked):
        if self.current_state not in [MissionState.READY, MissionState.ARMED]:
            self.btn_arm.setChecked(False)
            return

        if checked:
            self.btn_arm.setStyleSheet(self.get_btn_style("orange_checked"))
            self.change_state(MissionState.ARMED)
        else:
            self.btn_arm.setStyleSheet(self.get_btn_style("orange"))
            self.change_state(MissionState.READY)

    # --- TWO-MAN RULE (KEYBOARD INPUT) ---

    def keyPressEvent(self, event):
        self.pressed_keys.add(event.key())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in self.pressed_keys:
            self.pressed_keys.remove(event.key())
        super().keyReleaseEvent(event)

    def check_dual_keys(self):
        # Requires CTRL (16777249) + SHIFT (16777248) keys to be held
        # These are standard Qt Key codes
        keys = self.pressed_keys
        has_ctrl = (Qt.Key_Control in keys)
        has_shift = (Qt.Key_Shift in keys)
        return has_ctrl and has_shift

    def attempt_launch(self):
        if self.current_state != MissionState.ARMED: return

        # Verify Two-Man Rule
        if self.check_dual_keys():
            self.start_countdown()
        else:
            QMessageBox.warning(self, "AUTHORIZATION ERROR",
                                "Dual-Key Authorization Failed.\n\n"
                                "Hold CTRL + SHIFT (Simulating Two-Man Keys)\n"
                                "while pressing the Launch Button.")

    # --- COUNTDOWN ---

    def start_countdown(self):
        self.change_state(MissionState.COUNTDOWN)
        self.cd_thread = CountdownWorker()
        self.cd_thread.tick.connect(self.update_timer)
        self.cd_thread.aborted.connect(self.abort_launch)
        self.cd_thread.finished.connect(self.launch_success)
        self.cd_thread.start()

    def update_timer(self, val):
        self.lbl_timer.setText(f"T-MINUS: {val:02d}")
        # Blink LEDs yellow during countdown
        if val % 2 == 0:
            self.reset_leds("YELLOW")
        else:
            self.reset_leds("GREEN")

    def abort_launch(self, reason):
        self.change_state(MissionState.ABORTED)
        QMessageBox.critical(self, "LAUNCH ABORT", f"SEQUENCE HALTED.\nReason: {reason}")
        self.lbl_timer.setText("ABORT")

    def launch_success(self):
        self.change_state(MissionState.LAUNCHED)
        QMessageBox.information(self, "MISSION STATUS", "Projectile successfully deployed.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Custom Font attempt (falls back if not present)
    # Note: Requires QFontDatabase, not QFont
    font_id = QFontDatabase.addApplicationFont(":/fonts/Consolas.ttf")

    window = LaunchControlPanel()
    window.show()
    sys.exit(app.exec_())
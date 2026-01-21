import sys
import logging
import random
from enum import Enum, auto
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QProgressBar,
                             QTextEdit, QFrame, QMessageBox, QGroupBox, QSlider, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor

# --- 1. System Engineering: The Logic Core ---

# Configure Black Box Recorder (Logging)
# In a real system, this writes to a secure, write-only memory module.
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("blackbox_recorder.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


class ChainState(Enum):
    SCANNING = auto()  # Idle
    DETECT = auto()  # Raw Contact
    TRACK = auto()  # Stable Vector
    IDENTIFY = auto()  # IFF Check
    LOCK = auto()  # Fire Control Radar Lock
    AUTHORIZE = auto()  # Commander Key Turn
    ENGAGE = auto()  # Weapon Release


class KillChainViolation(Exception):
    """Raised when an illegal state transition is attempted."""
    pass


class SafetyInterlock(QObject):
    """
    The rigorous State Machine that enforces the Kill Chain.
    This logic is isolated from the GUI.
    """
    state_changed = pyqtSignal(ChainState)
    alert_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_state = ChainState.SCANNING
        self.track_quality = 0.0  # 0 to 100
        self.target_data = {}

    def set_track_quality(self, val):
        self.track_quality = val
        # Watchdog Logic: Auto-Abort if quality drops
        if self.current_state != ChainState.SCANNING and self.track_quality < 50:
            self.abort("CRITICAL SIGNAL LOSS (Track Quality < 50%)")

    def process_action(self, action):
        """
        The Gatekeeper.
        Takes a requested action, validates it against current state,
        and either transitions or raises an Error.
        """
        try:
            if action == "NEW_CONTACT":
                if self.current_state == ChainState.SCANNING:
                    self._transition(ChainState.DETECT, "Radar Contact Established")
                else:
                    pass  # Ignore new contacts while busy

            elif action == "ESTABLISH_TRACK":
                if self.current_state == ChainState.DETECT:
                    if self.track_quality > 60:
                        self._transition(ChainState.TRACK, "Track Vector Stabilized")
                    else:
                        raise KillChainViolation("Signal too weak to track.")
                elif self.current_state.value > ChainState.TRACK.value:
                    pass  # Already tracking
                else:
                    raise KillChainViolation(f"Cannot Track from {self.current_state.name}")

            elif action == "IDENTIFY_FRIEND_FOE":
                if self.current_state == ChainState.TRACK:
                    # Simulate IFF Logic
                    iff_result = "HOSTILE"  # Hardcoded for sim
                    self._transition(ChainState.IDENTIFY, f"IFF Response: {iff_result}")
                else:
                    raise KillChainViolation("Target must be Tracked before ID.")

            elif action == "RADAR_LOCK":
                if self.current_state == ChainState.IDENTIFY:
                    self._transition(ChainState.LOCK, "Fire Control Radar: LOCKED")
                else:
                    raise KillChainViolation("Cannot Lock unidentified target (ROE Violation).")

            elif action == "AUTHORIZE_LAUNCH":
                if self.current_state == ChainState.LOCK:
                    self._transition(ChainState.AUTHORIZE, "Commander Auth Verified.")
                else:
                    raise KillChainViolation("Cannot Authorize without Radar Lock.")

            elif action == "FIRE_WEAPON":
                if self.current_state == ChainState.AUTHORIZE:
                    self._transition(ChainState.ENGAGE, "FOX-3! Missile Away.")
                    # Reset after fire
                    QTimer.singleShot(3000, self.reset_system)
                else:
                    # THE CRITICAL CHECK
                    raise KillChainViolation(f"FATAL: FIRE INTERLOCK ACTIVE. Current State: {self.current_state.name}")

            elif action == "ABORT":
                self.abort("Operator Manual Abort")

        except KillChainViolation as e:
            logging.error(f"ILLEGAL OPERATION: {e}")
            self.alert_signal.emit(str(e))

    def _transition(self, new_state, reason):
        logging.info(f"TRANSITION: {self.current_state.name} -> {new_state.name} | Reason: {reason}")
        self.current_state = new_state
        self.state_changed.emit(new_state)

    def abort(self, reason):
        logging.warning(f"ABORT SEQUENCE INITIATED: {reason}")
        self.current_state = ChainState.SCANNING
        self.state_changed.emit(ChainState.SCANNING)
        self.alert_signal.emit(f"RESET: {reason}")

    def reset_system(self):
        self.current_state = ChainState.SCANNING
        self.state_changed.emit(ChainState.SCANNING)
        logging.info("System Reset to SCANNING.")


# --- 2. The Commander's Interface (GUI) ---

class StateIndicator(QLabel):
    def __init__(self, name, active_color="#00FF00"):
        super().__init__(name)
        self.active_color = active_color
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(50)
        self.setFont(QFont("Consolas", 12, QFont.Bold))
        self.set_inactive()

    def set_active(self):
        self.setStyleSheet(f"background-color: {self.active_color}; color: black; border: 2px solid white;")

    def set_inactive(self):
        self.setStyleSheet("background-color: #222; color: #555; border: 1px solid #444;")


class KillChainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AEGIS COMBAT SYSTEM // KILL CHAIN MONITOR")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #121212; color: #EEE;")

        self.logic = SafetyInterlock()
        self.logic.state_changed.connect(self.update_ui_state)
        self.logic.alert_signal.connect(self.show_alert)

        self.indicators = {}

        self.init_ui()

        # Simulate Radar Noise
        self.noise_timer = QTimer()
        self.noise_timer.timeout.connect(self.sim_radar_noise)
        self.noise_timer.start(500)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: THE CHAIN (Visual Flow) ---
        chain_panel = QFrame()
        chain_panel.setFixedWidth(300)
        chain_panel.setStyleSheet("background-color: #1a1a1a; border-right: 2px solid #333;")
        cp_layout = QVBoxLayout(chain_panel)

        lbl_chain = QLabel("ENGAGEMENT SEQUENCE")
        lbl_chain.setStyleSheet("font-size: 16px; font-weight: bold; color: #AAA;")
        cp_layout.addWidget(lbl_chain)

        # Create Stack of States
        states = [
            (ChainState.SCANNING, "1. SCANNING", "#AAAAAA"),
            (ChainState.DETECT, "2. DETECT", "#00FFFF"),
            (ChainState.TRACK, "3. TRACK", "#0088FF"),
            (ChainState.IDENTIFY, "4. IDENTIFY", "#FFFF00"),
            (ChainState.LOCK, "5. LOCK", "#FF8800"),
            (ChainState.AUTHORIZE, "6. AUTHORIZE", "#FF4400"),
            (ChainState.ENGAGE, "7. ENGAGE", "#FF0000")
        ]

        for state_enum, label, col in states:
            ind = StateIndicator(label, col)
            self.indicators[state_enum] = ind
            cp_layout.addWidget(ind)

            # Arrow
            if state_enum != ChainState.ENGAGE:
                arrow = QLabel("⬇")
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setStyleSheet("color: #444; font-weight: bold;")
                cp_layout.addWidget(arrow)

        cp_layout.addStretch()
        layout.addWidget(chain_panel)

        # --- RIGHT: CONTROLS & TELEMETRY ---
        control_panel = QVBoxLayout()
        control_panel.setContentsMargins(20, 20, 20, 20)

        # 1. Telemetry Box
        grp_telemetry = QGroupBox("TRACK TELEMETRY")
        grp_telemetry.setStyleSheet("border: 1px solid #444; font-weight: bold; color: #00FF00;")
        t_layout = QVBoxLayout(grp_telemetry)

        self.lbl_signal = QLabel("SIGNAL QUALITY: 0%")
        self.bar_signal = QProgressBar()
        self.bar_signal.setStyleSheet("""
            QProgressBar { border: 1px solid #444; background: #222; height: 20px; text-align: center; }
            QProgressBar::chunk { background-color: #00FF00; }
        """)

        # Slider to simulate jamming/loss
        self.slider_qual = QSlider(Qt.Horizontal)
        self.slider_qual.setRange(0, 100)
        self.slider_qual.setValue(0)
        self.slider_qual.valueChanged.connect(self.update_signal_quality)

        t_layout.addWidget(self.lbl_signal)
        t_layout.addWidget(self.bar_signal)
        t_layout.addWidget(QLabel("SIGNAL SIMULATOR (Drag to Test Abort Logic):"))
        t_layout.addWidget(self.slider_qual)

        control_panel.addWidget(grp_telemetry)

        # 2. Command Buttons
        grp_cmd = QGroupBox("COMMAND AUTHORITY")
        grp_cmd.setStyleSheet("border: 1px solid #444; font-weight: bold; color: #AAA;")
        c_layout = QGridLayout(grp_cmd)

        # We allow clicking buttons out of order to demonstrate the logic blocking it
        btn_detect = QPushButton("INIT TRACK")
        btn_detect.clicked.connect(lambda: self.logic.process_action("ESTABLISH_TRACK"))

        btn_id = QPushButton("QUERY IFF")
        btn_id.clicked.connect(lambda: self.logic.process_action("IDENTIFY_FRIEND_FOE"))

        btn_lock = QPushButton("RADAR LOCK")
        btn_lock.setStyleSheet("color: #FF8800;")
        btn_lock.clicked.connect(lambda: self.logic.process_action("RADAR_LOCK"))

        btn_auth = QPushButton("GRANT AUTH")
        btn_auth.clicked.connect(lambda: self.logic.process_action("AUTHORIZE_LAUNCH"))

        btn_fire = QPushButton("FIRE WEAPON")
        btn_fire.setFixedSize(150, 80)
        btn_fire.setStyleSheet(
            "background-color: #330000; color: #555; font-weight: bold; font-size: 16px; border: 2px solid #550000;")
        btn_fire.clicked.connect(lambda: self.logic.process_action("FIRE_WEAPON"))
        self.btn_fire_ref = btn_fire

        btn_abort = QPushButton("MANUAL ABORT")
        btn_abort.setStyleSheet("background-color: #444; color: white;")
        btn_abort.clicked.connect(lambda: self.logic.process_action("ABORT"))

        c_layout.addWidget(btn_detect, 0, 0)
        c_layout.addWidget(btn_id, 0, 1)
        c_layout.addWidget(btn_lock, 1, 0)
        c_layout.addWidget(btn_auth, 1, 1)
        c_layout.addWidget(btn_fire, 0, 2, 2, 1)
        c_layout.addWidget(btn_abort, 2, 0, 1, 3)

        control_panel.addWidget(grp_cmd)

        # 3. Black Box Log
        grp_log = QGroupBox("BLACK BOX RECORDER")
        grp_log.setStyleSheet("border: 1px solid #444; font-weight: bold; color: #AAA;")
        l_layout = QVBoxLayout(grp_log)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #000; color: #0F0; font-family: Courier;")

        l_layout.addWidget(self.log_view)
        control_panel.addWidget(grp_log)

        layout.addLayout(control_panel)

    # --- SIMULATION INPUTS ---

    def sim_radar_noise(self):
        # Randomly spawn a contact if scanning
        if self.logic.current_state == ChainState.SCANNING:
            if random.random() < 0.1:  # 10% chance
                self.logic.process_action("NEW_CONTACT")
                # Auto set signal strong for the "Demo"
                self.slider_qual.setValue(90)

    def update_signal_quality(self, val):
        self.bar_signal.setValue(val)
        self.lbl_signal.setText(f"SIGNAL QUALITY: {val}%")
        self.logic.set_track_quality(val)

        # Visual color for bar
        col = "#00FF00" if val > 50 else "#FF0000"
        self.bar_signal.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #444; background: #222; height: 20px; text-align: center; color: white; }}
            QProgressBar::chunk {{ background-color: {col}; }}
        """)

    # --- UI UPDATES ---

    def update_ui_state(self, state):
        # Update Chain Indicators
        for s_enum, widget in self.indicators.items():
            if s_enum == state:
                widget.set_active()
            elif s_enum.value < state.value:
                # Previous completed states
                widget.setStyleSheet(f"background-color: #224422; color: #888; border: 1px solid #444;")
            else:
                widget.set_inactive()

        # Update Fire Button
        if state == ChainState.AUTHORIZE:
            self.btn_fire_ref.setStyleSheet(
                "background-color: #b71c1c; color: white; font-weight: bold; font-size: 16px; border: 2px solid red;")
            self.btn_fire_ref.setEnabled(True)
        else:
            self.btn_fire_ref.setStyleSheet(
                "background-color: #330000; color: #555; font-weight: bold; font-size: 16px; border: 2px solid #550000;")

        # Log to GUI
        self.log_view.append(f"STATUS UPDATE: Entered {state.name} State.")

    def show_alert(self, msg):
        self.log_view.append(f"!!! ALERT: {msg} !!!")
        # Flash visual (Optional)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KillChainGUI()
    window.show()
    sys.exit(app.exec_())
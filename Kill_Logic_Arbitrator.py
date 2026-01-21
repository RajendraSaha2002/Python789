import sys
import random
from dataclasses import dataclass
from enum import Enum, auto

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QSpinBox, QCheckBox, QGroupBox, QTextEdit, QFrame,
                             QDial, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor


# --- 1. The Rules Engine (Backend Logic) ---

class GuidanceType(Enum):
    IR = auto()  # Infrared (Heat)
    RADAR = auto()  # Active Radar (RF)


@dataclass
class WeaponProfile:
    name: str
    guidance: GuidanceType
    max_range_nm: float
    min_range_nm: float
    all_aspect: bool  # If False, requires tail chase
    pk_base: float  # Base Probability of Kill (0.0 - 1.0)


# Weapon Database
ARMORY = {
    "AIM-9M (Legacy Sidewinder)": WeaponProfile("AIM-9M", GuidanceType.IR, 10.0, 0.5, False, 0.70),
    "AIM-9X (Modern Sidewinder)": WeaponProfile("AIM-9X", GuidanceType.IR, 18.0, 0.2, True, 0.90),
    "AIM-120C (AMRAAM)": WeaponProfile("AIM-120C", GuidanceType.RADAR, 55.0, 2.0, True, 0.85),
    "R-73 (Archer)": WeaponProfile("R-73", GuidanceType.IR, 16.0, 0.3, True, 0.80),
    "R-77 (Adder)": WeaponProfile("R-77", GuidanceType.RADAR, 50.0, 2.0, True, 0.82)
}


class ArbitratorEngine:
    """
    The Referee Logic.
    Determines outcome based on Rules of Engagement and Physics constraints.
    """

    @staticmethod
    def evaluate_shot(weapon_name, range_nm, aspect_deg, target_flares, target_chaff, target_maneuver):
        wpn = ARMORY[weapon_name]
        log = []
        result = "HIT"
        color = "#00FF00"  # Green

        log.append(f"--- SHOT EVALUATION: {weapon_name} ---")
        log.append(f"Geometry: Range {range_nm}nm | Aspect {aspect_deg}°")

        # RULE 1: KINEMATIC RANGE
        if range_nm > wpn.max_range_nm:
            return "MISS", "#FF0000", log + [f"FAIL: Target out of aerodynamic range (> {wpn.max_range_nm}nm)."]
        if range_nm < wpn.min_range_nm:
            return "MISS", "#FF0000", log + [f"FAIL: Target inside arming distance (< {wpn.min_range_nm}nm)."]

        log.append("PASS: Kinematic Range OK.")

        # RULE 2: ASPECT ANGLE
        # Aspect 0 = Tail Chase, 180 = Head On
        # Legacy IR missiles cannot lock onto the nose of a jet (no heat).
        if not wpn.all_aspect:
            if aspect_deg > 60:  # 60 degree cone from tail
                return "MISS", "#FF0000", log + [f"FAIL: Sensor requires Rear Aspect (Current: {aspect_deg}°)."]

        log.append("PASS: Seeker Field of View OK.")

        # RULE 3: COUNTERMEASURES (The Dice Roll)
        # Calculate PK (Probability of Kill)
        current_pk = wpn.pk_base * 100  # Convert to percentage

        # Flares vs IR
        if wpn.guidance == GuidanceType.IR and target_flares:
            log.append("DEFENSE: Target deployed FLARES against IR Seeker.")
            penalty = 40 if wpn.name == "AIM-9M" else 20  # Modern seekers resist flares better
            current_pk -= penalty
            log.append(f"   -> Pk reduced by {penalty}%")

        # Chaff vs Radar
        if wpn.guidance == GuidanceType.RADAR and target_chaff:
            log.append("DEFENSE: Target deployed CHAFF against RF Seeker.")
            current_pk -= 30
            log.append(f"   -> Pk reduced by 30%")

        # Maneuvering (High G turn)
        if target_maneuver:
            log.append("DEFENSE: Target pulling High-G Break.")
            current_pk -= 15
            log.append("   -> Pk reduced by 15%")

        # Final Calculation
        log.append(f"FINAL PROBABILITY OF KILL: {current_pk}%")

        # The RNG (Random Number Generator) God
        dice_roll = random.randint(0, 100)
        log.append(f"RNG DICE ROLL: {dice_roll}")

        if dice_roll <= current_pk:
            log.append(">>> SPLASH. TARGET DESTROYED. <<<")
            return "KILL", "#00FF00", log
        else:
            reason = "Spoofed by CM" if (target_flares or target_chaff) else "Missile Malfunction/Miss"
            log.append(f">>> MISS. ({reason}) <<<")
            return "MISS", "#FFA500", log


# --- 2. The Referee Console (GUI) ---

class RefereeConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIR WARFARE SIMULATION ARBITRATOR")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #222; color: #EEE; font-family: Consolas; }
            QGroupBox { font-weight: bold; border: 1px solid #555; margin-top: 10px; color: #4CAF50; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { font-size: 12px; }
            QComboBox, QSpinBox { background-color: #333; color: white; padding: 5px; border: 1px solid #555; }
            QCheckBox { spacing: 10px; font-weight: bold; }
            QCheckBox::indicator { width: 15px; height: 15px; }
            QTextEdit { background-color: #111; color: #0F0; border: 1px solid #333; font-family: Monospace; }
        """)

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: SETUP PANEL ---
        setup_layout = QVBoxLayout()

        # 1. Attacker Setup
        grp_blue = QGroupBox("BLUE FORCE (ATTACKER)")
        blue_layout = QVBoxLayout(grp_blue)

        blue_layout.addWidget(QLabel("Aircraft Type:"))
        self.combo_jet = QComboBox()
        self.combo_jet.addItems(["F-15C Eagle", "F-22 Raptor", "F/A-18 Super Hornet", "F-16 Viper"])
        blue_layout.addWidget(self.combo_jet)

        blue_layout.addWidget(QLabel("Selected Weapon:"))
        self.combo_weapon = QComboBox()
        self.combo_weapon.addItems(ARMORY.keys())
        blue_layout.addWidget(self.combo_weapon)

        setup_layout.addWidget(grp_blue)

        # 2. Geometry Setup
        grp_geo = QGroupBox("ENGAGEMENT GEOMETRY")
        geo_layout = QVBoxLayout(grp_geo)

        # Range
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Range (nautical miles):"))
        self.spin_range = QSpinBox()
        self.spin_range.setRange(0, 100)
        self.spin_range.setValue(15)
        range_layout.addWidget(self.spin_range)
        geo_layout.addLayout(range_layout)

        # Aspect Dial (Visual)
        geo_layout.addWidget(QLabel("Target Aspect Angle:"))
        self.dial_aspect = QDial()
        self.dial_aspect.setRange(0, 180)
        self.dial_aspect.setNotchesVisible(True)
        self.dial_aspect.setValue(180)  # Head on default
        self.dial_aspect.valueChanged.connect(self.update_aspect_label)
        geo_layout.addWidget(self.dial_aspect)

        self.lbl_aspect = QLabel("180° (HEAD ON)")
        self.lbl_aspect.setAlignment(Qt.AlignCenter)
        self.lbl_aspect.setStyleSheet("font-weight: bold; color: #FFF;")
        geo_layout.addWidget(self.lbl_aspect)

        setup_layout.addWidget(grp_geo)

        # 3. Target Setup
        grp_red = QGroupBox("RED FORCE (DEFENDER)")
        red_layout = QVBoxLayout(grp_red)

        red_layout.addWidget(QLabel("Defensive Measures:"))
        self.chk_flares = QCheckBox("Deploy Flares")
        self.chk_flares.setStyleSheet("color: #FF5555;")
        self.chk_chaff = QCheckBox("Deploy Chaff")
        self.chk_chaff.setStyleSheet("color: #55FFFF;")
        self.chk_maneuver = QCheckBox("High-G Break Turn")
        self.chk_maneuver.setStyleSheet("color: #FFFF55;")

        red_layout.addWidget(self.chk_flares)
        red_layout.addWidget(self.chk_chaff)
        red_layout.addWidget(self.chk_maneuver)

        setup_layout.addWidget(grp_red)

        # Fire Button
        self.btn_fire = QPushButton("VALIDATE SHOT")
        self.btn_fire.setFixedHeight(60)
        self.btn_fire.setStyleSheet("""
            QPushButton { background-color: #D32F2F; color: white; font-weight: bold; font-size: 16px; border-radius: 5px; }
            QPushButton:hover { background-color: #FF4444; }
        """)
        self.btn_fire.clicked.connect(self.process_shot)
        setup_layout.addWidget(self.btn_fire)

        layout.addLayout(setup_layout, 1)

        # --- RIGHT: EVENT LOG ---
        log_layout = QVBoxLayout()

        # Header
        lbl_log = QLabel("ENGAGEMENT LOG (DEBRIEF)")
        lbl_log.setStyleSheet("font-size: 16px; font-weight: bold; color: #AAA;")
        log_layout.addWidget(lbl_log)

        # Text Area
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)

        # Status Box
        self.status_box = QLabel("READY")
        self.status_box.setFixedHeight(80)
        self.status_box.setAlignment(Qt.AlignCenter)
        self.status_box.setFont(QFont("Arial Black", 24))
        self.status_box.setStyleSheet("background-color: #333; color: #AAA; border: 2px solid #555;")
        log_layout.addWidget(self.status_box)

        layout.addLayout(log_layout, 2)

    def update_aspect_label(self, val):
        desc = ""
        if val < 30:
            desc = "(TAIL CHASE)"
        elif val > 150:
            desc = "(HEAD ON)"
        else:
            desc = "(BEAM/SIDE)"
        self.lbl_aspect.setText(f"{val}° {desc}")

    def process_shot(self):
        # 1. Gather Inputs
        weapon = self.combo_weapon.currentText()
        rng = self.spin_range.value()
        aspect = self.dial_aspect.value()
        flares = self.chk_flares.isChecked()
        chaff = self.chk_chaff.isChecked()
        maneuver = self.chk_maneuver.isChecked()

        jet = self.combo_jet.currentText()

        # 2. Add Header to Log
        self.log_view.append("\n" + "=" * 40)
        self.log_view.append(f"EVENT: {jet} FIRES {weapon}")
        self.log_view.append("=" * 40)

        # 3. Run Logic Engine
        outcome, color_hex, logs = ArbitratorEngine.evaluate_shot(weapon, rng, aspect, flares, chaff, maneuver)

        # 4. Update Log
        for line in logs:
            self.log_view.append(line)

        # 5. Update Big Status Box
        self.status_box.setText(outcome)
        self.status_box.setStyleSheet(
            f"background-color: {color_hex}33; color: {color_hex}; border: 3px solid {color_hex}; font-weight: bold;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RefereeConsole()
    window.show()
    sys.exit(app.exec_())
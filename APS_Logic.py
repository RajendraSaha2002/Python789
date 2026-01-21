import sys
import math
import random
from enum import Enum, auto

import PyQt5.QtWidgets
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QRadialGradient

# --- Configuration ---
RADAR_SIZE = 600
TANK_SIZE = 60
DETECTION_RANGE = 250
INTERCEPT_RANGE = 100
AMMO_PER_SECTOR = 2

# Colors
COL_BG = QColor("#101010")
COL_GRID = QColor("#004400")
COL_TANK = QColor("#4CAF50")
COL_THREAT = QColor("#FF3333")
COL_BLAST = QColor("#FFD700")
COL_TEXT = QColor("#00FF00")


# --- 1. The Logic Engine (State Machine) ---

class Sector(Enum):
    FRONT = 0
    LEFT = 1
    REAR = 2
    RIGHT = 3


class EngagementResult(Enum):
    SUCCESS = auto()
    FAIL_DISARMED = auto()
    FAIL_SAFETY_LOCK = auto()
    FAIL_EMPTY = auto()


class APSSystemLogic:
    """
    The Brain. Pure logic, no GUI code here.
    Enforces the 'Kill Chain' rules.
    """

    def __init__(self):
        self.master_arm = False
        self.infantry_safety_override = False  # If True, don't fire (Infantry nearby)

        # Ammo inventory
        self.ammo = {
            Sector.FRONT: AMMO_PER_SECTOR,
            Sector.LEFT: AMMO_PER_SECTOR,
            Sector.REAR: AMMO_PER_SECTOR,
            Sector.RIGHT: AMMO_PER_SECTOR
        }

    def attempt_intercept(self, sector):
        # RULE 1: SYSTEM ARMED?
        if not self.master_arm:
            return EngagementResult.FAIL_DISARMED

        # RULE 2: INFANTRY SAFETY?
        # Note: In this sim, "Safety Override ON" means safety logic is active (Don't Fire)
        if self.infantry_safety_override:
            return EngagementResult.FAIL_SAFETY_LOCK

        # RULE 3: AMMO CHECK?
        if self.ammo[sector] <= 0:
            return EngagementResult.FAIL_EMPTY

        # ACTION: FIRE
        self.ammo[sector] -= 1
        return EngagementResult.SUCCESS

    def reload(self):
        for s in self.ammo:
            self.ammo[s] = AMMO_PER_SECTOR


# --- 2. Physics Entities ---

class Projectile:
    def __init__(self):
        # Pick random angle
        self.angle_deg = random.randint(0, 359)
        self.angle_rad = math.radians(self.angle_deg)
        self.dist = DETECTION_RANGE + 50
        self.speed = 3.0
        self.active = True
        self.intercepted = False

        # Determine Sector based on angle
        # Qt Angles: 0 is East (Right), 90 is North (Front) -- wait, 0 is 3 oclock.
        # Let's map standard math angles to Sectors.
        # Front: 45 to 135
        # Left: 135 to 225
        # Rear: 225 to 315
        # Right: 315 to 45

        norm_angle = self.angle_deg % 360
        if 45 <= norm_angle < 135:
            self.sector = Sector.FRONT
        elif 135 <= norm_angle < 225:
            self.sector = Sector.LEFT
        elif 225 <= norm_angle < 315:
            self.sector = Sector.REAR
        else:
            self.sector = Sector.RIGHT

    def update(self):
        if not self.active: return
        self.dist -= self.speed
        if self.dist <= 0:
            self.active = False  # Impact


# --- 3. GUI Components ---

class RadarScope(QWidget):
    def __init__(self, logic_engine):
        super().__init__()
        self.setFixedSize(RADAR_SIZE, RADAR_SIZE)
        self.logic = logic_engine
        self.threats = []
        self.blasts = []  # (sector, timer)
        self.flash_timer = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # 1. Background
        painter.fillRect(0, 0, w, h, COL_BG)

        # 2. Grid & Sectors
        painter.setPen(QPen(COL_GRID, 1, Qt.DashLine))
        painter.drawEllipse(QPointF(cx, cy), INTERCEPT_RANGE, INTERCEPT_RANGE)  # Hard Kill Zone
        painter.drawEllipse(QPointF(cx, cy), DETECTION_RANGE, DETECTION_RANGE)  # Detection Zone

        # Sector Lines (X shape)
        painter.drawLine(0, 0, w, h)
        painter.drawLine(0, h, w, 0)

        # 3. Draw Tank Hull
        painter.setBrush(QBrush(COL_TANK))
        painter.setPen(Qt.NoPen)
        tank_rect = QRectF(cx - TANK_SIZE / 2, cy - TANK_SIZE / 2, TANK_SIZE, TANK_SIZE)
        painter.drawRect(tank_rect)
        # Turret
        painter.setBrush(QBrush(QColor("#2E7D32")))
        painter.drawEllipse(QPointF(cx, cy), TANK_SIZE / 2.5, TANK_SIZE / 2.5)

        # 4. Draw Threats
        for t in self.threats:
            if not t.active: continue

            # Polar to Cartesian
            # Math: x = r * cos(theta), y = -r * sin(theta) (because screen Y is down)
            px = cx + t.dist * math.cos(math.radians(-t.angle_deg))
            py = cy + t.dist * math.sin(math.radians(-t.angle_deg))

            painter.setBrush(QBrush(COL_THREAT))
            painter.drawEllipse(QPointF(px, py), 5, 5)

            # Trail
            painter.setPen(QPen(COL_THREAT, 1))
            painter.drawLine(QPointF(px, py), QPointF(
                px + 20 * math.cos(math.radians(-t.angle_deg)),
                py + 20 * math.sin(math.radians(-t.angle_deg))
            ))

        # 5. Draw Active Blasts (Counter-measure firing)
        for i, (sector, timer) in enumerate(self.blasts):
            if timer > 0:
                self.draw_blast(painter, cx, cy, sector, timer)
                self.blasts[i] = (sector, timer - 1)

        # Remove old blasts
        self.blasts = [b for b in self.blasts if b[1] > 0]

    def draw_blast(self, painter, cx, cy, sector, timer):
        # Convert Sector to Angle
        # Front=90, Left=180... Qt DrawPie uses 16ths of degrees, 0 is 3 oclock (Right)
        # Angles: Right(0), Front(90), Left(180), Rear(270)
        start_angle = 0
        if sector == Sector.RIGHT:
            start_angle = -45
        elif sector == Sector.FRONT:
            start_angle = 45
        elif sector == Sector.LEFT:
            start_angle = 135
        elif sector == Sector.REAR:
            start_angle = 225

        # Opacity fades
        alpha = int((timer / 10) * 255)
        color = QColor(COL_BLAST)
        color.setAlpha(alpha)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        # drawPie(rect, startAngle * 16, spanAngle * 16)
        r = INTERCEPT_RANGE + 20
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        painter.drawPie(rect, start_angle * 16, 90 * 16)


class APSConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APS HARD-KILL CONTROL UNIT")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #222; color: #EEE; font-family: Consolas;")

        self.logic = APSSystemLogic()
        self.init_ui()

        # Simulation Loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_tick)
        self.timer.start(30)  # 30ms ~ 30fps

        # Threat Spawner
        self.spawn_timer = 0

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: RADAR ---
        self.radar = RadarScope(self.logic)
        layout.addWidget(self.radar)

        # --- RIGHT: CONTROLS ---
        controls = QWidget()
        controls.setFixedWidth(350)
        c_layout = QVBoxLayout(controls)

        # 1. Header
        lbl_head = QLabel("SYSTEM STATUS")
        lbl_head.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50; border-bottom: 2px solid #4CAF50;")
        c_layout.addWidget(lbl_head)

        # 2. Master Switches
        grp_switches = QGroupBox("INTERLOCKS")
        grp_switches.setStyleSheet("border: 1px solid #555; font-weight: bold;")
        sw_layout = QVBoxLayout(grp_switches)

        self.btn_arm = QPushButton("MASTER ARM: SAFE")
        self.btn_arm.setCheckable(True)
        self.btn_arm.setFixedHeight(50)
        self.btn_arm.clicked.connect(self.toggle_arm)
        self.update_arm_style()
        sw_layout.addWidget(self.btn_arm)

        self.chk_infantry = QCheckBox("INFANTRY SAFETY ZONE (NO FIRE)")
        self.chk_infantry.setStyleSheet("color: #FFDD00; font-size: 14px; padding: 10px;")
        self.chk_infantry.toggled.connect(self.toggle_infantry)
        sw_layout.addWidget(self.chk_infantry)

        c_layout.addWidget(grp_switches)

        # 3. Ammo Status
        grp_ammo = QGroupBox("COUNTERMEASURE INVENTORY")
        grp_ammo.setStyleSheet("border: 1px solid #555;")
        self.ammo_labels = {}
        am_layout = QGridLayout(grp_ammo)

        # Grid arrangement visually matching tank
        #       Front
        # Left  Tank  Right
        #       Rear

        self.create_ammo_lbl(am_layout, Sector.FRONT, 0, 1)
        self.create_ammo_lbl(am_layout, Sector.LEFT, 1, 0)
        self.create_ammo_lbl(am_layout, Sector.RIGHT, 1, 2)
        self.create_ammo_lbl(am_layout, Sector.REAR, 2, 1)

        btn_reload = QPushButton("RELOAD CANISTERS")
        btn_reload.setStyleSheet("background-color: #444; color: white; margin-top: 10px;")
        btn_reload.clicked.connect(self.do_reload)
        am_layout.addWidget(btn_reload, 3, 0, 1, 3)

        c_layout.addWidget(grp_ammo)

        # 4. Event Log
        c_layout.addWidget(QLabel("ENGAGEMENT LOG:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #000; color: #00FF00; border: 1px solid #333; font-size: 10px;")
        c_layout.addWidget(self.log_box)

        layout.addWidget(controls)

    def create_ammo_lbl(self, layout, sector, r, c):
        lbl = QLabel(f"{sector.name}\n[{AMMO_PER_SECTOR}]")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background-color: #004400; color: white; border: 1px solid #00FF00; padding: 10px;")
        self.ammo_labels[sector] = lbl
        layout.addWidget(lbl, r, c)

    def toggle_arm(self):
        self.logic.master_arm = self.btn_arm.isChecked()
        if self.logic.master_arm:
            self.btn_arm.setText("MASTER ARM: ARMED")
            self.log("SYSTEM ARMED. RADAR TRACKING.")
        else:
            self.btn_arm.setText("MASTER ARM: SAFE")
            self.log("SYSTEM DISARMED.")
        self.update_arm_style()

    def toggle_infantry(self):
        self.logic.infantry_safety_override = self.chk_infantry.isChecked()
        if self.logic.infantry_safety_override:
            self.log("SAFETY INTERLOCK: INFANTRY DETECTED. FIRING CIRCUITS OPEN.")
        else:
            self.log("SAFETY INTERLOCK: ZONE CLEAR.")

    def update_arm_style(self):
        if self.logic.master_arm:
            self.btn_arm.setStyleSheet(
                "background-color: #D32F2F; color: white; font-weight: bold; border: 2px solid red; font-size: 16px;")
        else:
            self.btn_arm.setStyleSheet(
                "background-color: #2E7D32; color: white; font-weight: bold; border: 2px solid #4CAF50; font-size: 16px;")

    def update_ammo_ui(self):
        for sector, count in self.logic.ammo.items():
            lbl = self.ammo_labels[sector]
            lbl.setText(f"{sector.name}\n[{count}]")
            if count > 0:
                lbl.setStyleSheet("background-color: #004400; color: white; border: 1px solid #00FF00;")
            else:
                lbl.setStyleSheet("background-color: #220000; color: #555; border: 1px solid #550000;")

    def do_reload(self):
        self.logic.reload()
        self.update_ammo_ui()
        self.log("MAINT: Canisters Reloaded.")

    def log(self, msg):
        self.log_box.append(f"> {msg}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def game_tick(self):
        # 1. Spawn Threats
        self.spawn_timer += 1
        if self.spawn_timer > 60:  # Every 2 seconds approx
            if random.random() < 0.4:
                self.radar.threats.append(Projectile())
                self.log("RADAR: Incoming Projectile Detected.")
            self.spawn_timer = 0

        # 2. Update Physics & Check Intercept
        for t in self.radar.threats:
            if not t.active: continue

            t.update()

            # TRIGGER LOGIC: If crosses Intercept Line
            if not t.intercepted and t.dist < INTERCEPT_RANGE:
                # Ask Logic Core for permission
                result = self.logic.attempt_intercept(t.sector)

                if result == EngagementResult.SUCCESS:
                    t.active = False
                    t.intercepted = True
                    self.radar.blasts.append((t.sector, 10))  # Visual blast for 10 frames
                    self.log(f"ENGAGED: Threat in {t.sector.name}. Hard Kill Confirmed.")
                    self.update_ammo_ui()

                elif result == EngagementResult.FAIL_DISARMED:
                    # Only log once per threat
                    if not hasattr(t, 'logged_fail'):
                        self.log(f"WARNING: Threat in {t.sector.name} IGNORED (System SAFE).")
                        t.logged_fail = True

                elif result == EngagementResult.FAIL_SAFETY_LOCK:
                    if not hasattr(t, 'logged_fail'):
                        self.log(f"CRITICAL: FIRE ABORTED {t.sector.name} (Infantry Safety).")
                        t.logged_fail = True

                elif result == EngagementResult.FAIL_EMPTY:
                    if not hasattr(t, 'logged_fail'):
                        self.log(f"CRITICAL: FAILURE {t.sector.name} (AMMO DEPLETED).")
                        t.logged_fail = True

            # Check Impact
            if t.active and t.dist <= 20:
                t.active = False
                self.log(f"!!! IMPACT DETECTED ON {t.sector.name} FLANK !!!")

        # Cleanup
        self.radar.threats = [t for t in self.radar.threats if t.active]
        self.radar.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = APSConsole()
    window.show()
    sys.exit(app.exec_())
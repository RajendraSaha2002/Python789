import sys
import random
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QFont, QBrush

# --- Configuration ---
SCENE_WIDTH = 2000
SCENE_HEIGHT = 600
COMM_VIEW_WIDTH = 800
GUNNER_VIEW_SIZE = 400
NUM_TARGETS = 8

# Colors
THERMAL_BLACK = QColor(20, 20, 20)
THERMAL_WHITE = QColor(230, 230, 230)  # Hot
RETICLE_COLOR = QColor(255, 0, 0)  # Red Overlay


# --- 1. Simulation Engine (Image Generator) ---

class ThermalGenerator:
    """
    Generates a synthetic thermal landscape with 'hot' targets.
    """

    @staticmethod
    def generate_landscape():
        # Create a blank image (numpy array logic simulated via QImage for simplicity)
        image = QImage(SCENE_WIDTH, SCENE_HEIGHT, QImage.Format_RGB32)
        image.fill(THERMAL_BLACK)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Draw Terrain (Cooler, dark grey)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(40, 40, 40))

        # Draw hills
        points = [QPointF(0, SCENE_HEIGHT)]
        for x in range(0, SCENE_WIDTH + 100, 100):
            y = SCENE_HEIGHT - 100 - random.randint(0, 200)
            points.append(QPointF(x, y))
        points.append(QPointF(SCENE_WIDTH, SCENE_HEIGHT))

        painter.drawPolygon(*points)

        # 2. Draw Targets (Hot/White Blobs)
        targets = []
        painter.setBrush(THERMAL_WHITE)

        for _ in range(NUM_TARGETS):
            # Pick a spot on the terrain roughly
            tx = random.randint(100, SCENE_WIDTH - 100)
            ty = random.randint(SCENE_HEIGHT - 250, SCENE_HEIGHT - 100)

            # Draw Tank shape (Hot Engine + Turret)
            w, h = 60, 30
            painter.drawRect(tx, ty, w, h)  # Hull
            painter.drawEllipse(tx + 15, ty - 10, 30, 15)  # Turret

            # Heat bloom (Glow effect simulated by circles)
            painter.setBrush(QColor(255, 255, 255, 50))
            painter.drawEllipse(tx - 10, ty - 20, w + 20, h + 40)
            painter.setBrush(THERMAL_WHITE)

            targets.append((tx + w / 2, ty + h / 2))  # Store center

        painter.end()
        return image, targets


# --- 2. Custom UI Widgets ---

class TacticalOverlay(QGraphicsView):
    """
    Base class for thermal sights. Adds Reticles and text.
    """

    def __init__(self, scene):
        super().__init__(scene)
        self.setStyleSheet("border: 2px solid #555; background-color: black;")
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # State
        self.is_slewing = False
        self.slew_target = None

    def drawForeground(self, painter, rect):
        """Draws the HUD overlay (Crosshairs) on top of the image."""
        painter.save()

        cx = rect.center().x()
        cy = rect.center().y()
        w = rect.width()
        h = rect.height()

        # Reticle Color
        pen = QPen(RETICLE_COLOR, 2)
        painter.setPen(pen)

        # Center Cross
        gap = 20
        length = 40
        painter.drawLine(int(cx - length), int(cy), int(cx - gap), int(cy))  # Left
        painter.drawLine(int(cx + gap), int(cy), int(cx + length), int(cy))  # Right
        painter.drawLine(int(cx), int(cy - length), int(cx), int(cy - gap))  # Top
        painter.drawLine(int(cx), int(cy + gap), int(cx), int(cy + length))  # Bottom

        # Box
        if self.is_slewing:
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.drawText(int(cx - 50), int(cy + 100), "SLEWING...")

        # Range Stadia lines
        painter.setPen(QPen(RETICLE_COLOR, 1))
        painter.drawLine(int(cx - 100), int(cy + 50), int(cx + 100), int(cy + 50))

        painter.restore()


class CommanderSight(TacticalOverlay):
    target_designated = pyqtSignal(float, float)  # Signal (x, y) to Gunner

    def __init__(self, scene):
        super().__init__(scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # "Hunter" Logic: Commander right-clicks to designate
            # Convert screen click to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Emit Signal (Handoff)
            self.target_designated.emit(scene_pos.x(), scene_pos.y())
        else:
            super().mousePressEvent(event)


class GunnerSight(TacticalOverlay):
    def __init__(self, scene):
        super().__init__(scene)
        # Gunner view is zoomed in
        self.scale(2.0, 2.0)
        self.setInteractive(False)  # Gunner doesn't drag, they get slewed

        # Slew Animation
        self.slew_timer = QTimer()
        self.slew_timer.timeout.connect(self.animate_slew)
        self.current_pos = QPointF(0, 0)
        self.target_pos = QPointF(0, 0)

    def slew_to(self, x, y):
        self.target_pos = QPointF(x, y)
        self.is_slewing = True
        self.slew_timer.start(20)  # 50 FPS

    def animate_slew(self):
        # Linear Interpolation (Lerp) for mechanical movement feel
        dx = self.target_pos.x() - self.current_pos.x()
        dy = self.target_pos.y() - self.current_pos.y()

        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist < 5:
            # Arrived
            self.current_pos = self.target_pos
            self.centerOn(self.current_pos)
            self.is_slewing = False
            self.slew_timer.stop()
        else:
            # Move 10% of distance + min speed
            speed = 0.1
            self.current_pos += QPointF(dx * speed, dy * speed)
            self.centerOn(self.current_pos)


# --- 3. Main Application ---

class HunterKillerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABRAMS HUNTER-KILLER INTERFACE")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #222; color: #EEE; font-family: Consolas;")

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- TOP HEADER ---
        header = QHBoxLayout()
        lbl_sys = QLabel("FIRE CONTROL SYSTEM: ONLINE")
        lbl_sys.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 16px;")
        header.addWidget(lbl_sys)
        header.addStretch()
        layout.addLayout(header)

        # --- GENERATE SCENE ---
        self.thermal_img, self.targets = ThermalGenerator.generate_landscape()
        self.pixmap = QPixmap.fromImage(self.thermal_img)
        self.scene = QGraphicsScene()
        self.scene.addItem(QGraphicsPixmapItem(self.pixmap))

        # --- SPLIT SCREEN VIEWS ---
        splitter = QSplitter(Qt.Vertical)

        # 1. COMMANDER VIEW (CITV)
        # Top window, wide view
        cmd_group = QGroupBox("COMMANDER'S INDEPENDENT THERMAL VIEWER (CITV)")
        cmd_group.setStyleSheet("font-weight: bold; color: #AAA; border: 1px solid #444;")
        cmd_layout = QVBoxLayout(cmd_group)

        self.view_cmd = CommanderSight(self.scene)
        self.view_cmd.setFixedHeight(300)
        # Fit logic
        self.view_cmd.fitInView(0, 0, SCENE_WIDTH, SCENE_HEIGHT, Qt.KeepAspectRatio)

        # Connect Handoff Signal
        self.view_cmd.target_designated.connect(self.perform_handoff)

        info_lbl = QLabel("INSTRUCTIONS: Drag to Scan. Right-Click a Hot Spot to HANDOFF to Gunner.")
        info_lbl.setStyleSheet("color: #AAA; font-size: 11px;")

        cmd_layout.addWidget(self.view_cmd)
        cmd_layout.addWidget(info_lbl)
        splitter.addWidget(cmd_group)

        # 2. GUNNER VIEW (GPS)
        # Bottom window, zoomed view
        gun_group = QGroupBox("GUNNER'S PRIMARY SIGHT (GPS)")
        gun_group.setStyleSheet("font-weight: bold; color: #AAA; border: 1px solid #444;")
        gun_layout = QVBoxLayout(gun_group)

        self.view_gun = GunnerSight(self.scene)
        # Center gunner initially
        self.view_gun.centerOn(SCENE_WIDTH / 2, SCENE_HEIGHT / 2)
        self.view_gun.current_pos = QPointF(SCENE_WIDTH / 2, SCENE_HEIGHT / 2)

        # Fire Control Panel
        fc_panel = QHBoxLayout()
        self.btn_fire = QPushButton("FIRE MAIN GUN")
        self.btn_fire.setFixedHeight(50)
        self.btn_fire.setStyleSheet(
            "background-color: #B71C1C; color: white; font-weight: bold; font-size: 18px; border: 2px solid red;")
        self.btn_fire.clicked.connect(self.fire_gun)

        self.lbl_status = QLabel("STATUS: OBSERVING")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")

        fc_panel.addWidget(self.lbl_status)
        fc_panel.addStretch()
        fc_panel.addWidget(self.btn_fire)

        gun_layout.addWidget(self.view_gun)
        gun_layout.addLayout(fc_panel)
        splitter.addWidget(gun_group)

        layout.addWidget(splitter)

    def perform_handoff(self, x, y):
        self.lbl_status.setText("STATUS: SLEWING TO COMMANDER DESIGNATION...")
        self.lbl_status.setStyleSheet("color: #FFFF00;")  # Yellow

        # Trigger the Gunner View to animate to x, y
        self.view_gun.slew_to(x, y)

        # After slew estimate (simple timer for status update)
        QTimer.singleShot(1000, lambda: self.update_status_ready())

    def update_status_ready(self):
        self.lbl_status.setText("STATUS: TARGET LOCKED")
        self.lbl_status.setStyleSheet("color: #FF0000;")  # Red

    def fire_gun(self):
        if self.view_gun.is_slewing:
            return  # Can't fire while moving

        self.lbl_status.setText("STATUS: ROUND AWAY")
        self.lbl_status.setStyleSheet("color: #FFFFFF; background-color: #B71C1C;")
        QTimer.singleShot(1500, lambda: self.update_status_ready())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HunterKillerApp()
    window.show()
    sys.exit(app.exec_())
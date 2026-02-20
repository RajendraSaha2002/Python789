import sys
import zmq
import psycopg2
import numpy as np
import time
import math
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

# CONFIG
DB_CONFIG = {"dbname": "postgres", "user": "postgres", "password": "varrie75", "host": "localhost"}
ZMQ_PORT = "5555"


class RadarEmitter(QThread):
    """Background thread that generates targets and broadcasts via ZeroMQ"""
    target_update = Signal(dict)

    def run(self):
        # 1. Setup ZMQ Publisher
        context = zmq.Context()
        publisher = context.socket(zmq.PUB)
        publisher.bind(f"tcp://*:{ZMQ_PORT}")
        print(f"📡 ZMQ Radar Publisher Active on Port {ZMQ_PORT}")

        # 2. Setup DB Connection
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
        except:
            print("DB Connection Failed")
            return

        angle = 0
        while True:
            # Physics Calculation (Circular Path)
            angle += 0.05
            distance = 200  # km
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)

            # Detect Threat logic (Simulated)
            is_threat = (int(angle * 10) % 50 == 0)  # Occasional threat
            obj_type = "BOGEY" if is_threat else "FRIENDLY"

            payload = {
                "type": obj_type,
                "x": x, "y": y,
                "alt": 25000,
                "speed": 900
            }

            # A. Log to Database (Async-ish)
            cur.execute("""
                        INSERT INTO radar_tracks (object_type, latitude, longitude, altitude_ft, speed_knots)
                        VALUES (%s, %s, %s, %s, %s)
                        """, (obj_type, x, y, 25000, 900))
            conn.commit()

            # B. Broadcast to Java (Instant)
            # Topic: "RADAR_CONTACT"
            msg = f"RADAR_CONTACT {obj_type} {x:.2f} {y:.2f}"
            publisher.send_string(msg)

            # C. Update Local GUI
            self.target_update.emit(payload)

            time.sleep(0.1)  # 10Hz Refresh Rate


class RadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_target = None
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: black;")

    def update_target(self, target):
        self.current_target = target
        self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center
        cx, cy = self.width() / 2, self.height() / 2

        # Draw Grid
        painter.setPen(QPen(QColor(0, 100, 0), 1))
        painter.drawEllipse(cx - 100, cy - 100, 200, 200)
        painter.drawEllipse(cx - 50, cy - 50, 100, 100)
        painter.drawLine(cx, 0, cx, self.height())
        painter.drawLine(0, cy, self.width(), cy)

        # Draw Sweep Line (Static for demo, normally rotates)
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        painter.drawLine(cx, cy, cx + 100, cy - 100)

        # Draw Target
        if self.current_target:
            tx = cx + (self.current_target['x'] * 0.5)  # Scale down
            ty = cy + (self.current_target['y'] * 0.5)

            if self.current_target['type'] == "BOGEY":
                painter.setBrush(QBrush(Qt.red))
                painter.setPen(Qt.red)
            else:
                painter.setBrush(QBrush(Qt.green))
                painter.setPen(Qt.green)

            painter.drawRect(tx, ty, 10, 10)
            painter.drawText(tx + 15, ty, self.current_target['type'])


class TacticalConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VAJRA-NET: TACTICAL SENSOR FUSION")
        self.resize(500, 600)

        layout = QVBoxLayout()

        self.label = QLabel("SENSOR STATUS: ACTIVE")
        self.label.setStyleSheet("color: #00FF00; font-size: 18px; font-weight: bold;")
        layout.addWidget(self.label)

        self.radar_display = RadarWidget()
        layout.addWidget(self.radar_display)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Start Thread
        self.thread = RadarEmitter()
        self.thread.target_update.connect(self.radar_display.update_target)
        self.thread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TacticalConsole()
    window.show()
    sys.exit(app.exec())
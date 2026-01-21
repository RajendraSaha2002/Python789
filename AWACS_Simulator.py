import sys
import random
import math
import re
import threading
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTextEdit,
                             QGroupBox, QLineEdit, QGraphicsView, QGraphicsScene,
                             QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QRectF
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter, QRadialGradient

# --- Audio Library ---
try:
    import speech_recognition as sr

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("WARNING: SpeechRecognition/PyAudio not found. Running in Text-Only mode.")

# --- Configuration ---
RADAR_RADIUS = 300
REFRESH_RATE = 50  # ms

# Colors
COL_BOGEY = QColor(255, 255, 0)  # Yellow (Unknown)
COL_HOSTILE = QColor(255, 0, 0)  # Red (Enemy)
COL_FRIENDLY = QColor(0, 255, 0)  # Green (Friend)
COL_NEUTRAL = QColor(255, 255, 255)  # White


# --- 1. The Logic: Command Parser ---

class BrevityParser:
    """
    Enforces strict military syntax for voice commands.
    """

    @staticmethod
    def parse(text):
        text = text.upper().strip()

        # Regex Patterns for Standard Commands
        # Pattern: "DECLARE TRACK [ID] [STATUS]"
        match_declare = re.search(
            r"(?:DECLARE|DESIGNATE|TAG)\s+TRACK\s+(\d+)\s+(AS\s+)?(HOSTILE|BANDIT|FRIENDLY|BOGEY|NEUTRAL)", text)

        # Pattern: "DROP TRACK [ID]"
        match_drop = re.search(r"(?:DROP|DELETE)\s+TRACK\s+(\d+)", text)

        if match_declare:
            track_id = int(match_declare.group(1))
            status_str = match_declare.group(3)

            # Normalize status
            if status_str in ["HOSTILE", "BANDIT"]: return ("UPDATE", track_id, "HOSTILE")
            if status_str == "FRIENDLY": return ("UPDATE", track_id, "FRIENDLY")
            if status_str == "BOGEY": return ("UPDATE", track_id, "BOGEY")
            if status_str == "NEUTRAL": return ("UPDATE", track_id, "NEUTRAL")

        if match_drop:
            track_id = int(match_drop.group(1))
            return ("DROP", track_id, None)

        return ("INVALID", None, None)


# --- 2. The Listener: Speech Recognition Thread ---

class VoiceListener(QThread):
    command_detected = pyqtSignal(str)  # The raw text
    status_update = pyqtSignal(str)  # Info like "Listening..."

    def __init__(self):
        super().__init__()
        self.running = False
        if AUDIO_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.mic = sr.Microphone()
            # Adjust for ambient noise once at startup
            with self.mic as source:
                self.status_update.emit("Calibrating Microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.status_update.emit("Mic Ready.")

    def run(self):
        if not AUDIO_AVAILABLE: return

        self.running = True
        with self.mic as source:
            while self.running:
                try:
                    self.status_update.emit("LISTENING (Speak Now)...")
                    # Listen with a timeout to allow the loop to check self.running
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)

                    self.status_update.emit("PROCESSING AUDIO...")
                    try:
                        # Use Google Web Speech API (Online) - default key included in library
                        text = self.recognizer.recognize_google(audio)
                        self.command_detected.emit(text)
                    except sr.UnknownValueError:
                        self.status_update.emit("Could not understand audio.")
                    except sr.RequestError:
                        self.status_update.emit("API Error (Check Internet).")

                except Exception as e:
                    # Usually happens on timeout/no speech, just loop
                    pass

    def stop(self):
        self.running = False


# --- 3. The Visuals: Radar Scope ---

class TrackItem(QGraphicsEllipseItem):
    def __init__(self, t_id, x, y):
        super().__init__(-6, -6, 12, 12)  # Centered dot
        self.t_id = t_id
        self.setPos(x, y)
        self.status = "BOGEY"  # Default

        # Visual setup
        self.setBrush(QBrush(COL_BOGEY))
        self.setPen(QPen(Qt.black, 1))

        # Label
        self.label = QGraphicsTextItem(f"T-{t_id}")
        self.label.setParentItem(self)
        self.label.setPos(8, -8)
        self.label.setDefaultTextColor(COL_BOGEY)
        self.label.setFont(QFont("Consolas", 10, QFont.Bold))

        # Vector
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)

    def update_status(self, new_status):
        self.status = new_status
        color = COL_BOGEY
        if new_status == "HOSTILE":
            color = COL_HOSTILE
        elif new_status == "FRIENDLY":
            color = COL_FRIENDLY
        elif new_status == "NEUTRAL":
            color = COL_NEUTRAL

        self.setBrush(QBrush(color))
        self.label.setDefaultTextColor(color)

    def move(self):
        # Update position
        self.setPos(self.x() + self.vx, self.y() + self.vy)

        # Bounce off radar edge
        dist = math.hypot(self.x(), self.y())
        if dist > RADAR_RADIUS - 10:
            # Simple bounce logic: reverse velocity
            self.vx *= -1
            self.vy *= -1


# --- 4. The Main Application ---

class AWACSConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AWACS 'PICTURE' MANAGER")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ddd; font-family: Consolas; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; font-weight: bold; color: #4fc3f7; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLineEdit { background-color: #111; color: #0f0; border: 1px solid #333; padding: 5px; }
            QTextEdit { background-color: #000; color: #0f0; border: 1px solid #333; }
            QLabel { color: #aaa; }
        """)

        self.tracks = {}  # {id: TrackItem}
        self.next_id = 101

        self.init_ui()

        # Setup Audio
        if AUDIO_AVAILABLE:
            self.voice_thread = VoiceListener()
            self.voice_thread.command_detected.connect(self.process_voice_command)
            self.voice_thread.status_update.connect(self.update_mic_status)
            self.voice_thread.start()
        else:
            self.log("SYS", "Audio Module Failed. Use Manual Input.")

        # Game Loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_tick)
        self.timer.start(REFRESH_RATE)

        # Spawn initial bogeys
        for _ in range(5):
            self.spawn_track()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: RADAR ---
        self.scene = QGraphicsScene(-RADAR_RADIUS, -RADAR_RADIUS, RADAR_RADIUS * 2, RADAR_RADIUS * 2)
        self.scene.setBackgroundBrush(QBrush(QColor("#001100")))

        # Draw Scope Rings
        pen_ring = QPen(QColor(0, 100, 0), 1, Qt.DashLine)
        self.scene.addEllipse(-100, -100, 200, 200, pen_ring)
        self.scene.addEllipse(-200, -200, 400, 400, pen_ring)
        self.scene.addEllipse(-300, -300, 600, 600, QPen(QColor(0, 200, 0), 2))

        # Crosshair
        self.scene.addLine(-300, 0, 300, 0, pen_ring)
        self.scene.addLine(0, -300, 0, 300, pen_ring)

        self.radar_view = QGraphicsView(self.scene)
        self.radar_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.radar_view, 65)

        # --- RIGHT: COMMS PANEL ---
        right_panel = QVBoxLayout()

        # 1. Header
        lbl_head = QLabel("BATTLE MANAGEMENT COMMAND")
        lbl_head.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        lbl_head.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(lbl_head)

        # 2. Status Light
        self.lbl_mic_status = QLabel("MIC STATUS: STANDBY")
        self.lbl_mic_status.setStyleSheet("background-color: #333; color: white; padding: 5px; border-radius: 4px;")
        self.lbl_mic_status.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(self.lbl_mic_status)

        # 3. Log
        grp_log = QGroupBox("VOICE COMMAND LOG")
        l_layout = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        l_layout.addWidget(self.txt_log)
        right_panel.addWidget(grp_log)

        # 4. Manual Input (Fallback)
        grp_manual = QGroupBox("MANUAL OVERRIDE")
        m_layout = QVBoxLayout(grp_manual)

        self.inp_cmd = QLineEdit()
        self.inp_cmd.setPlaceholderText("Type command (e.g., 'DECLARE TRACK 101 HOSTILE')...")
        self.inp_cmd.returnPressed.connect(self.manual_entry)

        m_layout.addWidget(self.inp_cmd)

        btn_send = QPushButton("SEND COMMAND")
        btn_send.setStyleSheet("background-color: #0d47a1; color: white; font-weight: bold; padding: 8px;")
        btn_send.clicked.connect(self.manual_entry)
        m_layout.addWidget(btn_send)

        right_panel.addWidget(grp_manual)

        # 5. Legend
        grp_leg = QGroupBox("LEGEND")
        leg_layout = QHBoxLayout(grp_leg)
        leg_layout.addWidget(QLabel("<font color='yellow'>BOGEY</font>"))
        leg_layout.addWidget(QLabel("<font color='red'>HOSTILE</font>"))
        leg_layout.addWidget(QLabel("<font color='#00FF00'>FRIENDLY</font>"))
        right_panel.addWidget(grp_leg)

        layout.addLayout(right_panel, 35)

    def log(self, sender, msg, color="#0f0"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(
            f"<span style='color:#555'>[{ts}]</span> <span style='color:{color}'><b>{sender}:</b> {msg}</span>")

    def update_mic_status(self, text):
        color = "#2e7d32" if "LISTENING" in text else "#333"
        if "Processing" in text: color = "#f57f17"
        self.lbl_mic_status.setText(text)
        self.lbl_mic_status.setStyleSheet(f"background-color: {color}; color: white; padding: 5px; border-radius: 4px;")

    def spawn_track(self):
        # Random pos inside circle
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(50, RADAR_RADIUS - 20)
        x = r * math.cos(angle)
        y = r * math.sin(angle)

        t = TrackItem(self.next_id, x, y)
        self.scene.addItem(t)
        self.tracks[self.next_id] = t
        self.next_id += 1

    def game_tick(self):
        for t in self.tracks.values():
            t.move()

    def process_voice_command(self, text):
        self.log("VOICE", f"'{text}'", "#fff")
        self.execute_logic(text)

    def manual_entry(self):
        text = self.inp_cmd.text()
        if not text: return
        self.log("MANUAL", f"'{text}'", "#aaa")
        self.execute_logic(text)
        self.inp_cmd.clear()

    def execute_logic(self, text):
        action, t_id, status = BrevityParser.parse(text)

        if action == "INVALID":
            self.log("SYSTEM", "SYNTAX ERROR: INVALID BREVITY CODE", "#f44336")
            return

        if t_id not in self.tracks:
            self.log("SYSTEM", f"ERROR: TRACK {t_id} NOT FOUND", "#f44336")
            return

        track = self.tracks[t_id]

        if action == "UPDATE":
            track.update_status(status)
            self.log("SYSTEM", f"TRACK {t_id} UPDATED TO {status}", "#2196f3")

        elif action == "DROP":
            self.scene.removeItem(track)
            del self.tracks[t_id]
            self.log("SYSTEM", f"TRACK {t_id} DROPPED", "#2196f3")

    def closeEvent(self, event):
        if AUDIO_AVAILABLE:
            self.voice_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AWACSConsole()
    window.show()
    sys.exit(app.exec_())
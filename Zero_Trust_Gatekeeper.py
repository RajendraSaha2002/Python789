import sys
import datetime
import json
from enum import Enum, auto

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QComboBox, QFrame, QTextEdit, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette

# --- Configuration ---
# Mock Database of Authorized Entities
AUTHORIZED_USERS = {
    "admin": {
        "password_hash": "admin123",  # In real app, use SHA-256
        "role": "TOP_SECRET",
        "allowed_devices": ["DEV-ADMIN-01", "DEV-ADMIN-02"],
        "allowed_zones": ["HQ_BUNKER", "PENTAGON_SECURE"]
    },
    "officer": {
        "password_hash": "duty",
        "role": "SECRET",
        "allowed_devices": ["DEV-FIELD-99"],
        "allowed_zones": ["HQ_BUNKER", "FIELD_STATION_ALPHA"]
    }
}


# --- 1. The Logic Engine (Policy Enforcer) ---

class AccessResult(Enum):
    GRANTED = auto()
    DENIED_AUTH = auto()
    DENIED_DEVICE = auto()
    DENIED_GEO = auto()
    DENIED_TIME = auto()


class PolicyEnforcer:
    def __init__(self):
        self.audit_log = []

    def log(self, user, result, reason):
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "result": result.name,
            "reason": reason
        }
        self.audit_log.append(entry)
        return entry

    def evaluate_request(self, username, password, device_id, location):
        """
        The Zero Trust Core Logic.
        All conditions must pass. One failure = Immediate Rejection.
        """
        # 1. Identity Check (Authentication)
        if username not in AUTHORIZED_USERS:
            return self.log(username, AccessResult.DENIED_AUTH, "User not found in directory.")

        user_profile = AUTHORIZED_USERS[username]

        if password != user_profile["password_hash"]:
            return self.log(username, AccessResult.DENIED_AUTH, "Invalid credentials.")

        # 2. Device Integrity Check
        # Zero Trust: Is this hardware managed by IT?
        if device_id not in user_profile["allowed_devices"]:
            return self.log(username, AccessResult.DENIED_DEVICE, f"Unregistered Device ID: {device_id}")

        # 3. Micro-Segmentation / Geofence Check
        # Zero Trust: Are you physically in a secure zone?
        if location not in user_profile["allowed_zones"]:
            return self.log(username, AccessResult.DENIED_GEO,
                            f"Geofence Violation. Location '{location}' not authorized.")

        # 4. Time Policy (Optional Logic Example)
        # e.g., No access between 0200 and 0500
        current_hour = datetime.datetime.now().hour
        if 2 <= current_hour < 5:
            return self.log(username, AccessResult.DENIED_TIME,
                            "Access restricted during maintenance window (0200-0500).")

        # ALL CHECKS PASSED
        return self.log(username, AccessResult.GRANTED, "Policy Validation Successful. Session Token Issued.")


# --- 2. GUI Application ---

class ZeroTrustGatekeeper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DOD ZERO TRUST ACCESS PORTAL")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: #E0E0E0; font-family: Segoe UI; }
            QLabel { font-size: 14px; }
            QLineEdit { background-color: #1E1E1E; border: 1px solid #333; color: white; padding: 8px; border-radius: 4px; }
            QComboBox { background-color: #1E1E1E; border: 1px solid #333; color: white; padding: 5px; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QPushButton { background-color: #0D47A1; color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1565C0; }
            QPushButton:pressed { background-color: #002171; }
        """)

        self.engine = PolicyEnforcer()
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- LEFT: LOGIN FORM ---
        form_panel = QFrame()
        form_panel.setFixedWidth(400)
        form_layout = QVBoxLayout(form_panel)

        # Header
        lbl_head = QLabel("SECURE FILE ACCESS")
        lbl_head.setStyleSheet("font-size: 24px; font-weight: bold; color: #90CAF9; margin-bottom: 20px;")
        lbl_head.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(lbl_head)

        # 1. Identity Input
        grp_auth = QGroupBox("1. IDENTITY CLAIM")
        auth_layout = QVBoxLayout(grp_auth)
        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("Username (e.g. admin)")
        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText("Password")
        self.inp_pass.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(QLabel("User Principal:"))
        auth_layout.addWidget(self.inp_user)
        auth_layout.addWidget(QLabel("Credential:"))
        auth_layout.addWidget(self.inp_pass)
        form_layout.addWidget(grp_auth)

        # 2. Context Simulation (The "Invisible" Factors)
        grp_ctx = QGroupBox("2. CONTEXT SIGNAL SIMULATOR")
        ctx_layout = QVBoxLayout(grp_ctx)

        ctx_layout.addWidget(QLabel("Device Fingerprint (ID):"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["DEV-ADMIN-01", "DEV-FIELD-99", "UNKNOWN-LAPTOP-X", "IPHONE-12"])
        ctx_layout.addWidget(self.combo_device)

        ctx_layout.addWidget(QLabel("Geo-Location Signal:"))
        self.combo_loc = QComboBox()
        self.combo_loc.addItems(["HQ_BUNKER", "FIELD_STATION_ALPHA", "STARBUCKS_WIFI", "IP_RUSSIA"])
        ctx_layout.addWidget(self.combo_loc)

        form_layout.addWidget(grp_ctx)

        # Submit
        self.btn_login = QPushButton("REQUEST ACCESS")
        self.btn_login.setFixedHeight(50)
        self.btn_login.clicked.connect(self.attempt_access)
        form_layout.addWidget(self.btn_login)

        form_layout.addStretch()
        main_layout.addWidget(form_panel)

        # --- RIGHT: STATUS & LOGS ---
        status_panel = QVBoxLayout()

        # Status Box
        self.lbl_status = QLabel("STATUS: AWAITING INPUT")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFixedHeight(100)
        self.lbl_status.setStyleSheet("""
            background-color: #222; 
            color: #AAA; 
            font-size: 20px; 
            font-weight: bold; 
            border: 2px dashed #444;
            border-radius: 10px;
        """)
        status_panel.addWidget(self.lbl_status)

        # Log Feed
        status_panel.addWidget(QLabel("POLICY ENGINE AUDIT TRAIL:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            background-color: #000; 
            color: #00FF00; 
            font-family: Consolas; 
            font-size: 11px;
            border: 1px solid #333;
        """)
        status_panel.addWidget(self.txt_log)

        main_layout.addLayout(status_panel)

    def attempt_access(self):
        # Gather inputs
        u = self.inp_user.text()
        p = self.inp_pass.text()
        d = self.combo_device.currentText()
        l = self.combo_loc.currentText()

        # Run Logic Engine
        result_entry = self.engine.evaluate_request(u, p, d, l)

        # Update UI
        self.update_status(result_entry)
        self.log_event(result_entry)

    def update_status(self, entry):
        res = entry['result']
        reason = entry['reason']

        if res == "GRANTED":
            style = "background-color: #1B5E20; color: #FFF; border: 2px solid #4CAF50;"
            text = f"ACCESS GRANTED\n\n{reason}"
        else:
            style = "background-color: #B71C1C; color: #FFF; border: 2px solid #EF5350;"
            text = f"ACCESS DENIED\n[{res}]\n\n{reason}"

        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(style + "font-size: 16px; font-weight: bold; border-radius: 10px;")

    def log_event(self, entry):
        ts = entry['timestamp']
        res = entry['result']
        reason = entry['reason']

        color = "#00FF00" if res == "GRANTED" else "#FF5252"

        html = f"""
        <span style="color: #555;">[{ts}]</span> 
        <span style="color: {color}; font-weight: bold;">{res}</span>: 
        {reason}
        """
        self.txt_log.append(html)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ZeroTrustGatekeeper()
    window.show()
    sys.exit(app.exec_())
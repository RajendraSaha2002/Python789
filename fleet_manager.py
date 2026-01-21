import sys
import psycopg2
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                             QPushButton, QLineEdit, QMessageBox, QHeaderView, QFormLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'fleet_db',  # Make sure you created this DB or use 'postgres'
    'port': 5432
}


class FleetManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Fleet Readiness System")
        self.setGeometry(100, 100, 1000, 600)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        # --- LEFT PANEL: Fleet List ---
        self.table_layout = QVBoxLayout()
        self.lbl_title = QLabel("FLEET STATUS OVERVIEW")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.table_layout.addWidget(self.lbl_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Vehicle Name", "Type", "Mileage", "Last Service", "Readiness"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemClicked.connect(self.load_selection)
        self.table_layout.addWidget(self.table)

        btn_refresh = QPushButton("Run Predictive Diagnostics (Refresh)")
        btn_refresh.setStyleSheet("background-color: #007bff; color: white; padding: 10px; font-weight: bold;")
        btn_refresh.clicked.connect(self.run_diagnostics)
        self.table_layout.addWidget(btn_refresh)

        self.layout.addLayout(self.table_layout, 70)  # 70% width

        # --- RIGHT PANEL: Action Area ---
        self.action_layout = QVBoxLayout()
        self.action_layout.setAlignment(Qt.AlignTop)

        # Details Form
        self.form_group = QWidget()
        self.form_layout = QFormLayout()

        self.input_id = QLineEdit()
        self.input_id.setReadOnly(True)
        self.input_name = QLineEdit()
        self.input_name.setReadOnly(True)
        self.input_mileage = QLineEdit()

        self.form_layout.addRow("Vehicle ID:", self.input_id)
        self.form_layout.addRow("Name:", self.input_name)
        self.form_layout.addRow("Current Mileage:", self.input_mileage)

        self.form_group.setLayout(self.form_layout)
        self.action_layout.addWidget(self.form_group)

        # Buttons
        self.btn_update_mileage = QPushButton("Update Mileage")
        self.btn_update_mileage.clicked.connect(self.update_mileage)
        self.action_layout.addWidget(self.btn_update_mileage)

        self.action_layout.addSpacing(20)

        self.lbl_service = QLabel("MAINTENANCE ACTIONS")
        self.lbl_service.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.action_layout.addWidget(self.lbl_service)

        self.btn_service = QPushButton("Log Service Performed")
        self.btn_service.setStyleSheet("background-color: #28a745; color: white; padding: 8px;")
        self.btn_service.clicked.connect(self.perform_service)
        self.action_layout.addWidget(self.btn_service)

        self.layout.addLayout(self.action_layout, 30)  # 30% width

        # Initial DB Setup & Load
        self.init_db_tables()
        self.run_diagnostics()

    # --- DATABASE HELPERS ---
    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            return None

    def init_db_tables(self):
        """Create tables if they don't exist (Self-healing)."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS vehicles
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            name
                            VARCHAR
                        (
                            100
                        ) NOT NULL,
                            type VARCHAR
                        (
                            50
                        ),
                            current_mileage INT DEFAULT 0,
                            last_service_date DATE DEFAULT CURRENT_DATE,
                            mileage_at_last_service INT DEFAULT 0,
                            status VARCHAR
                        (
                            50
                        ) DEFAULT 'Ready'
                            );
                        """)
            conn.commit()
        finally:
            conn.close()

    def run_diagnostics(self):
        """The Core Logic: Checks dates and mileage for every vehicle."""
        conn = self.connect()
        if not conn: return

        try:
            cur = conn.cursor()

            # 1. Fetch all data
            cur.execute(
                "SELECT id, name, type, current_mileage, last_service_date, mileage_at_last_service FROM vehicles ORDER BY id")
            rows = cur.fetchall()

            self.table.setRowCount(0)

            for row in rows:
                v_id, name, v_type, curr_mil, last_date, last_mil = row

                # --- PREDICTIVE LOGIC ---
                status = "Ready"
                alert = False

                # Check 1: Time (6 Months)
                # Ensure last_date is a datetime object
                if isinstance(last_date, str):
                    last_date = datetime.strptime(last_date, "%Y-%m-%d").date()

                days_since = (datetime.now().date() - last_date).days

                # Check 2: Mileage (5000 miles since last service)
                miles_since = curr_mil - last_mil

                if days_since > 180:
                    status = f"OVERDUE (Time: {days_since} days)"
                    alert = True
                elif miles_since > 5000:
                    status = f"OVERDUE (Miles: +{miles_since})"
                    alert = True

                # Update DB with new status
                update_cur = conn.cursor()
                update_cur.execute("UPDATE vehicles SET status = %s WHERE id = %s", (status, v_id))

                # Populate GUI Table
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)

                self.table.setItem(row_idx, 0, QTableWidgetItem(str(v_id)))
                self.table.setItem(row_idx, 1, QTableWidgetItem(name))
                self.table.setItem(row_idx, 2, QTableWidgetItem(v_type))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(curr_mil)))
                self.table.setItem(row_idx, 4, QTableWidgetItem(str(last_date)))

                status_item = QTableWidgetItem(status)
                if alert:
                    status_item.setBackground(QColor("#ffcccc"))  # Light Red
                    status_item.setForeground(QColor("#cc0000"))
                else:
                    status_item.setBackground(QColor("#ccffcc"))  # Light Green
                    status_item.setForeground(QColor("#006600"))

                self.table.setItem(row_idx, 5, status_item)

            conn.commit()

        except Exception as e:
            print(e)
        finally:
            conn.close()

    def load_selection(self, item):
        row = item.row()
        self.input_id.setText(self.table.item(row, 0).text())
        self.input_name.setText(self.table.item(row, 1).text())
        self.input_mileage.setText(self.table.item(row, 3).text())

    def update_mileage(self):
        v_id = self.input_id.text()
        new_mileage = self.input_mileage.text()

        if not v_id or not new_mileage.isdigit():
            return

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE vehicles SET current_mileage = %s WHERE id = %s", (new_mileage, v_id))
            conn.commit()
            QMessageBox.information(self, "Success", "Mileage Updated")
            self.run_diagnostics()  # Re-run logic to see if it triggers maintenance
        finally:
            conn.close()

    def perform_service(self):
        v_id = self.input_id.text()
        curr_mileage = self.input_mileage.text()

        if not v_id: return

        conn = self.connect()
        try:
            cur = conn.cursor()
            # Reset the clock:
            # 1. Update last_service_date to TODAY
            # 2. Update mileage_at_last_service to CURRENT mileage
            # 3. Reset Status to Ready
            cur.execute("""
                        UPDATE vehicles
                        SET last_service_date       = CURRENT_DATE,
                            mileage_at_last_service = %s,
                            status                  = 'Ready'
                        WHERE id = %s
                        """, (curr_mileage, v_id))

            conn.commit()
            QMessageBox.information(self, "Service Logged", "Vehicle is now marked READY.")
            self.run_diagnostics()
        finally:
            conn.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FleetManagerApp()
    window.show()
    sys.exit(app.exec_())
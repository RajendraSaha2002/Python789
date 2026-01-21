import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'naval_base_db',
    'port': 5432
}


class SmartGateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NAVAL STATION SECURITY // SMART GATE")
        self.root.geometry("900x650")
        self.root.configure(bg="#101010")

        self.init_db()
        self.setup_ui()
        self.load_logs()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing DB: Creates tables and seeds data if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # Create Tables (Simplified schema creation for auto-init)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS personnel
                        (
                            badge_id
                            VARCHAR
                        (
                            20
                        ) PRIMARY KEY,
                            name VARCHAR
                        (
                            100
                        ), rank VARCHAR
                        (
                            50
                        ),
                            clearance_level INT, status VARCHAR
                        (
                            20
                        ) DEFAULT 'ACTIVE'
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS gates
                        (
                            id
                            INT
                            PRIMARY
                            KEY,
                            name
                            VARCHAR
                        (
                            50
                        ), required_clearance INT
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS stolen_badges
                        (
                            badge_id
                            VARCHAR
                        (
                            20
                        ) PRIMARY KEY, reported_date DATE, notes TEXT
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS access_logs
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            timestamp
                            TIMESTAMP
                            DEFAULT
                            CURRENT_TIMESTAMP,
                            badge_id
                            VARCHAR
                        (
                            20
                        ), gate_id INT, result VARCHAR
                        (
                            20
                        ), details TEXT
                            );
                        """)

            # Seed Check
            cur.execute("SELECT count(*) FROM personnel")
            if cur.fetchone()[0] == 0:
                print("Seeding Database...")
                cur.execute(
                    "INSERT INTO personnel VALUES ('N-101', 'Admiral Vance', 'Admiral', 5), ('N-202', 'Lt. Shepard', 'Officer', 3), ('N-999', 'Recruit Jones', 'Enlisted', 1)")
                cur.execute(
                    "INSERT INTO gates VALUES (1, 'Main Gate', 1), (2, 'Sector 7 Labs', 3), (3, 'Nuclear Command', 5)")
                cur.execute("INSERT INTO stolen_badges (badge_id, notes) VALUES ('N-666', 'Lost off-base')")

            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1a1a1a", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="🛡️ BASE ACCESS CONTROL SYSTEM", font=("Impact", 24), bg="#1a1a1a", fg="#00ccff").pack()

        # Main Layout
        main_frame = tk.Frame(self.root, bg="#101010")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # LEFT: Scanner Interface
        scan_frame = tk.LabelFrame(main_frame, text=" RFID SCANNER SIMULATION ", bg="#1a1a1a", fg="white",
                                   font=("Arial", 12, "bold"))
        scan_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(scan_frame, text="Select Gate:", bg="#1a1a1a", fg="gray").pack(pady=(20, 5))
        self.gate_combo = ttk.Combobox(scan_frame, state="readonly", width=25)
        self.gate_combo.pack(pady=5)
        self.load_gates()

        tk.Label(scan_frame, text="Scan Badge ID:", bg="#1a1a1a", fg="gray").pack(pady=(20, 5))
        self.badge_entry = tk.Entry(scan_frame, font=("Courier", 18), justify="center", width=15)
        self.badge_entry.pack(pady=5)
        self.badge_entry.insert(0, "N-101")

        tk.Button(scan_frame, text="SCAN BADGE", command=self.scan_badge,
                  bg="#0055aa", fg="white", font=("Arial", 14, "bold"), height=2, width=20).pack(pady=30)

        # Status Display
        self.status_box = tk.Label(scan_frame, text="READY", font=("Arial", 16, "bold"), bg="#333", fg="white",
                                   width=25, height=4, relief="sunken")
        self.status_box.pack(pady=10)

        # RIGHT: Live Logs
        log_frame = tk.LabelFrame(main_frame, text=" SECURITY FEED ", bg="#1a1a1a", fg="white")
        log_frame.pack(side="right", fill="both", expand=True)

        cols = ("time", "badge", "gate", "result")
        self.tree = ttk.Treeview(log_frame, columns=cols, show="headings")
        self.tree.heading("time", text="TIMESTAMP")
        self.tree.heading("badge", text="BADGE")
        self.tree.heading("gate", text="GATE")
        self.tree.heading("result", text="RESULT")

        self.tree.column("time", width=120)
        self.tree.column("badge", width=80)
        self.tree.column("gate", width=100)
        self.tree.column("result", width=100)

        self.tree.tag_configure("GRANTED", foreground="#00ff00")
        self.tree.tag_configure("DENIED", foreground="orange")
        self.tree.tag_configure("ALARM", foreground="red", background="#330000")

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def load_gates(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM gates ORDER BY id")
            self.gates = {f"{r[1]} (ID: {r[0]})": r[0] for r in cur.fetchall()}
            self.gate_combo['values'] = list(self.gates.keys())
            if self.gates: self.gate_combo.current(0)
        finally:
            conn.close()

    def scan_badge(self):
        badge_id = self.badge_entry.get().strip()
        gate_name = self.gate_combo.get()

        if not badge_id or not gate_name: return
        gate_id = self.gates[gate_name]

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # 1. CHECK BLACKLIST (Priority)
            cur.execute("SELECT notes FROM stolen_badges WHERE badge_id = %s", (badge_id,))
            stolen = cur.fetchone()

            if stolen:
                self.trigger_response("SILENT_ALARM", badge_id, gate_id, f"STOLEN BADGE: {stolen[0]}")
                return

            # 2. CHECK BADGE VALIDITY & CLEARANCE
            cur.execute("SELECT name, rank, clearance_level, status FROM personnel WHERE badge_id = %s", (badge_id,))
            person = cur.fetchone()

            if not person:
                self.trigger_response("DENIED", badge_id, gate_id, "Badge ID not found in database.")
                return

            name, rank, user_level, status = person

            if status != 'ACTIVE':
                self.trigger_response("DENIED", badge_id, gate_id, f"Badge status is {status}.")
                return

            # 3. CHECK GATE REQUIREMENT
            cur.execute("SELECT required_clearance FROM gates WHERE id = %s", (gate_id,))
            req_level = cur.fetchone()[0]

            if user_level >= req_level:
                self.trigger_response("GRANTED", badge_id, gate_id, f"Welcome, {rank} {name}.")
            else:
                self.trigger_response("DENIED", badge_id, gate_id,
                                      f"Insufficient Clearance (User: {user_level}, Gate: {req_level}).")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def trigger_response(self, result, badge, gate, details):
        # 1. Update UI Visuals
        if result == "GRANTED":
            self.status_box.config(text=f"ACCESS GRANTED\n{details}", bg="green", fg="white")
        elif result == "DENIED":
            self.status_box.config(text=f"ACCESS DENIED\n{details}", bg="orange", fg="black")
        elif result == "SILENT_ALARM":
            # Silent Alarm: GUI shows 'Processing...' or generic error to user,
            # but internally logs ALARM. Here we show RED for the demo user.
            self.status_box.config(text="⚠️ SECURITY ALERT ⚠️\nGUARDS DISPATCHED", bg="red", fg="white",
                                   font=("Arial", 18, "bold"))
            # In a real app, you might popup a hidden window for the guard station

        # 2. Log to Database
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO access_logs (badge_id, gate_id, result, details) VALUES (%s, %s, %s, %s)",
                        (badge, gate, result, details))
            conn.commit()
        finally:
            conn.close()

        self.load_logs()

    def load_logs(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        SELECT to_char(timestamp, 'HH24:MI:SS'), badge_id, gate_id, result
                        FROM access_logs
                        ORDER BY id DESC LIMIT 15
                        """)
            rows = cur.fetchall()

            for item in self.tree.get_children():
                self.tree.delete(item)

            for row in rows:
                res_tag = "ALARM" if row[3] == "SILENT_ALARM" else row[3]
                self.tree.insert("", tk.END, values=row, tags=(res_tag,))
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartGateApp(root)
    root.mainloop()
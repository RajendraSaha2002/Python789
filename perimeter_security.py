import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import time

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'perimeter_db',
    'port': 5432
}


class SecurityGridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automated Perimeter Security Grid // Sensor Fusion")
        self.root.geometry("1000x600")
        self.root.configure(bg="#111")

        # State Variables for Fusion Logic
        # Dictionary to store last motion time per sector: {sector_id: timestamp}
        self.motion_timers = {}
        self.FUSION_WINDOW = 3.0  # Seconds allowed between Motion and Camera

        self.init_db()
        self.setup_ui()
        self.refresh_map_loop()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"Connection Error: {e}")
            return None

    def init_db(self):
        """Auto-create tables if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS sectors
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            name
                            VARCHAR
                        (
                            50
                        ) NOT NULL,
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'SECURE',
                            last_patrol TIMESTAMP
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS event_logs
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            sector_id
                            INT,
                            event_type
                            VARCHAR
                        (
                            50
                        ),
                            description TEXT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """)
            # Seed if empty
            cur.execute("SELECT count(*) FROM sectors")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO sectors (name) VALUES ('North Gate'), ('East Wall'), ('South Loading'), ('West Parking')")

            conn.commit()
            print("DB Initialized.")
        except Exception as e:
            print(f"Init Error: {e}")
        finally:
            conn.close()

    def setup_ui(self):
        # --- TOP: LIVE MAP ---
        map_frame = tk.LabelFrame(self.root, text="SECTOR STATUS MAP", bg="#222", fg="white")
        map_frame.pack(fill="x", padx=10, pady=10)

        self.sector_labels = {}
        # Create 4 visual blocks for sectors
        sectors = ["North Gate", "East Wall", "South Loading", "West Parking"]
        for i, name in enumerate(sectors):
            sid = i + 1
            lbl = tk.Label(map_frame, text=f"{name}\nSECURE", bg="green", fg="white",
                           font=("Arial", 12, "bold"), width=20, height=4)
            lbl.grid(row=0, column=i, padx=10, pady=10)
            self.sector_labels[sid] = lbl

        # --- MIDDLE: SENSOR SIMULATOR ---
        sim_frame = tk.LabelFrame(self.root, text="SENSOR INPUT SIMULATOR", bg="#222", fg="white")
        sim_frame.pack(fill="x", padx=10, pady=10)

        # Controls for each sector
        for i, name in enumerate(sectors):
            sid = i + 1
            frame = tk.Frame(sim_frame, bg="#333", padx=5, pady=5)
            frame.grid(row=0, column=i, padx=5, pady=5)

            tk.Label(frame, text=f"Sector {sid}", bg="#333", fg="#aaa").pack()

            # Motion Button
            tk.Button(frame, text="TRIP MOTION", bg="#aaaa00", width=15,
                      command=lambda s=sid: self.trigger_motion(s)).pack(pady=2)

            # Camera Button
            tk.Button(frame, text="CAM: HUMAN", bg="#00aaaa", width=15,
                      command=lambda s=sid: self.trigger_camera(s)).pack(pady=2)

            # Offline Button
            tk.Button(frame, text="CUT POWER", bg="#555", fg="white", width=15,
                      command=lambda s=sid: self.set_offline(s)).pack(pady=2)

        # --- BOTTOM: SYSTEM LOGS ---
        log_frame = tk.LabelFrame(self.root, text="FUSION LOGS", bg="#222", fg="white")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_text = tk.Text(log_frame, bg="black", fg="#0f0", height=10)
        self.log_text.pack(fill="both", expand=True)

    # --- SENSOR LOGIC ---

    def trigger_motion(self, sector_id):
        """Sensor A: Motion Detected. Starts the 'Fusion Window'."""
        self.log_event(sector_id, "MOTION", "Motion sensor tripped. Waiting for confirmation...")

        # Record time
        self.motion_timers[sector_id] = time.time()

        # Update Status to WARNING
        self.update_sector_status(sector_id, "WARNING")

    def trigger_camera(self, sector_id):
        """Sensor B: Human Shape Detected via Computer Vision."""
        now = time.time()
        last_motion = self.motion_timers.get(sector_id, 0)

        # FUSION LOGIC:
        # If camera sees human AND it's been less than 3 seconds since motion
        if (now - last_motion) <= self.FUSION_WINDOW:
            # REAL ALARM
            self.trigger_alarm(sector_id, "CONFIRMED INTRUSION: Motion + Human Shape")
        else:
            # Camera saw something, but no motion triggered recently (maybe patrol guard?)
            self.log_event(sector_id, "CAMERA_ONLY", "Human shape detected, but no motion trigger. Ignoring.")

    def trigger_alarm(self, sector_id, reason):
        self.log_event(sector_id, "FUSED_ALARM", reason)
        self.update_sector_status(sector_id, "ALARM")
        messagebox.showwarning("SECURITY BREACH", f"ALARM IN SECTOR {sector_id}\n{reason}")

    def set_offline(self, sector_id):
        self.log_event(sector_id, "OFFLINE", "Sector power loss / Comms failure.")
        self.update_sector_status(sector_id, "OFFLINE")
        # Logic: Reroute patrols (simulated log)
        self.log_msg(f"SYSTEM: Rerouting Patrol Unit Alpha to Sector {sector_id} due to blackout.")

    # --- DATABASE & UI UPDATES ---

    def update_sector_status(self, sector_id, status):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("UPDATE sectors SET status=%s WHERE id=%s", (status, sector_id))
            conn.commit()
        finally:
            conn.close()
        self.refresh_map()

    def log_event(self, sector_id, type, desc):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO event_logs (sector_id, event_type, description) VALUES (%s, %s, %s)",
                        (sector_id, type, desc))
            conn.commit()
            self.log_msg(f"[Sec {sector_id}] {type}: {desc}")
        finally:
            conn.close()

    def log_msg(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)

    def refresh_map_loop(self):
        self.refresh_map()
        # Auto-reset warnings to SECURE if time passes (simulating reset)
        self.check_timeouts()
        self.root.after(1000, self.refresh_map_loop)

    def check_timeouts(self):
        # If a sector is WARNING but fusion window passed, reset to SECURE
        now = time.time()
        for sid, timestamp in list(self.motion_timers.items()):
            if (now - timestamp) > self.FUSION_WINDOW:
                # Remove from timer list
                del self.motion_timers[sid]
                # If currently yellow, reset green
                lbl = self.sector_labels[sid]
                if "WARNING" in lbl.cget("text"):
                    self.update_sector_status(sid, "SECURE")
                    self.log_msg(f"[Sec {sid}] False positive ignored. Resetting to SECURE.")

    def refresh_map(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, status FROM sectors ORDER BY id")
            rows = cur.fetchall()

            for row in rows:
                sid, name, status = row
                lbl = self.sector_labels.get(sid)
                if lbl:
                    lbl.config(text=f"{name}\n{status}")
                    if status == 'SECURE':
                        lbl.config(bg="green")
                    elif status == 'WARNING':
                        lbl.config(bg="orange")
                    elif status == 'ALARM':
                        lbl.config(bg="red")
                    elif status == 'OFFLINE':
                        lbl.config(bg="grey")
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = SecurityGridApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'squadron_ops',
    'port': 5432
}

FATIGUE_LIMIT_HOURS = 50.0
LOOKBACK_DAYS = 7


class FlightDutyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SECURE SQUADRON // FLIGHT DUTY & FATIGUE LOG")
        self.root.geometry("900x650")
        self.root.configure(bg="#0f172a")  # Dark Slate

        self.init_db()
        self.setup_ui()
        self.load_pilots()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Ensures tables exist."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS squadron_pilots
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            callsign
                            VARCHAR
                        (
                            50
                        ) UNIQUE NOT NULL,
                            rank VARCHAR
                        (
                            20
                        ) NOT NULL,
                            total_career_hours DECIMAL
                        (
                            10,
                            2
                        ) DEFAULT 0.0
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS flight_logs
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            pilot_id
                            INT
                            REFERENCES
                            squadron_pilots
                        (
                            id
                        ),
                            mission_id VARCHAR
                        (
                            50
                        ),
                            takeoff_time TIMESTAMP NOT NULL,
                            landing_time TIMESTAMP NOT NULL,
                            duration_hours DECIMAL
                        (
                            5,
                            2
                        ) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """)
            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1e293b", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="✈️ SQUADRON FLIGHT OPERATIONS", font=("Courier", 20, "bold"), bg="#1e293b",
                 fg="#38bdf8").pack()

        # Input Area
        input_frame = tk.LabelFrame(self.root, text=" SIGN-IN NEW FLIGHT MISSION ", bg="#0f172a", fg="#94a3b8", padx=20,
                                    pady=20)
        input_frame.pack(fill="x", padx=20, pady=20)

        tk.Label(input_frame, text="PILOT CALLSIGN:", bg="#0f172a", fg="white").grid(row=0, column=0, sticky="w")
        self.pilot_combo = ttk.Combobox(input_frame, state="readonly", width=30)
        self.pilot_combo.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(input_frame, text="MISSION ID:", bg="#0f172a", fg="white").grid(row=1, column=0, sticky="w")
        self.mission_entry = tk.Entry(input_frame, width=33)
        self.mission_entry.insert(0, "MSN-" + datetime.now().strftime("%y%m%d"))
        self.mission_entry.grid(row=1, column=1, padx=10, pady=10)

        tk.Label(input_frame, text="ESTIMATED DURATION (HRS):", bg="#0f172a", fg="white").grid(row=0, column=2,
                                                                                               sticky="w", padx=(30, 0))
        self.duration_entry = tk.Entry(input_frame, width=15)
        self.duration_entry.insert(0, "4.0")
        self.duration_entry.grid(row=0, column=3, padx=10)

        self.btn_log = tk.Button(input_frame, text="AUTHORIZE FLIGHT", command=self.process_flight,
                                 bg="#0ea5e9", fg="white", font=("Arial", 10, "bold"), width=25)
        self.btn_log.grid(row=1, column=2, columnspan=2, padx=10)

        # Dashboard Area
        dash_frame = tk.Frame(self.root, bg="#0f172a")
        dash_frame.pack(fill="both", expand=True, padx=20)

        # Left: Recent Logs
        list_frame = tk.LabelFrame(dash_frame, text=" RECENT SQUADRON LOGS ", bg="#0f172a", fg="#94a3b8")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        self.tree = ttk.Treeview(list_frame, columns=("pilot", "mission", "date", "hours"), show="headings")
        self.tree.heading("pilot", text="PILOT")
        self.tree.heading("mission", text="MISSION")
        self.tree.heading("date", text="DATE")
        self.tree.heading("hours", text="HRS")
        self.tree.column("hours", width=50)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Right: Fatigue Monitor
        self.fatigue_frame = tk.LabelFrame(dash_frame, text=" FATIGUE MONITOR (7-DAY) ", bg="#0f172a", fg="#94a3b8",
                                           width=300)
        self.fatigue_frame.pack(side="right", fill="both", pady=10)

        self.fatigue_display = tk.Text(self.fatigue_frame, bg="#020617", fg="#10b981", font=("Courier", 10), width=35)
        self.fatigue_display.pack(fill="both", expand=True, padx=5, pady=5)

    def load_pilots(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT callsign FROM squadron_pilots ORDER BY callsign")
            pilots = [row[0] for row in cur.fetchall()]
            self.pilot_combo['values'] = pilots
            if pilots: self.pilot_combo.current(0)
            self.refresh_logs()
        finally:
            conn.close()

    def refresh_logs(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            # 1. Update Table
            for item in self.tree.get_children(): self.tree.delete(item)
            cur.execute("""
                        SELECT p.callsign, l.mission_id, l.takeoff_time, l.duration_hours
                        FROM flight_logs l
                                 JOIN squadron_pilots p ON l.pilot_id = p.id
                        ORDER BY l.takeoff_time DESC LIMIT 15
                        """)
            for row in cur.fetchall():
                self.tree.insert("", tk.END, values=(row[0], row[1], row[2].strftime("%Y-%m-%d"), row[3]))

            # 2. Update Fatigue Monitor
            self.fatigue_display.delete("1.0", tk.END)
            cur.execute("""
                        SELECT p.callsign, COALESCE(SUM(l.duration_hours), 0) as total
                        FROM squadron_pilots p
                                 LEFT JOIN flight_logs l ON p.id = l.pilot_id AND l.takeoff_time > NOW() - INTERVAL '7 days'
                        GROUP BY p.callsign
                        """)
            for name, hours in cur.fetchall():
                status = "READY" if hours < FATIGUE_LIMIT_HOURS else "!!! FATIGUE !!!"
                self.fatigue_display.insert(tk.END, f"{name:<12} : {hours:>5} hrs | {status}\n")
        finally:
            conn.close()

    def process_flight(self):
        callsign = self.pilot_combo.get()
        mission = self.mission_entry.get()
        try:
            duration = float(self.duration_entry.get())
        except:
            messagebox.showerror("Error", "Enter valid duration hours.")
            return

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            # 1. Get Pilot ID
            cur.execute("SELECT id FROM squadron_pilots WHERE callsign = %s", (callsign,))
            pilot_id = cur.fetchone()[0]

            # 2. THE LOGIC: Check Fatigue for the last 7 days
            cur.execute("""
                        SELECT SUM(duration_hours)
                        FROM flight_logs
                        WHERE pilot_id = %s
                          AND takeoff_time > NOW() - INTERVAL '7 days'
                        """, (pilot_id,))
            current_hours = cur.fetchone()[0] or 0.0

            if (float(current_hours) + duration) > FATIGUE_LIMIT_HOURS:
                # DENY FLIGHT
                messagebox.showerror("FATIGUE RISK: FLIGHT DENIED",
                                     f"Pilot {callsign} has logged {current_hours} hours in the last 7 days.\n"
                                     f"Adding {duration} hours would exceed the legal safety limit of {FATIGUE_LIMIT_HOURS} hours.\n\n"
                                     "GROUNDING ORDER IN EFFECT.")
                return

            # 3. AUTHORIZE FLIGHT
            now = datetime.now()
            landing = now + timedelta(hours=duration)
            cur.execute("""
                        INSERT INTO flight_logs (pilot_id, mission_id, takeoff_time, landing_time, duration_hours)
                        VALUES (%s, %s, %s, %s, %s)
                        """, (pilot_id, mission, now, landing, duration))
            conn.commit()

            messagebox.showinfo("AUTHORIZED", f"Mission {mission} approved for Pilot {callsign}.")
            self.refresh_logs()

        except Exception as e:
            messagebox.showerror("Database Error", str(e))
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = FlightDutyApp(root)
    root.mainloop()
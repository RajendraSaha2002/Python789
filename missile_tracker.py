import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'armory_db',
    'port': 5432
}


class MissileTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MUNITIONS LIFE-CYCLE TRACKER")
        self.root.geometry("800x600")
        self.root.configure(bg="#222")

        # Self-Healing DB Init
        self.init_db()
        self.setup_ui()
        self.refresh_data()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Creates tables and seed data if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS jets
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            tail_number
                            VARCHAR
                        (
                            20
                        ) UNIQUE NOT NULL,
                            model VARCHAR
                        (
                            20
                        ) NOT NULL
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS missiles
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            serial_number
                            VARCHAR
                        (
                            50
                        ) UNIQUE NOT NULL,
                            type VARCHAR
                        (
                            50
                        ) NOT NULL,
                            flight_hours DECIMAL
                        (
                            10,
                            2
                        ) DEFAULT 0.0,
                            max_hours DECIMAL
                        (
                            10,
                            2
                        ) DEFAULT 100.0,
                            service_status VARCHAR
                        (
                            20
                        ) DEFAULT 'SERVICEABLE',
                            attached_jet_id INT REFERENCES jets
                        (
                            id
                        ) ON DELETE SET NULL
                            );
                        """)

            # Check seed
            cur.execute("SELECT count(*) FROM jets")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO jets (tail_number, model) VALUES ('Viper-1', 'F-16'), ('Panther-2', 'F-35')")
                cur.execute(
                    "INSERT INTO missiles (serial_number, type, flight_hours, attached_jet_id) VALUES ('AIM-120-ALPHA', 'AIM-120', 10.5, 1)")
                cur.execute(
                    "INSERT INTO missiles (serial_number, type, flight_hours, attached_jet_id) VALUES ('AIM-9X-BRAVO', 'AIM-9X', 98.0, 1)")
                cur.execute(
                    "INSERT INTO missiles (serial_number, type, flight_hours, attached_jet_id) VALUES ('AIM-120-CHARLIE', 'AIM-120', 45.0, NULL)")

            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        tk.Label(self.root, text="🚀 MUNITIONS MAINTENANCE DEPOT",
                 font=("Courier", 20, "bold"), bg="#222", fg="#ffcc00").pack(pady=15)

        # --- TOP PANEL: Log Flight ---
        frame_log = tk.LabelFrame(self.root, text=" CREW CHIEF: LOG LANDING ",
                                  bg="#333", fg="white", font=("Arial", 10, "bold"), padx=15, pady=15)
        frame_log.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_log, text="Select Jet Landed:", bg="#333", fg="white").pack(side="left")

        self.jet_combo = ttk.Combobox(frame_log, state="readonly", width=15)
        self.jet_combo.pack(side="left", padx=10)

        tk.Label(frame_log, text="Sortie Duration (Hrs):", bg="#333", fg="white").pack(side="left", padx=(20, 0))
        self.duration_entry = tk.Entry(frame_log, width=8)
        self.duration_entry.pack(side="left", padx=10)
        self.duration_entry.insert(0, "4.0")

        tk.Button(frame_log, text="UPDATE MISSILE LOGS", command=self.log_landing,
                  bg="#ffcc00", font=("Arial", 9, "bold")).pack(side="left", padx=20)

        # --- BOTTOM PANEL: Inventory ---
        frame_inv = tk.LabelFrame(self.root, text=" ARMORY INVENTORY STATUS ",
                                  bg="#222", fg="white", font=("Arial", 10, "bold"))
        frame_inv.pack(fill="both", expand=True, padx=20, pady=10)

        cols = ("serial", "type", "jet", "hours", "status")
        self.tree = ttk.Treeview(frame_inv, columns=cols, show="headings")
        self.tree.heading("serial", text="Serial #")
        self.tree.heading("type", text="Type")
        self.tree.heading("jet", text="Location / Jet")
        self.tree.heading("hours", text="Acc. Hours")
        self.tree.heading("status", text="Condition")

        self.tree.column("hours", width=80)
        self.tree.column("status", width=120)

        # Color Tags
        self.tree.tag_configure("good", background="#ccffcc")  # Green
        self.tree.tag_configure("bad", background="#ffcccc")  # Red

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh_data(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # 1. Populate Jet Dropdown
            cur.execute("SELECT tail_number FROM jets")
            jets = [r[0] for r in cur.fetchall()]
            self.jet_combo['values'] = jets
            if jets: self.jet_combo.current(0)

            # 2. Populate Table
            cur.execute("""
                        SELECT m.serial_number,
                               m.type,
                               COALESCE(j.tail_number, 'STORAGE'),
                               m.flight_hours,
                               m.service_status
                        FROM missiles m
                                 LEFT JOIN jets j ON m.attached_jet_id = j.id
                        ORDER BY m.service_status DESC, m.flight_hours DESC
                        """)
            rows = cur.fetchall()

            self.tree.delete(*self.tree.get_children())
            for row in rows:
                status = row[4]
                tag = "bad" if status == "UNSERVICEABLE" else "good"
                self.tree.insert("", tk.END, values=row, tags=(tag,))
        finally:
            conn.close()

    def log_landing(self):
        tail_num = self.jet_combo.get()
        try:
            duration = float(self.duration_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid Duration")
            return

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # Get Jet ID
            cur.execute("SELECT id FROM jets WHERE tail_number = %s", (tail_num,))
            res = cur.fetchone()
            if not res: return
            jet_id = res[0]

            # 1. Update Flight Hours for all missiles on this jet
            cur.execute("""
                        UPDATE missiles
                        SET flight_hours = flight_hours + %s
                        WHERE attached_jet_id = %s
                        """, (duration, jet_id))

            # 2. TRIGGER LOGIC: Downgrade status if hours > 100
            cur.execute("""
                        UPDATE missiles
                        SET service_status = 'UNSERVICEABLE'
                        WHERE flight_hours > 100
                          AND service_status = 'SERVICEABLE'
                        """)

            # Check how many missiles were flagged
            count = cur.rowcount

            conn.commit()
            self.refresh_data()

            msg = f"Logged {duration} hours for {tail_num} payload."
            if count > 0:
                msg += f"\n\n⚠️ CRITICAL: {count} missile(s) exceeded life-cycle limits and are now UNSERVICEABLE."
                messagebox.showwarning("Maintenance Alert", msg)
            else:
                messagebox.showinfo("Success", msg)

        except Exception as e:
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = MissileTrackerApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'air_force_ops',  # Ensure this database exists in pgAdmin
    'port': 5432
}

# Intelligence Mapping: Target Type -> Required Weapon Effect
TARGET_REQUIREMENTS = {
    "Bunker": "Penetrator",
    "Tank Column": "Anti-Armor",
    "Interception": "Anti-Air"
}


class ATOGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("ATO GENERATOR v2.5 // JOINT AIR OPS CENTER")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1a1a1a")

        # Initialize DB Tables before loading data
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
        """Automatically creates the tables and seed data if they don't exist."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # 1. Pilots Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS pilots
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
                            certified_type VARCHAR
                        (
                            20
                        ) NOT NULL,
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'READY'
                            );
                        """)

            # 2. Weapons Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS weapons
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
                            effect_type VARCHAR
                        (
                            50
                        ) NOT NULL,
                            stock INT DEFAULT 0
                            );
                        """)

            # 3. Aircraft Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS aircraft
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
                            model_type VARCHAR
                        (
                            20
                        ) NOT NULL,
                            compatible_effects TEXT[],
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'READY'
                            );
                        """)

            # 4. Targets Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS targets
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
                            target_type VARCHAR
                        (
                            50
                        ) NOT NULL,
                            priority INT CHECK
                        (
                            priority
                            BETWEEN
                            1
                            AND
                            10
                        )
                            );
                        """)

            # 5. Missions Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS missions
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            target_id
                            INT
                            REFERENCES
                            targets
                        (
                            id
                        ),
                            pilot_id INT REFERENCES pilots
                        (
                            id
                        ),
                            aircraft_id INT REFERENCES aircraft
                        (
                            id
                        ),
                            weapon_id INT REFERENCES weapons
                        (
                            id
                        ),
                            start_time TIMESTAMP NOT NULL,
                            end_time TIMESTAMP NOT NULL
                            );
                        """)

            # Seed Data - Only if tables are empty
            cur.execute("SELECT COUNT(*) FROM pilots")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO pilots (callsign, certified_type) VALUES ('Maverick', 'F-35'), ('Jester', 'F-35'), ('Warthog', 'A-10')")
                cur.execute(
                    "INSERT INTO weapons (name, effect_type, stock) VALUES ('GBU-31 JDAM', 'Penetrator', 10), ('AGM-65 Maverick', 'Anti-Armor', 20)")
                cur.execute(
                    "INSERT INTO aircraft (tail_number, model_type, compatible_effects) VALUES ('AF-001', 'F-35', ARRAY['Penetrator', 'Anti-Air']), ('AF-088', 'A-10', ARRAY['Anti-Armor'])")
                cur.execute(
                    "INSERT INTO targets (name, target_type, priority) VALUES ('Command Bunker Z-1', 'Bunker', 10), ('Enemy Division Alpha', 'Tank Column', 7)")

            conn.commit()
            print("Database structure verified and initialized.")
        except Exception as e:
            messagebox.showerror("Database Init Error", f"Failed to setup tables: {e}")
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#2d2d2d", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="⚔️ AIR TASKING ORDER GENERATOR", font=("Courier", 22, "bold"), bg="#2d2d2d",
                 fg="#00ff00").pack()

        # Main Split
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1a1a1a")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # LEFT: Target Selection
        left_frame = tk.LabelFrame(paned, text=" 1. TARGETING INTELLIGENCE ", bg="#1a1a1a", fg="#aaa")
        paned.add(left_frame, width=400)

        self.target_tree = ttk.Treeview(left_frame, columns=("id", "name", "type"), show="headings", height=10)
        self.target_tree.heading("id", text="ID")
        self.target_tree.heading("name", text="Target Name")
        self.target_tree.heading("type", text="Type")
        self.target_tree.column("id", width=40)
        self.target_tree.pack(fill="x", padx=5, pady=5)

        tk.Label(left_frame, text="Set Time (HH:MM):", bg="#1a1a1a", fg="white").pack()
        self.time_entry = tk.Entry(left_frame, justify='center')
        self.time_entry.insert(0, "14:00")
        self.time_entry.pack(pady=5)

        tk.Button(left_frame, text="GENERATE MISSION PARAMS", command=self.generate_mission,
                  bg="#004400", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill="x", padx=20, pady=10)

        # RIGHT: ATO Output & Logs
        right_frame = tk.LabelFrame(paned, text=" 2. PUBLISHED AIR TASKING ORDER ", bg="#1a1a1a", fg="#aaa")
        paned.add(right_frame)

        cols = ("target", "pilot", "aircraft", "weapon", "time")
        self.ato_tree = ttk.Treeview(right_frame, columns=cols, show="headings")
        for col in cols: self.ato_tree.heading(col, text=col.upper())
        self.ato_tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = tk.Text(right_frame, height=8, bg="black", fg="#0f0", font=("Courier", 9))
        self.log_text.pack(fill="x", padx=5, pady=5)

    def log(self, msg):
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)

    def refresh_data(self):
        conn = self.connect()
        if not conn: return
        cur = conn.cursor()

        # Load Targets
        self.target_tree.delete(*self.target_tree.get_children())
        cur.execute("SELECT id, name, target_type FROM targets ORDER BY priority DESC")
        for row in cur.fetchall(): self.target_tree.insert("", tk.END, values=row)

        # Load Existing ATO
        self.ato_tree.delete(*self.ato_tree.get_children())
        query = """
                SELECT t.name, p.callsign, a.tail_number, w.name, m.start_time
                FROM missions m
                         JOIN targets t ON m.target_id = t.id
                         JOIN pilots p ON m.pilot_id = p.id
                         JOIN aircraft a ON m.aircraft_id = a.id
                         JOIN weapons w ON m.weapon_id = w.id \
                """
        cur.execute(query)
        for row in cur.fetchall(): self.ato_tree.insert("", tk.END, values=row)
        conn.close()

    def generate_mission(self):
        selected = self.target_tree.selection()
        if not selected:
            messagebox.showwarning("Incomplete", "Select a target from intelligence first.")
            return

        target_row = self.target_tree.item(selected[0])['values']
        target_id, target_name, target_type = target_row

        # 1. Determine Required Effect
        req_effect = TARGET_REQUIREMENTS.get(target_type)
        self.log(f"Mission: {target_name}. Required Effect: {req_effect}")

        # Define Mission Window
        mission_time_str = self.time_entry.get()
        start_time = datetime.combine(datetime.now().date(), datetime.strptime(mission_time_str, "%H:%M").time())
        end_time = start_time + timedelta(hours=2)

        conn = self.connect()
        cur = conn.cursor()

        try:
            # 2. MATCHING: Find compatible Weapon
            cur.execute("SELECT id, name FROM weapons WHERE effect_type = %s AND stock > 0 LIMIT 1", (req_effect,))
            weapon = cur.fetchone()
            if not weapon: raise Exception(f"No {req_effect} weapons in inventory.")

            # 3. MATCHING: Find compatible Aircraft
            cur.execute(
                "SELECT id, tail_number, model_type FROM aircraft WHERE %s = ANY(compatible_effects) AND status='READY' LIMIT 1",
                (req_effect,))
            ac = cur.fetchone()
            if not ac: raise Exception(f"No ready aircraft compatible with {req_effect} munitions.")

            # 4. MATCHING: Find certified Pilot
            cur.execute("SELECT id, callsign FROM pilots WHERE certified_type = %s AND status='READY' LIMIT 1",
                        (ac[2],))
            pilot = cur.fetchone()
            if not pilot: raise Exception(f"No pilots currently certified and ready for {ac[2]}.")

            # --- 5. CONFLICT DETECTION ---
            conflict_query = """
                             SELECT id \
                             FROM missions
                             WHERE (pilot_id = %s OR aircraft_id = %s)
                               AND (start_time, end_time) OVERLAPS (%s, %s) \
                             """
            cur.execute(conflict_query, (pilot[0], ac[0], start_time, end_time))
            if cur.fetchone():
                raise Exception(f"CONSTRAINT VIOLATION: Pilot {pilot[1]} or Aircraft {ac[1]} is already scheduled.")

            # 6. Publish to ATO
            cur.execute("""
                        INSERT INTO missions (target_id, pilot_id, aircraft_id, weapon_id, start_time, end_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """, (target_id, pilot[0], ac[0], weapon[0], start_time, end_time))

            # Deduct Weapon Stock
            cur.execute("UPDATE weapons SET stock = stock - 1 WHERE id = %s", (weapon[0],))

            conn.commit()
            self.log(f"SUCCESS: Mission published for {pilot[1]} in {ac[1]}")
            self.refresh_data()

        except Exception as e:
            self.log(f"ABORTED: {str(e)}")
            messagebox.showerror("Mission Planning Failed", str(e))
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = ATOGenerator(root)
    root.mainloop()
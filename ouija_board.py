import tkinter as tk
from tkinter import messagebox
import psycopg2

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'carrier_deck_db',
    'port': 5432
}

# Visual Settings
SPOT_WIDTH = 120
SPOT_HEIGHT = 80
GAP = 20


class OuijaBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FLIGHT DECK OUIJA BOARD // USS GERALD R. FORD")
        self.root.geometry("1000x700")
        self.root.configure(bg="#2c3e50")

        self.selected_plane_id = None
        self.selected_tail = None
        self.origin_spot_id = None

        self.init_db()
        self.setup_ui()
        self.refresh_board()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("DB Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing: Automatically creates tables and seeds data if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # 1. Create Aircraft Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS aircraft
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            tail_no
                            VARCHAR
                        (
                            20
                        ) UNIQUE NOT NULL,
                            model VARCHAR
                        (
                            20
                        ) NOT NULL,
                            fuel_level INT DEFAULT 100,
                            maintenance_status VARCHAR
                        (
                            20
                        ) DEFAULT 'GOOD',
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'ON_DECK'
                            );
                        """)

            # 2. Create Deck Spots Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS deck_spots
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            spot_name
                            VARCHAR
                        (
                            50
                        ) NOT NULL,
                            spot_type VARCHAR
                        (
                            20
                        ) NOT NULL,
                            operational_status VARCHAR
                        (
                            20
                        ) DEFAULT 'READY',
                            occupied_by_plane_id INT UNIQUE REFERENCES aircraft
                        (
                            id
                        ) ON DELETE SET NULL
                            );
                        """)

            # 3. Seed Data (Only if empty)
            cur.execute("SELECT COUNT(*) FROM aircraft")
            if cur.fetchone()[0] == 0:
                print("Seeding Database...")
                # Insert Aircraft
                cur.execute(
                    "INSERT INTO aircraft (tail_no, model) VALUES ('VFA-101', 'F-18'), ('VFA-102', 'F-18'), ('VFA-200', 'F-35'), ('VAW-12', 'E-2D')")

                # Insert Spots
                cur.execute(
                    "INSERT INTO deck_spots (spot_name, spot_type) VALUES ('Parking Alpha', 'PARKING'), ('Parking Bravo', 'PARKING'), ('Parking Charlie', 'PARKING')")
                cur.execute(
                    "INSERT INTO deck_spots (spot_name, spot_type) VALUES ('Catapult 1', 'CATAPULT'), ('Catapult 2', 'CATAPULT')")
                cur.execute(
                    "INSERT INTO deck_spots (spot_name, spot_type, operational_status) VALUES ('Elevator 1', 'ELEVATOR', 'READY'), ('Elevator 3', 'ELEVATOR', 'DOWN')")

                # Park planes (Linking tables)
                # We need to subquery IDs to be safe in case serials don't match 1-to-1
                cur.execute(
                    "UPDATE deck_spots SET occupied_by_plane_id = (SELECT id FROM aircraft WHERE tail_no='VFA-101') WHERE spot_name = 'Parking Alpha'")
                cur.execute(
                    "UPDATE deck_spots SET occupied_by_plane_id = (SELECT id FROM aircraft WHERE tail_no='VFA-102') WHERE spot_name = 'Parking Bravo'")

            conn.commit()
            print("Database initialized successfully.")

        except Exception as e:
            messagebox.showerror("Init Error", f"Failed to initialize DB: {e}")
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#34495e", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="DIGITAL FLIGHT DECK MANAGER", font=("Stencil", 24), bg="#34495e", fg="#ecf0f1").pack()

        self.status_lbl = tk.Label(header, text="Select an aircraft to move...", font=("Arial", 12), bg="#34495e",
                                   fg="#f1c40f")
        self.status_lbl.pack(pady=5)

        # Main Deck Canvas
        self.canvas = tk.Canvas(self.root, bg="#34495e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)

        # Controls
        controls = tk.Frame(self.root, bg="#2c3e50", pady=10)
        controls.pack(fill="x")
        tk.Button(controls, text="REFRESH DECK", command=self.refresh_board,
                  bg="#95a5a6", width=20, font=("Arial", 10, "bold")).pack(side="right", padx=20)

        # Launch Button (Hidden by default)
        self.btn_launch = tk.Button(controls, text="LAUNCH AIRCRAFT", command=self.launch_aircraft,
                                    bg="#e74c3c", fg="white", width=20, font=("Arial", 10, "bold"), state="disabled")
        self.btn_launch.pack(side="left", padx=20)

    def refresh_board(self):
        self.canvas.delete("all")
        self.selected_plane_id = None
        self.btn_launch.config(state="disabled", bg="#95a5a6")
        self.status_lbl.config(text="Select an aircraft to move...", fg="#f1c40f")

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        SELECT s.id,
                               s.spot_name,
                               s.spot_type,
                               s.operational_status,
                               a.id,
                               a.tail_no,
                               a.model
                        FROM deck_spots s
                                 LEFT JOIN aircraft a ON s.occupied_by_plane_id = a.id
                        ORDER BY s.spot_type, s.spot_name
                        """)
            spots = cur.fetchall()

            # Layout Logic (Simple Grid)
            x, y = 50, 50
            for row in spots:
                spot_id, name, type_, status, plane_id, tail, model = row

                # Draw Spot
                color = "#7f8c8d"  # Gray (Parking)
                if type_ == 'CATAPULT': color = "#27ae60"  # Green
                if type_ == 'ELEVATOR': color = "#d35400"  # Orange
                if status == 'DOWN': color = "#c0392b"  # Red (Broken)

                # Draw Rectangle (Spot)
                self.canvas.create_rectangle(x, y, x + SPOT_WIDTH, y + SPOT_HEIGHT,
                                             fill=color, outline="white", width=2,
                                             tags=f"spot_{spot_id}")

                # Label Spot
                self.canvas.create_text(x + SPOT_WIDTH / 2, y + 15, text=f"{name}\n({status})",
                                        fill="white", font=("Arial", 8))

                # Draw Plane (if present)
                if plane_id:
                    self.canvas.create_oval(x + 20, y + 30, x + SPOT_WIDTH - 20, y + SPOT_HEIGHT - 10,
                                            fill="#2980b9", outline="white", width=2,
                                            tags=f"plane_{plane_id}")
                    self.canvas.create_text(x + SPOT_WIDTH / 2, y + 55, text=f"{tail}\n{model}",
                                            fill="white", font=("Arial", 9, "bold"))

                    # Bind Click to Plane (Select)
                    self.canvas.tag_bind(f"plane_{plane_id}", "<Button-1>",
                                         lambda e, pid=plane_id, sid=spot_id, t=tail: self.select_plane(pid, sid, t))
                else:
                    # Bind Click to Empty Spot (Move Target)
                    self.canvas.tag_bind(f"spot_{spot_id}", "<Button-1>",
                                         lambda e, sid=spot_id, stat=status: self.move_plane(sid, stat))

                # Move X/Y for next spot
                x += SPOT_WIDTH + GAP
                if x > 800:
                    x = 50
                    y += SPOT_HEIGHT + GAP

        finally:
            conn.close()

    def select_plane(self, plane_id, spot_id, tail):
        self.selected_plane_id = plane_id
        self.origin_spot_id = spot_id
        self.selected_tail = tail
        self.status_lbl.config(text=f"SELECTED: {tail}. Click an empty spot to move.", fg="#3498db")

        # Check if on Catapult to enable launch
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT spot_type FROM deck_spots WHERE id=%s", (spot_id,))
        res = cur.fetchone()
        if res and res[0] == 'CATAPULT':
            self.btn_launch.config(state="normal", bg="#e74c3c")
        else:
            self.btn_launch.config(state="disabled", bg="#95a5a6")
        conn.close()

    def move_plane(self, target_spot_id, target_status):
        if not self.selected_plane_id: return

        # --- CONSTRAINT LOGIC ---
        if target_status == 'DOWN':
            messagebox.showerror("Safety Alert",
                                 "Cannot move aircraft to this spot.\n\nReason: Equipment is DOWN/Inoperable.")
            return

        conn = self.connect()
        try:
            cur = conn.cursor()

            # 1. Clear Origin
            cur.execute("UPDATE deck_spots SET occupied_by_plane_id = NULL WHERE id = %s", (self.origin_spot_id,))

            # 2. Occupy Target
            cur.execute("UPDATE deck_spots SET occupied_by_plane_id = %s WHERE id = %s",
                        (self.selected_plane_id, target_spot_id))

            conn.commit()
            self.refresh_board()
            self.status_lbl.config(text=f"Moved {self.selected_tail} successfully.", fg="#2ecc71")

        except Exception as e:
            messagebox.showerror("DB Error", str(e))
        finally:
            conn.close()

    def launch_aircraft(self):
        if not self.selected_plane_id: return

        if messagebox.askyesno("Confirm Launch", f"Launch {self.selected_tail} from Catapult?"):
            conn = self.connect()
            try:
                cur = conn.cursor()

                # 1. Update Aircraft Status to AIRBORNE
                cur.execute("UPDATE aircraft SET status = 'AIRBORNE' WHERE id = %s", (self.selected_plane_id,))

                # 2. Clear the Catapult Spot
                cur.execute("UPDATE deck_spots SET occupied_by_plane_id = NULL WHERE id = %s", (self.origin_spot_id,))

                conn.commit()
                self.refresh_board()
                messagebox.showinfo("Launch Successful", f"{self.selected_tail} is now AIRBORNE.")

            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = OuijaBoardApp(root)
    root.mainloop()
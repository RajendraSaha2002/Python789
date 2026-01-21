import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'biometric_db',
    'port': 5432
}


class AccessControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biometric Access Control // Watchdog")
        self.root.geometry("900x600")
        self.root.configure(bg="#222")

        self.last_log_id = 0
        self.breach_active = False

        # 1. Initialize DB (Fixes the "Relation does not exist" error)
        self.init_db()

        self.setup_ui()

        # Start the Watchdog Loop (Polls DB every 1 second)
        self.root.after(1000, self.watchdog_loop)

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"Connection Error: {e}")
            return None

    def init_db(self):
        """Automatically creates the table and security triggers if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # Create Table
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
                            user_id
                            VARCHAR
                        (
                            50
                        ),
                            door_id VARCHAR
                        (
                            50
                        ),
                            access_granted BOOLEAN
                            );
                        """)

            # Create Security Function
            cur.execute("""
                        CREATE
                        OR REPLACE FUNCTION prevent_log_deletion()
                RETURNS TRIGGER AS $$
                        BEGIN
                    RAISE
                        EXCEPTION 'SECURITY ALERT: Access Logs are Immutable. Deletion is strictly prohibited.';
                        END;
                $$
                        LANGUAGE plpgsql;
                        """)

            # Attach Trigger
            cur.execute("DROP TRIGGER IF EXISTS trigger_immutable_logs ON access_logs;")
            cur.execute("""
                        CREATE TRIGGER trigger_immutable_logs
                            BEFORE DELETE
                            ON access_logs
                            FOR EACH ROW
                            EXECUTE FUNCTION prevent_log_deletion();
                        """)

            conn.commit()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Database Init Error: {e}")
        finally:
            conn.close()

    def setup_ui(self):
        # --- LEFT PANEL: Simulator (The "Door") ---
        left_frame = tk.Frame(self.root, bg="#333", width=300, pady=20, padx=20)
        left_frame.pack(side=tk.LEFT, fill="y")

        tk.Label(left_frame, text="DOOR SIMULATOR", font=("Arial", 14, "bold"), bg="#333", fg="white").pack(pady=10)

        tk.Label(left_frame, text="User ID:", bg="#333", fg="white").pack(anchor="w")
        self.user_entry = tk.Entry(left_frame, font=("Arial", 12))
        self.user_entry.insert(0, "Agent_J")
        self.user_entry.pack(fill="x", pady=5)

        tk.Label(left_frame, text="Door ID:", bg="#333", fg="white").pack(anchor="w")
        self.door_combo = ttk.Combobox(left_frame, values=["Main_Entrance", "Server_Room", "Nuclear_Silo"])
        self.door_combo.set("Server_Room")
        self.door_combo.pack(fill="x", pady=5)

        tk.Label(left_frame, text="Swipe Card:", bg="#333", fg="white").pack(anchor="w", pady=(20, 0))

        tk.Button(left_frame, text="ACCESS GRANTED (Valid Card)", command=lambda: self.swipe_card(True),
                  bg="#006600", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill="x", pady=5)

        tk.Button(left_frame, text="ACCESS DENIED (Invalid Card)", command=lambda: self.swipe_card(False),
                  bg="#990000", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill="x", pady=5)

        # --- RIGHT PANEL: Watchdog Log ---
        right_frame = tk.Frame(self.root, bg="#222", padx=20, pady=20)
        right_frame.pack(side=tk.RIGHT, fill="both", expand=True)

        # Alarm Banner
        self.alarm_label = tk.Label(right_frame, text="SYSTEM SECURE", bg="#003300", fg="#00ff00",
                                    font=("Courier", 20, "bold"), pady=10)
        self.alarm_label.pack(fill="x", pady=(0, 10))

        # Log Table
        cols = ("time", "user", "door", "status")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)

        self.tree.heading("time", text="TIMESTAMP")
        self.tree.heading("user", text="USER ID")
        self.tree.heading("door", text="DOOR ID")
        self.tree.heading("status", text="RESULT")

        self.tree.column("time", width=150)
        self.tree.column("status", width=100)

        self.tree.pack(fill="both", expand=True)

        # Tag configuration for colors
        self.tree.tag_configure("success", foreground="#00ff00")  # Green text
        self.tree.tag_configure("fail", foreground="#ff3333")  # Red text

    # --- SIMULATOR LOGIC (Insert Data) ---
    def swipe_card(self, success):
        user = self.user_entry.get()
        door = self.door_combo.get()

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO access_logs (user_id, door_id, access_granted) VALUES (%s, %s, %s)",
                        (user, door, success))
            conn.commit()
            print(f"Swipe recorded: {user} @ {door} -> {success}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    # --- WATCHDOG LOGIC (Poll Data) ---
    def watchdog_loop(self):
        conn = self.connect()
        if conn:
            try:
                cur = conn.cursor()

                # 1. Fetch latest 20 logs
                cur.execute(
                    "SELECT id, timestamp, user_id, door_id, access_granted FROM access_logs ORDER BY id DESC LIMIT 20")
                rows = cur.fetchall()

                # Update Table
                for item in self.tree.get_children():
                    self.tree.delete(item)

                for row in rows:
                    log_id, ts, user, door, success = row
                    status_text = "GRANTED" if success else "DENIED"
                    tag = "success" if success else "fail"
                    # Format time
                    time_str = ts.strftime("%H:%M:%S")
                    self.tree.insert("", tk.END, values=(time_str, user, door, status_text), tags=(tag,))

                # 2. CHECK FOR BREACH (3 Consecutive Failures)
                cur.execute("SELECT access_granted FROM access_logs ORDER BY id DESC LIMIT 3")
                latest_3 = [r[0] for r in cur.fetchall()]

                # Logic: If we have at least 3 records AND all 3 are False
                if len(latest_3) == 3 and all(status is False for status in latest_3):
                    if not self.breach_active:
                        self.trigger_alarm()
                else:
                    if self.breach_active:
                        self.reset_alarm()

            except Exception as e:
                print(f"Watchdog Error: {e}")
            finally:
                conn.close()

        # Schedule next run in 1000ms (1 second)
        self.root.after(1000, self.watchdog_loop)

    def trigger_alarm(self):
        self.breach_active = True
        self.alarm_label.config(text="!!! SECURITY BREACH DETECTED !!!", bg="red", fg="white")

    def reset_alarm(self):
        self.breach_active = False
        self.alarm_label.config(text="SYSTEM SECURE", bg="#003300", fg="#00ff00")


if __name__ == "__main__":
    root = tk.Tk()
    app = AccessControlApp(root)
    root.mainloop()
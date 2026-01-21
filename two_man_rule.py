import tkinter as tk
from tkinter import messagebox
import psycopg2
import bcrypt
import time

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'nuclear_db',
    'port': 5432
}

TIMEOUT_SECONDS = 60


class TwoManRuleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("STRATEGIC COMMAND // TWO-MAN RULE")
        self.root.geometry("600x500")
        self.root.configure(bg="#1a1a1a")

        # State Variables
        self.officer_a = None
        self.timer_running = False
        self.time_left = 0

        self.init_db()
        self.setup_ui()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return None

    def init_db(self):
        """Self-healing: Creates tables and seeds users with hashed passwords if empty."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            # Ensure Schema
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS officers
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            username
                            VARCHAR
                        (
                            50
                        ) UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            rank VARCHAR
                        (
                            50
                        ) NOT NULL
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS audit_log
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            username
                            VARCHAR
                        (
                            50
                        ),
                            action VARCHAR
                        (
                            100
                        ),
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            ip_address VARCHAR
                        (
                            20
                        ) DEFAULT '127.0.0.1'
                            );
                        """)

            # Check if seeded
            cur.execute("SELECT count(*) FROM officers")
            if cur.fetchone()[0] == 0:
                # Seed with Bcrypt Hashes
                # Users: general_ripper (password: code123), major_kong (password: nuclear99)
                hash1 = bcrypt.hashpw("code123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                hash2 = bcrypt.hashpw("nuclear99".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                cur.execute("INSERT INTO officers (username, password_hash, rank) VALUES (%s, %s, %s)",
                            ('general_ripper', hash1, 'General'))
                cur.execute("INSERT INTO officers (username, password_hash, rank) VALUES (%s, %s, %s)",
                            ('major_kong', hash2, 'Major'))
                print("Database seeded with hashed credentials.")

            conn.commit()
        finally:
            conn.close()

    def log_audit(self, username, action):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO audit_log (username, action) VALUES (%s, %s)", (username, action))
            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        self.header = tk.Label(self.root, text="SYSTEM LOCKED", font=("Impact", 28), bg="#1a1a1a", fg="#ff0000")
        self.header.pack(pady=30)

        # Status Circle (Canvas)
        self.canvas = tk.Canvas(self.root, width=100, height=100, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack()
        self.status_light = self.canvas.create_oval(25, 25, 75, 75, fill="#550000")  # Dark Red

        # Timer Label
        self.timer_lbl = tk.Label(self.root, text="--", font=("Courier", 20, "bold"), bg="#1a1a1a", fg="#555")
        self.timer_lbl.pack(pady=10)

        # Login Form
        form_frame = tk.Frame(self.root, bg="#222", padx=20, pady=20)
        form_frame.pack(pady=20)

        tk.Label(form_frame, text="OFFICER ID:", bg="#222", fg="white").grid(row=0, column=0)
        self.user_entry = tk.Entry(form_frame)
        self.user_entry.grid(row=0, column=1, padx=5)

        tk.Label(form_frame, text="PASSWORD:", bg="#222", fg="white").grid(row=1, column=0)
        self.pass_entry = tk.Entry(form_frame, show="*")
        self.pass_entry.grid(row=1, column=1, padx=5)

        self.btn_auth = tk.Button(form_frame, text="TURN KEY", command=self.authenticate,
                                  bg="#444", fg="white", font=("Arial", 10, "bold"), width=15)
        self.btn_auth.grid(row=2, column=0, columnspan=2, pady=15)

        self.info_lbl = tk.Label(self.root, text="Awaiting First Officer Authorization...", bg="#1a1a1a", fg="#aaa")
        self.info_lbl.pack()

    def authenticate(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        # DB Verification
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT password_hash, rank FROM officers WHERE username = %s", (username,))
            result = cur.fetchone()

            if not result:
                messagebox.showerror("Error", "Invalid Credentials")
                self.log_audit(username, "LOGIN_FAILED")
                return

            stored_hash, rank = result

            # Verify Password using Bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                self.process_valid_login(username, rank)
            else:
                messagebox.showerror("Error", "Invalid Credentials")
                self.log_audit(username, "LOGIN_FAILED")

        finally:
            conn.close()
            # Clear Inputs
            self.user_entry.delete(0, tk.END)
            self.pass_entry.delete(0, tk.END)

    def process_valid_login(self, username, rank):
        # LOGIC: Check State

        if self.officer_a is None:
            # First Key Turn
            self.officer_a = username
            self.log_audit(username, "KEY_TURN_1")

            # Update UI
            self.header.config(text="⚠️ ARMED: AWAITING SECOND KEY", fg="yellow")
            self.canvas.itemconfig(self.status_light, fill="yellow")
            self.info_lbl.config(text=f"Key 1 Turned by {rank} {username}. Waiting for Officer B...", fg="yellow")

            # Start Timer
            self.start_timer()

        else:
            # Second Key Turn attempt
            if username == self.officer_a:
                messagebox.showwarning("Violation", "Two-Man Rule Violation:\nThe same officer cannot turn both keys.")
                self.log_audit(username, "VIOLATION_SAME_USER")
                return

            # Valid Second User
            self.stop_timer()
            self.log_audit(username, "KEY_TURN_2")
            self.log_audit("SYSTEM", "LAUNCH_AUTHORIZED")

            # Update UI to Success State
            self.header.config(text="☢️ LAUNCH SEQUENCE INITIATED", fg="#00ff00")
            self.canvas.itemconfig(self.status_light, fill="#00ff00")
            self.info_lbl.config(text=f"Authenticated: {self.officer_a} & {username}.\nMissiles Firing.", fg="#00ff00")
            self.btn_auth.config(state="disabled")

    def start_timer(self):
        self.time_left = TIMEOUT_SECONDS
        self.timer_running = True
        self.countdown()

    def stop_timer(self):
        self.timer_running = False
        self.timer_lbl.config(text="--", fg="#555")

    def countdown(self):
        if self.timer_running:
            if self.time_left > 0:
                self.timer_lbl.config(text=f"00:{self.time_left:02d}", fg="red")
                self.time_left -= 1
                self.root.after(1000, self.countdown)
            else:
                self.reset_system("TIMEOUT")

    def reset_system(self, reason):
        self.officer_a = None
        self.timer_running = False
        self.log_audit("SYSTEM", f"RESET_{reason}")

        self.header.config(text="SYSTEM LOCKED", fg="#ff0000")
        self.canvas.itemconfig(self.status_light, fill="#550000")
        self.info_lbl.config(text="Authorization Window Expired. System Reset.", fg="red")
        self.timer_lbl.config(text="--", fg="#555")
        messagebox.showinfo("Timeout", "Time window expired. Authorization reset.")


if __name__ == "__main__":
    root = tk.Tk()
    app = TwoManRuleApp(root)
    root.mainloop()
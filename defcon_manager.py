import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'defcon_db',
    'port': 5432
}

DEFCON_COLORS = {
    5: ("#00FF00", "white"),  # Green
    4: ("#00AA00", "white"),  # Dark Green
    3: ("#FFFF00", "black"),  # Yellow
    2: ("#FF8C00", "white"),  # Orange
    1: ("#FF0000", "white")  # Red
}


class DefconManager:
    def __init__(self, root):
        self.root = root
        self.root.title("STRATCOM // DEFCON PROTOCOL MANAGER")
        self.root.geometry("1000x700")
        self.root.configure(bg="#050505")

        self.current_defcon = 5

        self.setup_ui()
        self.init_db()
        self.switch_defcon(5)  # Start at DEFCON 5

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing: Ensures table exists."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS defcon_checklist
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            defcon_level
                            INT,
                            task_description
                            TEXT,
                            dept_head
                            VARCHAR
                        (
                            50
                        ),
                            is_completed BOOLEAN DEFAULT FALSE,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """)
            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # --- HEADER ---
        self.header_frame = tk.Frame(self.root, bg="#111", pady=10)
        self.header_frame.pack(fill="x")

        self.title_lbl = tk.Label(self.header_frame, text="BASE DEFCON STATUS", font=("Courier", 24, "bold"), bg="#111",
                                  fg="white")
        self.title_lbl.pack()

        # --- STATUS SELECTOR ---
        status_frame = tk.Frame(self.root, bg="#050505", pady=20)
        status_frame.pack(fill="x")

        for i in range(5, 0, -1):
            color, text_col = DEFCON_COLORS[i]
            btn = tk.Button(status_frame, text=f"DEFCON {i}", font=("Courier", 12, "bold"),
                            bg=color, fg=text_col, width=15, height=2,
                            command=lambda l=i: self.switch_defcon(l))
            btn.pack(side="left", padx=10, expand=True)

        # --- CONTENT SPLIT ---
        content_frame = tk.Frame(self.root, bg="#050505")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # LEFT: Checklist
        list_frame = tk.LabelFrame(content_frame, text=" PROTOCOL CHECKLIST ", bg="#050505", fg="#00ff00")
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("id", "task", "dept", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("task", text="PROTOCOL ACTION")
        self.tree.heading("dept", text="DEPT HEAD")
        self.tree.heading("status", text="STATE")
        self.tree.column("id", width=40)
        self.tree.column("status", width=100)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree.bind("<Double-1>", self.toggle_task)

        # RIGHT: Comms Log
        log_frame = tk.LabelFrame(content_frame, text=" ENCRYPTED COMMS LOG ", bg="#050505", fg="#00ff00", width=300)
        log_frame.pack(side="right", fill="both")

        self.log_text = tk.Text(log_frame, bg="black", fg="#00ff00", font=("Courier", 9), width=40)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)

    def switch_defcon(self, level):
        self.current_defcon = level
        bg_color, text_color = DEFCON_COLORS[level]

        self.header_frame.config(bg=bg_color)
        self.title_lbl.config(bg=bg_color, fg=text_color, text=f"BASE STATUS: DEFCON {level}")

        self.log(f"COMMAND: Setting Alert Level to DEFCON {level}")
        self.load_protocols(level)
        self.trigger_alerts(level)

    def load_protocols(self, level):
        """Queries DB for protocols associated with the current level."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            # Fetch protocols for this level
            cur.execute(
                "SELECT id, task_description, dept_head, is_completed FROM defcon_checklist WHERE defcon_level = %s",
                (level,))
            rows = cur.fetchall()

            for item in self.tree.get_children():
                self.tree.delete(item)

            for row in rows:
                status = "COMPLETED" if row[3] else "PENDING"
                self.tree.insert("", tk.END, values=(row[0], row[1], row[2], status))
        finally:
            conn.close()

    def trigger_alerts(self, level):
        """Simulates sending encrypted alerts to Dept Heads."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT dept_head FROM defcon_checklist WHERE defcon_level = %s", (level,))
            depts = cur.fetchall()

            for dept in depts:
                self.log(f"ALERT: Encrypted order sent to [{dept[0]}]")
        finally:
            conn.close()

    def toggle_task(self, event):
        """Updates completion status when a task is double-clicked."""
        selected = self.tree.selection()
        if not selected: return

        item = self.tree.item(selected[0])
        task_id = item['values'][0]
        current_status = item['values'][3]
        new_bool = False if current_status == "COMPLETED" else True

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("UPDATE defcon_checklist SET is_completed = %s WHERE id = %s", (new_bool, task_id))
            conn.commit()

            self.log(f"STATUS UPDATE: Task #{task_id} marked as {'COMPLETED' if new_bool else 'PENDING'}")
            self.load_protocols(self.current_defcon)
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = DefconManager(root)
    root.mainloop()
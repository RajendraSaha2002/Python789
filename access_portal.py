import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import os

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'postgres',  # Or your specific DB name
    'port': 5432
}

LOG_FILE = "access_audit.log"

# Clearance mapping for display
CLEARANCE_NAMES = {0: "PUBLIC", 1: "SECRET", 2: "TOP SECRET"}


class RBACPortal:
    def __init__(self, root):
        self.root = root
        self.root.title("DEPARTMENT OF DEFENSE // DOCUMENT PORTAL")
        self.root.geometry("800x600")
        self.root.configure(bg="#0a0a0a")

        self.current_agent = None

        self.setup_ui()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return None

    def setup_ui(self):
        # 1. Login Frame
        self.login_frame = tk.Frame(self.root, bg="#111", padx=50, pady=50)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self.login_frame, text="IDENTIFICATION REQUIRED", font=("Courier", 16, "bold"), bg="#111",
                 fg="#ff4444").pack(pady=20)

        tk.Label(self.login_frame, text="AGENT ID:", bg="#111", fg="white").pack(anchor="w")
        self.id_entry = tk.Entry(self.login_frame, font=("Arial", 12), width=30)
        self.id_entry.pack(pady=5)
        self.id_entry.insert(0, "J-117")

        tk.Label(self.login_frame, text="ACCESS CODE:", bg="#111", fg="white").pack(anchor="w")
        self.code_entry = tk.Entry(self.login_frame, font=("Arial", 12), width=30, show="*")
        self.code_entry.pack(pady=5)
        self.code_entry.insert(0, "alpha123")

        tk.Button(self.login_frame, text="AUTHENTICATE", command=self.authenticate,
                  bg="#333", fg="#00ff00", font=("Courier", 12, "bold"), width=25).pack(pady=30)

    def authenticate(self):
        agent_id = self.id_entry.get().strip()
        code = self.code_entry.get().strip()

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT agent_id, name, clearance_level FROM agents WHERE agent_id=%s AND access_code=%s",
                        (agent_id, code))
            user = cur.fetchone()

            if user:
                self.current_agent = {
                    "id": user[0],
                    "name": user[1],
                    "clearance": user[2]
                }
                self.show_dashboard()
                self.audit_log("LOGIN_SUCCESS", "Agent authenticated successfully.")
            else:
                self.audit_log("LOGIN_FAILURE", f"Invalid credentials attempt for ID: {agent_id}")
                messagebox.showerror("ACCESS DENIED", "Invalid Agent ID or Access Code.")
        finally:
            conn.close()

    def show_dashboard(self):
        self.login_frame.destroy()

        # Dashboard Header
        header = tk.Frame(self.root, bg="#222", pady=10)
        header.pack(fill="x")

        tk.Label(header,
                 text=f"WELCOME, {self.current_agent['name']} ({CLEARANCE_NAMES[self.current_agent['clearance']]})",
                 font=("Courier", 10), bg="#222", fg="#00ff00", padx=20).pack(side="left")

        tk.Button(header, text="LOGOUT", command=self.logout, bg="#444", fg="white").pack(side="right", padx=20)

        # Document List
        list_frame = tk.LabelFrame(self.root, text=" AVAILABLE CLASSIFIED ARCHIVES ", bg="#0a0a0a", fg="#aaa", padx=10,
                                   pady=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=20)

        cols = ("id", "filename", "clearance")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=15)
        self.tree.heading("id", text="ID")
        self.tree.heading("filename", text="DOCUMENT FILENAME")
        self.tree.heading("clearance", text="REQUIRED CLEARANCE")
        self.tree.column("id", width=50)
        self.tree.pack(fill="both", expand=True)

        tk.Button(self.root, text="OPEN ENCRYPTED DOCUMENT", command=self.access_document,
                  bg="#004400", fg="white", font=("Arial", 12, "bold"), pady=10).pack(fill="x", padx=20, pady=(0, 20))

        self.load_documents()

    def load_documents(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, filename, required_clearance FROM classified_docs ORDER BY required_clearance ASC")
            for row in cur.fetchall():
                # Display names instead of numbers for clearance
                display_row = (row[0], row[1], CLEARANCE_NAMES[row[2]])
                self.tree.insert("", tk.END, values=display_row)
        finally:
            conn.close()

    def access_document(self):
        selected = self.tree.selection()
        if not selected: return

        doc_id = self.tree.item(selected[0])['values'][0]

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT filename, required_clearance, summary FROM classified_docs WHERE id=%s", (doc_id,))
            doc = cur.fetchone()

            filename = doc[0]
            required_lvl = doc[1]
            content = doc[2]

            # --- THE RBAC LOGIC ---
            if self.current_agent['clearance'] >= required_lvl:
                # ACCESS GRANTED
                self.audit_log("ACCESS_GRANTED", f"Opened document: {filename}")
                messagebox.showinfo("DOCUMENT CONTENT", f"FILENAME: {filename}\n\n{content}")
            else:
                # ACCESS DENIED
                self.audit_log("ACCESS_DENIED", f"Unauthorized attempt to open: {filename}")
                messagebox.showerror("SECURITY ALERT",
                                     f"CLEARANCE INSUFFICIENT.\n\nRequired: {CLEARANCE_NAMES[required_lvl]}\nYour Level: {CLEARANCE_NAMES[self.current_agent['clearance']]}")
        finally:
            conn.close()

    def audit_log(self, status, detail):
        """Generates a log entry in a separate file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent_id = self.current_agent['id'] if self.current_agent else "ANONYMOUS"

        log_entry = f"[{timestamp}] [{status}] Agent:{agent_id} | {detail}\n"

        with open(LOG_FILE, "a") as f:
            f.write(log_entry)

        print(f"Audit: {log_entry.strip()}")

    def logout(self):
        self.audit_log("LOGOUT", "Agent logged out.")
        os.execl(sys.executable, sys.executable, *sys.argv)


if __name__ == "__main__":
    import sys

    root = tk.Tk()
    app = RBACPortal(root)
    root.mainloop()
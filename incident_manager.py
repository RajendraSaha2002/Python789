import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psycopg2
import json

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'cyber_def_db',
    'port': 5432
}


class IncidentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CYBER COMMAND // Incident Case Manager")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1e1e1e")  # Dark Theme

        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#333", foreground="white", fieldbackground="#333")
        style.configure("TLabel", background="#1e1e1e", foreground="#00ff00", font=("Consolas", 10))
        style.configure("TButton", font=("Consolas", 10, "bold"))

        self.setup_ui()
        self.init_db()  # <--- NEW: Automatically create tables if missing
        self.refresh_incidents()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Creates the database tables automatically if they don't exist."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # 1. Create Incidents Table
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS incidents
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            title
                            VARCHAR
                        (
                            200
                        ) NOT NULL,
                            severity VARCHAR
                        (
                            20
                        ) CHECK
                        (
                            severity
                            IN
                        (
                            'Low',
                            'Medium',
                            'High',
                            'CRITICAL'
                        )),
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'Open',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """)

            # 2. Create Evidence Table (with JSONB)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS evidence
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            incident_id
                            INT,
                            description
                            VARCHAR
                        (
                            255
                        ),
                            log_data JSONB,
                            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT fk_incident
                            FOREIGN KEY
                        (
                            incident_id
                        )
                            REFERENCES incidents
                        (
                            id
                        )
                            ON DELETE CASCADE
                            );
                        """)

            # 3. Create Index for fast JSON searching
            cur.execute("CREATE INDEX IF NOT EXISTS idx_log_data ON evidence USING GIN (log_data);")

            conn.commit()
        except Exception as e:
            messagebox.showerror("Database Init Error", str(e))
        finally:
            conn.close()

    def setup_ui(self):
        # --- LEFT PANEL: Incident List ---
        left_frame = tk.Frame(self.root, bg="#1e1e1e", width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left_frame, text="ACTIVE INCIDENTS").pack(anchor="w")

        cols = ("id", "title", "severity")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", height=20)
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("severity", text="Level")
        self.tree.column("id", width=40)
        self.tree.column("severity", width=80)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_incident_select)

        # Form to add incident
        form_frame = tk.Frame(left_frame, bg="#333", pady=5)
        form_frame.pack(fill="x", pady=10)
        self.title_entry = tk.Entry(form_frame, bg="black", fg="white", insertbackground="white")
        self.title_entry.pack(fill="x", padx=5)
        self.severity_combo = ttk.Combobox(form_frame, values=["Low", "Medium", "High", "CRITICAL"])
        self.severity_combo.set("Medium")
        self.severity_combo.pack(fill="x", padx=5, pady=5)
        tk.Button(form_frame, text="OPEN NEW CASE", command=self.create_incident, bg="#004400", fg="white").pack(
            fill="x", padx=5)

        # --- RIGHT PANEL: Evidence & Analysis ---
        right_frame = tk.Frame(self.root, bg="#1e1e1e")
        right_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=10, pady=10)

        # 1. Evidence Input
        ttk.Label(right_frame, text="ADD JSON EVIDENCE LOG:").pack(anchor="w")
        self.log_desc = tk.Entry(right_frame, bg="#333", fg="white")
        self.log_desc.insert(0, "Log Description (e.g., Firewall Block)")
        self.log_desc.pack(fill="x", pady=2)

        self.json_input = scrolledtext.ScrolledText(right_frame, height=5, bg="black", fg="#00ff00",
                                                    insertbackground="white")
        self.json_input.pack(fill="x", pady=5)

        tk.Button(right_frame, text="ATTACH LOG TO CASE", command=self.add_evidence, bg="#0055aa", fg="white").pack(
            anchor="e")

        # 2. JSON Query Tool
        ttk.Label(right_frame, text="--- THREAT HUNTING (JSONB Query) ---").pack(anchor="w", pady=(20, 5))

        search_frame = tk.Frame(right_frame, bg="#1e1e1e")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Find Logs containing Key:Value -> ").pack(side=tk.LEFT)
        self.search_key = tk.Entry(search_frame, width=15, bg="#333", fg="white")
        self.search_key.insert(0, "src_ip")
        self.search_key.pack(side=tk.LEFT, padx=5)

        self.search_val = tk.Entry(search_frame, width=20, bg="#333", fg="white")
        self.search_val.insert(0, "192.168.1.50")
        self.search_val.pack(side=tk.LEFT, padx=5)

        tk.Button(search_frame, text="SEARCH ALL CASES", command=self.search_json, bg="#aa0000", fg="white").pack(
            side=tk.LEFT)

        # 3. Results Area
        ttk.Label(right_frame, text="QUERY RESULTS:").pack(anchor="w", pady=5)
        self.results_area = scrolledtext.ScrolledText(right_frame, height=10, bg="#222", fg="white")
        self.results_area.pack(fill="both", expand=True)

    def refresh_incidents(self):
        conn = self.connect()
        if not conn: return
        cur = conn.cursor()
        cur.execute("SELECT id, title, severity FROM incidents ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()

        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            tag = "critical" if row[2] == "CRITICAL" else "normal"
            self.tree.insert("", tk.END, values=row, tags=(tag,))

    def create_incident(self):
        title = self.title_entry.get()
        sev = self.severity_combo.get()
        if not title: return

        conn = self.connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO incidents (title, severity) VALUES (%s, %s)", (title, sev))
        conn.commit()
        conn.close()
        self.refresh_incidents()
        self.title_entry.delete(0, tk.END)

    def on_incident_select(self, event):
        # When user clicks an incident, show its raw logs
        selected = self.tree.selection()
        if not selected: return
        inc_id = self.tree.item(selected[0])['values'][0]

        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT description, log_data FROM evidence WHERE incident_id = %s", (inc_id,))
        rows = cur.fetchall()
        conn.close()

        self.results_area.delete("1.0", tk.END)
        self.results_area.insert(tk.END, f"--- EVIDENCE FOR CASE #{inc_id} ---\n")
        for desc, log in rows:
            # Pretty print the JSON
            pretty_json = json.dumps(log, indent=2)
            self.results_area.insert(tk.END, f"[{desc}]\n{pretty_json}\n\n")

    def add_evidence(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Error", "Select an Active Incident first.")
            return
        inc_id = self.tree.item(selected[0])['values'][0]

        desc = self.log_desc.get()
        raw_text = self.json_input.get("1.0", tk.END).strip()

        # VALIDATE JSON BEFORE SENDING
        try:
            json_obj = json.loads(raw_text)  # Checks if valid JSON
        except json.JSONDecodeError:
            messagebox.showerror("Invalid Format", "The text provided is not valid JSON.")
            return

        conn = self.connect()
        cur = conn.cursor()
        # Insert the JSON object directly. Psycopg2 handles the conversion to JSONB
        cur.execute("INSERT INTO evidence (incident_id, description, log_data) VALUES (%s, %s, %s)",
                    (inc_id, desc, json.dumps(json_obj)))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Evidence Log attached.")
        self.json_input.delete("1.0", tk.END)
        self.on_incident_select(None)  # Refresh view

    def search_json(self):
        # THIS IS THE POWERFUL PART: QUERYING INSIDE JSONB
        key = self.search_key.get()
        val = self.search_val.get()

        conn = self.connect()
        cur = conn.cursor()

        # The SQL Operator ->> extracts a JSON field as text
        query = """
                SELECT i.id, i.title, e.description, e.log_data
                FROM evidence e
                         JOIN incidents i ON e.incident_id = i.id
                WHERE e.log_data ->> %s = %s \
                """

        cur.execute(query, (key, val))
        rows = cur.fetchall()
        conn.close()

        self.results_area.delete("1.0", tk.END)
        self.results_area.insert(tk.END, f"--- SEARCH RESULTS for '{key}': '{val}' ---\n")

        if not rows:
            self.results_area.insert(tk.END, "No matches found in any case file.")

        for inc_id, title, desc, log in rows:
            self.results_area.insert(tk.END, f"CASE #{inc_id}: {title}\n")
            self.results_area.insert(tk.END, f"LOG SOURCE: {desc}\n")
            self.results_area.insert(tk.END, f"DATA: {json.dumps(log)}\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = IncidentApp(root)
    root.mainloop()
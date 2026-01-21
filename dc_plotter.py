import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from collections import deque

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'damage_control_db',
    'port': 5432
}

# Visual Config
ROOM_W = 120
ROOM_H = 80
COLOR_NORMAL = "#004400"  # Green
COLOR_FIRE = "#cc0000"  # Red
COLOR_FLOOD = "#0000cc"  # Blue
COLOR_PATH = "#ffff00"  # Yellow line


class DCPlotterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DAMAGE CONTROL CENTRAL PLOTTER")
        self.root.geometry("800x700")
        self.root.configure(bg="#111")

        self.team_start_node = 101  # Default Team Location (Bridge)
        self.compartments = {}  # Cache: {id: {data}}
        self.active_incidents = {}  # Cache: {id: type}

        self.init_db()
        self.setup_ui()
        self.refresh_plot()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing DB init."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS compartments
                        (
                            id
                            INT
                            PRIMARY
                            KEY,
                            name
                            VARCHAR
                        (
                            50
                        ),
                            x_coord INT, y_coord INT,
                            neighbor_ids INT []
                            );
                        """)
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS incidents
                        (
                            room_id
                            INT
                            PRIMARY
                            KEY
                            REFERENCES
                            compartments
                        (
                            id
                        ),
                            type VARCHAR
                        (
                            20
                        ),
                            severity INT DEFAULT 1
                            );
                        """)

            # Check Seed
            cur.execute("SELECT COUNT(*) FROM compartments")
            if cur.fetchone()[0] == 0:
                print("Seeding Ship Layout...")
                seed_sql = """
                           INSERT INTO compartments (id, name, x_coord, y_coord, neighbor_ids) \
                           VALUES (101, 'Bridge', 100, 100, ARRAY[102]), \
                                  (102, 'Main Hallway', 300, 100, ARRAY[101, 103, 201]), \
                                  (103, 'Mess Hall', 500, 100, ARRAY[102]), \
                                  (201, 'Engine Room', 300, 300, ARRAY[102, 202, 301]), \
                                  (202, 'Fuel Storage', 500, 300, ARRAY[201]), \
                                  (301, 'Ammo Magazine', 300, 500, ARRAY[201]); \
                           """
                cur.execute(seed_sql)
            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#222", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="GENERAL QUARTERS - DC STATUS", font=("Impact", 20), bg="#222", fg="#ffcc00").pack()

        # Canvas
        self.canvas = tk.Canvas(self.root, bg="#001100", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=10)

        # Controls
        controls = tk.Frame(self.root, bg="#111", pady=10)
        controls.pack(fill="x", padx=20)

        tk.Label(controls, text="Click Room to Toggle FIRE. Right-Click to set TEAM START.", bg="#111", fg="#aaa").pack(
            side="left")
        tk.Button(controls, text="DEPLOY REPAIR TEAM (Find Path)", command=self.calculate_path,
                  bg="#0055ff", fg="white", font=("Arial", 10, "bold")).pack(side="right")

        self.status_lbl = tk.Label(self.root, text="System Ready", bg="#111", fg="white", font=("Courier", 12))
        self.status_lbl.pack(pady=5)

    def refresh_plot(self):
        self.canvas.delete("all")
        conn = self.connect()
        if not conn: return

        try:
            cur = conn.cursor()

            # 1. Fetch Compartments
            cur.execute("SELECT id, name, x_coord, y_coord, neighbor_ids FROM compartments")
            rows = cur.fetchall()
            self.compartments = {r[0]: {'name': r[1], 'pos': (r[2], r[3]), 'neighbors': r[4]} for r in rows}

            # 2. Fetch Incidents
            cur.execute("SELECT room_id, type FROM incidents")
            self.active_incidents = {r[0]: r[1] for r in cur.fetchall()}

            # 3. Draw Connections (Lines) first so they appear behind rooms
            for cid, data in self.compartments.items():
                x1, y1 = data['pos']
                cx1, cy1 = x1 + ROOM_W // 2, y1 + ROOM_H // 2

                if data['neighbors']:
                    for nid in data['neighbors']:
                        if nid in self.compartments:
                            x2, y2 = self.compartments[nid]['pos']
                            cx2, cy2 = x2 + ROOM_W // 2, y2 + ROOM_H // 2
                            self.canvas.create_line(cx1, cy1, cx2, cy2, fill="#004400", width=3)

            # 4. Draw Rooms
            for cid, data in self.compartments.items():
                x, y = data['pos']
                name = data['name']

                # Determine Color
                fill_col = COLOR_NORMAL
                if cid in self.active_incidents:
                    fill_col = COLOR_FIRE if self.active_incidents[cid] == 'FIRE' else COLOR_FLOOD

                # Highlight Team Start
                outline_col = "white"
                width = 2
                if cid == self.team_start_node:
                    outline_col = "#0055ff"  # Bright Blue
                    width = 4

                # Draw Box
                tag_id = f"room_{cid}"
                self.canvas.create_rectangle(x, y, x + ROOM_W, y + ROOM_H,
                                             fill=fill_col, outline=outline_col, width=width, tags=tag_id)

                # Text
                self.canvas.create_text(x + ROOM_W // 2, y + ROOM_H // 2, text=f"{name}\n({cid})",
                                        fill="white", font=("Arial", 9, "bold"), tags=tag_id)

                # Bindings
                self.canvas.tag_bind(tag_id, "<Button-1>", lambda e, r=cid: self.toggle_incident(r))
                self.canvas.tag_bind(tag_id, "<Button-3>", lambda e, r=cid: self.set_team_start(r))

        finally:
            conn.close()

    def toggle_incident(self, room_id):
        conn = self.connect()
        try:
            cur = conn.cursor()
            if room_id in self.active_incidents:
                # Extinguish
                cur.execute("DELETE FROM incidents WHERE room_id = %s", (room_id,))
                self.status_lbl.config(text=f"Room {room_id} Secured.", fg="#00ff00")
            else:
                # Set Fire
                cur.execute("INSERT INTO incidents (room_id, type) VALUES (%s, 'FIRE')", (room_id,))
                self.check_risk_propagation(room_id)

            conn.commit()
            self.refresh_plot()
        finally:
            conn.close()

    def set_team_start(self, room_id):
        self.team_start_node = room_id
        self.refresh_plot()
        self.status_lbl.config(text=f"Repair Team stationed at {self.compartments[room_id]['name']}", fg="#00ccff")

    def check_risk_propagation(self, room_id):
        """Logic: If Fire is near Ammo/Fuel, Warn User."""
        room_data = self.compartments[room_id]
        neighbors = room_data['neighbors']

        warnings = []
        for nid in neighbors:
            n_name = self.compartments[nid]['name']
            if "Magazine" in n_name or "Fuel" in n_name:
                warnings.append(f"CRITICAL: Fire in {room_data['name']} threatens {n_name}!")

        if warnings:
            alert_text = "\n".join(warnings)
            self.status_lbl.config(text=alert_text, fg="#ff0000")
            messagebox.showwarning("SYMPATHETIC DETONATION RISK", alert_text)
        else:
            self.status_lbl.config(text=f"Fire reported in {room_data['name']}", fg="orange")

    def calculate_path(self):
        """BFS Pathfinding to nearest Incident, avoiding other Incidents."""
        start = self.team_start_node
        goals = list(self.active_incidents.keys())

        if not goals:
            self.status_lbl.config(text="Ship Secure. No active incidents.", fg="#00ff00")
            return

        # Queue: (current_node, path_history)
        queue = deque([(start, [start])])
        visited = set([start])

        found_path = None

        while queue:
            current, path = queue.popleft()

            if current in goals:
                found_path = path
                break

            # Check neighbors
            neighbors = self.compartments[current]['neighbors']
            if neighbors:
                for n in neighbors:
                    if n not in visited:
                        # LOGIC: Avoid rooms that are ON FIRE (unless it's the destination)
                        if n in self.active_incidents and n not in goals:
                            continue  # Blocked route

                        visited.add(n)
                        queue.append((n, path + [n]))

        if found_path:
            self.draw_path(found_path)
            target_name = self.compartments[found_path[-1]]['name']
            self.status_lbl.config(text=f"Route plotted to {target_name}. Path: {found_path}", fg="yellow")
        else:
            self.status_lbl.config(text="NO SAFE ROUTE AVAILABLE! ALL PATHS BLOCKED.", fg="red")
            messagebox.showerror("ROUTING FAILURE", "Team is cut off. No safe path to casualty.")

    def draw_path(self, path):
        """Visualizes the yellow route line."""
        self.refresh_plot()  # Clear old lines

        if len(path) < 2: return

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            x1, y1 = self.compartments[u]['pos']
            x2, y2 = self.compartments[v]['pos']

            cx1, cy1 = x1 + ROOM_W // 2, y1 + ROOM_H // 2
            cx2, cy2 = x2 + ROOM_W // 2, y2 + ROOM_H // 2

            # Draw thick yellow line on top
            self.canvas.create_line(cx1, cy1, cx2, cy2, fill=COLOR_PATH, width=5, arrow=tk.LAST)


if __name__ == "__main__":
    root = tk.Tk()
    app = DCPlotterApp(root)
    root.mainloop()
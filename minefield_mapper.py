import tkinter as tk
from tkinter import messagebox
import psycopg2
import math
import heapq

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'navmine_db',
    'port': 5432
}

# Simulation Scale
GRID_SIZE = 60  # 60x60 calculation grid
CANVAS_SIZE = 600  # 600x600 pixels
SCALE = CANVAS_SIZE / GRID_SIZE  # Pixels per grid unit
SAFE_DISTANCE = 6  # "500 yards" relative to grid size


class MineMapperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MCM TACTICAL PLOTTER // ROUTE CLEARING")
        self.root.geometry("900x700")
        self.root.configure(bg="#001133")

        self.start_point = None
        self.end_point = None
        self.mines = []

        self.init_db()
        self.setup_ui()
        self.load_mines()

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
                        CREATE TABLE IF NOT EXISTS mines
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            latitude
                            FLOAT,
                            longitude
                            FLOAT,
                            mine_type
                            VARCHAR
                        (
                            50
                        ),
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'ACTIVE'
                            );
                        """)
            # Check Seed
            cur.execute("SELECT COUNT(*) FROM mines")
            if cur.fetchone()[0] == 0:
                seed_data = [
                    (50.0, 40.0, 'ACTIVE'), (52.0, 42.0, 'ACTIVE'),
                    (48.0, 45.0, 'ACTIVE'), (55.0, 50.0, 'ACTIVE'),
                    (45.0, 55.0, 'ACTIVE'), (30.0, 70.0, 'NEUTRALIZED')
                ]
                for lat, lon, stat in seed_data:
                    cur.execute("INSERT INTO mines (latitude, longitude, status) VALUES (%s, %s, %s)", (lat, lon, stat))
            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#002244", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="🌊 MINE COUNTERMEASURES MAP",
                 font=("Courier", 20, "bold"), bg="#002244", fg="#00ccff").pack()

        # Controls
        controls = tk.Frame(self.root, bg="#001133")
        controls.pack(fill="x", pady=10)

        self.lbl_status = tk.Label(controls, text="Click Map to set START point",
                                   font=("Arial", 12), bg="#001133", fg="yellow")
        self.lbl_status.pack()

        # Canvas (The Map)
        # Using a Frame to center the canvas
        canvas_frame = tk.Frame(self.root, bg="#001133")
        canvas_frame.pack()

        self.canvas = tk.Canvas(canvas_frame, width=CANVAS_SIZE, height=CANVAS_SIZE,
                                bg="#000033", highlightthickness=2, highlightbackground="#004488")
        self.canvas.pack()

        # Grid lines
        for i in range(0, CANVAS_SIZE, int(CANVAS_SIZE / 10)):
            self.canvas.create_line(i, 0, i, CANVAS_SIZE, fill="#002266")
            self.canvas.create_line(0, i, CANVAS_SIZE, i, fill="#002266")

        self.canvas.bind("<Button-1>", self.on_map_click)

        # Legend
        legend = tk.Frame(self.root, bg="#001133")
        legend.pack(pady=10)
        tk.Label(legend, text="🔴 Active Mine", bg="#001133", fg="red").pack(side="left", padx=10)
        tk.Label(legend, text="⭕ Danger Zone", bg="#001133", fg="#ff6666").pack(side="left", padx=10)
        tk.Label(legend, text="🟢 Neutralized", bg="#001133", fg="green").pack(side="left", padx=10)
        tk.Label(legend, text="🟨 Safe Route", bg="#001133", fg="yellow").pack(side="left", padx=10)

    def load_mines(self):
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT longitude, latitude, status, mine_type FROM mines")
            rows = cur.fetchall()

            self.mines = []  # Store logical coordinates

            for lon, lat, status, mtype in rows:
                # Logic: Convert DB Coordinates (0-100) to Canvas Pixels
                cx = (lon / 100) * CANVAS_SIZE
                cy = (lat / 100) * CANVAS_SIZE  # Invert Y if using real mapping, but keeping simple here

                # Visuals
                if status == 'ACTIVE':
                    # Draw Danger Zone (Radius)
                    radius_px = SAFE_DISTANCE * SCALE
                    self.canvas.create_oval(cx - radius_px, cy - radius_px, cx + radius_px, cy + radius_px,
                                            outline="#ff4444", fill="#330000", width=1)
                    # Draw Mine
                    self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="red")

                    # Store logical position for Pathfinding (Grid Coordinates)
                    gx = int(lon / 100 * GRID_SIZE)
                    gy = int(lat / 100 * GRID_SIZE)
                    self.mines.append((gx, gy))

                else:
                    # Neutralized
                    self.canvas.create_text(cx, cy, text="X", fill="green", font=("Arial", 10, "bold"))

        finally:
            conn.close()

    def on_map_click(self, event):
        # Convert Pixel -> Grid
        gx = int(event.x / SCALE)
        gy = int(event.y / SCALE)

        if not self.start_point:
            self.start_point = (gx, gy)
            self.draw_marker(event.x, event.y, "START", "#00ff00")
            self.lbl_status.config(text="Click Map to set END point")
        elif not self.end_point:
            self.end_point = (gx, gy)
            self.draw_marker(event.x, event.y, "END", "#00ff00")
            self.lbl_status.config(text="Calculating Safe Lane...", fg="white")
            self.calculate_route()
        else:
            # Reset
            self.start_point = (gx, gy)
            self.end_point = None
            self.canvas.delete("route")
            self.canvas.delete("marker")
            self.draw_marker(event.x, event.y, "START", "#00ff00")
            self.lbl_status.config(text="Click Map to set END point", fg="yellow")

    def draw_marker(self, x, y, text, color):
        self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, tags="marker")
        self.canvas.create_text(x, y - 15, text=text, fill=color, font=("Arial", 8, "bold"), tags="marker")

    def calculate_route(self):
        # A* Pathfinding

        # 1. Create Collision Grid
        grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        for mx, my in self.mines:
            # Mark danger zones on grid
            # Naive radius check on grid cells
            r = int(SAFE_DISTANCE)
            for x in range(mx - r, mx + r + 1):
                for y in range(my - r, my + r + 1):
                    if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
                        # Euclidean Distance Check
                        if math.sqrt((x - mx) ** 2 + (y - my) ** 2) <= r:
                            grid[x][y] = 1  # Blocked

        # 2. Check if Start/End are blocked
        sx, sy = self.start_point
        ex, ey = self.end_point

        if grid[sx][sy] == 1 or grid[ex][ey] == 1:
            messagebox.showerror("Plot Error", "Start or End point is inside a Danger Zone!")
            self.lbl_status.config(text="Route Failed: Zones Blocked", fg="red")
            return

        # 3. A* Algorithm
        # Priority Queue: (Cost, x, y, path_list)
        queue = [(0, sx, sy, [])]
        visited = set()

        final_path = None

        while queue:
            cost, cx, cy, path = heapq.heappop(queue)

            if (cx, cy) == (ex, ey):
                final_path = path + [(cx, cy)]
                break

            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            # Neighbors (8 directions)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue

                    nx, ny = cx + dx, cy + dy

                    if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                        if grid[nx][ny] == 0:  # Not blocked
                            # Heuristic (Euclidean to end)
                            h = math.sqrt((nx - ex) ** 2 + (ny - ey) ** 2)
                            # Movement cost (1 for straight, 1.4 for diagonal)
                            g = 1 if (dx == 0 or dy == 0) else 1.414

                            new_cost = cost + g + h
                            heapq.heappush(queue, (new_cost, nx, ny, path + [(cx, cy)]))

        if final_path:
            self.draw_route(final_path)
            self.lbl_status.config(text="SAFE LANE ESTABLISHED", fg="#00ff00")
        else:
            self.lbl_status.config(text="NO SAFE ROUTE FOUND", fg="red")
            messagebox.showwarning("Navigation Warning", "Minefield density too high. No safe path found.")

    def draw_route(self, path):
        # Convert Grid -> Pixels
        pixel_path = []
        for gx, gy in path:
            px = gx * SCALE + (SCALE / 2)  # Center of grid cell
            py = gy * SCALE + (SCALE / 2)
            pixel_path.append(px)
            pixel_path.append(py)

        self.canvas.create_line(pixel_path, fill="yellow", width=3, tags="route", arrow=tk.LAST)


if __name__ == "__main__":
    root = tk.Tk()
    app = MineMapperApp(root)
    root.mainloop()
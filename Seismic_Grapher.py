import tkinter as tk
from tkinter import messagebox


class SeismicGrapherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seismic Travel-Time Curve Grapher")
        self.root.geometry("950x550")
        self.root.configure(bg="#1e1e24")

        # --- Seismological Constants (Crustal Velocity Model) ---
        self.V_P = 6.0  # Average P-wave velocity (km/s)
        self.V_S = 3.5  # Average S-wave velocity (km/s)

        # --- Graph Data Window Boundaries ---
        self.MAX_DIST = 1000.0  # X-axis maximum (km)
        self.MAX_TIME = 200.0  # Y-axis maximum (seconds)
        self.PADDING = 60  # Pixel border spacing around graph axes

        self.setup_layout()
        self.root.update()  # Force dynamic geometry evaluation
        self.draw_graph_base()

    def setup_layout(self):
        """Creates a two-column layout: Inputs on the Left, Graph Canvas on the Right."""
        # --- Left Control Panel Container ---
        self.ctrl_panel = tk.Frame(self.root, bg="#2a2a35", width=300, bd=0)
        self.ctrl_panel.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)
        self.ctrl_panel.pack_propagate(False)

        # Title Header
        header = tk.Label(self.ctrl_panel, text="SEISMIC ANALYSIS", font=("Arial", 14, "bold"), bg="#2a2a35",
                          fg="#61afef")
        header.pack(pady=20)

        # P-wave Arrival Input
        lbl_p = tk.Label(self.ctrl_panel, text="P-Wave Arrival Time (sec):", font=("Arial", 10), bg="#2a2a35",
                         fg="#abb2bf")
        lbl_p.pack(anchor=tk.W, padx=20, pady=(10, 2))
        self.entry_p = tk.Entry(self.ctrl_panel, font=("Arial", 11), bg="#1e1e24", fg="white", insertbackground="white",
                                bd=1)
        self.entry_p.insert(0, "20.0")
        self.entry_p.pack(fill=tk.X, padx=20)

        # S-wave Arrival Input
        lbl_s = tk.Label(self.ctrl_panel, text="S-Wave Arrival Time (sec):", font=("Arial", 10), bg="#2a2a35",
                         fg="#abb2bf")
        lbl_s.pack(anchor=tk.W, padx=20, pady=(15, 2))
        self.entry_s = tk.Entry(self.ctrl_panel, font=("Arial", 11), bg="#1e1e24", fg="white", insertbackground="white",
                                bd=1)
        self.entry_s.insert(0, "92.0")
        self.entry_s.pack(fill=tk.X, padx=20)

        # Action Execution Button
        self.calc_btn = tk.Button(self.ctrl_panel, text="Calculate Distance", font=("Arial", 11, "bold"),
                                  bg="#98c379", fg="#1e1e24", activebackground="#a3d18a", bd=0, cursor="hand2",
                                  command=self.process_seismic_calculation)
        self.calc_btn.pack(fill=tk.X, padx=20, pady=30)

        # --- Separator Line ---
        sep = tk.Frame(self.ctrl_panel, bg="#3e4451", height=1)
        sep.pack(fill=tk.X, padx=20, pady=10)

        # Results Panel Layout
        self.res_title = tk.Label(self.ctrl_panel, text="EPICENTER DATA OUTPUT", font=("Arial", 10, "bold"),
                                  bg="#2a2a35", fg="#e5c07b")
        self.res_title.pack(pady=(10, 5))

        self.lbl_delta_t = tk.Label(self.ctrl_panel, text="Time Gap (S - P): --", font=("Courier", 11), bg="#2a2a35",
                                    fg="#abb2bf")
        self.lbl_delta_t.pack(anchor=tk.W, padx=20, pady=5)

        self.lbl_distance = tk.Label(self.ctrl_panel, text="Est. Distance: --", font=("Courier", 12, "bold"),
                                     bg="#2a2a35", fg="#e06c75")
        self.lbl_distance.pack(anchor=tk.W, padx=20, pady=5)

        # --- Right Visualization Canvas ---
        self.canvas = tk.Canvas(self.root, bg="#111115", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 15), pady=15)

        # Re-draw the workspace dynamically if the user resizes their screen window
        self.canvas.bind("<Configure>", lambda event: self.draw_graph_base())

    def to_canvas_coords(self, dist_km, time_sec):
        """Maps raw physical earth coordinates into local canvas drawing pixels."""
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()

        # Scale multipliers based on rendering window size
        scale_x = (c_width - (self.PADDING * 2)) / self.MAX_DIST
        scale_y = (c_height - (self.PADDING * 2)) / self.MAX_TIME

        pixel_x = self.PADDING + (dist_km * scale_x)
        # Invert Y coordinate space since canvas (0,0) starts at top-left
        pixel_y = (c_height - self.PADDING) - (time_sec * scale_y)

        return pixel_x, pixel_y

    def draw_graph_base(self):
        """Clears rendering canvas and builds out the mathematical coordinate grid overlay."""
        self.canvas.delete("all")
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()

        # 1. Main Axis Boundaries
        x_start, y_start = self.to_canvas_coords(0, 0)
        x_end, y_end = self.to_canvas_coords(self.MAX_DIST, self.MAX_TIME)

        self.canvas.create_line(x_start, y_start, x_end, y_start, fill="#3e4451", width=2)  # X Axis Line
        self.canvas.create_line(x_start, y_start, x_start, y_end, fill="#3e4451", width=2)  # Y Axis Line

        # 2. X-Axis Gridlines & Incremental Tick Values (Distance in KM)
        for dist in range(0, int(self.MAX_DIST) + 1, 100):
            px, py = self.to_canvas_coords(dist, 0)
            self.canvas.create_line(px, y_start, px, y_end, fill="#1e1e24", dash=(2, 4))  # Grid line
            self.canvas.create_line(px, y_start, px, y_start + 5, fill="#3e4451", width=1)  # Tick line
            self.canvas.create_text(px, y_start + 18, text=str(dist), fill="#5c6370", font=("Arial", 9))

        # 3. Y-Axis Gridlines & Incremental Tick Values (Time in Seconds)
        for t_sec in range(0, int(self.MAX_TIME) + 1, 20):
            px, py = self.to_canvas_coords(0, t_sec)
            self.canvas.create_line(x_start, py, x_end, py, fill="#1e1e24", dash=(2, 4))  # Grid line
            self.canvas.create_line(x_start, py, x_start - 5, py, fill="#3e4451", width=1)  # Tick line
            self.canvas.create_text(x_start - 22, py, text=str(t_sec), fill="#5c6370", font=("Arial", 9))

        # Axis Structural Descriptive Labels
        self.canvas.create_text(c_width / 2, y_start + 40, text="Distance from Epicenter (km)", fill="#abb2bf",
                                font=("Arial", 11, "bold"))
        self.canvas.create_text(20, c_height / 2, text="Travel Time (seconds)", fill="#abb2bf",
                                font=("Arial", 11, "bold"), angle=90)

        # 4. Plot Continuous Velocity Vectors (Lines representing P and S travel slopes)
        p_start_x, p_start_y = self.to_canvas_coords(0, 0)
        p_end_x, p_end_y = self.to_canvas_coords(self.MAX_DIST, self.MAX_DIST / self.V_P)
        self.canvas.create_line(p_start_x, p_start_y, p_end_x, p_end_y, fill="#61afef", width=3)
        self.canvas.create_text(p_end_x - 30, p_end_y - 12, text="P-Wave Curve", fill="#61afef",
                                font=("Arial", 9, "bold"))

        s_start_x, s_start_y = self.to_canvas_coords(0, 0)
        s_end_x, s_end_y = self.to_canvas_coords(self.MAX_DIST, self.MAX_DIST / self.V_S)
        self.canvas.create_line(s_start_x, s_start_y, s_end_x, s_end_y, fill="#e06c75", width=3)
        self.canvas.create_text(s_end_x - 35, s_end_y - 12, text="S-Wave Curve", fill="#e06c75",
                                font=("Arial", 9, "bold"))

    def process_seismic_calculation(self):
        """Validates user data inputs, calculates epicenter distance, and renders visual overlay."""
        try:
            t_p = float(self.entry_p.get())
            t_s = float(self.entry_s.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please parse numerical value increments inside time windows.")
            return

        if t_p <= 0 or t_s <= 0:
            messagebox.showerror("Physical Anomaly", "Arrival indices must register as positive scalars.")
            return

        if t_s <= t_p:
            messagebox.showerror("Seismological Anomaly",
                                 "S-waves travel slower than P-waves.\nS-arrival time must exceed P-arrival time.")
            return

        delta_t = t_s - t_p

        # --- The Distance Formula ---
        # Derived from: delta_t = (Dist / V_S) - (Dist / V_P)
        # Dist = delta_t / ((1 / V_S) - (1 / V_P))
        denominator = (1.0 / self.V_S) - (1.0 / self.V_P)
        calculated_distance = delta_t / denominator

        # Edge handling constraint check against graph viewport limits
        if calculated_distance > self.MAX_DIST or t_s > self.MAX_TIME:
            messagebox.showwarning("Out of Bounding Range",
                                   "Calculated distance scales beyond the current visual graph limits (1000km).")

        # Update Sidebar Output Text Blocks
        self.lbl_delta_t.config(text=f"Time Gap (S - P): {delta_t:.1f} s")
        self.lbl_distance.config(text=f"Est. Distance: {calculated_distance:.1f} km")

        # Refresh background layout canvas frame to wipe out historical target points
        self.draw_graph_base()
        self.render_calculation_overlay(calculated_distance, t_p, t_s)

    def render_calculation_overlay(self, distance, tp, ts):
        """Draws analytical bounding intersection paths tracking exactly how the result was derived."""
        # Convert physical math dimensions to specific monitor coordinates
        cx_dist, cy_zero = self.to_canvas_coords(distance, 0)
        _, cy_p = self.to_canvas_coords(distance, tp)
        _, cy_s = self.to_canvas_coords(distance, ts)
        cx_zero, _ = self.to_canvas_coords(0, tp)
        _, cy_target_s = self.to_canvas_coords(0, ts)

        # Draw horizontal and vertical projection alignment paths (Dotted Target Reticle)
        # Vertical alignment line to ground scale
        self.canvas.create_line(cx_dist, cy_s, cx_dist, cy_zero, fill="#98c379", width=2, dash=(3, 3))

        # Horizontal alignments tracing back to time axes indexes
        self.canvas.create_line(cx_dist, cy_p, cx_zero, cy_p, fill="#61afef", width=1, dash=(5, 5))
        self.canvas.create_line(cx_dist, cy_s, cx_zero, cy_target_s, fill="#e06c75", width=1, dash=(5, 5))

        # Highlight intersection interception nodes on actual line profiles
        self.canvas.create_oval(cx_dist - 5, cy_p - 5, cx_dist + 5, cy_p + 5, fill="#61afef", outline="white")
        self.canvas.create_oval(cx_dist - 5, cy_s - 5, cx_dist + 5, cy_s + 5, fill="#e06c75", outline="white")

        # Draw a bracket showing the time gap delta interval
        mid_y = (cy_p + cy_s) / 2
        self.canvas.create_line(cx_dist + 15, cy_p, cx_dist + 15, cy_s, fill="#e5c07b", width=2)
        self.canvas.create_line(cx_dist + 10, cy_p, cx_dist + 20, cy_p, fill="#e5c07b", width=2)
        self.canvas.create_line(cx_dist + 10, cy_s, cx_dist + 20, cy_s, fill="#e5c07b", width=2)
        self.canvas.create_text(cx_dist + 35, mid_y, text="Δt", fill="#e5c07b", font=("Arial", 10, "bold"))

        # Pinpoint intersection result label on distance axis line
        self.canvas.create_polygon(cx_dist, cy_zero, cx_dist - 8, cy_zero + 12, cx_dist + 8, cy_zero + 12,
                                   fill="#98c379")
        self.canvas.create_text(cx_dist, cy_zero + 25, text=f"{distance:.0f} km", fill="#98c379",
                                font=("Arial", 9, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    app = SeismicGrapherApp(root)
    root.mainloop()
import tkinter as tk
import math


class TsunamiSimulationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tsunami Cellular Automata Simulator")
        self.root.geometry("1000x600")
        self.root.configure(bg="#1e1e24")

        # --- Simulation Grid Settings ---
        self.COLS = 60
        self.ROWS = 30
        self.CELL_SIZE = 15

        # Grid state matrices
        self.depth = [[0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.u = [[0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)]  # Current wave height
        self.u_old = [[0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)]  # Previous wave height
        self.u_new = [[0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)]  # Next step wave height

        self.rect_ids = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]

        self.is_running = False

        self.setup_ui()
        self.initialize_bathymetry()
        self.build_grid()

    def setup_ui(self):
        # --- Control Panel ---
        ctrl_panel = tk.Frame(self.root, bg="#2a2a35", height=80)
        ctrl_panel.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        title = tk.Label(ctrl_panel, text="TSUNAMI PROPAGATION ENGINE", font=("Arial", 14, "bold"), fg="#61afef",
                         bg="#2a2a35")
        title.pack(side=tk.LEFT, padx=20)

        # FIXED: Changed px=10 to padx=10
        self.btn_trigger = tk.Button(ctrl_panel, text="⚠️ Trigger Megathrust Fault", font=("Arial", 11, "bold"),
                                     bg="#e06c75", fg="white", activebackground="#ff7b86", bd=0, padx=10,
                                     cursor="hand2",
                                     command=self.trigger_earthquake)
        self.btn_trigger.pack(side=tk.RIGHT, padx=10, pady=15)

        # FIXED: Changed px=10 to padx=10
        self.btn_reset = tk.Button(ctrl_panel, text="Reset Ocean", font=("Arial", 11, "bold"),
                                   bg="#abb2bf", fg="#1e1e24", bd=0, padx=10, cursor="hand2",
                                   command=self.reset_simulation)
        self.btn_reset.pack(side=tk.RIGHT, padx=10, pady=15)

        # --- Main Viewport Canvas ---
        canvas_frame = tk.Frame(self.root, bg="#111115")
        canvas_frame.pack(side=tk.TOP, pady=10)

        self.canvas = tk.Canvas(canvas_frame, width=self.COLS * self.CELL_SIZE, height=self.ROWS * self.CELL_SIZE,
                                bg="#111115", highlightthickness=0)
        self.canvas.pack()

        # Legend Panel
        legend = tk.Label(self.root,
                          text="Left: Deep Ocean (Fast, Low Height)  -->  Right: Coastline (Slow, High Amplitude)",
                          font=("Arial", 10, "italic"), fg="#abb2bf", bg="#1e1e24")
        legend.pack(pady=5)

    def initialize_bathymetry(self):
        """Sets up the ocean floor depth profile from left (deep) to right (shallow/land)."""
        for y in range(self.ROWS):
            for x in range(self.COLS):
                if x < 25:
                    # Deep Ocean Trench
                    self.depth[y][x] = 4000.0
                elif x < 45:
                    # Continental Slope (gradual shallowing)
                    ratio = (x - 25) / 20.0
                    self.depth[y][x] = 4000.0 - (ratio * 3800.0)
                elif x < 56:
                    # Continental Shelf
                    self.depth[y][x] = 200.0
                else:
                    # Beach / Land Boundary
                    self.depth[y][x] = 0.0

    def build_grid(self):
        """Draws the initial cellular grid onto the Tkinter canvas."""
        self.canvas.delete("all")
        for y in range(self.ROWS):
            for x in range(self.COLS):
                x1 = x * self.CELL_SIZE
                y1 = y * self.CELL_SIZE
                x2 = x1 + self.CELL_SIZE
                y2 = y1 + self.CELL_SIZE

                base_color = self.get_color(x, y, 0.0)
                rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill=base_color, outline="#1e1e24")
                self.rect_ids[y][x] = rect_id

    def rgb_to_hex(self, r, g, b):
        """Clamps values and converts RGB tuples to Tkinter hex strings."""
        r, g, b = max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_color(self, x, y, wave_height):
        """Calculates cell color based on depth and current wave energy."""
        d = self.depth[y][x]

        # Draw Land
        if d == 0:
            return "#8f7a66"  # Sand/Dirt color

        # Calculate base water color depending on depth
        depth_ratio = d / 4000.0
        base_r = int(10 + (30 * (1 - depth_ratio)))
        base_g = int(30 + (80 * (1 - depth_ratio)))
        base_b = int(80 + (100 * depth_ratio))

        # Add wave energy highlights (Shoaling effect visualization)
        # Green's Law: Amplitude increases as depth decreases (A ~ d^(-1/4))
        shoal_multiplier = (4000.0 / max(10.0, d)) ** 0.25
        visual_amplitude = wave_height * shoal_multiplier

        if visual_amplitude > 0.1:
            # Wave Crest (Bright Cyan/White)
            intensity = min(255, int(visual_amplitude * 80))
            return self.rgb_to_hex(base_r + intensity, base_g + intensity, base_b + intensity)
        elif visual_amplitude < -0.1:
            # Wave Trough (Deep Dark Blue)
            intensity = min(base_b, int(abs(visual_amplitude) * 60))
            return self.rgb_to_hex(max(0, base_r - intensity), max(0, base_g - intensity), max(0, base_b - intensity))

        return self.rgb_to_hex(base_r, base_g, base_b)

    def trigger_earthquake(self):
        """Injects massive wave displacement energy at the fault line (deep ocean)."""
        # Inject an ellipse-shaped uplift into the left side of the grid
        center_y = self.ROWS // 2
        for y in range(self.ROWS):
            for x in range(5, 10):
                distance_from_center = abs(y - center_y)
                if distance_from_center < 8:
                    # Uplift calculation
                    uplift = math.cos((distance_from_center / 8.0) * (math.pi / 2)) * 3.0
                    self.u[y][x] = uplift
                    self.u_old[y][x] = uplift

        if not self.is_running:
            self.is_running = True
            self.physics_loop()

    def reset_simulation(self):
        """Clears all wave energy and stops the loop."""
        self.is_running = False
        for y in range(self.ROWS):
            for x in range(self.COLS):
                self.u[y][x] = 0.0
                self.u_old[y][x] = 0.0
                self.u_new[y][x] = 0.0

                # Reset visual canvas color
                color = self.get_color(x, y, 0.0)
                self.canvas.itemconfig(self.rect_ids[y][x], fill=color)

    def physics_loop(self):
        """The core Cellular Automata wave equation solver."""
        if not self.is_running:
            return

        # 1. Calculate next state for all water cells using Finite Difference Wave Equation
        for y in range(1, self.ROWS - 1):
            for x in range(1, self.COLS - 1):
                # Skip land processing
                if self.depth[y][x] == 0:
                    continue

                # Local wave speed squared (proportional to depth: v^2 = g*d)
                # Scaled for simulation stability (Courant-Friedrichs-Lewy condition)
                c_squared_dt_dx = (self.depth[y][x] / 4000.0) * 0.4

                # Laplacian (Sum of neighbors - 4 * center)
                laplacian = (self.u[y][x + 1] + self.u[y][x - 1] + self.u[y + 1][x] + self.u[y - 1][x] - 4 * self.u[y][
                    x])

                # Core Wave Equation
                self.u_new[y][x] = (2 * self.u[y][x]) - self.u_old[y][x] + (c_squared_dt_dx * laplacian)

                # Apply slight friction/damping to prevent infinite echoes
                self.u_new[y][x] *= 0.995

        # 2. Advance time state and update GUI
        for y in range(1, self.ROWS - 1):
            for x in range(1, self.COLS - 1):
                self.u_old[y][x] = self.u[y][x]
                self.u[y][x] = self.u_new[y][x]

                # Update visual colors only if there is notable wave energy to save CPU cycles
                if abs(self.u[y][x]) > 0.05 or abs(self.u_old[y][x]) > 0.05:
                    color = self.get_color(x, y, self.u[y][x])
                    self.canvas.itemconfig(self.rect_ids[y][x], fill=color)

        # 3. Schedule next frame (~30 FPS)
        self.root.after(30, self.physics_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = TsunamiSimulationApp(root)
    root.mainloop()
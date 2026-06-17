import tkinter as tk
from tkinter import ttk
import math


class ShakeMapSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seismic ShakeMap & Soil Amplification Simulator")
        self.root.geometry("1050x650")
        self.root.configure(bg="#1e1e24")

        # --- Grid Resolution ---
        self.GRID_SIZE = 10  # Size of each cell block in pixels
        self.COLS = 55
        self.ROWS = 55
        self.MAP_WIDTH = self.COLS * self.GRID_SIZE
        self.MAP_HEIGHT = self.ROWS * self.GRID_SIZE

        # --- Simulation State ---
        self.epicenter_x = None
        self.epicenter_y = None
        self.grid_rects = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]

        self.setup_ui()
        self.build_base_map()

    def setup_ui(self):
        """Builds out the control console dashboard and mapping canvas layout."""
        # --- Left Control Panel ---
        ctrl_panel = tk.Frame(self.root, bg="#2a2a35", width=380)
        ctrl_panel.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)
        ctrl_panel.pack_propagate(False)

        title = tk.Label(ctrl_panel, text="SHAKEMAP SIMULATOR", font=("Arial", 14, "bold"), fg="#61afef", bg="#2a2a35")
        title.pack(pady=(20, 5))

        subtitle = tk.Label(ctrl_panel, text="Site Effects & Wave Attenuation Engine", font=("Arial", 9, "italic"),
                            fg="#abb2bf", bg="#2a2a35")
        subtitle.pack(pady=(0, 20))

        # --- Interactive Parameter Adjusters ---
        sliders_frame = tk.LabelFrame(ctrl_panel, text=" Earthquake Source Parameters ", font=("Arial", 10, "bold"),
                                      bg="#2a2a35", fg="#e5c07b", bd=1, padx=15, pady=10)
        sliders_frame.pack(fill=tk.X, padx=15, pady=10)

        # Magnitude (Richter) Slider
        tk.Label(sliders_frame, text="Moment Magnitude (Mw):", font=("Arial", 9), bg="#2a2a35", fg="white").pack(
            anchor=tk.W)
        self.slider_mag = tk.Scale(sliders_frame, from_=4.0, to=8.5, resolution=0.1, orient=tk.HORIZONTAL,
                                   bg="#2a2a35", fg="#abb2bf", highlightthickness=0, command=self.trigger_recalculation)
        self.slider_mag.set(6.5)
        self.slider_mag.pack(fill=tk.X, pady=(0, 15))

        # Depth Slider (Hypocentral Depth)
        tk.Label(sliders_frame, text="Focal Depth (Hypocenter):", font=("Arial", 9), bg="#2a2a35", fg="white").pack(
            anchor=tk.W)
        self.slider_depth = tk.Scale(sliders_frame, from_=5, to=50, resolution=1, orient=tk.HORIZONTAL,
                                     bg="#2a2a35", fg="#abb2bf", highlightthickness=0,
                                     command=self.trigger_recalculation)
        self.slider_depth.set(12)
        self.slider_depth.pack(fill=tk.X)

        # --- Modified Mercalli Intensity Legend Panel ---
        legend_frame = tk.LabelFrame(ctrl_panel, text=" Modified Mercalli Scale (MMI) ", font=("Arial", 10, "bold"),
                                     bg="#2a2a35", fg="#e5c07b", bd=1, padx=10, pady=10)
        legend_frame.pack(fill=tk.X, padx=15, pady=15)

        mmi_scales = [
            ("VIII+ . Severe / Destructive", "#e06c75"),
            ("VII ... Very Strong Shaking", "#d19a66"),
            ("VI .... Strong Shaking", "#e5c07b"),
            ("V ..... Moderate Shaking", "#98c379"),
            ("III-IV . Light / Weak Shaking", "#61afef"),
            ("I-II .. Not Felt / Background", "#282c34")
        ]

        for text, color in mmi_scales:
            row = tk.Frame(legend_frame, bg="#2a2a35", pady=2)
            row.pack(fill=tk.X)
            box = tk.Frame(row, width=20, height=14, bg=color, bd=1, relief=tk.SOLID)
            box.pack(side=tk.LEFT, padx=(5, 10))
            box.pack_propagate(False)
            tk.Label(row, text=text, font=("Courier", 9, "bold"), fg="#abb2bf", bg="#2a2a35").pack(side=tk.LEFT)

        # Help Info
        info_lbl = tk.Label(ctrl_panel,
                            text="👉 Click anywhere on the map to place the\n seismic epicenter and generate the ShakeMap.",
                            font=("Arial", 9, "italic"), fg="#5c6370", bg="#2a2a35", justify=tk.LEFT)
        info_lbl.pack(side=tk.BOTTOM, pady=20)

        # --- Right Visualization Viewport ---
        view_frame = tk.Frame(self.root, bg="#111115")
        view_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 15), pady=15)

        # Canvas Mapping Grid
        self.canvas = tk.Canvas(view_frame, width=self.MAP_WIDTH, height=self.MAP_HEIGHT, bg="#111115",
                                highlightthickness=0)
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.on_map_click)

        # Explicit Visual Geology Boundary Text Lines overlaying canvas boundaries
        geology_lbl = tk.Label(view_frame,
                               text="▲ NORTH ZONE: Solid Granite Bedrock (Low Wave Amplitude) ▲\n▼ SOUTH ZONE: Soft River Silt/Alluvium (High Wave Amplification) ▼",
                               font=("Arial", 9, "bold"), fg="#5c6370", bg="#111115")
        geology_lbl.pack()

    def build_base_map(self):
        """Populates the canvas layout window with structured geometric cell grid blocks."""
        self.canvas.delete("all")
        for y in range(self.ROWS):
            for x in range(self.COLS):
                x1 = x * self.GRID_SIZE
                y1 = y * self.GRID_SIZE
                x2 = x1 + self.GRID_SIZE
                y2 = y1 + self.GRID_SIZE

                # Establish underlying geology blueprint colors
                # Top Half: Bedrock (Dark Grey). Bottom Half: Soft Soil (Dull Olive Mud)
                bg_color = "#21252b" if y < (self.ROWS // 2) else "#282c30"

                rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="")
                self.grid_rects[y][x] = rect_id

        # Draw a distinctive dashed boundary separator identifying the geological fault line limit
        mid_y = (self.ROWS // 2) * self.GRID_SIZE
        self.canvas.create_line(0, mid_y, self.MAP_WIDTH, mid_y, fill="#3e4451", dash=(6, 6), width=2)

    def on_map_click(self, event):
        """Captures mouse clicks to change epicenter point target parameters."""
        self.epicenter_x = event.x // self.GRID_SIZE
        self.epicenter_y = event.y // self.GRID_SIZE
        self.calculate_shakemap()

    def trigger_recalculation(self, val):
        """Helper callback tracking parameter changes to slide updates smoothly."""
        if self.epicenter_x is not None:
            self.calculate_shakemap()

    def calculate_shakemap(self):
        """Main attenuation mathematical calculation loops mapping intensities to pixels."""
        mag = self.slider_mag.get()
        focal_depth = self.slider_depth.get()

        # Calculate epicentral starting peak intensity (Derived from Gutenberg-Richter relationships)
        # I_0 = 1.5 * Mw - 1.5
        i_zero = (1.5 * mag) - 1.0

        for y in range(self.ROWS):
            for x in range(self.COLS):
                # 1. Compute Hypocentral Distance (incorporating 3D depth geometry using Pythagorean theorem)
                dx = (x - self.epicenter_x) * 4.0  # Scale multiplier converting cells into real kilometers
                dy = (y - self.epicenter_y) * 4.0
                epicentral_dist = math.sqrt(dx ** 2 + dy ** 2)
                hypocentral_dist = math.sqrt(epicentral_dist ** 2 + focal_depth ** 2)

                # 2. Apply Wave Attenuation Formula (Standard Geometrical Decay models)
                # Shaking decreases logarithmically over distance traveled
                mmi = i_zero - (3.2 * math.log10(hypocentral_dist / focal_depth + 1.0))

                # 3. Apply Local Geology Site Effects (Soil Amplification Modifiers)
                if y >= (self.ROWS // 2):
                    # Southern section contains soft alluvium, increasing MMI intensity by a full 1.4 units
                    mmi += 1.4

                # Determine mapped color profiling based on computed local node intensity values
                cell_color = None
                if mmi >= 7.5:
                    cell_color = "#e06c75"  # Severe (USGS Red equivalent)
                elif mmi >= 6.2:
                    cell_color = "#d19a66"  # Very Strong (Orange)
                elif mmi >= 5.0:
                    cell_color = "#e5c07b"  # Strong (Yellow)
                elif mmi >= 3.8:
                    cell_color = "#98c379"  # Moderate (Green)
                elif mmi >= 2.0:
                    cell_color = "#61afef"  # Light / Weak (Blue)
                else:
                    # Return baseline geology environmental shading if shaking is negligible
                    cell_color = "#21252b" if y < (self.ROWS // 2) else "#282c30"

                self.canvas.itemconfig(self.grid_rects[y][x], fill=cell_color)

        # Redraw epicenter marker node graphic overlay element
        self.canvas.delete("epicenter_pin")
        ex = (self.epicenter_x * self.GRID_SIZE) + (self.GRID_SIZE // 2)
        ey = (self.epicenter_y * self.GRID_SIZE) + (self.GRID_SIZE // 2)

        # Outer pulsing ring vector marks
        self.canvas.create_oval(ex - 12, ey - 12, ex + 12, ey + 12, outline="white", width=2, tags="epicenter_pin")
        # Internal bold star center indicator
        self.canvas.create_text(ex, ey + 2, text="★", fill="#ffffff", font=("Arial", 14, "bold"), tags="epicenter_pin")


if __name__ == "__main__":
    root = tk.Tk()
    app = ShakeMapSimulatorApp(root)
    root.mainloop()
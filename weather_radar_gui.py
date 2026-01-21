import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.colors as mcolors


class WeatherRadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Doppler Radar Station")
        self.root.geometry("1200x850")

        # --- Radar Configuration ---
        self.max_range = 250  # km
        self.azimuths = np.linspace(0, 2 * np.pi, 360)
        self.ranges = np.linspace(0, self.max_range, 400)
        self.r_grid, self.az_grid = np.meshgrid(self.ranges, self.azimuths)

        # --- Simulation State ---
        # Storm parameters (Azimuth, Range, Size)
        self.storm_angle = 0.5  # radians
        self.storm_dist = 100  # km
        self.rotation_speed = 0.02

        # --- Controls ---
        self.var_threshold = tk.DoubleVar(value=15.0)
        self.var_smoothing = tk.BooleanVar(value=False)
        self.var_clutter = tk.BooleanVar(value=True)

        self.setup_ui()
        self.setup_plot()

        # Start Animation Loop
        self.animate()

    def setup_ui(self):
        # Control Panel
        panel = ttk.LabelFrame(self.root, text="Radar Control Unit (R.C.U)", padding="10")
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Reflectivity Threshold Slider
        ttk.Label(panel, text="Reflectivity Filter (dBZ)").pack(anchor='w', pady=(10, 0))
        scale = ttk.Scale(panel, from_=0, to=60, variable=self.var_threshold, orient='horizontal')
        scale.pack(fill=tk.X, pady=5)
        self.lbl_thresh = ttk.Label(panel, text="Threshold: 15 dBZ")
        self.lbl_thresh.pack(anchor='w')

        # Toggle Switches
        ttk.Checkbutton(panel, text="Ground Clutter Simulation", variable=self.var_clutter).pack(anchor='w', pady=10)
        ttk.Checkbutton(panel, text="Smooth Interpolation", variable=self.var_smoothing,
                        command=self.update_plot_style).pack(anchor='w', pady=5)

        # Legend
        ttk.Label(panel, text="\nLegend:", font='bold').pack(anchor='w')
        ttk.Label(panel, text="> 60 dBZ: Extreme (Hail)", foreground="magenta").pack(anchor='w')
        ttk.Label(panel, text="40-60 dBZ: Heavy Rain", foreground="red").pack(anchor='w')
        ttk.Label(panel, text="20-40 dBZ: Light Rain", foreground="green").pack(anchor='w')
        ttk.Label(panel, text="< 20 dBZ: Mist/Clutter", foreground="grey").pack(anchor='w')

    def setup_plot(self):
        # Create Dark Theme Plot
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(8, 8))
        self.ax = self.fig.add_subplot(111, projection='polar')

        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Initialize Mesh (Empty)
        self.mesh = None
        self.cbar = None

        # Custom Colormap simulating NWS radar colors
        colors = [
            (0, "black"),
            (0.2, "cyan"),  # Light Rain
            (0.4, "lime"),  # Moderate
            (0.6, "yellow"),  # Heavy
            (0.8, "red"),  # Severe
            (1.0, "magenta")  # Hail
        ]
        self.cmap = mcolors.LinearSegmentedColormap.from_list("NWS_Radar", colors)

    def generate_data(self):
        # 1. Base Atmosphere (Noise)
        dbz = np.random.normal(5, 5, size=self.r_grid.shape)

        # 2. Add Moving Storm (Supercell)
        # Calculate angular distance accounting for wrap-around
        ang_diff = np.abs(self.az_grid - self.storm_angle)
        ang_diff = np.minimum(ang_diff, 2 * np.pi - ang_diff)

        # Storm Core shape
        dist_sq = (ang_diff * 4) ** 2 + ((self.r_grid - self.storm_dist) / 20) ** 2
        storm = 65 * np.exp(-dist_sq)  # 65 dBZ peak

        # Storm Hook Echo (Tornado signature)
        hook_angle = self.storm_angle - 0.2
        hook_dist = self.storm_dist - 15
        hook_diff = np.abs(self.az_grid - hook_angle)
        hook_diff = np.minimum(hook_diff, 2 * np.pi - hook_diff)
        dist_sq_hook = (hook_diff * 8) ** 2 + ((self.r_grid - hook_dist) / 10) ** 2
        hook = 50 * np.exp(-dist_sq_hook)

        dbz += storm + hook

        # 3. Add Ground Clutter (if enabled)
        if self.var_clutter.get():
            clutter_mask = self.r_grid < 30
            dbz[clutter_mask] += np.random.normal(25, 8, size=np.sum(clutter_mask))

        return dbz

    def animate(self):
        # Update Physics
        self.storm_angle = (self.storm_angle + 0.01) % (2 * np.pi)
        self.storm_dist = 100 + 20 * np.sin(self.storm_angle * 3)  # Meander slightly

        # Update Data
        raw_dbz = self.generate_data()

        # Update Threshold Label
        thresh_val = self.var_threshold.get()
        self.lbl_thresh.config(text=f"Threshold: {thresh_val:.1f} dBZ")

        # Apply Threshold Mask
        masked_dbz = np.ma.masked_where(raw_dbz < thresh_val, raw_dbz)

        # Clear and Redraw?
        # Note: clearing axes is slow. Updating pcolormesh is faster.
        # However, pcolormesh dimensions are fixed.

        if self.mesh is None:
            self.ax.clear()
            self.ax.set_ylim(0, self.max_range)
            self.ax.set_theta_zero_location('N')
            self.ax.set_theta_direction(-1)
            self.ax.grid(True, color='green', alpha=0.3)

            # Initial Draw
            self.mesh = self.ax.pcolormesh(self.az_grid, self.r_grid, masked_dbz,
                                           cmap=self.cmap, vmin=0, vmax=75, shading='auto')

            if self.cbar is None:
                self.cbar = self.fig.colorbar(self.mesh, ax=self.ax, shrink=0.8)
                self.cbar.set_label("Reflectivity (dBZ)")
                self.cbar.ax.yaxis.set_tick_params(color='white')
                plt.setp(plt.getp(self.cbar.ax.axes, 'yticklabels'), color='white')

        else:
            # Update data only
            # ravel() flattens the array for set_array
            # Note: For pcolormesh, set_array expects a 1D flattened array of the colors
            # But masked arrays can be tricky.
            self.mesh.set_array(masked_dbz.ravel())

        self.canvas.draw()

        # Schedule next frame (50ms = 20fps)
        self.root.after(100, self.animate)

    def update_plot_style(self):
        # Reset mesh to force redraw with new style if needed
        self.mesh = None


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherRadarGUI(root)
    root.mainloop()
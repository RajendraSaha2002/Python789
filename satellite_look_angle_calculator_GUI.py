import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from skyfield.api import load, wgs84, EarthSatellite
import threading
from datetime import datetime
import ssl

# SSL Certificate Fix for Windows
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


class SatelliteTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Satellite Look Angle Tracker")
        self.root.geometry("1100x700")

        # --- Data & State ---
        self.ts = load.timescale()
        self.is_tracking = False
        self.current_sat = None
        self.observer = None

        # Pre-defined TLE Data Sources (Popular Satellites)
        # We fetch these on startup
        self.sat_catalog = {
            "ISS (ZARYA)": 25544,
            "GOES-16 (GEO)": 41866,
            "NOAA-20 (Polar)": 43013,
            "STARLINK-1007": 44713
        }
        self.loaded_sats = {}

        # --- GUI Layout ---
        self.create_layout()

        # --- Start Data Load in Background ---
        self.status_var.set("Downloading TLE Data... Please Wait.")
        threading.Thread(target=self.load_tle_data, daemon=True).start()

    def create_layout(self):
        # 1. Left Control Panel
        control_frame = ttk.Frame(self.root, padding="15")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Title
        ttk.Label(control_frame, text="Observer Location", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Inputs
        ttk.Label(control_frame, text="Latitude (deg):").pack(anchor=tk.W)
        self.lat_entry = ttk.Entry(control_frame)
        self.lat_entry.insert(0, "40.7128")  # Default NYC
        self.lat_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Longitude (deg):").pack(anchor=tk.W)
        self.lon_entry = ttk.Entry(control_frame)
        self.lon_entry.insert(0, "-74.0060")  # Default NYC
        self.lon_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=15)

        ttk.Label(control_frame, text="Select Target", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))
        self.sat_combo = ttk.Combobox(control_frame, values=list(self.sat_catalog.keys()), state="readonly")
        self.sat_combo.current(0)
        self.sat_combo.pack(fill=tk.X, pady=(0, 10))

        self.btn_track = ttk.Button(control_frame, text="START TRACKING", command=self.toggle_tracking)
        self.btn_track.pack(fill=tk.X, pady=10)

        # Digital Readout
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(control_frame, text="Live Telemetry", font=("Arial", 14, "bold")).pack(anchor=tk.W)

        self.lbl_az = ttk.Label(control_frame, text="Azimuth: ---", font=("Courier", 14))
        self.lbl_az.pack(anchor=tk.W, pady=5)

        self.lbl_el = ttk.Label(control_frame, text="Elevation: ---", font=("Courier", 14))
        self.lbl_el.pack(anchor=tk.W, pady=5)

        self.lbl_dist = ttk.Label(control_frame, text="Distance: ---", font=("Courier", 12))
        self.lbl_dist.pack(anchor=tk.W, pady=5)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.BOTTOM, anchor=tk.W)

        # 2. Right Visualization Panel (Matplotlib)
        viz_frame = ttk.Frame(self.root)
        viz_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.figure(figsize=(6, 6), facecolor='#f0f0f0')
        # Polar projection for Skyplot
        self.ax = self.fig.add_subplot(111, projection='polar')
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.init_radar_plot()

    def init_radar_plot(self):
        """Sets up the static elements of the radar view."""
        self.ax.clear()

        # Configure Compass Direction
        self.ax.set_theta_zero_location('N')  # 0 degrees is North
        self.ax.set_theta_direction(-1)  # Clockwise angles

        # Configure Elevation (Radius)
        # Center is 90 deg (Zenith), Edge is 0 deg (Horizon)
        self.ax.set_ylim(0, 90)
        self.ax.set_yticks([0, 30, 60, 90])
        self.ax.set_yticklabels(['90°', '60°', '30°', 'Horizon'])
        self.ax.set_rlabel_position(45)

        self.ax.set_title("Sky View (Radar)", pad=20, fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.5)

        # Create the dynamic marker (The Satellite Dot)
        # Initial position off-screen
        self.sat_marker, = self.ax.plot([], [], 'ro', markersize=12, label='Satellite')
        self.sat_trail, = self.ax.plot([], [], 'r-', linewidth=1, alpha=0.5)

        # History buffers for trail
        self.trail_az = []
        self.trail_el = []

        self.canvas.draw()

    def load_tle_data(self):
        """Fetches orbital data from CelesTrak."""
        try:
            # Using GP API by Catalog Number
            base_url = 'https://celestrak.org/NORAD/elements/gp.php?CATNR={}'

            print("--- Starting Download ---")
            for name, catnr in self.sat_catalog.items():
                try:
                    url = base_url.format(catnr)
                    # reload=True forces a fresh download, ignoring bad cache
                    sat_data = load.tle_file(url, reload=True)
                    sat = list(sat_data.values())[0]
                    sat.name = name
                    self.loaded_sats[name] = sat
                    print(f"Loaded: {name}")
                except Exception as e:
                    # Print exact error for debugging
                    print(f"Failed to load {name}. Error: {e}")

            if not self.loaded_sats:
                self.root.after(0, lambda: self.status_var.set("Error: No data loaded. Check Console."))
            else:
                self.root.after(0, lambda: self.status_var.set("Data Loaded. Ready to Track."))

        except Exception as global_e:
            print(f"Critical Error in loader: {global_e}")
            self.root.after(0, lambda: self.status_var.set(f"Error loading data: {global_e}"))

    def toggle_tracking(self):
        if self.is_tracking:
            # Stop Tracking
            self.is_tracking = False
            self.btn_track.config(text="START TRACKING")
            self.status_var.set("Tracking Stopped.")
        else:
            # Start Tracking
            try:
                lat = float(self.lat_entry.get())
                lon = float(self.lon_entry.get())
                sat_name = self.sat_combo.get()

                if sat_name not in self.loaded_sats:
                    messagebox.showerror("Error", "Satellite data not ready yet. Check console for errors.")
                    return

                # define observer
                self.observer = wgs84.latlon(lat, lon)
                self.current_sat = self.loaded_sats[sat_name]

                # Reset Plot
                self.init_radar_plot()
                self.trail_az = []
                self.trail_el = []

                self.is_tracking = True
                self.btn_track.config(text="STOP TRACKING")
                self.status_var.set(f"Tracking {sat_name}...")

                # Start Loop
                self.update_loop()

            except ValueError:
                messagebox.showerror("Input Error", "Invalid Latitude/Longitude.")

    def update_loop(self):
        if not self.is_tracking:
            return

        # 1. Get Current Time
        now = self.ts.now()

        # 2. Compute Position relative to observer
        difference = self.current_sat - self.observer
        topocentric = difference.at(now)
        alt, az, distance = topocentric.altaz()

        # 3. Extract Values
        el_deg = alt.degrees
        az_deg = az.degrees
        dist_km = distance.km

        # 4. Update Text Labels
        self.lbl_az.config(text=f"Azimuth: {az_deg:.1f}°")
        self.lbl_el.config(text=f"Elevation: {el_deg:.1f}°")
        self.lbl_dist.config(text=f"Range: {dist_km:.0f} km")

        # 5. Update Radar Plot
        # Convert Azimuth to Radians for Matplotlib
        az_rad = np.deg2rad(az_deg)

        # Map Elevation to Radius
        # Center is 90 deg, Outer is 0 deg.
        # So Radius = 90 - Elevation.
        # If Elevation is negative (below horizon), we clamp it or hide it.

        if el_deg >= 0:
            radius = 90 - el_deg

            # Update Marker
            self.sat_marker.set_data([az_rad], [radius])

            # Color logic: Green if high in sky, Red if near horizon
            if el_deg > 30:
                self.sat_marker.set_color('#00ff00')  # Good signal
            else:
                self.sat_marker.set_color('#ffaa00')  # Weak signal

            self.status_var.set("Target Visible")

            # Update Trail
            self.trail_az.append(az_rad)
            self.trail_el.append(radius)
            # Keep trail short (last 50 points)
            if len(self.trail_az) > 50:
                self.trail_az.pop(0)
                self.trail_el.pop(0)
            self.sat_trail.set_data(self.trail_az, self.trail_el)

        else:
            # Below Horizon
            self.sat_marker.set_data([], [])  # Hide dot
            self.sat_trail.set_data([], [])
            self.status_var.set("Target Below Horizon (Waiting...)")
            self.lbl_el.config(text=f"Elevation: {el_deg:.1f}° (LOW)")

        self.canvas.draw()

        # 6. Schedule Next Update (1000ms = 1 second)
        self.root.after(1000, self.update_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = SatelliteTrackerApp(root)
    root.mainloop()
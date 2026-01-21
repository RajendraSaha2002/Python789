"""
Doppler Shift Simulator for Low Earth Orbit (LEO) and Sun-Synchronous Orbit (SSO) Satellites
Calculates and visualizes frequency shifts due to satellite motion relative to ground stations
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from skyfield.api import load, wgs84, EarthSatellite
import threading
from matplotlib.patches import Circle, FancyBboxPatch
import warnings

warnings.filterwarnings('ignore')


class DopplerSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Doppler Shift Simulator - LEO/SSO Satellites")
        self.root.geometry("1500x950")
        self.root.configure(bg="#0a0e27")

        # Physical constants
        self.c = 299792.458  # Speed of light in km/s

        # Satellite data storage
        self.satellite = None
        self.observer_location = None
        self.times = None
        self.frequencies = None
        self.elevations = None
        self.ranges = None
        self.animation_running = False
        self.animation = None

        # TLE data for popular satellites
        self.tle_database = {
            "NOAA 18": {
                "line1": "1 28654U 05018A   23365.50000000  .00000123  00000-0  71585-4 0  9993",
                "line2": "2 28654  98.9739 350.7326 0014531  73.9446 286.3486 14.12501077971234",
                "freq": 137.9125,
                "description": "Weather satellite"
            },
            "NOAA 19": {
                "line1": "1 33591U 09005A   23365.50000000  .00000134  00000-0  80234-4 0  9990",
                "line2": "2 33591  99.1891  29.7234 0014216  21.4562 338.7563 14.12513493765432",
                "freq": 137.1000,
                "description": "Weather satellite"
            },
            "ISS (ZARYA)": {
                "line1": "1 25544U 98067A   23365.50000000  .00016717  00000-0  10270-3 0  9999",
                "line2": "2 25544  51.6416 208.3720 0001350  59.0712 301.0749 15.50030698123456",
                "freq": 145.8000,
                "description": "International Space Station"
            },
            "METEOR-M2": {
                "line1": "1 40069U 14037A   23365.50000000  .00000234  00000-0  12345-3 0  9997",
                "line2": "2 40069  98.5123 123.4567 0002345  89.1234 270.9876 14.23456789123456",
                "freq": 137.1000,
                "description": "Russian weather satellite"
            }
        }

        self.setup_gui()

    def setup_gui(self):
        # Title Frame
        title_frame = tk.Frame(self.root, bg="#0a0e27")
        title_frame.pack(pady=15)

        title_label = tk.Label(
            title_frame,
            text="📡 Doppler Shift Simulator",
            font=("Arial", 28, "bold"),
            bg="#0a0e27",
            fg="#00d9ff"
        )
        title_label.pack()

        subtitle = tk.Label(
            title_frame,
            text="Real-time Frequency Analysis for LEO/SSO Satellite Communications",
            font=("Arial", 12),
            bg="#0a0e27",
            fg="#7dd3fc"
        )
        subtitle.pack()

        # Main container
        main_container = tk.Frame(self.root, bg="#0a0e27")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left Panel - Controls
        left_panel = tk.Frame(main_container, bg="#1e3a5f", relief=tk.RAISED, bd=3)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Satellite Selection
        sat_frame = tk.LabelFrame(
            left_panel,
            text="🛰️ Satellite Selection",
            bg="#1e3a5f",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        sat_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(sat_frame, text="Select Satellite:", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(anchor="w",
                                                                                                           pady=5)

        self.sat_var = tk.StringVar(value="NOAA 18")
        sat_combo = ttk.Combobox(
            sat_frame,
            textvariable=self.sat_var,
            values=list(self.tle_database.keys()),
            state="readonly",
            font=("Arial", 10),
            width=25
        )
        sat_combo.pack(pady=5)
        sat_combo.bind("<<ComboboxSelected>>", self.update_satellite_info)

        self.sat_info_label = tk.Label(
            sat_frame,
            text="",
            bg="#1e3a5f",
            fg="#7dd3fc",
            font=("Arial", 9),
            justify=tk.LEFT,
            wraplength=250
        )
        self.sat_info_label.pack(pady=5)

        # Observer Location
        obs_frame = tk.LabelFrame(
            left_panel,
            text="📍 Observer Location",
            bg="#1e3a5f",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        obs_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(obs_frame, text="Latitude (°):", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(anchor="w")
        self.lat_entry = tk.Entry(obs_frame, font=("Arial", 10), width=20)
        self.lat_entry.insert(0, "26.7271")  # Siliguri
        self.lat_entry.pack(pady=2)

        tk.Label(obs_frame, text="Longitude (°):", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(anchor="w",
                                                                                                        pady=(5, 0))
        self.lon_entry = tk.Entry(obs_frame, font=("Arial", 10), width=20)
        self.lon_entry.insert(0, "88.3953")  # Siliguri
        self.lon_entry.pack(pady=2)

        tk.Label(obs_frame, text="Altitude (m):", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(anchor="w",
                                                                                                       pady=(5, 0))
        self.alt_entry = tk.Entry(obs_frame, font=("Arial", 10), width=20)
        self.alt_entry.insert(0, "122")
        self.alt_entry.pack(pady=2)

        # Simulation Parameters
        sim_frame = tk.LabelFrame(
            left_panel,
            text="⚙️ Simulation Settings",
            bg="#1e3a5f",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        sim_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(sim_frame, text="Pass Duration (min):", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(
            anchor="w")
        self.duration_entry = tk.Entry(sim_frame, font=("Arial", 10), width=20)
        self.duration_entry.insert(0, "15")
        self.duration_entry.pack(pady=2)

        tk.Label(sim_frame, text="Carrier Frequency (MHz):", bg="#1e3a5f", fg="#ffffff", font=("Arial", 10)).pack(
            anchor="w", pady=(5, 0))
        self.freq_entry = tk.Entry(sim_frame, font=("Arial", 10), width=20)
        self.freq_entry.insert(0, "137.9125")
        self.freq_entry.pack(pady=2)

        # Action Buttons
        btn_frame = tk.Frame(left_panel, bg="#1e3a5f")
        btn_frame.pack(padx=10, pady=20, fill=tk.X)

        self.calc_btn = tk.Button(
            btn_frame,
            text="🚀 Calculate Pass",
            command=self.calculate_doppler,
            bg="#00d9ff",
            fg="#0a0e27",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=10,
            pady=8
        )
        self.calc_btn.pack(fill=tk.X, pady=5)

        self.animate_btn = tk.Button(
            btn_frame,
            text="▶️ Animate",
            command=self.start_animation,
            bg="#4ade80",
            fg="#0a0e27",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=10,
            pady=8,
            state=tk.DISABLED
        )
        self.animate_btn.pack(fill=tk.X, pady=5)

        self.clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear",
            command=self.clear_all,
            bg="#ef4444",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=10,
            pady=8
        )
        self.clear_btn.pack(fill=tk.X, pady=5)

        # Status Display
        status_frame = tk.LabelFrame(
            left_panel,
            text="📊 Statistics",
            bg="#1e3a5f",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        status_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.stats_text = tk.Text(
            status_frame,
            height=10,
            width=30,
            bg="#0f1729",
            fg="#7dd3fc",
            font=("Courier", 9),
            relief=tk.FLAT,
            padx=5,
            pady=5
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.stats_text.insert("1.0", "Calculate a pass to see statistics...")
        self.stats_text.config(state=tk.DISABLED)

        # Right Panel - Visualization
        right_panel = tk.Frame(main_container, bg="#0a0e27")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create matplotlib figure
        self.fig = plt.figure(figsize=(12, 8), facecolor="#0a0e27")

        # Create subplots
        gs = self.fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        self.ax_doppler = self.fig.add_subplot(gs[0:2, :])
        self.ax_elevation = self.fig.add_subplot(gs[2, 0])
        self.ax_range = self.fig.add_subplot(gs[2, 1])

        for ax in [self.ax_doppler, self.ax_elevation, self.ax_range]:
            ax.set_facecolor('#1e3a5f')
            ax.tick_params(colors='#7dd3fc')
            ax.spines['bottom'].set_color('#7dd3fc')
            ax.spines['left'].set_color('#7dd3fc')
            ax.spines['top'].set_color('#7dd3fc')
            ax.spines['right'].set_color('#7dd3fc')

        self.ax_doppler.set_title('Doppler Shift vs Time (S-Curve)', color='#00d9ff', fontsize=14, fontweight='bold',
                                  pad=15)
        self.ax_doppler.set_xlabel('Time (seconds)', color='#ffffff', fontsize=11)
        self.ax_doppler.set_ylabel('Frequency Shift (kHz)', color='#ffffff', fontsize=11)
        self.ax_doppler.grid(True, alpha=0.2, color='#7dd3fc')

        self.ax_elevation.set_title('Elevation Angle', color='#4ade80', fontsize=11, fontweight='bold')
        self.ax_elevation.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_elevation.set_ylabel('Elevation (°)', color='#ffffff', fontsize=9)
        self.ax_elevation.grid(True, alpha=0.2, color='#7dd3fc')

        self.ax_range.set_title('Range to Satellite', color='#fbbf24', fontsize=11, fontweight='bold')
        self.ax_range.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_range.set_ylabel('Range (km)', color='#ffffff', fontsize=9)
        self.ax_range.grid(True, alpha=0.2, color='#7dd3fc')

        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Status: Ready | Select satellite and calculate pass",
            bg="#0f1729",
            fg="#00d9ff",
            font=("Arial", 10),
            anchor="w",
            padx=10,
            pady=5
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize
        self.update_satellite_info()

    def update_satellite_info(self, event=None):
        """Update satellite information display"""
        sat_name = self.sat_var.get()
        sat_data = self.tle_database[sat_name]

        info = f"Frequency: {sat_data['freq']} MHz\n{sat_data['description']}"
        self.sat_info_label.config(text=info)
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, str(sat_data['freq']))

    def calculate_doppler(self):
        """Calculate Doppler shift for satellite pass"""
        try:
            # Get parameters
            sat_name = self.sat_var.get()
            sat_data = self.tle_database[sat_name]

            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            alt = float(self.alt_entry.get())
            duration = float(self.duration_entry.get())
            carrier_freq = float(self.freq_entry.get())  # MHz

            self.status_label.config(text="⏳ Calculating satellite pass...")
            self.root.update()

            # Load ephemeris
            ts = load.timescale()

            # Create satellite object from TLE
            self.satellite = EarthSatellite(sat_data['line1'], sat_data['line2'], sat_name, ts)

            # Create observer location
            self.observer_location = wgs84.latlon(lat, lon, alt)

            # Create time array (centered around now)
            t0 = ts.now()
            start_time = t0 - timedelta(minutes=duration / 2)
            end_time = t0 + timedelta(minutes=duration / 2)

            # Generate time points
            num_points = int(duration * 60)  # One point per second
            time_range = np.linspace(0, duration * 60, num_points)

            self.times = []
            positions = []
            velocities = []
            self.elevations = []
            self.ranges = []

            for dt in time_range:
                t = ts.utc(start_time.utc_datetime() + timedelta(seconds=dt))
                self.times.append(dt)

                # Get satellite position relative to observer
                difference = self.satellite - self.observer_location
                topocentric = difference.at(t)

                alt_deg, az_deg, distance = topocentric.altaz()
                self.elevations.append(alt_deg.degrees)
                self.ranges.append(distance.km)

                # Get velocity (range rate)
                positions.append(topocentric.position.km)
                if len(positions) > 1:
                    dt_sec = time_range[1] - time_range[0]
                    velocity = (np.array(positions[-1]) - np.array(positions[-2])) / dt_sec
                    range_rate = np.linalg.norm(velocity)  # km/s
                    velocities.append(range_rate)

            # Calculate Doppler shift
            # Δf = (v_relative / c) × f_carrier
            self.frequencies = []

            for i in range(len(positions)):
                if i == 0:
                    range_rate = 0
                else:
                    # Calculate radial velocity
                    pos_vec = np.array(positions[i])
                    prev_pos_vec = np.array(positions[i - 1])
                    dt_sec = time_range[1] - time_range[0]

                    vel_vec = (pos_vec - prev_pos_vec) / dt_sec
                    range_rate = np.dot(vel_vec, pos_vec) / np.linalg.norm(pos_vec)

                # Doppler shift formula
                doppler_shift = (range_rate / self.c) * carrier_freq * 1000  # Convert to kHz
                self.frequencies.append(doppler_shift)

            # Plot results
            self.plot_results()

            # Update statistics
            self.update_statistics()

            self.animate_btn.config(state=tk.NORMAL)
            self.status_label.config(text=f"✅ Pass calculated successfully for {sat_name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate Doppler shift:\n{str(e)}")
            self.status_label.config(text="❌ Calculation failed")

    def plot_results(self):
        """Plot Doppler shift and related data"""
        # Clear previous plots
        self.ax_doppler.clear()
        self.ax_elevation.clear()
        self.ax_range.clear()

        # Doppler shift plot (S-curve)
        self.ax_doppler.plot(self.times, self.frequencies, 'c-', linewidth=2.5, label='Doppler Shift')
        self.ax_doppler.axhline(y=0, color='#ef4444', linestyle='--', linewidth=1.5, alpha=0.7,
                                label='Carrier Frequency')
        self.ax_doppler.fill_between(self.times, self.frequencies, 0, alpha=0.3, color='#00d9ff')

        self.ax_doppler.set_title('Doppler Shift vs Time (S-Curve)', color='#00d9ff', fontsize=14, fontweight='bold',
                                  pad=15)
        self.ax_doppler.set_xlabel('Time (seconds)', color='#ffffff', fontsize=11)
        self.ax_doppler.set_ylabel('Frequency Shift (kHz)', color='#ffffff', fontsize=11)
        self.ax_doppler.grid(True, alpha=0.2, color='#7dd3fc')
        self.ax_doppler.legend(loc='upper right', facecolor='#1e3a5f', edgecolor='#7dd3fc', labelcolor='#ffffff')

        # Elevation plot
        self.ax_elevation.plot(self.times, self.elevations, '#4ade80', linewidth=2)
        self.ax_elevation.fill_between(self.times, self.elevations, 0, alpha=0.3, color='#4ade80')
        self.ax_elevation.axhline(y=0, color='#ef4444', linestyle='--', linewidth=1, alpha=0.5)
        self.ax_elevation.set_title('Elevation Angle', color='#4ade80', fontsize=11, fontweight='bold')
        self.ax_elevation.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_elevation.set_ylabel('Elevation (°)', color='#ffffff', fontsize=9)
        self.ax_elevation.grid(True, alpha=0.2, color='#7dd3fc')

        # Range plot
        self.ax_range.plot(self.times, self.ranges, '#fbbf24', linewidth=2)
        self.ax_range.fill_between(self.times, self.ranges, min(self.ranges), alpha=0.3, color='#fbbf24')
        self.ax_range.set_title('Range to Satellite', color='#fbbf24', fontsize=11, fontweight='bold')
        self.ax_range.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_range.set_ylabel('Range (km)', color='#ffffff', fontsize=9)
        self.ax_range.grid(True, alpha=0.2, color='#7dd3fc')

        for ax in [self.ax_doppler, self.ax_elevation, self.ax_range]:
            ax.set_facecolor('#1e3a5f')
            ax.tick_params(colors='#7dd3fc')
            for spine in ax.spines.values():
                spine.set_color('#7dd3fc')

        self.canvas.draw()

    def update_statistics(self):
        """Update statistics display"""
        if self.frequencies is None or len(self.frequencies) == 0:
            return

        max_shift = max(self.frequencies)
        min_shift = min(self.frequencies)
        total_shift = max_shift - min_shift
        max_elevation = max(self.elevations)
        min_range = min(self.ranges)

        # Find closest approach
        closest_idx = self.ranges.index(min_range)
        closest_time = self.times[closest_idx]

        stats = f"""
╔═══════════════════════════════╗
║   PASS STATISTICS            ║
╚═══════════════════════════════╝

Doppler Shift:
  Max: +{max_shift:.3f} kHz
  Min: {min_shift:.3f} kHz
  Total: {total_shift:.3f} kHz

Geometry:
  Max Elevation: {max_elevation:.2f}°
  Min Range: {min_range:.1f} km
  Closest at: {closest_time:.0f}s

Observer Location:
  Lat: {self.lat_entry.get()}°
  Lon: {self.lon_entry.get()}°
  Alt: {self.alt_entry.get()}m
        """

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert("1.0", stats)
        self.stats_text.config(state=tk.DISABLED)

    def start_animation(self):
        """Start animated visualization of the pass"""
        if self.animation_running:
            return

        self.animation_running = True
        self.animate_btn.config(state=tk.DISABLED)

        # Create animation point
        self.doppler_point, = self.ax_doppler.plot([], [], 'ro', markersize=10, zorder=5)
        self.elevation_point, = self.ax_elevation.plot([], [], 'go', markersize=8, zorder=5)
        self.range_point, = self.ax_range.plot([], [], 'yo', markersize=8, zorder=5)

        # Animation function
        def animate(frame):
            if frame < len(self.times):
                self.doppler_point.set_data([self.times[frame]], [self.frequencies[frame]])
                self.elevation_point.set_data([self.times[frame]], [self.elevations[frame]])
                self.range_point.set_data([self.times[frame]], [self.ranges[frame]])

                self.status_label.config(
                    text=f"▶️ Animating... Time: {self.times[frame]:.1f}s | Shift: {self.frequencies[frame]:.3f} kHz")

            return self.doppler_point, self.elevation_point, self.range_point

        self.animation = FuncAnimation(
            self.fig,
            animate,
            frames=len(self.times),
            interval=50,
            repeat=False,
            blit=True
        )

        self.canvas.draw()

        # Reset after animation
        self.root.after(len(self.times) * 50 + 500, self.reset_animation)

    def reset_animation(self):
        """Reset animation state"""
        self.animation_running = False
        self.animate_btn.config(state=tk.NORMAL)
        self.status_label.config(text="✅ Animation complete")

    def clear_all(self):
        """Clear all data and plots"""
        self.times = None
        self.frequencies = None
        self.elevations = None
        self.ranges = None

        for ax in [self.ax_doppler, self.ax_elevation, self.ax_range]:
            ax.clear()
            ax.set_facecolor('#1e3a5f')
            ax.grid(True, alpha=0.2, color='#7dd3fc')

        self.ax_doppler.set_title('Doppler Shift vs Time (S-Curve)', color='#00d9ff', fontsize=14, fontweight='bold',
                                  pad=15)
        self.ax_doppler.set_xlabel('Time (seconds)', color='#ffffff', fontsize=11)
        self.ax_doppler.set_ylabel('Frequency Shift (kHz)', color='#ffffff', fontsize=11)

        self.ax_elevation.set_title('Elevation Angle', color='#4ade80', fontsize=11, fontweight='bold')
        self.ax_elevation.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_elevation.set_ylabel('Elevation (°)', color='#ffffff', fontsize=9)

        self.ax_range.set_title('Range to Satellite', color='#fbbf24', fontsize=11, fontweight='bold')
        self.ax_range.set_xlabel('Time (s)', color='#ffffff', fontsize=9)
        self.ax_range.set_ylabel('Range (km)', color='#ffffff', fontsize=9)

        self.canvas.draw()

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert("1.0", "Calculate a pass to see statistics...")
        self.stats_text.config(state=tk.DISABLED)

        self.animate_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Cleared | Ready for new calculation")


# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = DopplerSimulator(root)
    root.mainloop()
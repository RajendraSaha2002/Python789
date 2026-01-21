"""
Solar Interference (Sun Outage) Predictor for Geostationary Satellites
Predicts when the sun passes behind a GEO satellite, causing signal interference
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Wedge, FancyBboxPatch
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from skyfield.api import load, wgs84, Topos
from skyfield import almanac
import warnings

warnings.filterwarnings('ignore')


class SunOutagePredictor:
    def __init__(self, root):
        self.root = root
        self.root.title("☀️ Solar Interference Predictor - GEO Satellites")
        self.root.geometry("1600x950")
        self.root.configure(bg="#0f0f23")

        # Data storage
        self.outage_events = []
        self.daily_separations = []
        self.dates = []
        self.animation_running = False
        self.animation = None

        # Popular GEO satellites (longitude positions)
        self.geo_satellites = {
            "Intelsat 20 (68.5°E)": {"longitude": 68.5, "service": "TV/Comm", "frequency": "C/Ku-band"},
            "GSAT-10 (83°E)": {"longitude": 83.0, "service": "TV/DTH", "frequency": "Ku-band"},
            "Insat 4A (83°E)": {"longitude": 83.0, "service": "TV/Comm", "frequency": "C/Ku-band"},
            "AsiaSat 5 (100.5°E)": {"longitude": 100.5, "service": "TV/Comm", "frequency": "C/Ku-band"},
            "SES-8 (95°E)": {"longitude": 95.0, "service": "TV/Comm", "frequency": "C/Ku-band"},
            "Thaicom 5 (78.5°E)": {"longitude": 78.5, "service": "TV/Comm", "frequency": "C/Ku-band"},
            "Intelsat 19 (166°E)": {"longitude": 166.0, "service": "TV/Comm", "frequency": "C-band"},
            "Galaxy 19 (97°W)": {"longitude": -97.0, "service": "TV/Comm", "frequency": "C/Ku-band"},
        }

        self.setup_gui()

    def setup_gui(self):
        # Title Frame
        title_frame = tk.Frame(self.root, bg="#0f0f23")
        title_frame.pack(pady=15)

        title_label = tk.Label(
            title_frame,
            text="☀️ Solar Interference Predictor",
            font=("Arial", 28, "bold"),
            bg="#0f0f23",
            fg="#fbbf24"
        )
        title_label.pack()

        subtitle = tk.Label(
            title_frame,
            text="Sun Outage Analysis for Geostationary Satellites",
            font=("Arial", 13),
            bg="#0f0f23",
            fg="#fcd34d"
        )
        subtitle.pack()

        description = tk.Label(
            title_frame,
            text="Predict signal disruptions when the Sun passes directly behind GEO satellites (Equinox phenomenon)",
            font=("Arial", 10),
            bg="#0f0f23",
            fg="#a3a3a3"
        )
        description.pack()

        # Main container
        main_container = tk.Frame(self.root, bg="#0f0f23")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left Panel - Controls
        left_panel = tk.Frame(main_container, bg="#1c1c3a", relief=tk.RAISED, bd=3)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Satellite Selection
        sat_frame = tk.LabelFrame(
            left_panel,
            text="🛰️ Satellite Configuration",
            bg="#1c1c3a",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        sat_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(sat_frame, text="Select GEO Satellite:", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(
            anchor="w", pady=5)

        self.sat_var = tk.StringVar(value="GSAT-10 (83°E)")
        sat_combo = ttk.Combobox(
            sat_frame,
            textvariable=self.sat_var,
            values=list(self.geo_satellites.keys()),
            state="readonly",
            font=("Arial", 10),
            width=28
        )
        sat_combo.pack(pady=5)
        sat_combo.bind("<<ComboboxSelected>>", self.update_satellite_info)

        self.sat_info_label = tk.Label(
            sat_frame,
            text="",
            bg="#1c1c3a",
            fg="#fcd34d",
            font=("Arial", 9),
            justify=tk.LEFT,
            wraplength=280
        )
        self.sat_info_label.pack(pady=5)

        # Ground Station Location
        gs_frame = tk.LabelFrame(
            left_panel,
            text="📍 Ground Station",
            bg="#1c1c3a",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        gs_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(gs_frame, text="Latitude (°):", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(anchor="w")
        self.lat_entry = tk.Entry(gs_frame, font=("Arial", 10), width=25)
        self.lat_entry.insert(0, "26.7271")  # Siliguri
        self.lat_entry.pack(pady=2)

        tk.Label(gs_frame, text="Longitude (°):", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(anchor="w",
                                                                                                       pady=(5, 0))
        self.lon_entry = tk.Entry(gs_frame, font=("Arial", 10), width=25)
        self.lon_entry.insert(0, "88.3953")  # Siliguri
        self.lon_entry.pack(pady=2)

        tk.Label(gs_frame, text="Altitude (m):", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(anchor="w",
                                                                                                      pady=(5, 0))
        self.alt_entry = tk.Entry(gs_frame, font=("Arial", 10), width=25)
        self.alt_entry.insert(0, "122")
        self.alt_entry.pack(pady=2)

        # Antenna Parameters
        antenna_frame = tk.LabelFrame(
            left_panel,
            text="📡 Antenna Specifications",
            bg="#1c1c3a",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        antenna_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(antenna_frame, text="Beamwidth (°):", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(anchor="w")
        self.beamwidth_entry = tk.Entry(antenna_frame, font=("Arial", 10), width=25)
        self.beamwidth_entry.insert(0, "0.5")
        self.beamwidth_entry.pack(pady=2)

        tk.Label(
            antenna_frame,
            text="Typical: 0.3-0.8° for TV dishes\n1.0-2.0° for smaller antennas",
            bg="#1c1c3a",
            fg="#a3a3a3",
            font=("Arial", 8),
            justify=tk.LEFT
        ).pack(pady=2)

        # Analysis Period
        period_frame = tk.LabelFrame(
            left_panel,
            text="📅 Analysis Period",
            bg="#1c1c3a",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        period_frame.pack(padx=10, pady=10, fill=tk.X)

        tk.Label(period_frame, text="Days to analyze:", bg="#1c1c3a", fg="#ffffff", font=("Arial", 10)).pack(anchor="w")
        self.days_entry = tk.Entry(period_frame, font=("Arial", 10), width=25)
        self.days_entry.insert(0, "365")
        self.days_entry.pack(pady=2)

        tk.Label(
            period_frame,
            text="Recommended: 180-365 days\n(covers both equinox periods)",
            bg="#1c1c3a",
            fg="#a3a3a3",
            font=("Arial", 8),
            justify=tk.LEFT
        ).pack(pady=2)

        # Action Buttons
        btn_frame = tk.Frame(left_panel, bg="#1c1c3a")
        btn_frame.pack(padx=10, pady=20, fill=tk.X)

        self.predict_btn = tk.Button(
            btn_frame,
            text="🔍 Predict Outages",
            command=self.predict_outages,
            bg="#fbbf24",
            fg="#0f0f23",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=10,
            pady=10
        )
        self.predict_btn.pack(fill=tk.X, pady=5)

        self.animate_btn = tk.Button(
            btn_frame,
            text="▶️ Animate Year",
            command=self.start_animation,
            bg="#4ade80",
            fg="#0f0f23",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=10,
            pady=10,
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
            pady=10
        )
        self.clear_btn.pack(fill=tk.X, pady=5)

        # Results Display
        results_frame = tk.LabelFrame(
            left_panel,
            text="📊 Outage Events",
            bg="#1c1c3a",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10
        )
        results_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Add scrollbar
        scroll_frame = tk.Frame(results_frame, bg="#1c1c3a")
        scroll_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_text = tk.Text(
            scroll_frame,
            height=12,
            width=35,
            bg="#0a0a1a",
            fg="#fcd34d",
            font=("Courier", 9),
            relief=tk.FLAT,
            padx=5,
            pady=5,
            yscrollcommand=scrollbar.set
        )
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_text.yview)

        self.results_text.insert("1.0", "Click 'Predict Outages' to analyze...")
        self.results_text.config(state=tk.DISABLED)

        # Right Panel - Visualization
        right_panel = tk.Frame(main_container, bg="#0f0f23")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create matplotlib figure
        self.fig = plt.figure(figsize=(13, 9), facecolor="#0f0f23")

        # Create subplots
        gs = self.fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)
        self.ax_main = self.fig.add_subplot(gs[0:2, :])
        self.ax_sky = self.fig.add_subplot(gs[2, 0], projection='polar')
        self.ax_calendar = self.fig.add_subplot(gs[2, 1])

        for ax in [self.ax_main, self.ax_calendar]:
            ax.set_facecolor('#1a1a2e')
            ax.tick_params(colors='#fcd34d')
            for spine in ax.spines.values():
                spine.set_color('#fbbf24')

        self.ax_sky.set_facecolor('#1a1a2e')
        self.ax_sky.tick_params(colors='#fcd34d')
        self.ax_sky.spines['polar'].set_color('#fbbf24')

        self.ax_main.set_title(
            'Sun-Satellite Separation Angle Over Time',
            color='#fbbf24',
            fontsize=15,
            fontweight='bold',
            pad=20
        )
        self.ax_main.set_xlabel('Date', color='#ffffff', fontsize=12)
        self.ax_main.set_ylabel('Separation Angle (degrees)', color='#ffffff', fontsize=12)
        self.ax_main.grid(True, alpha=0.3, color='#fcd34d')

        self.ax_sky.set_title('Sky View (Ground Station)', color='#4ade80', fontsize=12, fontweight='bold', pad=15)

        self.ax_calendar.set_title('Outage Calendar', color='#f472b6', fontsize=12, fontweight='bold')
        self.ax_calendar.set_xlabel('Day of Year', color='#ffffff', fontsize=10)
        self.ax_calendar.set_ylabel('Hour (UTC)', color='#ffffff', fontsize=10)

        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Status: Ready | Configure parameters and click 'Predict Outages'",
            bg="#1a1a2e",
            fg="#fbbf24",
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
        sat_data = self.geo_satellites[sat_name]

        info = f"Longitude: {sat_data['longitude']}°\n"
        info += f"Service: {sat_data['service']}\n"
        info += f"Band: {sat_data['frequency']}"

        self.sat_info_label.config(text=info)

    def predict_outages(self):
        """Predict sun outage events"""
        try:
            # Get parameters
            sat_name = self.sat_var.get()
            sat_data = self.geo_satellites[sat_name]
            sat_lon = sat_data['longitude']

            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            alt = float(self.alt_entry.get())
            beamwidth = float(self.beamwidth_entry.get())
            days = int(self.days_entry.get())

            self.status_label.config(text="⏳ Analyzing sun-satellite alignment...")
            self.root.update()

            # Load ephemeris
            ts = load.timescale()
            eph = load('de421.bsp')
            earth = eph['earth']
            sun = eph['sun']

            # Create observer location
            observer = earth + wgs84.latlon(lat, lon, alt)

            # GEO satellite is at 35,786 km altitude, at specified longitude
            # For simplicity, we create a fixed position for the GEO satellite
            from skyfield.positionlib import Geocentric
            from skyfield.units import Distance, Angle

            # Start from today
            start_date = datetime.now()
            self.dates = []
            self.daily_separations = []
            self.outage_events = []

            # Analyze each day
            for day in range(days):
                current_date = start_date + timedelta(days=day)

                # Sample times throughout the day (every hour)
                daily_seps = []
                for hour in range(24):
                    t = ts.utc(current_date.year, current_date.month, current_date.day, hour, 0, 0)

                    # Get sun position
                    sun_pos = observer.at(t).observe(sun).apparent()
                    sun_alt, sun_az, _ = sun_pos.altaz()

                    # Calculate GEO satellite position in the sky
                    # GEO satellites appear at a fixed point in the sky for a given observer
                    sat_az = sat_lon - lon  # Approximate azimuth
                    if sat_az < -180:
                        sat_az += 360
                    if sat_az > 180:
                        sat_az -= 360

                    # Calculate elevation angle for GEO satellite
                    # Using simplified geometry
                    earth_radius = 6371  # km
                    geo_altitude = 35786  # km
                    geo_radius = earth_radius + geo_altitude

                    observer_lat_rad = np.radians(lat)
                    sat_lon_rad = np.radians(sat_lon)
                    observer_lon_rad = np.radians(lon)

                    # Angular separation in longitude
                    delta_lon = sat_lon_rad - observer_lon_rad

                    # Calculate elevation
                    cos_el = np.cos(observer_lat_rad) * np.cos(delta_lon)
                    sat_el = np.degrees(np.arctan((cos_el - earth_radius / geo_radius) / np.sqrt(1 - cos_el ** 2)))

                    # Calculate angular separation between sun and satellite
                    sun_alt_rad = sun_alt.radians
                    sun_az_rad = sun_az.radians
                    sat_el_rad = np.radians(sat_el)
                    sat_az_rad = np.radians(sat_az)

                    # Angular separation formula
                    cos_sep = (np.sin(sun_alt_rad) * np.sin(sat_el_rad) +
                               np.cos(sun_alt_rad) * np.cos(sat_el_rad) *
                               np.cos(sun_az_rad - sat_az_rad))

                    # Clamp to valid range
                    cos_sep = np.clip(cos_sep, -1, 1)
                    separation = np.degrees(np.arccos(cos_sep))

                    daily_seps.append(separation)

                    # Check for outage (separation less than beamwidth and satellite above horizon)
                    if separation < beamwidth and sat_el > 0:
                        self.outage_events.append({
                            'date': current_date,
                            'hour': hour,
                            'separation': separation,
                            'sat_elevation': sat_el,
                            'sun_elevation': sun_alt.degrees
                        })

                self.dates.append(current_date)
                self.daily_separations.append(min(daily_seps))  # Minimum separation for the day

            # Plot results
            self.plot_results()

            # Display outage events
            self.display_outage_events()

            self.animate_btn.config(state=tk.NORMAL)
            self.status_label.config(
                text=f"✅ Analysis complete | Found {len(self.outage_events)} potential outage periods")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to predict outages:\n{str(e)}")
            self.status_label.config(text="❌ Prediction failed")

    def plot_results(self):
        """Plot prediction results"""
        # Clear previous plots
        self.ax_main.clear()
        self.ax_sky.clear()
        self.ax_calendar.clear()

        beamwidth = float(self.beamwidth_entry.get())

        # Main plot - Separation angle over time
        self.ax_main.plot(self.dates, self.daily_separations, 'gold', linewidth=2.5, label='Minimum Daily Separation')
        self.ax_main.axhline(y=beamwidth, color='#ef4444', linestyle='--', linewidth=2,
                             label=f'Beamwidth Threshold ({beamwidth}°)', alpha=0.8)

        # Fill danger zone
        self.ax_main.fill_between(self.dates, 0, beamwidth, alpha=0.3, color='red', label='Outage Risk Zone')

        # Mark outage events
        if self.outage_events:
            outage_dates = [event['date'] for event in self.outage_events]
            outage_seps = [event['separation'] for event in self.outage_events]
            self.ax_main.scatter(outage_dates, outage_seps, c='red', s=100, marker='x',
                                 linewidths=3, label='Outage Events', zorder=5)

        self.ax_main.set_title('Sun-Satellite Separation Angle Over Time',
                               color='#fbbf24', fontsize=15, fontweight='bold', pad=20)
        self.ax_main.set_xlabel('Date', color='#ffffff', fontsize=12)
        self.ax_main.set_ylabel('Separation Angle (degrees)', color='#ffffff', fontsize=12)
        self.ax_main.grid(True, alpha=0.3, color='#fcd34d')
        self.ax_main.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='#fbbf24',
                            labelcolor='#ffffff', fontsize=9)
        self.ax_main.set_facecolor('#1a1a2e')
        self.ax_main.tick_params(colors='#fcd34d')

        # Rotate date labels
        self.fig.autofmt_xdate()

        # Sky view (polar plot)
        sat_name = self.sat_var.get()
        sat_data = self.geo_satellites[sat_name]
        sat_lon = sat_data['longitude']
        lon = float(self.lon_entry.get())
        lat = float(self.lat_entry.get())

        sat_az = sat_lon - lon
        if sat_az < -180:
            sat_az += 360
        if sat_az > 180:
            sat_az -= 360

        # Calculate satellite elevation
        earth_radius = 6371
        geo_altitude = 35786
        geo_radius = earth_radius + geo_altitude
        observer_lat_rad = np.radians(lat)
        delta_lon = np.radians(sat_lon - lon)
        cos_el = np.cos(observer_lat_rad) * np.cos(delta_lon)
        sat_el = np.degrees(np.arctan((cos_el - earth_radius / geo_radius) / np.sqrt(1 - cos_el ** 2)))

        # Plot satellite position
        sat_az_rad = np.radians(sat_az)
        sat_zenith = 90 - sat_el
        self.ax_sky.plot([sat_az_rad], [sat_zenith], 'c*', markersize=25, label='GEO Satellite', zorder=10)

        # Plot beamwidth cone
        beam_rad = np.radians(beamwidth)
        theta = np.linspace(sat_az_rad - beam_rad, sat_az_rad + beam_rad, 50)
        r = np.full_like(theta, sat_zenith)
        self.ax_sky.plot(theta, r, 'c-', linewidth=2, alpha=0.6)
        self.ax_sky.fill_between(theta, 0, r, alpha=0.2, color='cyan')

        # Sun path during outages (if any)
        if self.outage_events:
            ts = load.timescale()
            eph = load('de421.bsp')
            earth = eph['earth']
            sun = eph['sun']
            observer = earth + wgs84.latlon(lat, lon, float(self.alt_entry.get()))

            for event in self.outage_events[:10]:  # Plot first 10 events
                t = ts.utc(event['date'].year, event['date'].month, event['date'].day,
                           event['hour'], 0, 0)
                sun_pos = observer.at(t).observe(sun).apparent()
                sun_alt, sun_az, _ = sun_pos.altaz()

                sun_az_rad = sun_az.radians
                sun_zenith = 90 - sun_alt.degrees
                self.ax_sky.plot([sun_az_rad], [sun_zenith], 'yo', markersize=15,
                                 alpha=0.7, markeredgecolor='orange', markeredgewidth=2)

        self.ax_sky.set_theta_zero_location('N')
        self.ax_sky.set_theta_direction(-1)
        self.ax_sky.set_ylim(0, 90)
        self.ax_sky.set_yticks([0, 30, 60, 90])
        self.ax_sky.set_yticklabels(['90°', '60°', '30°', '0°'])
        self.ax_sky.set_title('Sky View (Ground Station)', color='#4ade80',
                              fontsize=12, fontweight='bold', pad=15)
        self.ax_sky.legend(loc='upper right', fontsize=8, facecolor='#1a1a2e',
                           edgecolor='#fbbf24', labelcolor='#ffffff')

        # Outage calendar (heatmap)
        if self.outage_events:
            days_of_year = [event['date'].timetuple().tm_yday for event in self.outage_events]
            hours = [event['hour'] for event in self.outage_events]

            # Create heatmap data
            calendar_data = np.zeros((24, 366))
            for doy, hour in zip(days_of_year, hours):
                calendar_data[hour, doy - 1] = 1

            im = self.ax_calendar.imshow(calendar_data, cmap='hot', aspect='auto',
                                         extent=[1, 366, 24, 0], interpolation='nearest')
            self.ax_calendar.set_title('Outage Calendar', color='#f472b6',
                                       fontsize=12, fontweight='bold')
            self.ax_calendar.set_xlabel('Day of Year', color='#ffffff', fontsize=10)
            self.ax_calendar.set_ylabel('Hour (UTC)', color='#ffffff', fontsize=10)

            # Add colorbar
            cbar = self.fig.colorbar(im, ax=self.ax_calendar, fraction=0.046, pad=0.04)
            cbar.set_label('Outage Risk', color='#ffffff')
            cbar.ax.tick_params(colors='#fcd34d')

        self.ax_calendar.set_facecolor('#1a1a2e')
        self.ax_calendar.tick_params(colors='#fcd34d')

        for ax in [self.ax_main, self.ax_calendar]:
            for spine in ax.spines.values():
                spine.set_color('#fbbf24')

        self.ax_sky.set_facecolor('#1a1a2e')
        self.ax_sky.spines['polar'].set_color('#fbbf24')

        self.canvas.draw()

    def display_outage_events(self):
        """Display outage events in text widget"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)

        if not self.outage_events:
            self.results_text.insert("1.0", "✅ No outages predicted in the analysis period!")
        else:
            header = "╔═══════════════════════════════╗\n"
            header += "║   SUN OUTAGE EVENTS          ║\n"
            header += "╚═══════════════════════════════╝\n\n"
            self.results_text.insert("1.0", header)

            # Group by date
            events_by_date = {}
            for event in self.outage_events:
                date_str = event['date'].strftime('%Y-%m-%d')
                if date_str not in events_by_date:
                    events_by_date[date_str] = []
                events_by_date[date_str].append(event)

            for date_str, events in sorted(events_by_date.items())[:30]:  # Show first 30 days
                self.results_text.insert(tk.END, f"📅 {date_str}\n")
                for event in events:
                    time_str = f"{event['hour']:02d}:00 UTC"
                    sep = event['separation']
                    self.results_text.insert(
                        tk.END,
                        f"   ⚠️ {time_str} | Sep: {sep:.3f}°\n"
                    )
                self.results_text.insert(tk.END, "\n")

            if len(events_by_date) > 30:
                self.results_text.insert(tk.END, f"\n... and {len(events_by_date) - 30} more days with outages\n")

        self.results_text.config(state=tk.DISABLED)

    def start_animation(self):
        """Animate the yearly progression"""
        if self.animation_running or not self.dates:
            return

        self.animation_running = True
        self.animate_btn.config(state=tk.DISABLED)
        self.status_label.config(text="▶️ Animating yearly sun-satellite alignment...")

        # Create animation marker
        self.time_marker, = self.ax_main.plot([], [], 'ro', markersize=12, zorder=10,
                                              label='Current Date')

        # Animation function
        def animate(frame):
            if frame < len(self.dates):
                current_date = self.dates[frame]
                current_sep = self.daily_separations[frame]

                self.time_marker.set_data([current_date], [current_sep])

                date_str = current_date.strftime('%Y-%m-%d')
                self.status_label.config(
                    text=f"▶️ Animating: {date_str} | Separation: {current_sep:.2f}°"
                )

            return self.time_marker,

        self.animation = FuncAnimation(
            self.fig,
            animate,
            frames=len(self.dates),
            interval=50,
            repeat=False,
            blit=True
        )

        self.canvas.draw()

        # Reset after animation
        self.root.after(len(self.dates) * 50 + 500, self.reset_animation)

    def reset_animation(self):
        """Reset animation state"""
        self.animation_running = False
        self.animate_btn.config(state=tk.NORMAL)
        self.status_label.config(text="✅ Animation complete")

    def clear_all(self):
        """Clear all data and plots"""
        self.outage_events = []
        self.daily_separations = []
        self.dates = []

        for ax in [self.ax_main, self.ax_calendar]:
            ax.clear()
            ax.set_facecolor('#1a1a2e')
            ax.grid(True, alpha=0.3, color='#fcd34d')

        self.ax_sky.clear()
        self.ax_sky.set_facecolor('#1a1a2e')

        self.ax_main.set_title('Sun-Satellite Separation Angle Over Time',
                               color='#fbbf24', fontsize=15, fontweight='bold', pad=20)
        self.ax_main.set_xlabel('Date', color='#ffffff', fontsize=12)
        self.ax_main.set_ylabel('Separation Angle (degrees)', color='#ffffff', fontsize=12)

        self.ax_sky.set_title('Sky View (Ground Station)', color='#4ade80',
                              fontsize=12, fontweight='bold', pad=15)
        self.ax_sky.set_theta_zero_location('N')
        self.ax_sky.set_theta_direction(-1)

        self.ax_calendar.set_title('Outage Calendar', color='#f472b6',
                                   fontsize=12, fontweight='bold')
        self.ax_calendar.set_xlabel('Day of Year', color='#ffffff', fontsize=10)
        self.ax_calendar.set_ylabel('Hour (UTC)', color='#ffffff', fontsize=10)

        self.canvas.draw()

        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", "Click 'Predict Outages' to analyze...")
        self.results_text.config(state=tk.DISABLED)

        self.animate_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Cleared | Ready for new analysis")


# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = SunOutagePredictor(root)
    root.mainloop()
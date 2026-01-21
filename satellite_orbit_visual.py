import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from skyfield.api import load, wgs84
from datetime import timedelta
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def fetch_satellite_data(satellite_specs):
    """
    Fetches TLE data for specific satellites from CelesTrak.
    satellite_specs: List of tuples (Name, NORAD_ID)
    """
    satellites = []
    # CelesTrak GP API allows fetching by CATNR (Catalog Number)
    base_url = 'https://celestrak.org/NORAD/elements/gp.php?CATNR={}'

    print("Downloading orbital data...")
    for name, norad_id in satellite_specs:
        try:
            url = base_url.format(norad_id)
            # load.tle_file returns a dictionary of satellites in the file
            sats = load.tle_file(url)
            # Since we queried by specific ID, we take the first (and likely only) value
            sat = list(sats.values())[0]
            sat.name = name  # Ensure the custom name is set
            satellites.append(sat)
            print(f"Loaded: {name} (ID: {norad_id})")
        except Exception as e:
            print(f"Failed to load {name}: {e}")

    return satellites


def calculate_ground_track(satellite, duration_hours=24, interval_minutes=1):
    """
    Propagates the orbit and calculates Latitude/Longitude for a duration.
    """
    ts = load.timescale()
    t0 = ts.now()

    # Generate time points
    minutes = range(0, int(duration_hours * 60), interval_minutes)
    times = [t0 + timedelta(minutes=m) for m in minutes]

    lats = []
    lons = []

    # Vectorized calculation for speed (Skyfield handles lists of times efficiently)
    geocentric = satellite.at(ts.from_datetimes(times))
    subpoint = wgs84.geographic_position_of(geocentric)

    lats = subpoint.latitude.degrees
    lons = subpoint.longitude.degrees

    return lats, lons


def split_track_at_dateline(lats, lons):
    """
    Splits coordinate arrays into segments to prevent horizontal lines
    streaking across the map when crossing the International Date Line (180 to -180).
    """
    threshold = 180  # Degrees difference to consider a wrap

    segments = []
    current_lat_seg = [lats[0]]
    current_lon_seg = [lons[0]]

    for i in range(1, len(lats)):
        # Check if longitude jumped significantly (crossing date line)
        if abs(lons[i] - lons[i - 1]) > threshold:
            # Finish current segment
            segments.append((current_lon_seg, current_lat_seg))
            # Start new segment
            current_lat_seg = [lats[i]]
            current_lon_seg = [lons[i]]
        else:
            current_lat_seg.append(lats[i])
            current_lon_seg.append(lons[i])

    # Append final segment
    segments.append((current_lon_seg, current_lat_seg))
    return segments


class OrbitPlotterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Satellite Ground Track Plotter")
        self.root.geometry("1200x800")

        # 1. Configuration & Data Loading
        self.target_sats_specs = [
            ('GOES-16 (GEO)', 41866),
            ('Landsat 8 (SSO)', 39084)
        ]
        self.satellites = fetch_satellite_data(self.target_sats_specs)

        # 2. GUI Setup
        self.create_widgets()

        # 3. Initial Plot
        self.update_plot()

    def create_widgets(self):
        # --- Control Panel (Left Side) ---
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="Satellites", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # Checkboxes for satellites
        self.sat_vars = {}
        for sat in self.satellites:
            var = tk.BooleanVar(value=True)
            self.sat_vars[sat.name] = var
            chk = ttk.Checkbutton(control_frame, text=sat.name, variable=var, command=self.update_plot)
            chk.pack(anchor=tk.W, pady=2)

        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=15)

        # Slider for Duration
        ttk.Label(control_frame, text="Duration (Hours)", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.duration_var = tk.DoubleVar(value=24)
        self.duration_label = ttk.Label(control_frame, text="24.0 hours")
        self.duration_label.pack(anchor=tk.W)

        self.slider = ttk.Scale(control_frame, from_=1, to=48, orient=tk.HORIZONTAL,
                                variable=self.duration_var, command=self.on_slider_change)
        self.slider.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Refresh Plot", command=self.update_plot).pack(pady=20, fill=tk.X)

        # --- Plot Area (Right Side) ---
        plot_frame = ttk.Frame(self.root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_slider_change(self, value):
        # Update label text only (defer plotting to button or release if expensive,
        # but here we'll just update label and let user click refresh or auto-update)
        hours = float(value)
        self.duration_label.config(text=f"{hours:.1f} hours")
        # Optional: auto-update plot on slide (can be laggy if calculation is slow)
        # self.update_plot()

    def update_plot(self):
        self.fig.clear()

        # Create Cartopy axes
        ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND, facecolor='#e6e6e6')
        ax.add_feature(cfeature.OCEAN, facecolor='#ccf2ff')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)

        colors = {'GOES-16 (GEO)': 'red', 'Landsat 8 (SSO)': 'blue'}
        duration = self.duration_var.get()

        for sat in self.satellites:
            # Check if satellite is enabled via checkbox
            if not self.sat_vars[sat.name].get():
                continue

            lats, lons = calculate_ground_track(sat, duration_hours=duration)
            segments = split_track_at_dateline(lats, lons)
            color = colors.get(sat.name, 'black')

            # Plot Start Point
            ax.plot(lons[0], lats[0], marker='o', color=color, markersize=8,
                    transform=ccrs.PlateCarree(), label=f"{sat.name} Start")

            # Plot Segments
            first_segment = True
            for seg_lon, seg_lat in segments:
                lbl = sat.name if first_segment else "_nolegend_"
                ax.plot(seg_lon, seg_lat, color=color, linewidth=2,
                        transform=ccrs.PlateCarree(), label=lbl)
                first_segment = False

        ax.set_global()
        ax.set_title(f"Ground Track ({duration:.1f} Hours): GEO vs SSO", fontsize=14)
        ax.legend(loc='lower left', frameon=True, framealpha=0.9)
        ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False, linestyle='--', alpha=0.5)

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = OrbitPlotterApp(root)
    root.mainloop()
import numpy as np
import matplotlib.pyplot as plt


def simulate_weather_radar():
    print("--- Weather Radar Data Visualizer (NEXRAD Simulator) ---")

    # --- 1. Define Radar Geometry (The Grid) ---
    # Weather radar scans in Polar Coordinates: Angle (Azimuth) and Distance (Range)
    # A standard sweep might have 360 rays (one per degree) and 1000 range gates.

    azimuths = np.linspace(0, 360, 360)  # 0 to 360 degrees
    max_range = 200.0  # 200 km range
    range_gates = np.linspace(0, max_range, 800)  # 800 bins along each ray

    # Create a 2D Meshgrid for calculations (Angle, Distance)
    # We convert to Radians for numpy math
    az_rad = np.radians(azimuths)
    r_grid, az_grid = np.meshgrid(range_gates, az_rad)

    # --- 2. Generate Synthetic "Storm" Data (Reflectivity Z) ---
    # Reflectivity (dBZ) measures rain intensity.
    # > 50 dBZ = Heavy Hail/Rain
    # 30-50 dBZ = Moderate Rain
    # < 20 dBZ = Light Rain / Clouds / Noise

    # Initialize empty sky (Noise floor around 5 dBZ)
    reflectivity = np.random.normal(5, 2, size=r_grid.shape)

    # Function to add a storm cell (Gaussian blob)
    def add_storm_cell(az_center, r_center, width_az, width_r, intensity):
        # Calculate distance of every point from the storm center
        # Simplified distance metric in polar space
        delta_az = np.abs(az_grid - np.radians(az_center))
        delta_az = np.minimum(delta_az, 2 * np.pi - delta_az)  # Handle 360 wraparound

        dist_sq = (delta_az / np.radians(width_az)) ** 2 + ((r_grid - r_center) / width_r) ** 2

        # Add the storm intensity falling off from the center
        storm_signal = intensity * np.exp(-dist_sq)
        return storm_signal

    # Create a "Supercell" structure
    print("Generating synthetic storm cell...")
    reflectivity += add_storm_cell(45, 100, 15, 20, 55)  # Main Core (Heavy)
    reflectivity += add_storm_cell(35, 90, 20, 30, 35)  # Anvil/Rain shield
    reflectivity += add_storm_cell(60, 110, 10, 10, 45)  # Flanking line

    # --- 3. Add "Ground Clutter" (Noise) ---
    # Radar picks up buildings and mountains near the station (center)
    print("Adding ground clutter and noise...")
    clutter_mask = r_grid < 20.0  # Everything within 20km
    reflectivity[clutter_mask] += np.random.normal(30, 5, size=np.sum(clutter_mask))

    # --- 4. Filter Data (Meteorological Quality Control) ---
    # A simple threshold filter to remove noise
    THRESHOLD_DBZ = 20.0

    # Mask data for plotting (Hide values below threshold)
    reflectivity_masked = np.ma.masked_where(reflectivity < THRESHOLD_DBZ, reflectivity)

    # --- 5. Visualization (PPI - Plan Position Indicator) ---
    fig = plt.figure(figsize=(14, 6))

    # PLOT 1: Raw Data (Polar Plot)
    ax1 = fig.add_subplot(121, projection='polar')
    ax1.set_title(f"Raw Radar Return\n(Includes Ground Clutter)", fontweight='bold')

    # pcolormesh is used for radar plots.
    # vmin/vmax set standard NWS colors (0 to 70 dBZ)
    mesh1 = ax1.pcolormesh(az_rad, range_gates, reflectivity, cmap='pyart_Theodore16', vmin=0, vmax=70, shading='auto')
    # Note: 'pyart_Theodore16' is standard, but if missing, matplotlib falls back or we use 'jet'/'nipy_spectral'
    # Let's use 'nipy_spectral' which looks very "weather-like" if pyart isn't installed.
    mesh1.set_cmap('nipy_spectral')

    ax1.set_theta_zero_location('N')  # North up
    ax1.set_theta_direction(-1)  # Clockwise
    ax1.grid(True, alpha=0.3)

    # PLOT 2: Filtered Data
    ax2 = fig.add_subplot(122, projection='polar')
    ax2.set_title(f"Meteorological Mode\n(Filter > {THRESHOLD_DBZ} dBZ)", fontweight='bold')

    mesh2 = ax2.pcolormesh(az_rad, range_gates, reflectivity_masked, cmap='nipy_spectral', vmin=0, vmax=70,
                           shading='auto')

    ax2.set_theta_zero_location('N')
    ax2.set_theta_direction(-1)
    ax2.grid(True, alpha=0.3)

    # Colorbar
    cbar = plt.colorbar(mesh2, ax=[ax1, ax2], orientation='horizontal', fraction=0.05, pad=0.1)
    cbar.set_label('Reflectivity (dBZ)')

    print("Displaying Radar Scope...")
    plt.show()


if __name__ == "__main__":
    simulate_weather_radar()
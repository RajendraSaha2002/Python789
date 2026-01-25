import psycopg2
import time
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sgp4.api import Satrec
from sgp4.api import jday
import datetime
import numpy as np

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'orbital_uplink_db',
    'port': 5432
}


def get_satellites():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, name, tle_line1, tle_line2 FROM satellites")
    data = cur.fetchall()
    conn.close()
    return data


def update_telemetry(sat_id, lat, lon, alt):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Upsert (Insert or Update)
        sql = """
              INSERT INTO live_telemetry (satellite_id, current_lat, current_lon, current_alt_km)
              VALUES (%s, %s, %s, %s) ON CONFLICT (satellite_id) 
            DO \
              UPDATE SET current_lat=EXCLUDED.current_lat, \
                  current_lon=EXCLUDED.current_lon, \
                  current_alt_km=EXCLUDED.current_alt_km, \
                  last_updated=NOW() \
              """
        cur.execute(sql, (sat_id, lat, lon, alt))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")


def run_tracker():
    print("--- ORBITAL TRACKER ENGINE ONLINE ---")

    # Setup Plot
    plt.ion()
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Earth Sphere
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x_earth = 6371 * np.outer(np.cos(u), np.sin(v))
    y_earth = 6371 * np.outer(np.sin(u), np.sin(v))
    z_earth = 6371 * np.outer(np.ones(np.size(u)), np.cos(v))

    while True:
        sats = get_satellites()
        ax.clear()
        # Draw Earth (Wireframe for speed)
        ax.plot_wireframe(x_earth, y_earth, z_earth, color='blue', alpha=0.1)
        ax.set_title("Real-Time Satellite Constellation")

        current_time = datetime.datetime.utcnow()
        jd, fr = jday(current_time.year, current_time.month, current_time.day,
                      current_time.hour, current_time.minute, current_time.second)

        for sat in sats:
            sid, name, l1, l2 = sat
            satellite = Satrec.twoline2rv(l1, l2)
            e, r, v_vec = satellite.sgp4(jd, fr)

            if e == 0:
                # SGP4 returns position in km (ECI coordinates roughly)
                x, y, z = r

                # Simple conversion ECI to Geodetic (Lat/Lon) - Approximation
                # In real app, use pyproj or skyfield
                # r_mag = math.sqrt(x*x + y*y + z*z)
                # lat = math.degrees(math.asin(z / r_mag))
                # lon = math.degrees(math.atan2(y, x))
                # For demo visualization, we just plot X,Y,Z
                # But we need Lat/Lon for Java logic.
                # Let's fake a "scan" by adding rotation to simulate earth spin relative to sat

                # Simplified Physics for Demo:
                # We will output the X/Y/Z directly for visualization
                # And a calculated Lat/Lon for the DB

                r_km = math.sqrt(x ** 2 + y ** 2 + z ** 2)
                lat = math.degrees(math.asin(z / r_km))
                # Account for earth rotation (Greenwich Hour Angle) roughly
                t_ut = (current_time.hour * 3600 + current_time.minute * 60 + current_time.second) / 86400.0
                gst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + t_ut * 360) % 360
                lon = (math.degrees(math.atan2(y, x)) - gst) % 360
                if lon > 180: lon -= 360

                alt = r_km - 6371

                # Update DB
                update_telemetry(sid, lat, lon, alt)

                # Plot
                ax.scatter(x, y, z, color='red', s=50)
                ax.text(x, y, z, name, color='black')

                print(f"Updated {name}: Lat {lat:.2f}, Lon {lon:.2f}, Alt {alt:.0f}km")

        plt.draw()
        plt.pause(1.0)  # 1 sec update rate


if __name__ == "__main__":
    run_tracker()
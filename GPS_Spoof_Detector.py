import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from datetime import datetime
from geopy.distance import geodesic

# --- Configuration ---
st.set_page_config(page_title="GPS Integrity Monitor", layout="wide", page_icon="📡")

# Physics Limits
MAX_POSSIBLE_SPEED_MS = 50.0  # ~110 mph (Drone Top Speed)
SIMULATION_STEP = 1.0  # Seconds per tick


# --- Logic Core: The Drone Monitor ---

class DroneMonitor:
    def __init__(self):
        # State History
        self.history = []
        self.status = "NOMINAL"
        self.nav_source = "GPS (SATELLITE)"
        self.last_valid_pos = (36.1699, -115.1398)  # Start near Las Vegas
        self.last_valid_velocity = (0.0001, 0.0001)  # Lat/Lon delta per tick
        self.spoof_detected_at = None

    def process_telemetry(self, input_lat, input_lon, timestamp):
        """
        The Sanity Check Engine.
        Compares incoming GPS data against physics constraints.
        """
        current_pos = (input_lat, input_lon)

        # 1. Physics Calculation
        # Calculate distance from last VALID position
        distance_m = geodesic(self.last_valid_pos, current_pos).meters

        # Calculate implied speed
        implied_speed = distance_m / SIMULATION_STEP

        # 2. Logic Gate (The Integrity Check)
        is_spoofed = False

        if implied_speed > MAX_POSSIBLE_SPEED_MS:
            is_spoofed = True
            self.status = "CRITICAL: GPS SPOOFING DETECTED"
            self.nav_source = "INS (INERTIAL BACKUP)"
            if not self.spoof_detected_at:
                self.spoof_detected_at = timestamp
        else:
            # Signal is valid
            self.status = "NOMINAL"
            self.nav_source = "GPS (SATELLITE)"
            self.last_valid_pos = current_pos
            # Update velocity vector for INS extrapolation
            if len(self.history) > 0:
                prev_lat = self.history[-1]['lat']
                prev_lon = self.history[-1]['lon']
                self.last_valid_velocity = (input_lat - prev_lat, input_lon - prev_lon)

        # 3. Determine Output Position
        if is_spoofed:
            # REJECT GPS. USE INS EXTRAPOLATION.
            # Dead Reckoning: Pos = Last_Valid + Velocity
            ins_lat = self.last_valid_pos[0] + self.last_valid_velocity[0]
            ins_lon = self.last_valid_pos[1] + self.last_valid_velocity[1]

            # Update internal state for next calculation
            self.last_valid_pos = (ins_lat, ins_lon)

            output_data = {
                'time': timestamp,
                'lat': ins_lat,
                'lon': ins_lon,
                'raw_gps_lat': input_lat,  # Log the fake data for analysis
                'raw_gps_lon': input_lon,
                'speed': implied_speed,
                'source': 'INS',
                'alert': True
            }
        else:
            # ACCEPT GPS.
            output_data = {
                'time': timestamp,
                'lat': input_lat,
                'lon': input_lon,
                'raw_gps_lat': input_lat,
                'raw_gps_lon': input_lon,
                'speed': implied_speed,
                'source': 'GPS',
                'alert': False
            }

        self.history.append(output_data)
        return output_data


# --- Streamlit Application ---

def main():
    # Sidebar Controls
    st.sidebar.title("Simulation Controls")

    # Session State Initialization
    if 'monitor' not in st.session_state:
        st.session_state['monitor'] = DroneMonitor()
        st.session_state['tick'] = 0
        st.session_state['simulation_running'] = False
        st.session_state['spoof_active'] = False

    # Controls
    if st.sidebar.button("▶ START / RESUME"):
        st.session_state['simulation_running'] = True

    if st.sidebar.button("⏸ PAUSE"):
        st.session_state['simulation_running'] = False

    if st.sidebar.button("🔄 RESET"):
        st.session_state['monitor'] = DroneMonitor()
        st.session_state['tick'] = 0
        st.session_state['simulation_running'] = False
        st.session_state['spoof_active'] = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Electronic Warfare")

    if st.sidebar.checkbox("Activate GPS Spoofer", value=st.session_state['spoof_active']):
        st.session_state['spoof_active'] = True
        st.sidebar.error("TRANSMITTING FAKE GPS SIGNALS")
    else:
        st.session_state['spoof_active'] = False

    # --- Main Dashboard ---

    st.title("🛰️ Navigation Integrity Dashboard")

    # Metric Row
    monitor = st.session_state['monitor']
    latest = monitor.history[-1] if monitor.history else None

    col1, col2, col3 = st.columns(3)

    status_color = "normal"
    if monitor.status.startswith("CRITICAL"): status_color = "inverse"

    col1.metric("System Status", monitor.status, delta_color=status_color)
    col2.metric("Nav Source", monitor.nav_source)

    speed_val = f"{latest['speed']:.1f} m/s" if latest else "0.0 m/s"
    col3.metric("Measured GPS Velocity", speed_val)

    # Alerts
    if monitor.status.startswith("CRITICAL"):
        st.error(
            f"🚨 INTEGRITY FAILURE: Implied velocity exceeds physics model ({latest['speed']:.1f} m/s). Switching to Inertial Hold.")

    # --- Simulation Loop Logic ---

    if st.session_state['simulation_running']:
        time.sleep(0.5)  # Simulate tick rate
        st.session_state['tick'] += 1

        # 1. Generate "True" Path (Drone flying North-East)
        # Base Lat/Lon + Velocity
        tick = st.session_state['tick']
        true_lat = 36.1699 + (tick * 0.0001)
        true_lon = -115.1398 + (tick * 0.0001)

        # 2. Apply Spoofing (If Active)
        if st.session_state['spoof_active']:
            # Spoofer sends coordinates for Area 51 (miles away)
            # Or erratic jumps
            input_lat = 37.2343 + (np.random.normal(0, 0.01))
            input_lon = -115.8067 + (np.random.normal(0, 0.01))
        else:
            # Normal GPS has slight noise
            input_lat = true_lat + np.random.normal(0, 0.00001)
            input_lon = true_lon + np.random.normal(0, 0.00001)

        # 3. Process Data
        monitor.process_telemetry(input_lat, input_lon, tick)

        # Force refresh to update UI
        st.rerun()

    # --- Visualization ---

    if monitor.history:
        df = pd.DataFrame(monitor.history)

        # Map Visualization
        # We plot two traces: The Raw GPS input (what the antenna hears) and the Filtered Output (what the autopilot uses)

        # Create separate dataframes for plotting
        df_nav = df[['lat', 'lon', 'source', 'time']].copy()
        df_nav['Type'] = 'Approved Nav Solution'

        df_raw = df[['raw_gps_lat', 'raw_gps_lon', 'source', 'time']].copy()
        df_raw.columns = ['lat', 'lon', 'source', 'time']
        df_raw['Type'] = 'Raw GPS Input'

        # Only show Raw trace if it differs (during spoofing)
        df_combined = pd.concat([df_nav, df_raw])

        fig = px.scatter_mapbox(
            df_combined,
            lat="lat",
            lon="lon",
            color="Type",
            hover_data=["time", "source"],
            color_discrete_map={'Approved Nav Solution': 'green', 'Raw GPS Input': 'red'},
            zoom=12,
            height=500
        )

        fig.update_layout(mapbox_style="carto-darkmatter")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

        st.plotly_chart(fig, use_container_width=True)

        # Data Table
        with st.expander("Telemetry Log"):
            st.dataframe(df.tail(10))


if __name__ == "__main__":
    main()
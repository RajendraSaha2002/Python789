import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy.fft import fft, fftfreq
import plotly.graph_objects as go
import plotly.express as px
import time

# --- Configuration ---
st.set_page_config(page_title="HUMS: Armored Vehicle Maintenance", layout="wide", page_icon="🛡️")

VEHICLES = ['TANK-Alpha (M1)', 'APC-Bravo (Stryker)', 'IFV-Charlie (Bradley)', 'TANK-Delta (Leopard)',
            'LOG-Echo (Truck)']
SENSORS = ['Engine RPM', 'Oil Temp (C)', 'Vibration (RMS)', 'Hydraulic Pressure (PSI)']


# --- 1. Data Simulation Engine ---

@st.cache_data
def generate_fleet_data():
    """
    Generates synthetic telemetry data for a fleet of 5 vehicles over 100 operational hours.
    Injects specific faults into 'TANK-Alpha' and 'IFV-Charlie'.
    """
    fleet_data = {}

    # 100 Hours of data, sampled every minute
    periods = 100 * 60
    time_index = pd.date_range(start='2024-01-01', periods=periods, freq='min')

    for v_id in VEHICLES:
        # Base normal behavior
        rpm = np.random.normal(2200, 50, periods)
        temp = np.random.normal(85, 2, periods)
        vib = np.random.normal(0.5, 0.05, periods)  # g-force RMS
        pressure = np.random.normal(2500, 10, periods)

        # --- Fault Injection ---

        # Scenario A: TANK-Alpha has a cooling failure starting at hour 60
        if v_id == 'TANK-Alpha (M1)':
            # Temperature drifts upwards linearly after index 3600
            start_fault = 60 * 60
            drift = np.linspace(0, 40, periods - start_fault)
            temp[start_fault:] += drift

            # Vibration spikes randomly (loose parts)
            spike_indices = np.random.choice(range(start_fault, periods), size=50)
            vib[spike_indices] += 2.0

        # Scenario B: IFV-Charlie has a bearing fault (High Vibration) starting at hour 40
        elif v_id == 'IFV-Charlie (Bradley)':
            start_fault = 40 * 60
            # Vibration RMS gradually increases
            vib[start_fault:] += np.linspace(0, 1.5, periods - start_fault)

        df = pd.DataFrame({
            'Timestamp': time_index,
            'Engine RPM': rpm,
            'Oil Temp (C)': temp,
            'Vibration (RMS)': vib,
            'Hydraulic Pressure (PSI)': pressure,
            'Vehicle ID': v_id
        })

        fleet_data[v_id] = df

    return fleet_data


def generate_high_freq_vibration_snapshot(condition="Normal"):
    """
    Generates a 1-second 'burst' of high-frequency raw vibration data (not RMS).
    Used for FFT Analysis to detect specific frequencies (50Hz = Bearing Fault).
    """
    fs = 1000  # Sampling rate 1000 Hz
    t = np.linspace(0, 1, fs)

    # Base Noise
    signal = np.random.normal(0, 0.1, fs)

    if condition == "Normal":
        # Normal engine hum at 20Hz
        signal += 0.5 * np.sin(2 * np.pi * 20 * t)

    elif condition == "Overheating":
        # Just louder noise, no specific frequency spike
        signal += 0.8 * np.sin(2 * np.pi * 20 * t)
        signal += np.random.normal(0, 0.3, fs)

    elif condition == "Bearing Fault":
        # Normal engine hum
        signal += 0.5 * np.sin(2 * np.pi * 20 * t)
        # DISTINCT SPIKE at 50Hz (Bearing characteristic frequency)
        signal += 2.0 * np.sin(2 * np.pi * 50 * t)
        # Harmonics
        signal += 0.5 * np.sin(2 * np.pi * 100 * t)

    return t, signal


# --- 2. Analytics Engine ---

def calculate_rul(df, current_temp, current_vib):
    """
    Simple rule-based Remaining Useful Life (RUL) estimator.
    """
    # Max safe limits
    max_temp = 110
    max_vib = 1.5

    health_score = 100

    # Penalize for Temperature
    if current_temp > 90:
        health_score -= (current_temp - 90) * 2

    # Penalize for Vibration
    if current_vib > 0.8:
        health_score -= (current_vib - 0.8) * 40

    # RUL is roughly proportional to Health Score, but decays faster
    rul_hours = max(0, health_score * 5)  # Arbitrary mapping 100 health -> 500 hours

    return int(rul_hours), health_score


def train_anomaly_detector(df):
    """
    Trains an Isolation Forest on the first 20% of data (assumed healthy).
    Returns the model to predict on the rest.
    """
    # Use first 20 hours as baseline
    baseline = df.iloc[:1200][['Engine RPM', 'Oil Temp (C)', 'Vibration (RMS)']]

    model = IsolationForest(contamination=0.01, random_state=42)
    model.fit(baseline)
    return model


# --- 3. Dashboard Interface ---

def main():
    # Header
    st.title("🛡️ HUMS: Armored Vehicle Health Monitoring")
    st.markdown("### Regiment 7 - Logistics & Maintenance Command")

    # Load Data
    fleet_data = generate_fleet_data()

    # Sidebar
    st.sidebar.header("Fleet Control")
    selected_vehicle = st.sidebar.selectbox("Select Asset ID", VEHICLES)

    df = fleet_data[selected_vehicle]

    # --- Top Level Metrics ---
    # Get latest values
    latest = df.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    # RUL Calculation
    rul, health = calculate_rul(df, latest['Oil Temp (C)'], latest['Vibration (RMS)'])

    # Determine Status
    if health > 80:
        status = "OPERATIONAL"
        status_color = "green"
    elif health > 40:
        status = "WARNING"
        status_color = "orange"
    else:
        status = "CRITICAL FAILURE"
        status_color = "red"

    with col1:
        st.metric("Status", status, delta_color="off")
    with col2:
        st.metric("Remaining Useful Life (RUL)", f"{rul} Hours", delta=f"{health - 100:.1f} Health Score")
    with col3:
        st.metric("Current Oil Temp", f"{latest['Oil Temp (C)']:.1f} °C", delta=f"{latest['Oil Temp (C)'] - 85:.1f}")
    with col4:
        st.metric("Vibration Level", f"{latest['Vibration (RMS)']:.2f} G",
                  delta=f"{latest['Vibration (RMS)'] - 0.5:.2f}")

    st.markdown(f"**Asset Condition:** :{status_color}[{status}]")

    # --- Tabbed View ---
    tab1, tab2, tab3 = st.tabs(["📉 Sensor Telemetry", "🔍 Vibration Analysis (FFT)", "🤖 Anomaly Detection"])

    # TAB 1: Time Series Plots
    with tab1:
        st.subheader(f"Telemetry History: {selected_vehicle}")

        # Interactive Plotly Chart
        fig = px.line(df, x='Timestamp', y=['Oil Temp (C)', 'Vibration (RMS)'],
                      title="Temperature & Vibration Trends (100 Hours)")

        # Add visual threshold lines
        fig.add_hline(y=110, line_dash="dash", line_color="red", annotation_text="Max Temp Limit")
        fig.add_hline(y=1.5, line_dash="dash", line_color="orange", annotation_text="Vibration Warning")

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("View Raw Data Log"):
            st.dataframe(df.tail(100))

    # TAB 2: FFT Analysis
    with tab2:
        col_fft_1, col_fft_2 = st.columns([1, 2])

        with col_fft_1:
            st.markdown("#### Diagnostic Tool")
            st.info(
                "The HUMS system captures high-frequency vibration snapshots to identify specific component failures.")

            # Simulate fetching a "burst" of data based on current vehicle condition
            condition = "Normal"
            if "TANK-Alpha" in selected_vehicle and latest['Oil Temp (C)'] > 100:
                condition = "Overheating"
            elif "IFV-Charlie" in selected_vehicle and latest['Vibration (RMS)'] > 1.0:
                condition = "Bearing Fault"

            st.write(f"**Detected Signature:** {condition}")

            if st.button("Run FFT Analysis"):
                with st.spinner("Acquiring 1000Hz Signal... Performing Fast Fourier Transform..."):
                    time.sleep(1)  # Simulate processing time
                    t, signal = generate_high_freq_vibration_snapshot(condition)

                    # FFT Calculation
                    N = len(signal)
                    yf = fft(signal)
                    xf = fftfreq(N, 1 / 1000)[:N // 2]

                    # Plot Frequency Domain
                    fig_fft = go.Figure()
                    fig_fft.add_trace(go.Scatter(x=xf, y=2.0 / N * np.abs(yf[0:N // 2]), mode='lines', name='Spectrum'))
                    fig_fft.update_layout(title="Frequency Spectrum (Hz)", xaxis_title="Frequency (Hz)",
                                          yaxis_title="Amplitude")

                    # Highlight 50Hz (Bearing Fault Freq)
                    fig_fft.add_vline(x=50, line_dash="dot", line_color="red",
                                      annotation_text="Bearing Cage Freq (50Hz)")

                    col_fft_2.plotly_chart(fig_fft, use_container_width=True)

                    if condition == "Bearing Fault":
                        col_fft_1.error("CRITICAL: High Amplitude at 50Hz indicates inner race bearing wear.")

    # TAB 3: Machine Learning Anomaly Detection
    with tab3:
        st.subheader("Unsupervised Anomaly Detection (Isolation Forest)")

        if st.button("Train & Scan Model"):
            with st.spinner("Training model on initial 20 hours... Scanning recent telemetry..."):
                # Prepare data
                features = ['Engine RPM', 'Oil Temp (C)', 'Vibration (RMS)']
                model = train_anomaly_detector(df)

                df['Anomaly_Score'] = model.decision_function(df[features])
                df['Anomaly'] = model.predict(df[features])  # -1 is anomaly, 1 is normal

                # Plot
                anomalies = df[df['Anomaly'] == -1]

                fig_anom = px.scatter(df, x='Timestamp', y='Oil Temp (C)', color='Anomaly',
                                      color_discrete_map={1: 'blue', -1: 'red'},
                                      title="Anomaly Detection Results (Red = Anomalous Behavior)")

                st.plotly_chart(fig_anom, use_container_width=True)

                st.warning(f"Model detected {len(anomalies)} anomalous data points.")
                st.dataframe(anomalies.tail(5))


if __name__ == "__main__":
    main()
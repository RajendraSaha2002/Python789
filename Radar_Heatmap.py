import sys
import io
import random
import datetime
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import folium
from folium.plugins import HeatMap, MousePosition

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider,
                             QGroupBox, QFrame, QSpinBox, QFileDialog, QMessageBox, QTextEdit)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt


# --- 1. Mock Data Generator ---

class DataGenerator:
    @staticmethod
    def generate_mock_data(num_points=500):
        """
        Generates synthetic radar detections.
        Creates 3 distinct 'Enemy Batteries' (clusters) and some random noise.
        """
        # Base location (e.g., Donbas region approx coords for realism context)
        base_lat = 48.0
        base_lon = 37.0

        data = []
        now = datetime.datetime.now()

        # Define 3 Battery Locations (Lat, Lon)
        batteries = [
            (base_lat + 0.05, base_lon + 0.05),
            (base_lat - 0.03, base_lon - 0.04),
            (base_lat + 0.08, base_lon - 0.02)
        ]

        for _ in range(num_points):
            # 80% chance to come from a battery (Cluster), 20% random noise
            if random.random() < 0.8:
                center = random.choice(batteries)
                # Add Gaussian noise (firing dispersion error)
                lat = center[0] + np.random.normal(0, 0.005)
                lon = center[1] + np.random.normal(0, 0.005)
            else:
                # Random noise across the sector
                lat = base_lat + random.uniform(-0.1, 0.1)
                lon = base_lon + random.uniform(-0.1, 0.1)

            # Random timestamp within last 24 hours
            hours_ago = random.uniform(0, 24)
            ts = now - datetime.timedelta(hours=hours_ago)

            data.append({
                'Latitude': lat,
                'Longitude': lon,
                'Timestamp': ts,
                'Hours_Ago': hours_ago
            })

        return pd.DataFrame(data)


# --- 2. Analytics Engine ---

class IntelAnalyst:
    def __init__(self, df):
        self.df = df
        self.filtered_df = df
        self.clusters = []

    def filter_by_time(self, max_hours_ago):
        """Filters dataframe for events within the last X hours."""
        self.filtered_df = self.df[self.df['Hours_Ago'] <= max_hours_ago].copy()
        return len(self.filtered_df)

    def detect_clusters(self, k=3):
        """
        Uses K-Means Clustering to find the geometric center of enemy batteries.
        """
        if len(self.filtered_df) < k:
            return []

        coords = self.filtered_df[['Latitude', 'Longitude']].values
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(coords)

        self.clusters = kmeans.cluster_centers_
        return self.clusters


# --- 3. GUI Application ---

class RadarHeatmapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Counter-Battery Radar Analysis Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #EEE; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: #EEE; }
        """)

        # Data Logic
        self.raw_data = DataGenerator.generate_mock_data()
        self.engine = IntelAnalyst(self.raw_data)

        self.init_ui()
        self.update_map()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QHBoxLayout(main)

        # --- LEFT SIDEBAR (Controls) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background-color: #333; border-right: 1px solid #444;")
        sb_layout = QVBoxLayout(sidebar)

        # 1. Header
        lbl_title = QLabel("TACTICAL INTEL\nDASHBOARD")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff5555; margin-bottom: 10px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(lbl_title)

        # 2. Data Controls
        grp_data = QGroupBox("Data Source")
        d_layout = QVBoxLayout(grp_data)

        self.lbl_count = QLabel(f"Total Detections: {len(self.raw_data)}")
        d_layout.addWidget(self.lbl_count)

        btn_regen = QPushButton("Simulate New Radar Data")
        btn_regen.clicked.connect(self.regenerate_data)
        btn_regen.setStyleSheet("background-color: #444; color: white; padding: 5px;")
        d_layout.addWidget(btn_regen)
        sb_layout.addWidget(grp_data)

        # 3. Time Filter
        grp_time = QGroupBox("Time Filter")
        t_layout = QVBoxLayout(grp_time)

        self.lbl_time = QLabel("Show: Last 24 Hours")
        t_layout.addWidget(self.lbl_time)

        self.slider_time = QSlider(Qt.Horizontal)
        self.slider_time.setRange(1, 24)
        self.slider_time.setValue(24)
        self.slider_time.valueChanged.connect(self.update_time_filter)
        t_layout.addWidget(self.slider_time)
        sb_layout.addWidget(grp_time)

        # 4. Analytics (K-Means)
        grp_ai = QGroupBox("Cluster Detection (AI)")
        a_layout = QVBoxLayout(grp_ai)

        h_spin = QHBoxLayout()
        h_spin.addWidget(QLabel("Est. Batteries:"))
        self.spin_k = QSpinBox()
        self.spin_k.setRange(1, 10)
        self.spin_k.setValue(3)
        h_spin.addWidget(self.spin_k)
        a_layout.addLayout(h_spin)

        self.btn_detect = QPushButton("RUN K-MEANS ANALYSIS")
        self.btn_detect.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 10px;")
        self.btn_detect.clicked.connect(self.run_analysis)
        a_layout.addWidget(self.btn_detect)
        sb_layout.addWidget(grp_ai)

        # 5. Export
        sb_layout.addStretch()

        self.txt_report = QTextEdit()
        self.txt_report.setPlaceholderText("Analysis results will appear here...")
        self.txt_report.setMaximumHeight(150)
        self.txt_report.setStyleSheet(
            "font-family: monospace; font-size: 10px; background-color: #222; border: 1px solid #555;")
        sb_layout.addWidget(self.txt_report)

        btn_export = QPushButton("EXPORT TARGET LIST")
        btn_export.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px;")
        btn_export.clicked.connect(self.export_data)
        sb_layout.addWidget(btn_export)

        layout.addWidget(sidebar)

        # --- RIGHT SIDE (Map) ---
        self.map_view = QWebEngineView()
        layout.addWidget(self.map_view)

    # --- LOGIC ---

    def regenerate_data(self):
        self.raw_data = DataGenerator.generate_mock_data()
        self.engine = IntelAnalyst(self.raw_data)
        self.lbl_count.setText(f"Total Detections: {len(self.raw_data)}")
        self.update_time_filter()  # Triggers map update

    def update_time_filter(self):
        hours = self.slider_time.value()
        self.lbl_time.setText(f"Show: Last {hours} Hours")
        count = self.engine.filter_by_time(hours)
        self.lbl_count.setText(f"Active Points: {count} / {len(self.raw_data)}")
        self.update_map(show_clusters=False)

    def run_analysis(self):
        k = self.spin_k.value()
        centers = self.engine.detect_clusters(k)

        # Update Report
        report = "--- TARGET ACQUISITION REPORT ---\n"
        report += datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
        for i, (lat, lon) in enumerate(centers):
            report += f"TGT-{i + 1:02d}: {lat:.5f}, {lon:.5f}\n"

        self.txt_report.setText(report)
        self.update_map(show_clusters=True)

    def export_data(self):
        content = self.txt_report.toPlainText()
        if not content:
            QMessageBox.warning(self, "No Data", "Run analysis first.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "target_list.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w") as f:
                f.write(content)
            QMessageBox.information(self, "Export", "Intel report saved successfully.")

    def update_map(self, show_clusters=False):
        """Generates the Folium map HTML."""
        df = self.engine.filtered_df

        if df.empty:
            center_lat, center_lon = 48.0, 37.0
        else:
            center_lat = df['Latitude'].mean()
            center_lon = df['Longitude'].mean()

        # 1. Base Map (Dark Theme for military look)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='CartoDB dark_matter',
            control_scale=True
        )

        # 2. Heatmap Layer
        # Data format for HeatMap: [[lat, lon, weight], ...]
        heat_data = df[['Latitude', 'Longitude']].values.tolist()
        HeatMap(heat_data, radius=15, blur=20, min_opacity=0.4).add_to(m)

        # 3. Add Clusters (if analyzed)
        if show_clusters:
            for i, (lat, lon) in enumerate(self.engine.clusters):
                # Marker
                folium.Marker(
                    [lat, lon],
                    tooltip=f"TGT-{i + 1:02d} (CONFIRMED)",
                    icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
                ).add_to(m)

                # Accuracy Radius Ring
                folium.Circle(
                    location=[lat, lon],
                    radius=500,  # meters
                    color='red',
                    fill=False,
                    weight=2,
                    dash_array='5, 5'
                ).add_to(m)

        # 4. Mouse Position Tool
        formatter = "function(num) {return L.Util.formatNum(num, 5);};"
        MousePosition(
            position='topright',
            separator=' | ',
            empty_string='NaN',
            lng_first=False,
            num_digits=20,
            prefix='MGRS Coords: ',
            lat_formatter=formatter,
            lng_formatter=formatter,
        ).add_to(m)

        # 5. Render to Widget
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.map_view.setHtml(data.getvalue().decode())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarHeatmapApp()
    window.show()
    sys.exit(app.exec_())
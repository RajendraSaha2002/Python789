import sys
import io
import json
import math
import numpy as np
import folium
from folium.plugins import MousePosition

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl

# --- Configuration ---
DEFAULT_LAT = 25.0
DEFAULT_LON = -71.0  # Bermuda Triangle area (Classic ASW training zone)
ZOOM_START = 8


# --- Geospatial Logic Engine ---

class GeoMath:
    @staticmethod
    def get_points_on_line(start_coords, end_coords, spacing_nm):
        """
        Generates GPS points along a line segment.
        start_coords: (lat, lon)
        spacing_nm: Nautical Miles between buoys
        """
        lat1, lon1 = map(math.radians, start_coords)
        lat2, lon2 = map(math.radians, end_coords)

        # Earth Radius in NM
        R = 3440.06

        # Total Distance (Haversine)
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        total_dist_nm = R * c

        if total_dist_nm == 0: return []

        num_buoys = int(total_dist_nm / spacing_nm)
        if num_buoys < 2: num_buoys = 2  # Minimum start and end

        points = []

        # Interpolate
        for i in range(num_buoys + 1):
            fraction = i / num_buoys
            # Simple linear interpolation for short tactical distances (Flat earth approx is ok for <100nm)
            # For high precision over long distances, intermediate bearing calc is needed.
            # Using simple lerp for simplicity/speed in demo.

            # Convert back to degrees for output
            i_lat = start_coords[0] + (end_coords[0] - start_coords[0]) * fraction
            i_lon = start_coords[1] + (end_coords[1] - start_coords[1]) * fraction
            points.append((i_lat, i_lon))

        return points

    @staticmethod
    def get_box_pattern(p1, p2):
        """
        Generates 5-point Dice Pattern (Corners + Center).
        p1: Top-Left (Lat, Lon)
        p2: Bottom-Right (Lat, Lon)
        """
        lat1, lon1 = p1
        lat2, lon2 = p2

        # Corners
        # P1 is one corner, P2 is opposite corner.
        # We need the other two.
        # C1 = (lat1, lon1)
        # C2 = (lat1, lon2)
        # C3 = (lat2, lon2)
        # C4 = (lat2, lon1)

        corners = [
            (lat1, lon1),  # Top-Left
            (lat1, lon2),  # Top-Right
            (lat2, lon2),  # Bottom-Right
            (lat2, lon1)  # Bottom-Left
        ]

        # Center
        center = ((lat1 + lat2) / 2, (lon1 + lon2) / 2)

        return corners + [center]


# --- GUI Application ---

class SonobuoyPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASW MISSION PLANNER: SONOBUOY PATTERN GENERATOR")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #2b2b2b; color: #EEE; font-family: Consolas;")

        # State
        self.clicks = []  # Stores (lat, lon) clicks
        self.generated_points = []  # Stores final drop points
        self.pattern_type = "Linear Barrier"

        self.init_ui()
        self.render_map()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT PANEL: CONTROLS ---
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(350)
        ctrl_panel.setStyleSheet("background-color: #333; border-right: 1px solid #555;")
        vbox = QVBoxLayout(ctrl_panel)

        # Header
        lbl_h = QLabel("DEPLOYMENT SETTINGS")
        lbl_h.setStyleSheet("font-size: 18px; font-weight: bold; color: #4fc3f7; border-bottom: 2px solid #4fc3f7;")
        vbox.addWidget(lbl_h)

        # Pattern Selector
        vbox.addWidget(QLabel("Select Pattern:"))
        self.combo_pat = QComboBox()
        self.combo_pat.addItems(["Linear Barrier", "Box Search (Dice-5)"])
        self.combo_pat.currentTextChanged.connect(self.update_pattern_mode)
        vbox.addWidget(self.combo_pat)

        # Spacing Input (Linear only)
        self.lbl_space = QLabel("Spacing (NM):")
        vbox.addWidget(self.lbl_space)
        self.spin_space = QSpinBox()
        self.spin_space.setRange(1, 50)
        self.spin_space.setValue(5)
        vbox.addWidget(self.spin_space)

        # Instructions
        self.lbl_status = QLabel("STATUS: AWAITING INPUT\nClick MAP to set Point A.")
        self.lbl_status.setStyleSheet("color: #FFD700; font-weight: bold; padding: 10px; border: 1px dashed #777;")
        vbox.addWidget(self.lbl_status)

        # Actions
        btn_layout = QHBoxLayout()
        btn_gen = QPushButton("GENERATE DROPS")
        btn_gen.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 10px;")
        btn_gen.clicked.connect(self.generate_pattern)

        btn_reset = QPushButton("RESET MAP")
        btn_reset.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 10px;")
        btn_reset.clicked.connect(self.reset_map)

        btn_layout.addWidget(btn_gen)
        btn_layout.addWidget(btn_reset)
        vbox.addLayout(btn_layout)

        # Results Table
        vbox.addWidget(QLabel("DROP COORDINATES:"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "LATITUDE", "LONGITUDE"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: #222; color: #FFF; gridline-color: #444;")
        vbox.addWidget(self.table)

        layout.addWidget(ctrl_panel)

        # --- RIGHT PANEL: MAP ---
        self.web_view = QWebEngineView()
        # Intercept title changes to capture JS events
        self.web_view.titleChanged.connect(self.handle_map_click)
        layout.addWidget(self.web_view)

    def update_pattern_mode(self, text):
        self.pattern_type = text
        if "Box" in text:
            self.spin_space.setEnabled(False)
            self.lbl_status.setText("STATUS: BOX MODE\nClick Top-Left, then Bottom-Right.")
        else:
            self.spin_space.setEnabled(True)
            self.lbl_status.setText("STATUS: BARRIER MODE\nClick Start Point, then End Point.")

    def reset_map(self):
        self.clicks = []
        self.generated_points = []
        self.table.setRowCount(0)
        self.lbl_status.setText("STATUS: RESET\nAwaiting Input.")
        self.render_map()

    def render_map(self):
        """Generates the Folium map HTML."""
        # Center map
        center = [DEFAULT_LAT, DEFAULT_LON]
        if self.clicks:
            center = self.clicks[-1]  # Center on last click

        m = folium.Map(
            location=center,
            zoom_start=ZOOM_START,
            tiles='CartoDB dark_matter',
            control_scale=True
        )

        # Draw User Clicks (Anchors)
        for i, (lat, lon) in enumerate(self.clicks):
            color = 'green' if i == 0 else 'red'
            label = "START" if i == 0 else "END"
            folium.Marker(
                [lat, lon],
                icon=folium.Icon(color=color, icon='flag'),
                tooltip=f"{label} POINT"
            ).add_to(m)

        # Draw Generated Buoys
        for i, (lat, lon) in enumerate(self.generated_points):
            drop_time = f"T+{i * 5:02d}m"  # Assume 5 min interval
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color='cyan',
                fill=True,
                fill_color='blue',
                popup=f"BUOY #{i + 1} ({drop_time})"
            ).add_to(m)

            # Add label
            folium.map.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 10pt; color: cyan; font-weight: bold;">#{i + 1}</div>'
                )
            ).add_to(m)

        # Draw Connector Line
        if len(self.clicks) == 2:
            folium.PolyLine(
                self.clicks,
                color="white",
                weight=2,
                opacity=0.5,
                dash_array='5, 10'
            ).add_to(m)

            if self.pattern_type == "Box Search (Dice-5)":
                # Draw the box outline
                lat1, lon1 = self.clicks[0]
                lat2, lon2 = self.clicks[1]
                # Rectangle needs logic to define corners properly
                bounds = [[lat1, lon1], [lat2, lon2]]
                folium.Rectangle(bounds, color="yellow", fill=False).add_to(m)

        # Javascript for Click Capture
        m.get_root().script.add_child(folium.Element("""
            function onMapClick(e) {
                var lat = e.latlng.lat;
                var lng = e.latlng.lng;
                document.title = "CLICK:" + lat + "," + lng;
            }
            map_""" + m.get_name() + """.on('click', onMapClick);
        """))

        # Render
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.web_view.setHtml(data.getvalue().decode())

    def handle_map_click(self, title):
        if not title.startswith("CLICK:"): return

        # Parse coords
        coords_str = title.split(":")[1]
        lat, lon = map(float, coords_str.split(","))

        if len(self.clicks) >= 2:
            # Reset if already has 2 points
            self.clicks = [(lat, lon)]
            self.lbl_status.setText("STATUS: POINT A SET\nClick Point B.")
        else:
            self.clicks.append((lat, lon))
            if len(self.clicks) == 1:
                self.lbl_status.setText("STATUS: POINT A SET\nClick Point B.")
            else:
                self.lbl_status.setText("STATUS: AREA DEFINED\nReady to Generate.")

        self.generated_points = []  # Clear old buoys if input changes
        self.render_map()

    def generate_pattern(self):
        if len(self.clicks) < 2:
            self.lbl_status.setText("ERROR: DEFINE 2 POINTS FIRST")
            return

        p1 = self.clicks[0]
        p2 = self.clicks[1]

        if "Linear" in self.pattern_type:
            spacing = self.spin_space.value()
            self.generated_points = GeoMath.get_points_on_line(p1, p2, spacing)
        else:
            self.generated_points = GeoMath.get_box_pattern(p1, p2)

        # Update Table
        self.table.setRowCount(0)
        for i, (lat, lon) in enumerate(self.generated_points):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"BUOY-{i + 1:02d}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"{lat:.5f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{lon:.5f}"))

        self.lbl_status.setText(f"SUCCESS: {len(self.generated_points)} DROPS PLOTTED")
        self.render_map()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SonobuoyPlanner()
    window.show()
    sys.exit(app.exec_())
import sys
import io
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QListWidget, QGroupBox, QFrame, QSplitter)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import folium
from folium.plugins import MousePosition

# --- Configuration ---
# Map Default Center (Middle East region for context)
DEFAULT_LAT = 33.3152
DEFAULT_LON = 44.3661
DEFAULT_ZOOM = 6


class AssetType:
    PATRIOT = "Patriot Battery (160km)"
    RADAR = "Early Warning Radar (300km)"
    THREAT = "No Fly Zone (Threat)"


class MissionPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mission Planner: Geospatial Defense Tool")
        self.setGeometry(100, 100, 1200, 800)

        # State Data
        self.assets = []  # List of dicts: {'type': str, 'lat': float, 'lon': float}
        self.current_tool = AssetType.PATRIOT

        self.init_ui()
        self.render_map()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- LEFT SIDEBAR (Asset Library) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")
        sb_layout = QVBoxLayout(sidebar)

        # Header
        lbl_title = QLabel("ASSET LIBRARY")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
        sb_layout.addWidget(lbl_title)

        # Tool Selection
        grp_tools = QGroupBox("Select Tool")
        vbox_tools = QVBoxLayout()

        self.combo_tool = QComboBox()
        self.combo_tool.addItems([AssetType.PATRIOT, AssetType.RADAR, AssetType.THREAT])
        self.combo_tool.currentTextChanged.connect(self.change_tool)
        vbox_tools.addWidget(self.combo_tool)

        self.lbl_instruction = QLabel("Click on map to place asset.")
        self.lbl_instruction.setStyleSheet("font-style: italic; color: #666;")
        vbox_tools.addWidget(self.lbl_instruction)

        grp_tools.setLayout(vbox_tools)
        sb_layout.addWidget(grp_tools)

        # Deployed Assets List
        sb_layout.addWidget(QLabel("Deployed Assets:"))
        self.list_assets = QListWidget()
        sb_layout.addWidget(self.list_assets)

        # Controls
        btn_clear = QPushButton("Clear All Assets")
        btn_clear.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        btn_clear.clicked.connect(self.clear_assets)
        sb_layout.addWidget(btn_clear)

        sb_layout.addStretch()
        layout.addWidget(sidebar)

        # --- RIGHT SIDE (Map View) ---
        self.map_view = QWebEngineView()
        # Connect title change signal to intercept JavaScript clicks
        self.map_view.titleChanged.connect(self.handle_map_click)
        layout.addWidget(self.map_view)

    def change_tool(self, text):
        self.current_tool = text

    def clear_assets(self):
        self.assets = []
        self.list_assets.clear()
        self.render_map()

    def render_map(self):
        """
        Generates the Folium map HTML and loads it into the WebEngine.
        """
        # 1. Create Base Map
        m = folium.Map(
            location=[DEFAULT_LAT, DEFAULT_LON],
            zoom_start=DEFAULT_ZOOM,
            tiles='CartoDB dark_matter',  # Military style dark map
            control_scale=True
        )

        # 2. Add Mouse Position Coordinates (Top Right)
        formatter = "function(num) {return L.Util.formatNum(num, 5);};"
        MousePosition(
            position='topright',
            separator=' | ',
            empty_string='NaN',
            lng_first=False,
            num_digits=20,
            prefix='Coordinates:',
            lat_formatter=formatter,
            lng_formatter=formatter,
        ).add_to(m)

        # 3. Render Deployed Assets
        for i, asset in enumerate(self.assets):
            lat, lon = asset['lat'], asset['lon']
            a_type = asset['type']

            # Asset Logic
            if a_type == AssetType.PATRIOT:
                # Icon
                folium.Marker(
                    [lat, lon],
                    tooltip=f"Patriot Battery #{i + 1}",
                    icon=folium.Icon(color='blue', icon='rocket', prefix='fa')
                ).add_to(m)

                # Range Ring (160km)
                folium.Circle(
                    location=[lat, lon],
                    radius=160000,  # meters
                    color='#4a90e2',
                    fill=True,
                    fill_opacity=0.2
                ).add_to(m)

            elif a_type == AssetType.RADAR:
                # Icon
                folium.Marker(
                    [lat, lon],
                    tooltip=f"Radar Site #{i + 1}",
                    icon=folium.Icon(color='green', icon='wifi', prefix='fa')
                ).add_to(m)

                # Range Ring (300km)
                folium.Circle(
                    location=[lat, lon],
                    radius=300000,
                    color='#50e3c2',
                    fill=False,  # Just a ring
                    dash_array='5, 5'
                ).add_to(m)

            elif a_type == AssetType.THREAT:
                # Threat Zone (Red Polygon/Circle)
                folium.Circle(
                    location=[lat, lon],
                    radius=100000,  # 100km No Fly Zone
                    color='#d0021b',
                    fill=True,
                    fill_color='#d0021b',
                    fill_opacity=0.4,
                    tooltip="NO FLY ZONE"
                ).add_to(m)

        # 4. Inject Custom JavaScript for Click Handling
        # This script listens for map clicks and updates the document title
        # with the coordinates. PyQt intercepts the title change.
        m.get_root().script.add_child(folium.Element("""
            function onMapClick(e) {
                var lat = e.latlng.lat;
                var lng = e.latlng.lng;
                document.title = "CLICK:" + lat + "," + lng;
            }
            map_""" + m.get_name() + """.on('click', onMapClick);
        """))

        # 5. Save and Load
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.map_view.setHtml(data.getvalue().decode())

    def handle_map_click(self, title):
        """
        Intercepts the browser title change to get data from JavaScript.
        Format: "CLICK:lat,lon"
        """
        if title.startswith("CLICK:"):
            try:
                # Parse Coordinates
                coords = title.split(":")[1]
                lat_str, lon_str = coords.split(",")
                lat, lon = float(lat_str), float(lon_str)

                # Add Asset
                new_asset = {'type': self.current_tool, 'lat': lat, 'lon': lon}
                self.assets.append(new_asset)

                # Update UI
                self.list_assets.addItem(f"{self.current_tool} @ {lat:.3f}, {lon:.3f}")

                # Re-render map to show new asset
                self.render_map()

            except ValueError:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MissionPlanner()
    window.show()
    sys.exit(app.exec_())
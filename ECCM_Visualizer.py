import sys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider,
                             QGroupBox, QCheckBox, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


# --- Physics / Signal Engine ---

class RadarSignalProcessor:
    def __init__(self, width=200, height=200):
        self.w = width
        self.h = height

        # Grid State
        self.raw_data = np.zeros((width, height))

        # Target State
        self.target_angle = 0.0
        self.target_radius = 50.0

        # Simulation Settings
        self.jamming_intensity = 0.5  # 0.0 to 1.0 (Amplitude of noise)
        self.burn_through_active = False
        self.target_power = 0.6  # Base signal strength of aircraft

    def update_physics(self):
        """Generates the next frame of Radar Data."""
        # 1. Generate Noise Floor (Thermal Noise)
        # Background static is always present (low amplitude)
        noise = np.random.normal(0.1, 0.05, (self.w, self.h))

        # 2. Generate Jamming (High Amplitude Noise)
        # Barrage jamming covers the whole screen with high intensity spikes
        if self.jamming_intensity > 0:
            jamming = np.random.normal(0.5, 0.2, (self.w, self.h)) * self.jamming_intensity
            # Make jamming "clumpy" or shifting to look realistic
            noise += jamming

        # 3. Generate Target (The Aircraft)
        # Move target in a circle
        self.target_angle += 0.02
        cx = int(self.w / 2 + np.cos(self.target_angle) * self.target_radius)
        cy = int(self.h / 2 + np.sin(self.target_angle) * self.target_radius)

        # Create a 2D Gaussian blob for the target
        target_grid = np.zeros((self.w, self.h))

        # Basic bounds check
        if 0 <= cx < self.w and 0 <= cy < self.h:
            # Signal Power Logic
            power = self.target_power
            if self.burn_through_active:
                power *= 3.0  # Burn-through triples the return signal

            # Draw point (simplified gaussian)
            # Center
            target_grid[cx, cy] = power
            # Neighbors (blur)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if 0 <= cx + dx < self.w and 0 <= cy + dy < self.h:
                        target_grid[cx + dx, cy + dy] += power * 0.5

        # Combine
        self.raw_data = noise + target_grid

        # Clip to valid range 0.0 - 1.0 (or higher if burn through)
        self.raw_data = np.clip(self.raw_data, 0, 2.0)
        return self.raw_data


# --- GUI Application ---

class ECCMVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECCM Radar Signal Visualizer")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #101010; color: #00FF00; font-family: Consolas; }
            QGroupBox { border: 1px solid #333; margin-top: 10px; font-weight: bold; color: #AAA; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: #EEE; font-size: 12px; }
            QSlider::handle:horizontal { background-color: #00FF00; width: 10px; margin: -5px 0; }
        """)

        # Logic
        self.processor = RadarSignalProcessor(100, 100)
        self.threshold_val = 0.0

        self.init_ui()

        # Animation Loop (30 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(33)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- LEFT: CONTROLS ---
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(300)
        ctrl_panel.setStyleSheet("background-color: #1a1a1a; border-right: 2px solid #333;")
        vbox = QVBoxLayout(ctrl_panel)

        # Header
        lbl_title = QLabel("RADAR PROCESSOR\nAN/SPY-1 SIM")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00FF00; margin-bottom: 20px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(lbl_title)

        # 1. Jamming Controls
        grp_ew = QGroupBox("ELECTRONIC WARFARE (OPFOR)")
        l_ew = QVBoxLayout(grp_ew)

        l_ew.addWidget(QLabel("Noise Jamming Intensity:"))
        self.slider_jam = QSlider(Qt.Horizontal)
        self.slider_jam.setRange(0, 200)  # 0.0 to 2.0
        self.slider_jam.setValue(50)  # 0.5 default
        self.slider_jam.valueChanged.connect(self.update_params)
        l_ew.addWidget(self.slider_jam)

        vbox.addWidget(grp_ew)

        # 2. Filter Controls
        grp_filter = QGroupBox("SIGNAL PROCESSING (ECCM)")
        l_filt = QVBoxLayout(grp_filter)

        l_filt.addWidget(QLabel("Noise Gate Threshold:"))
        self.slider_thresh = QSlider(Qt.Horizontal)
        self.slider_thresh.setRange(0, 100)  # 0.0 to 1.0
        self.slider_thresh.setValue(0)
        self.slider_thresh.valueChanged.connect(self.update_params)
        l_filt.addWidget(self.slider_thresh)

        self.lbl_thresh_val = QLabel("Cutoff: 0.00v")
        self.lbl_thresh_val.setStyleSheet("color: #AAA;")
        l_filt.addWidget(self.lbl_thresh_val)

        vbox.addWidget(grp_filter)

        # 3. Active Measures
        grp_active = QGroupBox("ACTIVE MEASURES")
        l_act = QVBoxLayout(grp_active)

        self.btn_burn = QPushButton("ACTIVATE BURN-THROUGH")
        self.btn_burn.setCheckable(True)
        self.btn_burn.setFixedHeight(60)
        self.btn_burn.setStyleSheet(self.get_btn_style(False))
        self.btn_burn.toggled.connect(self.toggle_burn)
        l_act.addWidget(self.btn_burn)

        info = QLabel("INFO: Burn-Through focuses max power on sector to overcome jamming amplitude.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 10px; margin-top: 5px;")
        l_act.addWidget(info)

        vbox.addWidget(grp_active)

        vbox.addStretch()
        layout.addWidget(ctrl_panel)

        # --- RIGHT: SCOPE VISUALIZATION ---
        right_panel = QVBoxLayout()

        # PyQtGraph Image View
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setBackground('#001100')  # Radar Green/Black

        # Image Item
        self.img_item = pg.ImageItem()
        self.plot_widget.addItem(self.img_item)

        # Color Map (Heatmap style: Black -> Green -> Yellow -> Red)
        # Positions: 0.0, 0.3, 0.7, 1.0
        pos = np.array([0.0, 0.4, 0.8, 1.0])
        color = np.array([
            [0, 0, 0, 255],  # Black (Noise floor)
            [0, 100, 0, 255],  # Dark Green
            [0, 255, 0, 255],  # Bright Green (Signal)
            [255, 255, 255, 255]  # White (Hot/Burn Through)
        ], dtype=np.ubyte)
        map = pg.ColorMap(pos, color)
        lut = map.getLookupTable(0.0, 1.0, 256)
        self.img_item.setLookupTable(lut)

        right_panel.addWidget(QLabel("PRIMARY SEARCH RADAR (RAW DATA)"))
        right_panel.addWidget(self.plot_widget)
        layout.addLayout(right_panel)

    def get_btn_style(self, active):
        if active:
            return """
                QPushButton {
                    background-color: #D32F2F; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 14px;
                    border: 2px solid #FF5555;
                    border-radius: 5px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #333; 
                    color: #AAA; 
                    font-weight: bold; 
                    font-size: 14px;
                    border: 1px solid #555;
                    border-radius: 5px;
                }
            """

    def toggle_burn(self, checked):
        self.processor.burn_through_active = checked
        self.btn_burn.setStyleSheet(self.get_btn_style(checked))
        if checked:
            self.btn_burn.setText("BURN-THROUGH ACTIVE\n(HIGH POWER)")
        else:
            self.btn_burn.setText("ACTIVATE BURN-THROUGH")

    def update_params(self):
        # Update Logic parameters from sliders
        self.processor.jamming_intensity = self.slider_jam.value() / 100.0
        self.threshold_val = self.slider_thresh.value() / 100.0
        self.lbl_thresh_val.setText(f"Cutoff: {self.threshold_val:.2f}v")

    def update_display(self):
        # 1. Get raw physics frame
        data = self.processor.update_physics()

        # 2. Apply ECCM Filter (Thresholding)
        # Any signal below threshold becomes 0 (Black)
        filtered_data = np.where(data < self.threshold_val, 0, data)

        # 3. Update Visuals
        # Transpose data because PyQtGraph uses column-major by default
        self.img_item.setImage(filtered_data.T, autoLevels=False, levels=(0.0, 1.2))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ECCMVisualizer()
    window.show()
    sys.exit(app.exec_())
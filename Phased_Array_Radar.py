import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSlider, QLabel, QGroupBox, QCheckBox)
from PyQt5.QtCore import QTimer, Qt


# --- Physics Engine: Phased Array Beamforming ---

class PhasedArrayPhysics:
    def __init__(self, num_elements=16):
        self.N = num_elements  # Number of antenna elements
        self.d = 0.5  # Spacing in wavelengths (lambda/2 is standard to avoid grating lobes)
        self.k = 2 * np.pi  # Wavenumber (2*pi/lambda, assuming lambda=1)

        # Simulation Resolution
        self.theta_range = np.linspace(-np.pi / 2, np.pi / 2, 360)  # -90 to +90 degrees

    def calculate_array_factor(self, steer_angle_deg):
        """
        Calculates the Radiation Pattern (Array Factor) for a specific steering angle.

        Math: AF(theta) = Sum( exp(j * (n * k * d * sin(theta) + beta_n)) )
        Where beta_n is the phase shift required to steer the beam.
        """
        theta0 = np.radians(steer_angle_deg)

        # 1. Calculate required phase shift (beta) per element to steer to theta0
        # beta_n = -n * k * d * sin(theta0)
        n = np.arange(self.N)
        beta = -n * self.k * self.d * np.sin(theta0)

        # 2. Calculate Array Factor for all observation angles (theta_range)
        # We use broadcasting to do this efficiently without loops
        # Dimensions: theta_grid (360, 1), n_grid (1, N)
        theta_grid = self.theta_range[:, np.newaxis]
        n_grid = n[np.newaxis, :]

        # Argument of the exponential
        psi = self.k * self.d * np.sin(theta_grid) * n_grid + beta

        # Sum across all elements (axis 1)
        af_complex = np.sum(np.exp(1j * psi), axis=1)

        # Normalize Magnitude (0 to 1) for plotting
        af_mag = np.abs(af_complex)
        af_mag = af_mag / self.N

        return self.theta_range, af_mag


# --- GUI Application ---

class RadarSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phased Array Radar Simulator (Beamforming)")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #222; color: #EEE;")

        # Physics
        self.radar = PhasedArrayPhysics(num_elements=16)

        # State
        self.steer_angle = 0.0
        self.target_angle = 30.0
        self.target_direction = 1
        self.tracking_mode = False

        self.init_ui()

        # Animation Loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(30)  # 30ms update

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL: Controls ---
        ctrl_panel = QGroupBox("Radar Control")
        ctrl_panel.setStyleSheet("border: 1px solid #555; border-radius: 5px; margin-top: 10px;")
        ctrl_panel.setFixedWidth(250)
        ctrl_layout = QVBoxLayout(ctrl_panel)

        # Steering Slider
        self.lbl_angle = QLabel("Steering Angle: 0.0°")
        self.lbl_angle.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.slider_angle = QSlider(Qt.Horizontal)
        self.slider_angle.setRange(-80, 80)
        self.slider_angle.setValue(0)
        self.slider_angle.valueChanged.connect(self.manual_steer)

        ctrl_layout.addWidget(self.lbl_angle)
        ctrl_layout.addWidget(self.slider_angle)

        # Tracking Toggle
        self.chk_track = QCheckBox("Auto-Track Target")
        self.chk_track.setStyleSheet("font-size: 14px; padding: 10px;")
        self.chk_track.toggled.connect(self.toggle_tracking)
        ctrl_layout.addWidget(self.chk_track)

        ctrl_layout.addStretch()

        # Info Box
        info = QLabel(
            "Physics Note:\n\nThe 'Main Lobe' steers to the\ntarget angle by adding a\nprecise phase shift to each\nof the 16 antenna elements.\n\nThe smaller ripples are\n'Side Lobes' (unwanted signal).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #AAA; font-style: italic; padding: 10px;")
        ctrl_layout.addWidget(info)

        main_layout.addWidget(ctrl_panel)

        # --- RIGHT PANEL: Polar Plot ---
        self.fig = Figure(figsize=(6, 6), dpi=100)
        self.fig.patch.set_facecolor('#111')
        self.canvas = FigureCanvas(self.fig)
        main_layout.addWidget(self.canvas)

        # Initial Plot Setup
        self.ax = self.fig.add_subplot(111, projection='polar')
        self.setup_plot()

    def setup_plot(self):
        self.ax.set_facecolor('#001100')  # Radar Green/Black background
        self.ax.set_theta_zero_location("N")  # 0 degrees at top
        self.ax.set_theta_direction(-1)  # Clockwise
        self.ax.set_thetamin(-90)
        self.ax.set_thetamax(90)

        # Customize grid
        self.ax.grid(True, color='#004400', linestyle='--')
        self.ax.set_rticks([0.25, 0.5, 0.75, 1.0])
        self.ax.set_yticklabels([])  # Hide radial labels
        self.ax.tick_params(axis='x', colors='#00FF00')

        # Plot Objects
        # 1. The Beam Pattern (Blue Line)
        self.line_beam, = self.ax.plot([], [], color='#00FFFF', linewidth=2, label='Radar Beam')

        # 2. The Target (Red Dot)
        self.plot_target, = self.ax.plot([], [], 'ro', markersize=10, label='Target')

        # 3. Target Line (Red dashed line)
        self.line_target, = self.ax.plot([], [], 'r--', linewidth=1, alpha=0.5)

        # Legend
        leg = self.ax.legend(loc='lower left', facecolor='#222', edgecolor='#555')
        for text in leg.get_texts():
            text.set_color("white")

    def manual_steer(self):
        self.steer_angle = self.slider_angle.value()
        self.lbl_angle.setText(f"Steering Angle: {self.steer_angle}°")

    def toggle_tracking(self, checked):
        self.tracking_mode = checked
        self.slider_angle.setEnabled(not checked)

    def update_simulation(self):
        # 1. Update Target Position (Simulate movement)
        self.target_angle += 0.5 * self.target_direction
        if self.target_angle > 70 or self.target_angle < -70:
            self.target_direction *= -1

        # 2. Logic: Determine Beam Angle
        if self.tracking_mode:
            # Electronic Tracking: Beam locks onto target instantly
            self.steer_angle = self.target_angle
            # Update slider visualization (but disabled)
            self.slider_angle.blockSignals(True)
            self.slider_angle.setValue(int(self.steer_angle))
            self.slider_angle.blockSignals(False)
            self.lbl_angle.setText(f"Steering Angle: {self.steer_angle:.1f}° (LOCKED)")

        # 3. Physics Calculation: Get Beam Pattern
        theta, gain = self.radar.calculate_array_factor(self.steer_angle)

        # 4. Update Plot
        self.line_beam.set_data(theta, gain)

        # Update Target Marker
        target_rad = np.radians(self.target_angle)
        self.plot_target.set_data([target_rad], [0.95])  # Place target at edge
        self.line_target.set_data([target_rad, target_rad], [0, 1.0])

        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarSimulator()
    window.show()
    sys.exit(app.exec_())
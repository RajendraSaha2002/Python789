import sys
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QFrame)
from PyQt5.QtCore import QTimer, Qt
from scipy.interpolate import splprep, splev


# --- Mathematics & Geometry Engine ---

class OrganGenerator:
    def __init__(self):
        self.centerline = None
        self.mesh = None
        self.path_points = []

    def generate_colon(self, num_points=2000):
        """
        Generates a winding 3D path and constructs a tube around it
        to simulate a biological organ (Colon).
        """
        # 1. Generate Control Points (A winding spiral/sine wave)
        t = np.linspace(0, 20, 40)  # Coarse control points
        x = np.sin(t) * 10
        y = t * 5
        z = np.cos(t * 1.5) * 10

        # Add some random jitter to make it organic
        noise = np.random.normal(0, 1.0, x.shape)
        x += noise
        z += noise

        # 2. Spline Interpolation (Smoothing the path)
        # scipy.interpolate.splprep calculates the B-spline representation of the curve
        tck, u = splprep([x, y, z], s=5)  # s is smoothing factor

        # Evaluate spline at high resolution for the camera path
        u_new = np.linspace(0, 1, num_points)
        smooth_x, smooth_y, smooth_z = splev(u_new, tck)

        self.path_points = np.column_stack((smooth_x, smooth_y, smooth_z))

        # 3. Create the Tube Mesh
        # We need the points to be connected as a line for the tube filter to work.
        # pv.lines_from_points creates the necessary connectivity.
        spline_poly = pv.lines_from_points(self.path_points)

        # Variable radius to simulate "Haustra" (folds in the colon)
        # We create a scalar array based on the sine of the distance along the line
        dist = np.linspace(0, 100, num_points)
        radius_values = 3.0 + 1.0 * np.sin(dist)  # Radius oscillates between 2.0 and 4.0

        spline_poly["radius_variation"] = radius_values

        # Generate Tube
        # We use the scalar to vary the radius
        self.mesh = spline_poly.tube(scalars="radius_variation", absolute=True, capping=False, n_sides=30)

        # Calculate texture coordinates/normals for better lighting
        self.mesh.compute_normals(inplace=True)

        return self.mesh, self.path_points


# --- Main Application ---

class EndoscopySimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Endoscopy Simulator (Fly-Through)")
        self.setGeometry(100, 100, 1200, 800)

        # Physics / Logic
        self.organ_gen = OrganGenerator()
        self.mesh, self.path = self.organ_gen.generate_colon()

        # Camera State
        self.frame_idx = 0
        self.is_flying = False
        self.look_ahead = 50  # How many points ahead the camera looks
        self.speed = 2  # Frames per tick

        self.setup_ui()
        self.init_scene()

        # Animation Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.fly_step)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Panel: Controls ---
        panel = QFrame()
        panel.setFixedWidth(250)
        panel.setStyleSheet("background-color: #222; color: #EEE;")
        panel_layout = QVBoxLayout(panel)

        lbl_title = QLabel("ENDOSCOPY\nCONTROLS")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff9999;")
        lbl_title.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(lbl_title)

        # Buttons
        self.btn_fly = QPushButton("Start Flight")
        self.btn_fly.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.btn_fly.clicked.connect(self.toggle_flight)
        panel_layout.addWidget(self.btn_fly)

        self.btn_reset = QPushButton("Reset Camera")
        self.btn_reset.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        self.btn_reset.clicked.connect(self.reset_flight)
        panel_layout.addWidget(self.btn_reset)

        # Speed Slider
        panel_layout.addWidget(QLabel("Travel Speed:"))
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(1, 10)
        self.slider_speed.setValue(2)
        self.slider_speed.valueChanged.connect(self.update_speed)
        panel_layout.addWidget(self.slider_speed)

        # Info
        self.lbl_status = QLabel("Status: Ready")
        panel_layout.addWidget(self.lbl_status)

        panel_layout.addStretch()

        # Add panel to layout
        main_layout.addWidget(panel)

        # --- Right Panel: 3D View ---
        self.plotter = QtInteractor(self)
        self.plotter.set_background("black")
        main_layout.addWidget(self.plotter.interactor)

    def init_scene(self):
        # Add the Organ Mesh
        # Color it pink/fleshy
        self.plotter.add_mesh(self.mesh, color="#dba3a3", specular=0.5, smooth_shading=True, show_edges=False)

        # Add a light attached to the camera (headlight)
        self.light = pv.Light(position=(0, 0, 0), focal_point=(0, 0, 1), color='white', intensity=0.8)
        self.plotter.add_light(self.light)

        # Initial Camera Position (Outside looking in)
        start_pos = self.path[0]
        start_focus = self.path[self.look_ahead]

        self.plotter.camera.position = start_pos
        self.plotter.camera.focal_point = start_focus
        self.plotter.camera.view_up = (0, 1, 0)
        self.plotter.camera.zoom(1.0)

    def toggle_flight(self):
        if self.is_flying:
            self.is_flying = False
            self.timer.stop()
            self.btn_fly.setText("Resume Flight")
            self.lbl_status.setText("Status: Paused")
        else:
            if self.frame_idx >= len(self.path) - self.look_ahead:
                self.frame_idx = 0  # Restart if at end

            self.is_flying = True
            self.timer.start(20)  # 50 FPS
            self.btn_fly.setText("Pause Flight")
            self.lbl_status.setText("Status: Flying...")

    def reset_flight(self):
        self.is_flying = False
        self.timer.stop()
        self.frame_idx = 0
        self.btn_fly.setText("Start Flight")

        # Reset camera
        pos = self.path[0]
        focus = self.path[self.look_ahead]
        self.plotter.camera.position = pos
        self.plotter.camera.focal_point = focus
        self.plotter.render()

    def update_speed(self):
        self.speed = self.slider_speed.value()

    def fly_step(self):
        # 1. Update Index
        self.frame_idx += self.speed

        # Check bounds
        if self.frame_idx + self.look_ahead >= len(self.path):
            self.toggle_flight()  # Stop at end
            self.lbl_status.setText("Status: Exam Complete")
            return

        # 2. Get Camera Vectors from Path
        idx = int(self.frame_idx)
        cam_pos = self.path[idx]
        cam_focus = self.path[idx + self.look_ahead]

        # 3. Update Camera
        self.plotter.camera.position = cam_pos
        self.plotter.camera.focal_point = cam_focus

        # 4. Update Light (Endoscope Headlight)
        # The light must move with the camera to illuminate the dark tube
        self.light.position = cam_pos
        self.light.focal_point = cam_focus

        # 5. Render
        self.plotter.render()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EndoscopySimulator()
    window.show()
    sys.exit(app.exec_())
import sys
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSlider, QLabel, QGroupBox, QPushButton,
                             QCheckBox, QSplitter)
from PyQt5.QtCore import Qt


# --- 1. Synthetic Data & AI Simulation Engine ---

class MedicalDataEngine:
    def __init__(self, size=128):
        self.size = size
        # Voxel dimensions in mm (simulating high-res MRI)
        self.voxel_spacing = (1.0, 1.0, 1.0)
        self.volume = None
        self.tumor_mask = None

    def generate_synthetic_brain(self):
        """
        Generates a 3D Volumetric MRI (Numpy Array).
        Simulates: Background (Air), Skull/Skin, Brain Tissue, and a Hyperintense Tumor.
        """
        print("Generating 3D MRI Volume...")
        n = self.size
        # Create a grid
        x, y, z = np.ogrid[:n, :n, :n]
        center = n / 2

        # Distance from center
        radius = np.sqrt((x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2)

        # Initialize Volume (Air = 0)
        self.volume = np.zeros((n, n, n), dtype=np.float32)

        # 1. Skull/Skin (Outer Shell)
        skull_mask = (radius > 45) & (radius < 50)
        self.volume[skull_mask] = 0.8  # High intensity bone/fat

        # 2. Brain Tissue (Inner Sphere)
        brain_mask = radius <= 45
        # Add Perlin-like noise for tissue texture
        noise = np.random.normal(0, 0.05, (n, n, n))
        self.volume[brain_mask] = 0.4 + noise[brain_mask]

        # 3. The Tumor (Hidden Anomaly)
        # Place it off-center
        t_center_x, t_center_y, t_center_z = center + 15, center - 10, center + 5
        t_dist = np.sqrt((x - t_center_x) ** 2 + (y - t_center_y) ** 2 + (z - t_center_z) ** 2)

        tumor_mask_logic = t_dist < 8.0  # 8mm radius tumor
        self.volume[tumor_mask_logic] = 0.95  # Hyperintense (Bright White)

        # Normalize to 0-1 range
        self.volume = np.clip(self.volume, 0, 1)

        return self.volume

    def run_ai_segmentation(self):
        """
        Simulates running a U-Net Deep Learning model.
        In a real app, this would load a .h5 file and predict.
        Here, we use thresholding and morphology to 'find' the tumor we generated.
        """
        print("Running AI Segmentation Inference...")
        # Mock AI: Detects high intensity region inside the brain
        # In reality: prediction = model.predict(self.volume)

        # We cheat slightly by using the known generation logic for the demo's accuracy
        # But let's make it 'calculated' based on intensity to be semi-realistic
        mask = np.zeros_like(self.volume)
        mask[self.volume > 0.9] = 1  # Thresholding "AI"

        self.tumor_mask = mask
        return mask

    def calculate_tumor_volume(self):
        if self.tumor_mask is None: return 0.0

        voxel_vol = self.voxel_spacing[0] * self.voxel_spacing[1] * self.voxel_spacing[2]
        count = np.sum(self.tumor_mask)
        return count * voxel_vol


# --- 2. The AI Radiologist GUI ---

class AIRadiologistApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The AI Radiologist: 3D Volumetric Viewer")
        self.setGeometry(50, 50, 1280, 800)

        # Backend
        self.engine = MedicalDataEngine(size=100)  # 100x100x100 volume
        self.vol_data = self.engine.generate_synthetic_brain()
        self.mask_data = None

        # PyVista Grid Object (The container for 3D data)
        # CHANGED: pv.UniformGrid() -> pv.ImageData() due to deprecation
        self.grid = pv.ImageData()
        self.grid.dimensions = self.vol_data.shape
        self.grid.spacing = self.engine.voxel_spacing
        self.grid.point_data["MRI_Intensity"] = self.vol_data.flatten(order="F")

        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- LEFT PANEL: Controls ---
        panel = QWidget()
        panel.setFixedWidth(300)
        panel_layout = QVBoxLayout(panel)

        # Title
        lbl_title = QLabel("AI DIAGNOSTICS")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4488ff;")
        panel_layout.addWidget(lbl_title)

        # 1. Visualization Controls
        grp_vis = QGroupBox("Scan Visualization")
        layout_vis = QVBoxLayout()

        layout_vis.addWidget(QLabel("Opacity Threshold (Skin/Air):"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(10)
        self.slider_opacity.valueChanged.connect(self.update_opacity)
        layout_vis.addWidget(self.slider_opacity)

        self.chk_slices = QCheckBox("Show Orthogonal Slices")
        self.chk_slices.toggled.connect(self.toggle_slices)
        layout_vis.addWidget(self.chk_slices)

        grp_vis.setLayout(layout_vis)
        panel_layout.addWidget(grp_vis)

        # 2. AI Controls
        grp_ai = QGroupBox("Deep Learning Analysis")
        layout_ai = QVBoxLayout()

        self.btn_run_ai = QPushButton("RUN U-NET SEGMENTATION")
        self.btn_run_ai.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_ai.clicked.connect(self.run_ai)
        layout_ai.addWidget(self.btn_run_ai)

        self.lbl_vol = QLabel("Tumor Volume: N/A")
        self.lbl_vol.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout_ai.addWidget(self.lbl_vol)

        grp_ai.setLayout(layout_ai)
        panel_layout.addWidget(grp_ai)

        panel_layout.addStretch()
        layout.addWidget(panel)

        # --- RIGHT PANEL: 3D Viewport ---
        self.frame = QWidget()
        self.plotter = QtInteractor(self.frame)
        self.plotter.set_background("black")
        layout.addWidget(self.plotter.interactor)

        # Initial Render
        self.render_volume()

    def render_volume(self):
        self.plotter.clear()

        # Opacity Mapping: Make low values (Air) transparent
        # 0.0 -> 0.0 (Transparent)
        # 0.2 -> 0.0
        # 0.5 -> 0.3 (Semi-transparent Brain)
        # 1.0 -> 0.8 (Solid Bone/Tumor)
        opacity = [0, 0, 0.1, 0.3, 0.8]

        # Render the MRI Volume
        self.vol_actor = self.plotter.add_volume(
            self.grid,
            scalars="MRI_Intensity",
            cmap="gray",
            opacity=opacity,
            shade=True,
            show_scalar_bar=False
        )

        # If AI has run, render the Tumor Mask on top
        if self.mask_data is not None:
            # We create a contour (isosurface) for the tumor
            # Create a new grid for the mask
            # CHANGED: pv.UniformGrid() -> pv.ImageData() due to deprecation
            mask_grid = pv.ImageData()
            mask_grid.dimensions = self.mask_data.shape
            mask_grid.spacing = self.engine.voxel_spacing
            mask_grid.point_data["Tumor"] = self.mask_data.flatten(order="F")

            # Extract surface where value > 0.5
            tumor_mesh = mask_grid.contour([0.5], scalars="Tumor")

            self.plotter.add_mesh(tumor_mesh, color="red", opacity=0.6, label="Tumor")
            self.plotter.add_legend_scale(bottom_axis_visibility=False, left_axis_visibility=False)

        self.plotter.reset_camera()

    def update_opacity(self):
        # Adjust the 'min' threshold of the opacity function
        val = self.slider_opacity.value() / 100.0
        # Create a sigmoid-like mapping based on slider
        # This allows user to peel away layers of the brain
        opacity_map = [0, 0, 0, 0.1, 0.8]
        # We define opacity by shifting the mapping
        # PyVista handles opacity usually as a mapping from scalar value to alpha
        # Simple approach: Removing and re-adding is easiest for this demo structure
        self.render_volume()

    def toggle_slices(self, checked):
        if checked:
            self.plotter.add_mesh(self.grid.slice_orthogonal(), opacity=0.5, cmap="gray")
        else:
            self.render_volume()  # Re-renders without slices

    def run_ai(self):
        # 1. Run "Inference"
        self.mask_data = self.engine.run_ai_segmentation()

        # 2. Calculate Stats
        vol = self.engine.calculate_tumor_volume()
        self.lbl_vol.setText(f"Tumor Volume: {vol:.2f} mm³")

        # 3. Update 3D View
        self.render_volume()
        self.plotter.add_text("TUMOR DETECTED", position='upper_left', color='red', font_size=12)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AIRadiologistApp()
    window.show()
    sys.exit(app.exec_())
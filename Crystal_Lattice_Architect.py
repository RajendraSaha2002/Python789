import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QSpinBox,
                             QSlider, QGroupBox, QFrame)
from PyQt5.QtCore import Qt

import pyvista as pv
from pyvistaqt import QtInteractor
from ase.lattice.cubic import SimpleCubic, BodyCenteredCubic, FaceCenteredCubic
from ase import Atoms


# --- XRD Physics Engine ---

class XRDPhysics:
    def __init__(self, wavelength=1.5406):
        # Default X-Ray wavelength (Copper K-alpha)
        self.wavelength = wavelength

    def calculate_pattern(self, structure_type, lattice_constant):
        """
        Calculates 2-Theta positions and Intensities based on
        Structure Factor selection rules.
        """
        # Max 2-Theta to calculate
        max_2theta = 90

        # Generate possible h,k,l indices
        hkls = []
        for h in range(0, 4):
            for k in range(0, 4):
                for l in range(0, 4):
                    if h == 0 and k == 0 and l == 0: continue
                    hkls.append((h, k, l))

        peaks = []  # (2Theta, Intensity, Label)

        for h, k, l in hkls:
            # 1. Structure Factor Selection Rules
            # SC: All reflections allowed
            # BCC: (h + k + l) must be even
            # FCC: h, k, l must be all even or all odd
            allowed = False

            if structure_type == "Simple Cubic":
                allowed = True
            elif structure_type == "Body Centered Cubic":
                if (h + k + l) % 2 == 0:
                    allowed = True
            elif structure_type == "Face Centered Cubic":
                # Check parity (all even or all odd)
                mod_sum = (h % 2) + (k % 2) + (l % 2)
                if mod_sum == 0 or mod_sum == 3:
                    allowed = True

            if not allowed:
                continue

            # 2. Bragg's Law: n*lambda = 2*d*sin(theta)
            # Cubic d-spacing: d = a / sqrt(h^2 + k^2 + l^2)
            d = lattice_constant / np.sqrt(h ** 2 + k ** 2 + l ** 2)

            # sin(theta) = lambda / 2d
            val = self.wavelength / (2 * d)
            if val >= 1.0: continue  # Physically impossible

            theta_rad = np.arcsin(val)
            two_theta_deg = 2 * np.degrees(theta_rad)

            if two_theta_deg > max_2theta: continue

            # 3. Simple Intensity Approximation (Multiplicity + Structure Factor)
            # Real XRD involves atomic form factors, thermal factors, etc.
            # Here we just visualize the *positions* and basic relative intensity.
            # Multiplicity roughly correlates to how many permutations of h,k,l exist.
            intensity = 100.0 / (h ** 2 + k ** 2 + l ** 2)  # Decaying intensity proxy

            peaks.append((two_theta_deg, intensity, f"({h}{k}{l})"))

        # Sort by angle
        peaks.sort(key=lambda x: x[0])
        return peaks


# --- GUI Application ---

class CrystalArchitect(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Crystal Lattice Architect (XRD Simulator)")
        self.setGeometry(100, 100, 1200, 800)

        # State
        self.lattice_a = 4.0  # Angstroms
        self.xrd_engine = XRDPhysics()

        self.setup_ui()
        self.update_crystal()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL: 3D Visualization ---
        self.plotter_frame = QFrame()
        self.plotter_layout = QVBoxLayout(self.plotter_frame)
        self.plotter = QtInteractor(self.plotter_frame)
        self.plotter.set_background("black")
        self.plotter.add_axes()
        self.plotter_layout.addWidget(self.plotter.interactor)

        # --- RIGHT PANEL: Controls & XRD ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(400)

        # 1. Structure Controls
        grp_struct = QGroupBox("Lattice Construction")
        vbox_struct = QVBoxLayout()

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Simple Cubic", "Body Centered Cubic", "Face Centered Cubic"])
        self.combo_type.currentIndexChanged.connect(self.update_crystal)
        vbox_struct.addWidget(QLabel("Bravais Lattice:"))
        vbox_struct.addWidget(self.combo_type)

        self.slider_supercell = QSlider(Qt.Horizontal)
        self.slider_supercell.setRange(1, 4)
        self.slider_supercell.setValue(2)
        self.slider_supercell.valueChanged.connect(self.update_crystal)
        vbox_struct.addWidget(QLabel("Supercell Size (Repeat Unit):"))
        vbox_struct.addWidget(self.slider_supercell)

        grp_struct.setLayout(vbox_struct)
        right_layout.addWidget(grp_struct)

        # 2. Miller Plane Slicer
        grp_miller = QGroupBox("Miller Plane Slicer (h k l)")
        hbox_miller = QHBoxLayout()

        self.spin_h = QSpinBox();
        self.spin_h.setRange(0, 5);
        self.spin_h.setValue(1)
        self.spin_k = QSpinBox();
        self.spin_k.setRange(0, 5);
        self.spin_k.setValue(1)
        self.spin_l = QSpinBox();
        self.spin_l.setRange(0, 5);
        self.spin_l.setValue(0)

        for s in [self.spin_h, self.spin_k, self.spin_l]:
            s.valueChanged.connect(self.update_plane)
            hbox_miller.addWidget(s)

        grp_miller.setLayout(hbox_miller)
        right_layout.addWidget(grp_miller)

        # 3. XRD Graph
        grp_xrd = QGroupBox("Simulated XRD Pattern")
        vbox_xrd = QVBoxLayout()
        self.fig = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        vbox_xrd.addWidget(self.canvas)
        grp_xrd.setLayout(vbox_xrd)
        right_layout.addWidget(grp_xrd)

        right_layout.addStretch()

        main_layout.addWidget(self.plotter_frame, 65)
        main_layout.addWidget(right_panel, 35)

    def generate_atoms(self):
        """Use ASE to build the crystal object."""
        struct_type = self.combo_type.currentText()
        size = self.slider_supercell.value()

        # Using simple Iron (Fe) or generic element just for visualization
        if struct_type == "Simple Cubic":
            # ASE doesn't have a direct SC helper, easiest to build manually or hack Po (Polonium)
            atoms = SimpleCubic(symbol='Po', latticeconstant=self.lattice_a)
        elif struct_type == "Body Centered Cubic":
            atoms = BodyCenteredCubic(symbol='Fe', latticeconstant=self.lattice_a)
        elif struct_type == "Face Centered Cubic":
            atoms = FaceCenteredCubic(symbol='Au', latticeconstant=self.lattice_a)

        return atoms.repeat((size, size, size))

    def update_crystal(self):
        self.plotter.clear()

        # 1. Get Atoms
        atoms = self.generate_atoms()
        positions = atoms.get_positions()

        # 2. Render Atoms (PyVista)
        # Create a point cloud
        point_cloud = pv.PolyData(positions)
        # Create spheres for each point
        spheres = point_cloud.glyph(scale=False, geom=pv.Sphere(radius=0.4))

        # Color based on structure
        color_map = {"Simple Cubic": "cyan", "Body Centered Cubic": "orange", "Face Centered Cubic": "magenta"}
        c = color_map.get(self.combo_type.currentText(), "white")

        self.plotter.add_mesh(spheres, color=c, specular=0.5, smooth_shading=True)

        # 3. Draw Bounding Box of the whole supercell
        box = pv.Box(bounds=(0, np.max(positions[:, 0]), 0, np.max(positions[:, 1]), 0, np.max(positions[:, 2])))
        self.plotter.add_mesh(box, color="white", style="wireframe", opacity=0.3)

        # 4. Update features
        self.update_plane()
        self.update_xrd_plot()

    def update_plane(self):
        # Remove old plane if exists (by tag or simply logic, here we just clear/redraw often
        # but to avoid clearing atoms, we use names in add_mesh if we were optimizing.
        # For simplicity, we just called update_crystal which clears all.)
        # Note: In a full app, we would manage actor references.
        # Let's add the plane on top.

        h = self.spin_h.value()
        k = self.spin_k.value()
        l = self.spin_l.value()

        if h == 0 and k == 0 and l == 0: return  # Invalid plane

        # Size of the crystal
        size = self.slider_supercell.value() * self.lattice_a
        center = np.array([size / 2, size / 2, size / 2])

        # Normal Vector is just (h, k, l) for cubic
        normal = np.array([h, k, l])

        # Create Plane
        plane = pv.Plane(center=center, direction=normal, i_size=size * 2, j_size=size * 2)

        # We need to give it a unique name so we can overwrite it without clearing the atoms
        self.plotter.add_mesh(plane, color="yellow", opacity=0.35, name="miller_plane")

    def update_xrd_plot(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        struct_type = self.combo_type.currentText()
        peaks = self.xrd_engine.calculate_pattern(struct_type, self.lattice_a)

        # Plot "Sticks"
        for two_theta, intensity, label in peaks:
            ax.vlines(x=two_theta, ymin=0, ymax=intensity, colors='b', linewidth=2)
            # Add HKL label on top
            ax.text(two_theta, intensity + 2, label, ha='center', fontsize=8, rotation=90)

        ax.set_xlim(10, 90)
        ax.set_ylim(0, 120)
        ax.set_xlabel(r"2$\theta$ (degrees)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.grid(True, linestyle='--', alpha=0.5)
        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CrystalArchitect()
    window.show()
    sys.exit(app.exec_())
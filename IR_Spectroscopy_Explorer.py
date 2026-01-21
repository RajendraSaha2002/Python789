import sys
import numpy as np
from scipy.linalg import eigh
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QFrame, QSplitter)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import mpl_toolkits.mplot3d.art3d as art3d


# --- Physics Engine: Normal Mode Analysis ---

class MolecularPhysics:
    def __init__(self):
        # Define Molecule: Water (H2O)
        # Approximate Geometry (Angstroms)
        # O at origin, H's in XY plane
        # O-H bond length ~0.96 A, Angle ~104.5 degrees

        angle_rad = np.radians(104.5 / 2)
        bond_len = 0.96

        # Coordinates: [x, y, z]
        self.atoms = ["H", "O", "H"]
        self.masses = np.array([1.008, 15.999, 1.008])  # AMU

        self.coords = np.array([
            [bond_len * np.sin(angle_rad), bond_len * np.cos(angle_rad), 0.0],  # H1
            [0.0, 0.0, 0.0],  # O
            [-bond_len * np.sin(angle_rad), bond_len * np.cos(angle_rad), 0.0]  # H2
        ])

        self.num_atoms = len(self.atoms)
        self.modes = []
        self.frequencies = []

        # Physics Constants for "Springs"
        # k_bond approx 500 N/m = 5 mdyn/A (approximate for O-H)
        # k_angle (simulated as a spring between H-H)
        self.k_bond = 5.0
        self.k_angle = 0.5

    def calculate_modes(self):
        """
        Solves the Eigenvalue problem for the Mass-Weighted Hessian Matrix.
        This allows us to find the natural frequencies and movement vectors.
        """
        N = self.num_atoms
        Hessian = np.zeros((3 * N, 3 * N))

        # --- Build Hessian (Simplified Spring Model) ---
        # We model bonds as springs obeying Hooke's law: V = 0.5 * k * (r - r0)^2
        # We calculate the second derivatives (force constants) numerically or analytically.
        # For this demo, we use a connectivity map and apply spring forces.

        # Connectivity: (Atom1, Atom2, SpringConstant)
        springs = [
            (0, 1, self.k_bond),  # H1-O
            (1, 2, self.k_bond),  # O-H2
            (0, 2, self.k_angle)  # H1-H2 (Simulates angle bending)
        ]

        # Populate Hessian via numerical differentiation of Gradient
        eps = 1e-4

        def get_forces(current_coords):
            forces = np.zeros_like(current_coords)
            for i, j, k in springs:
                # Vector r_ij
                vec = current_coords[j] - current_coords[i]
                dist = np.linalg.norm(vec)

                # Equilibrium distance (taken from initial geometry)
                vec_eq = self.coords[j] - self.coords[i]
                dist_eq = np.linalg.norm(vec_eq)

                # Force magnitude F = -k(r - r0)
                # We need vector force. Direction is vec / dist
                force_mag = -k * (dist - dist_eq)
                force_vec = force_mag * (vec / dist)

                forces[j] += force_vec
                forces[i] -= force_vec
            return forces.flatten()

        # Finite Difference to build Hessian
        # H_ij = dF_i / dx_j
        base_forces = get_forces(self.coords)

        for i in range(3 * N):
            # Perturb coordinate i
            perturb_coords = self.coords.flatten()
            perturb_coords[i] += eps
            perturb_coords = perturb_coords.reshape((N, 3))

            new_forces = get_forces(perturb_coords)

            # Derivative
            diff = (base_forces - new_forces) / eps
            # Note: Force F = -dV/dx. Hessian is d^2V/dx^2 = -dF/dx.
            # So H = (F_base - F_new) / dx

            Hessian[:, i] = diff

        # --- Mass Weighting ---
        # M_ij = H_ij / sqrt(m_i * m_j)
        mass_vector = []
        for m in self.masses:
            mass_vector.extend([m, m, m])  # x, y, z
        mass_vector = np.array(mass_vector)

        M = np.zeros_like(Hessian)
        for i in range(3 * N):
            for j in range(3 * N):
                M[i, j] = Hessian[i, j] / np.sqrt(mass_vector[i] * mass_vector[j])

        # --- Solve Eigenproblem ---
        # w^2 are eigenvalues, v are eigenvectors
        evals, evecs = eigh(M)

        # Process results
        self.modes = []
        self.frequencies = []

        for i in range(len(evals)):
            val = evals[i]
            if val > 0.1:  # Filter out Translations/Rotations (near 0)
                freq = np.sqrt(val) * 1300  # Arbitrary scaling factor to look like cm-1

                # Get eigenvector (displacement)
                # Need to un-mass-weight the eigenvector to get Cartesian displacements
                # L = M^(-1/2) * Q
                vec_mass_weighted = evecs[:, i]
                vec_cartesian = vec_mass_weighted / np.sqrt(mass_vector)

                # Normalize vector
                vec_cartesian = vec_cartesian / np.linalg.norm(vec_cartesian)

                self.frequencies.append(freq)
                self.modes.append(vec_cartesian.reshape((N, 3)))

        # Sort by frequency (high to low usually in IR, but low to high is fine)
        # Let's verify we have 3 modes for H2O (3N - 6 = 3)
        # The logic above usually finds the 3 stretches/bends accurately.


# --- GUI & Visualization ---

class SpectrumCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(SpectrumCanvas, self).__init__(fig)
        self.setParent(parent)
        fig.tight_layout()


class MoleculeCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111, projection='3d')
        super(MoleculeCanvas, self).__init__(fig)
        self.setParent(parent)
        fig.patch.set_facecolor('black')
        self.axes.set_facecolor('black')
        self.axes.grid(False)
        self.axes.axis('off')


class IRExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IR Spectroscopy: The Vibration Explorer")
        self.setGeometry(100, 100, 1000, 800)

        # Physics
        self.physics = MolecularPhysics()
        self.physics.calculate_modes()
        self.current_mode_index = 0
        self.is_animating = True

        self.setup_ui()
        self.plot_spectrum()
        self.start_animation()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Header
        header = QLabel("Water Molecule (H₂O) - Normal Mode Analysis")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Splitter for 3D View (Top) and Spectrum (Bottom)
        splitter = QSplitter(Qt.Vertical)

        # 3D Canvas
        self.mol_canvas = MoleculeCanvas(self, width=5, height=5, dpi=100)
        splitter.addWidget(self.mol_canvas)

        # Spectrum Canvas
        self.spec_canvas = SpectrumCanvas(self, width=5, height=3, dpi=100)
        self.spec_canvas.mpl_connect('button_press_event', self.on_spectrum_click)
        splitter.addWidget(self.spec_canvas)

        layout.addWidget(splitter)

        # Instructions
        info = QLabel("Click on a peak in the spectrum below to visualize the vibration.")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

    def plot_spectrum(self):
        ax = self.spec_canvas.axes
        ax.clear()

        freqs = self.physics.frequencies
        intensities = [0.8, 0.4, 1.0]  # Mock intensities for the 3 modes
        if len(freqs) > 3: intensities = np.random.rand(len(freqs))

        # Invert X axis (standard for IR)
        # Plot "Sticks"
        self.bars = ax.bar(freqs, intensities, width=50, color='crimson', alpha=0.7, picker=5)

        # Lorentzians for visual appeal
        x_smooth = np.linspace(min(freqs) - 500, max(freqs) + 500, 1000)
        y_smooth = np.zeros_like(x_smooth)
        for f, i in zip(freqs, intensities):
            # Add Lorentzian peak
            gamma = 50
            y_smooth += i * (gamma ** 2 / ((x_smooth - f) ** 2 + gamma ** 2))

        ax.plot(x_smooth, y_smooth, 'k-', linewidth=1, alpha=0.5)

        ax.set_xlim(max(freqs) + 200, min(freqs) - 200)  # Inverted Scale
        ax.set_ylim(0, 1.2)
        ax.set_xlabel("Wavenumber ($cm^{-1}$)")
        ax.set_ylabel("Transmittance (Simulated)")
        ax.set_title("Infrared Spectrum")
        ax.grid(True, linestyle='--', alpha=0.3)
        self.spec_canvas.draw()

    def on_spectrum_click(self, event):
        if event.inaxes != self.spec_canvas.axes: return

        # Find closest frequency
        click_x = event.xdata
        if click_x is None: return

        # Find nearest mode
        freqs = np.array(self.physics.frequencies)
        idx = (np.abs(freqs - click_x)).argmin()

        self.current_mode_index = idx
        freq = freqs[idx]
        print(f"Selected Mode: {freq:.1f} cm-1")

        # Highlight selected bar
        for i, bar in enumerate(self.bars):
            bar.set_color('crimson' if i != idx else 'blue')
        self.spec_canvas.draw()

    def start_animation(self):
        # Animation Func
        def update(frame):
            ax = self.mol_canvas.axes
            ax.clear()
            ax.set_facecolor('black')
            ax.axis('off')

            # Physics Calculation
            t = frame * 0.1
            mode_vec = self.physics.modes[self.current_mode_index]
            base_coords = self.physics.coords

            # Apply Vibration: r(t) = r0 + A * mode * sin(t)
            amplitude = 0.4
            current_coords = base_coords + amplitude * mode_vec * np.sin(t)

            # Drawing

            # Bonds (Connect 0-1 and 1-2)
            # O is index 1
            bonds = [(0, 1), (1, 2)]
            for i, j in bonds:
                p1 = current_coords[i]
                p2 = current_coords[j]
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                        color='white', linewidth=4, alpha=0.8)

            # Atoms
            # Colors: H=White, O=Red
            colors = ['white', 'red', 'white']
            sizes = [100, 300, 100]

            xs = current_coords[:, 0]
            ys = current_coords[:, 1]
            zs = current_coords[:, 2]

            ax.scatter(xs, ys, zs, s=sizes, c=colors, depthshade=True)

            # Set consistent view limits
            limit = 1.5
            ax.set_xlim(-limit, limit)
            ax.set_ylim(-limit, limit)
            ax.set_zlim(-limit, limit)

            # Add Frequency Text
            freq = self.physics.frequencies[self.current_mode_index]
            ax.text2D(0.05, 0.95, f"Frequency: {freq:.1f} cm⁻¹",
                      transform=ax.transAxes, color='white', fontsize=12)

        self.anim = FuncAnimation(self.mol_canvas.figure, update, frames=200, interval=50)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IRExplorer()
    window.show()
    sys.exit(app.exec_())
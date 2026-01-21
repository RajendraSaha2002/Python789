"""
Interactive Quantum Orbital Visualizer
Visualizes electron orbitals using spherical harmonics and Laguerre polynomials
Solves the Schrödinger equation for hydrogen-like atoms
"""

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from scipy.special import sph_harm, genlaguerre, factorial
import threading


class QuantumOrbitalVisualizer:
    def __init__(self):
        self.n = 1  # Principal quantum number
        self.l = 0  # Angular momentum quantum number
        self.m = 0  # Magnetic quantum number
        self.iso_value = 0.1  # Isosurface threshold
        self.grid_size = 50  # Resolution
        self.a0 = 1.0  # Bohr radius (normalized)

        # Computed data
        self.psi = None
        self.psi_squared = None
        self.grid = None

    def radial_wavefunction(self, r, n, l):
        """
        Compute radial wavefunction R_nl(r) using Laguerre polynomials

        R_nl(r) = sqrt((2/n*a0)^3 * (n-l-1)! / (2n[(n+l)!]^3)) *
                  exp(-r/n*a0) * (2r/n*a0)^l * L_{n-l-1}^{2l+1}(2r/n*a0)
        """
        a0 = self.a0
        rho = 2.0 * r / (n * a0)

        # Normalization constant
        norm = np.sqrt(
            (2.0 / (n * a0)) ** 3 *
            factorial(n - l - 1) /
            (2.0 * n * factorial(n + l) ** 3)
        )

        # Generalized Laguerre polynomial L_{n-l-1}^{2l+1}
        laguerre_poly = genlaguerre(n - l - 1, 2 * l + 1)

        # Radial wavefunction
        R_nl = norm * np.exp(-rho / 2.0) * rho ** l * laguerre_poly(rho)

        return R_nl

    def angular_wavefunction(self, theta, phi, l, m):
        """
        Compute angular wavefunction using spherical harmonics Y_l^m(theta, phi)
        Uses scipy.special.sph_harm which returns Y_l^m
        """
        # Note: scipy uses Y_l^m(phi, theta) convention
        Y_lm = sph_harm(m, l, phi, theta)
        return Y_lm

    def wavefunction(self, r, theta, phi, n, l, m):
        """
        Complete wavefunction: ψ_nlm(r,θ,φ) = R_nl(r) * Y_l^m(θ,φ)
        """
        R_nl = self.radial_wavefunction(r, n, l)
        Y_lm = self.angular_wavefunction(theta, phi, l, m)
        psi = R_nl * Y_lm
        return psi

    def compute_orbital(self, n, l, m, grid_size=50):
        """Compute the orbital on a 3D grid"""
        self.n, self.l, self.m = n, l, m
        self.grid_size = grid_size

        # Create 3D grid in spherical coordinates
        max_radius = n ** 2 * 3  # Extend beyond most probable radius

        # Cartesian grid
        x = np.linspace(-max_radius, max_radius, grid_size)
        y = np.linspace(-max_radius, max_radius, grid_size)
        z = np.linspace(-max_radius, max_radius, grid_size)

        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')

        # Convert to spherical coordinates
        R = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
        R[R == 0] = 1e-10  # Avoid division by zero

        Theta = np.arccos(Z / R)
        Phi = np.arctan2(Y, X)

        # Compute wavefunction
        self.psi = self.wavefunction(R, Theta, Phi, n, l, m)
        self.psi_squared = np.abs(self.psi) ** 2
        self.grid = (X, Y, Z)

        return self.psi_squared

    def get_orbital_name(self, n, l):
        """Convert quantum numbers to orbital name"""
        orbital_letters = ['s', 'p', 'd', 'f', 'g', 'h']
        if l < len(orbital_letters):
            return f"{n}{orbital_letters[l]}"
        return f"{n}(l={l})"


class OrbitalVisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Quantum Orbital Visualizer")
        self.root.geometry("1200x800")

        self.visualizer = QuantumOrbitalVisualizer()
        self.current_plot = None
        self.is_computing = False

        self.setup_ui()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Controls
        control_frame = ttk.LabelFrame(main_frame, text="Quantum Numbers & Controls", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Title
        title_label = ttk.Label(control_frame, text="Quantum Orbital Visualizer",
                                font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # Quantum numbers
        qn_frame = ttk.LabelFrame(control_frame, text="Quantum Numbers", padding="10")
        qn_frame.pack(fill=tk.X, pady=5)

        # Principal quantum number n
        ttk.Label(qn_frame, text="n (Principal):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.n_var = tk.IntVar(value=1)
        self.n_spinbox = ttk.Spinbox(qn_frame, from_=1, to=7, textvariable=self.n_var,
                                     width=10, command=self.update_l_limits)
        self.n_spinbox.grid(row=0, column=1, pady=5, padx=5)

        # Angular momentum quantum number l
        ttk.Label(qn_frame, text="l (Angular):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.l_var = tk.IntVar(value=0)
        self.l_spinbox = ttk.Spinbox(qn_frame, from_=0, to=0, textvariable=self.l_var,
                                     width=10, command=self.update_m_limits)
        self.l_spinbox.grid(row=1, column=1, pady=5, padx=5)

        # Magnetic quantum number m
        ttk.Label(qn_frame, text="m (Magnetic):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.m_var = tk.IntVar(value=0)
        self.m_spinbox = ttk.Spinbox(qn_frame, from_=0, to=0, textvariable=self.m_var,
                                     width=10)
        self.m_spinbox.grid(row=2, column=1, pady=5, padx=5)

        # Orbital name display
        self.orbital_name_label = ttk.Label(qn_frame, text="Orbital: 1s",
                                            font=("Arial", 12, "bold"), foreground="blue")
        self.orbital_name_label.grid(row=3, column=0, columnspan=2, pady=10)

        # Common orbitals quick select
        quick_frame = ttk.LabelFrame(control_frame, text="Quick Select", padding="10")
        quick_frame.pack(fill=tk.X, pady=5)

        orbitals = [
            ("1s", 1, 0, 0), ("2s", 2, 0, 0), ("2p", 2, 1, 0),
            ("3s", 3, 0, 0), ("3p", 3, 1, 0), ("3d", 3, 2, 0),
            ("4s", 4, 0, 0), ("4p", 4, 1, 1), ("4d", 4, 2, 0)
        ]

        for i, (name, n, l, m) in enumerate(orbitals):
            btn = ttk.Button(quick_frame, text=name, width=6,
                             command=lambda n=n, l=l, m=m: self.set_quantum_numbers(n, l, m))
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2)

        # Visualization settings
        vis_frame = ttk.LabelFrame(control_frame, text="Visualization", padding="10")
        vis_frame.pack(fill=tk.X, pady=5)

        # Iso-value slider
        ttk.Label(vis_frame, text="Iso-value (threshold):").pack(anchor=tk.W)
        self.iso_var = tk.DoubleVar(value=0.1)
        iso_scale = ttk.Scale(vis_frame, from_=0.01, to=0.5, variable=self.iso_var,
                              orient=tk.HORIZONTAL, length=200, command=self.update_iso_label)
        iso_scale.pack(fill=tk.X, pady=5)
        self.iso_label = ttk.Label(vis_frame, text="0.100")
        self.iso_label.pack()

        # Resolution
        ttk.Label(vis_frame, text="Grid Resolution:").pack(anchor=tk.W, pady=(10, 0))
        self.res_var = tk.IntVar(value=50)
        res_combo = ttk.Combobox(vis_frame, textvariable=self.res_var,
                                 values=[30, 40, 50, 60, 70], width=10, state='readonly')
        res_combo.pack(pady=5)
        res_combo.current(2)

        # Render buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=20)

        self.render_button = ttk.Button(button_frame, text="Render Orbital",
                                        command=self.render_orbital, width=20)
        self.render_button.pack(pady=5)

        self.slice_button = ttk.Button(button_frame, text="Show Cross-Section",
                                       command=self.show_slice, width=20)
        self.slice_button.pack(pady=5)

        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var,
                                            maximum=100, length=200)
        self.progress_bar.pack(pady=5)

        self.status_label = ttk.Label(control_frame, text="Ready", foreground="green")
        self.status_label.pack(pady=5)

        # Info panel
        info_frame = ttk.LabelFrame(control_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        info_text = tk.Text(info_frame, height=10, width=30, wrap=tk.WORD, font=("Arial", 9))
        info_text.pack(fill=tk.BOTH, expand=True)
        info_text.insert("1.0",
                         "Quantum Numbers:\n\n"
                         "n: Principal (1, 2, 3, ...)\n"
                         "  Energy level\n\n"
                         "l: Angular (0 to n-1)\n"
                         "  0=s, 1=p, 2=d, 3=f\n\n"
                         "m: Magnetic (-l to +l)\n"
                         "  Orbital orientation\n\n"
                         "The visualization shows |ψ|² isosurfaces"
                         )
        info_text.config(state=tk.DISABLED)

        # Right panel - 3D Visualization
        plot_frame = ttk.LabelFrame(main_frame, text="3D Orbital Visualization", padding="10")
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Matplotlib 3D figure
        self.fig = Figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X (Bohr radii)')
        self.ax.set_ylabel('Y (Bohr radii)')
        self.ax.set_zlabel('Z (Bohr radii)')
        self.ax.set_title('Quantum Orbital')

        # Initial placeholder
        self.ax.text(0.5, 0.5, 0.5, 'Click "Render Orbital" to begin',
                     ha='center', va='center', fontsize=14, transform=self.ax.transAxes)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Initialize limits
        self.update_l_limits()
        self.update_orbital_name()

    def update_l_limits(self, *args):
        """Update l spinbox limits based on n"""
        n = self.n_var.get()
        self.l_spinbox.config(to=n - 1)
        if self.l_var.get() >= n:
            self.l_var.set(0)
        self.update_m_limits()
        self.update_orbital_name()

    def update_m_limits(self, *args):
        """Update m spinbox limits based on l"""
        l = self.l_var.get()
        self.m_spinbox.config(from_=-l, to=l)
        if abs(self.m_var.get()) > l:
            self.m_var.set(0)
        self.update_orbital_name()

    def update_orbital_name(self):
        """Update the displayed orbital name"""
        n = self.n_var.get()
        l = self.l_var.get()
        m = self.m_var.get()
        name = self.visualizer.get_orbital_name(n, l)
        if m != 0:
            name += f" (m={m:+d})"
        self.orbital_name_label.config(text=f"Orbital: {name}")

    def update_iso_label(self, value):
        """Update iso-value label"""
        self.iso_label.config(text=f"{float(value):.3f}")

    def set_quantum_numbers(self, n, l, m):
        """Set quantum numbers from quick select"""
        self.n_var.set(n)
        self.update_l_limits()
        self.l_var.set(l)
        self.update_m_limits()
        self.m_var.set(m)
        self.update_orbital_name()

    def render_orbital(self):
        """Render the 3D orbital"""
        if self.is_computing:
            messagebox.showwarning("Busy", "Already computing...")
            return

        self.is_computing = True
        self.render_button.config(state=tk.DISABLED)
        self.status_label.config(text="Computing...", foreground="orange")
        self.progress_var.set(0)

        # Run in thread
        thread = threading.Thread(target=self._render_thread, daemon=True)
        thread.start()

    def _render_thread(self):
        """Background rendering thread"""
        try:
            n = self.n_var.get()
            l = self.l_var.get()
            m = self.m_var.get()
            res = self.res_var.get()
            iso = self.iso_var.get()

            # Compute orbital
            self.root.after(0, lambda: self.progress_var.set(20))
            psi_squared = self.visualizer.compute_orbital(n, l, m, grid_size=res)

            self.root.after(0, lambda: self.progress_var.set(60))

            # Plot
            self.root.after(0, lambda: self._plot_orbital(psi_squared, iso))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to render: {str(e)}"))
        finally:
            self.root.after(0, self._render_complete)

    def _plot_orbital(self, psi_squared, iso_value):
        """Plot the 3D isosurface"""
        self.ax.clear()

        X, Y, Z = self.visualizer.grid

        # Normalize for better visualization
        psi_norm = psi_squared / np.max(psi_squared)

        # Find isosurface points
        mask = psi_norm > iso_value

        if np.sum(mask) == 0:
            self.ax.text(0.5, 0.5, 0.5, 'No points above threshold\nTry lower iso-value',
                         ha='center', va='center', fontsize=12, transform=self.ax.transAxes)
        else:
            # Plot points as scatter (simplified - could use marching cubes for true surface)
            # Downsample for performance
            step = max(1, self.visualizer.grid_size // 30)
            x_plot = X[mask][::step]
            y_plot = Y[mask][::step]
            z_plot = Z[mask][::step]
            c_plot = psi_norm[mask][::step]

            scatter = self.ax.scatter(x_plot, y_plot, z_plot, c=c_plot,
                                      cmap='viridis', alpha=0.6, s=2)
            self.fig.colorbar(scatter, ax=self.ax, label='|ψ|² (normalized)',
                              shrink=0.6, pad=0.1)

        # Labels
        name = self.visualizer.get_orbital_name(self.n_var.get(), self.l_var.get())
        m = self.m_var.get()
        if m != 0:
            name += f" (m={m:+d})"

        self.ax.set_xlabel('X (Bohr radii)')
        self.ax.set_ylabel('Y (Bohr radii)')
        self.ax.set_zlabel('Z (Bohr radii)')
        self.ax.set_title(f'Quantum Orbital: {name}')

        # Equal aspect ratio
        max_range = np.max([X.max() - X.min(), Y.max() - Y.min(), Z.max() - Z.min()]) / 2
        mid_x = (X.max() + X.min()) / 2
        mid_y = (Y.max() + Y.min()) / 2
        mid_z = (Z.max() + Z.min()) / 2
        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

        self.canvas.draw()
        self.progress_var.set(100)

    def _render_complete(self):
        """Called when rendering completes"""
        self.is_computing = False
        self.render_button.config(state=tk.NORMAL)
        self.status_label.config(text="Render complete!", foreground="green")

    def show_slice(self):
        """Show 2D cross-section through the orbital"""
        if self.visualizer.psi_squared is None:
            messagebox.showinfo("Info", "Please render an orbital first")
            return

        # Create new window for slice
        slice_window = tk.Toplevel(self.root)
        slice_window.title("Orbital Cross-Section")
        slice_window.geometry("800x600")

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        X, Y, Z = self.visualizer.grid
        psi_sq = self.visualizer.psi_squared

        mid = self.visualizer.grid_size // 2

        # XY plane (z=0)
        axes[0, 0].imshow(psi_sq[:, :, mid].T, cmap='hot', origin='lower',
                          extent=[X.min(), X.max(), Y.min(), Y.max()])
        axes[0, 0].set_title('XY Plane (z=0)')
        axes[0, 0].set_xlabel('X')
        axes[0, 0].set_ylabel('Y')

        # XZ plane (y=0)
        axes[0, 1].imshow(psi_sq[:, mid, :].T, cmap='hot', origin='lower',
                          extent=[X.min(), X.max(), Z.min(), Z.max()])
        axes[0, 1].set_title('XZ Plane (y=0)')
        axes[0, 1].set_xlabel('X')
        axes[0, 1].set_ylabel('Z')

        # YZ plane (x=0)
        axes[1, 0].imshow(psi_sq[mid, :, :].T, cmap='hot', origin='lower',
                          extent=[Y.min(), Y.max(), Z.min(), Z.max()])
        axes[1, 0].set_title('YZ Plane (x=0)')
        axes[1, 0].set_xlabel('Y')
        axes[1, 0].set_ylabel('Z')

        # Radial probability
        r_max = int(np.sqrt(X ** 2 + Y ** 2 + Z ** 2).max())
        r_bins = np.linspace(0, r_max, 100)
        r_values = np.sqrt(X ** 2 + Y ** 2 + Z ** 2).flatten()
        psi_values = psi_sq.flatten()

        radial_prob = np.zeros(len(r_bins) - 1)
        for i in range(len(r_bins) - 1):
            mask = (r_values >= r_bins[i]) & (r_values < r_bins[i + 1])
            if np.sum(mask) > 0:
                radial_prob[i] = np.mean(psi_values[mask]) * r_bins[i] ** 2

        axes[1, 1].plot(r_bins[:-1], radial_prob, 'b-', linewidth=2)
        axes[1, 1].set_title('Radial Probability Distribution')
        axes[1, 1].set_xlabel('r (Bohr radii)')
        axes[1, 1].set_ylabel('P(r)')
        axes[1, 1].grid(True, alpha=0.3)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=slice_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def main():
    root = tk.Tk()
    app = OrbitalVisualizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
import numpy as np
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr


class SeismicTomography:
    def __init__(self, nx=30, ny=30, dx=1.0, dy=1.0):
        self.nx = nx
        self.ny = ny
        self.dx = dx
        self.dy = dy

        self.width = nx * dx
        self.height = ny * dy

        # Grid edge coordinates for ray-intersection calculations
        self.x_edges = np.linspace(0, self.width, nx + 1)
        self.y_edges = np.linspace(0, self.height, ny + 1)

        self.rays = []
        self.G = None  # Fréchet Sensitivity Matrix
        self.hit_count = None

    def setup_geometry(self):
        """Sets up cross-hole and surface-to-surface source/receiver geometries."""
        sources = []
        receivers = []

        # Sources along Left and Top boundaries
        for y in np.linspace(0, self.height, 15):
            sources.append((0.0, y))
        for x in np.linspace(0, self.width, 15):
            sources.append((x, 0.0))

        # Receivers along Right and Bottom boundaries
        for y in np.linspace(0, self.height, 20):
            receivers.append((self.width, y))
        for x in np.linspace(0, self.width, 20):
            receivers.append((x, self.height))

        # Create crossing ray pairs (All sources to all receivers)
        for sx, sy in sources:
            for rx, ry in receivers:
                self.rays.append((sx, sy, rx, ry))

        print(f"Geometry initialized with {len(self.rays)} ray paths.")

    def build_frechet_matrix(self):
        """
        Calculates the Fréchet sensitivity kernel (G matrix) using Siddon's algorithm.
        Maps the distance each ray travels through each specific grid cell.
        """
        n_rays = len(self.rays)
        n_cells = self.nx * self.ny

        row_idx = []
        col_idx = []
        data = []

        self.hit_count = np.zeros(n_cells)

        for i, (sx, sy, rx, ry) in enumerate(self.rays):
            dist = np.hypot(rx - sx, ry - sy)
            if dist < 1e-6:
                continue

            # Parametric line equations: t varies from 0 to 1
            # Find t values where the ray crosses grid lines
            if abs(rx - sx) > 1e-9:
                tx = (self.x_edges - sx) / (rx - sx)
            else:
                tx = np.array([])

            if abs(ry - sy) > 1e-9:
                ty = (self.y_edges - sy) / (ry - sy)
            else:
                ty = np.array([])

            # Keep only intersections within the ray segment bounds [0, 1]
            tx = tx[(tx >= 0.0) & (tx <= 1.0)]
            ty = ty[(ty >= 0.0) & (ty <= 1.0)]

            # Combine, add start and end points, and sort
            t_all = np.unique(np.concatenate(([0.0, 1.0], tx, ty)))
            t_all.sort()

            # Calculate segment lengths inside each cell
            for j in range(len(t_all) - 1):
                t_mid = (t_all[j] + t_all[j + 1]) / 2.0
                x_mid = sx + t_mid * (rx - sx)
                y_mid = sy + t_mid * (ry - sy)

                ix = int(x_mid / self.dx)
                iy = int(y_mid / self.dy)

                # Clamp indices to handle floating point edge cases
                ix = max(0, min(self.nx - 1, ix))
                iy = max(0, min(self.ny - 1, iy))

                cell_idx = iy * self.nx + ix
                segment_len = (t_all[j + 1] - t_all[j]) * dist

                if segment_len > 1e-6:
                    row_idx.append(i)
                    col_idx.append(cell_idx)
                    data.append(segment_len)
                    self.hit_count[cell_idx] += 1

        # Construct Sparse CSR matrix for fast LSQR solving
        self.G = csr_matrix((data, (row_idx, col_idx)), shape=(n_rays, n_cells))
        print("Fréchet matrix G built successfully.")

    def create_anomaly_model(self, v_bg=5.0):
        """Creates a true velocity model with a fast and a slow structural anomaly."""
        V = np.ones((self.ny, self.nx)) * v_bg
        x, y = np.meshgrid(np.linspace(0, self.width, self.nx),
                           np.linspace(0, self.height, self.ny))

        # Slow anomaly (Red)
        slow_mask = ((x - 8) ** 2 + (y - 8) ** 2) < 25
        V[slow_mask] -= 0.8

        # Fast anomaly (Blue)
        fast_mask = ((x - 22) ** 2 + (y - 20) ** 2) < 30
        V[fast_mask] += 0.8

        return V

    def create_checkerboard_model(self, v_bg=5.0, freq=3):
        """Creates an alternating +/- velocity perturbation grid for resolution testing."""
        x = np.linspace(0, np.pi * freq, self.nx)
        y = np.linspace(0, np.pi * freq, self.ny)
        X, Y = np.meshgrid(x, y)

        perturbation = np.sin(X) * np.cos(Y) * 0.5
        return v_bg + perturbation

    def invert(self, V_true, v_bg=5.0, damp=1.5, noise_level=0.01):
        """
        Executes the linear travel-time inversion.
        d_obs = G * m_true + noise.
        We solve G * delta_s = delta_t using Damped LSQR.
        """
        S_true = 1.0 / V_true.flatten()
        S_init = np.ones(self.nx * self.ny) * (1.0 / v_bg)

        # 1. Forward Model (Calculate synthetic observed travel times)
        t_true = self.G.dot(S_true)

        # Add random Gaussian noise to synthetic times
        np.random.seed(42)
        t_obs = t_true + np.random.normal(0, noise_level * np.mean(t_true), len(t_true))

        # 2. Initial Model Times
        t_init = self.G.dot(S_init)

        # 3. Residuals Vector
        delta_t = t_obs - t_init

        # 4. Damped LSQR Inversion (Tikhonov Regularization built-in)
        # Solves: minimize ||G * ds - dt||^2 + damp^2 ||ds||^2
        delta_s, istop, itn, r1norm = lsqr(self.G, delta_t, damp=damp, iter_lim=1000)[:4]

        # 5. Model Update
        S_inv = S_init + delta_s

        # Prevent non-physical negative slownesses
        S_inv = np.clip(S_inv, a_min=1e-4, a_max=None)
        V_inv = 1.0 / S_inv

        # Calculate final residuals
        t_inv = self.G.dot(S_inv)
        residuals_init = t_obs - t_init
        residuals_inv = t_obs - t_inv

        return V_inv.reshape((self.ny, self.nx)), residuals_init, residuals_inv


def plot_dashboard():
    # 1. Initialize System
    tomo = SeismicTomography(nx=30, ny=30, dx=1.0, dy=1.0)
    tomo.setup_geometry()
    tomo.build_frechet_matrix()

    # 2. Setup Velocity Models
    V_true = tomo.create_anomaly_model()
    V_check = tomo.create_checkerboard_model()

    # 3. Run Inversions
    print("Inverting structural anomaly model...")
    V_inv, res_init, res_inv = tomo.invert(V_true, damp=2.0)

    print("Inverting checkerboard resolution test...")
    V_check_inv, _, _ = tomo.invert(V_check, damp=2.0)

    # 4. Rendering the Dashboard
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, axs = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('2D Seismic Tomography Inversion & Resolution Analysis', fontsize=18, fontweight='bold', y=0.96)

    extent = [0, tomo.width, tomo.height, 0]
    cmap = 'RdYlBu'  # Diverging colormap: Red (Slow) to Blue (Fast)
    vmin, vmax = 4.2, 5.8

    # --- Panel 1: True Model & Ray Paths ---
    ax = axs[0, 0]
    im1 = ax.imshow(V_true, extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)
    # Plot a subset of rays to avoid blacking out the screen
    for i, (sx, sy, rx, ry) in enumerate(tomo.rays[::40]):
        ax.plot([sx, rx], [sy, ry], 'k-', alpha=0.1, linewidth=0.5)
    ax.set_title("1. True Model & Ray Coverage Sample")
    ax.set_ylabel("Depth (km)")
    fig.colorbar(im1, ax=ax, label='Velocity (km/s)')

    # --- Panel 2: Ray Hit Count (Coverage Matrix) ---
    ax = axs[0, 1]
    hit_grid = tomo.hit_count.reshape((tomo.ny, tomo.nx))
    im2 = ax.imshow(hit_grid, extent=extent, cmap='viridis')
    ax.set_title("2. Fréchet Ray Density (Hit Count)")
    fig.colorbar(im2, ax=ax, label='Number of Intersections')

    # --- Panel 3: Inverted Model ---
    ax = axs[0, 2]
    im3 = ax.imshow(V_inv, extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title("3. LSQR Inverted Model")
    fig.colorbar(im3, ax=ax, label='Velocity (km/s)')

    # --- Panel 4: Checkerboard True Model ---
    ax = axs[1, 0]
    im4 = ax.imshow(V_check, extent=extent, cmap=cmap, vmin=4.5, vmax=5.5)
    ax.set_title("4. Checkerboard True Model")
    ax.set_ylabel("Depth (km)")
    ax.set_xlabel("Distance (km)")
    fig.colorbar(im4, ax=ax, label='Velocity (km/s)')

    # --- Panel 5: Checkerboard Inverted Model ---
    ax = axs[1, 1]
    im5 = ax.imshow(V_check_inv, extent=extent, cmap=cmap, vmin=4.5, vmax=5.5)
    ax.set_title("5. Checkerboard Inversion (Resolution Limits)")
    ax.set_xlabel("Distance (km)")
    fig.colorbar(im5, ax=ax, label='Velocity (km/s)')

    # --- Panel 6: Travel-Time Residuals ---
    ax = axs[1, 2]
    ax.hist(res_init, bins=50, alpha=0.6, color='red', label=f'Initial RMS: {np.sqrt(np.mean(res_init ** 2)):.3f}s')
    ax.hist(res_inv, bins=50, alpha=0.8, color='blue', label=f'Inverted RMS: {np.sqrt(np.mean(res_inv ** 2)):.3f}s')
    ax.set_title("6. Travel-Time Residual Histogram")
    ax.set_xlabel("Residual Time (Seconds)")
    ax.set_ylabel("Frequency")
    ax.legend()

    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    plt.show()


if __name__ == "__main__":
    plot_dashboard()
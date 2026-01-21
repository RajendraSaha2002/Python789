"""
2D Lattice Boltzmann Method (LBM) Wind Tunnel Simulation
Demonstrates Von Kármán Vortex Street behind a circular obstacle
Uses vectorized NumPy operations for performance
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle

# Simulation Parameters
NX = 400  # Grid width
NY = 150  # Grid height
OBSTACLE_X = NX // 4
OBSTACLE_Y = NY // 2
OBSTACLE_R = 15  # Obstacle radius

U_INLET = 0.1  # Inlet velocity
VISCOSITY = 0.02  # Kinematic viscosity
OMEGA = 1.0 / (3.0 * VISCOSITY + 0.5)  # Relaxation parameter (BGK)

# D2Q9 Lattice vectors
CX = np.array([0, 1, 0, -1, 0, 1, -1, -1, 1])
CY = np.array([0, 0, 1, 0, -1, 1, 1, -1, -1])
WEIGHTS = np.array([4 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 36, 1 / 36, 1 / 36, 1 / 36])

# Opposite directions for bounce-back
OPP = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6])


def create_obstacle():
    """Create circular obstacle mask"""
    x = np.arange(NX)
    y = np.arange(NY)
    X, Y = np.meshgrid(x, y)
    obstacle = ((X - OBSTACLE_X) ** 2 + (Y - OBSTACLE_Y) ** 2) < OBSTACLE_R ** 2
    return obstacle


def equilibrium(rho, ux, uy):
    """
    Compute equilibrium distribution function
    f_i^eq = w_i * rho * (1 + 3*c_i·u + 9/2*(c_i·u)^2 - 3/2*u^2)
    """
    cu = np.zeros((9, NY, NX))
    for i in range(9):
        cu[i] = CX[i] * ux + CY[i] * uy

    u_sq = ux ** 2 + uy ** 2

    feq = np.zeros((9, NY, NX))
    for i in range(9):
        feq[i] = WEIGHTS[i] * rho * (
                1.0 + 3.0 * cu[i] + 4.5 * cu[i] ** 2 - 1.5 * u_sq
        )

    return feq


def initialize():
    """Initialize simulation state"""
    # Macroscopic variables
    rho = np.ones((NY, NX))
    ux = np.ones((NY, NX)) * U_INLET
    uy = np.zeros((NY, NX))

    # Distribution functions
    f = equilibrium(rho, ux, uy)

    # Create obstacle
    obstacle = create_obstacle()

    return f, rho, ux, uy, obstacle


def stream(f):
    """
    Streaming step: propagate distribution functions
    Uses NumPy array slicing for vectorization
    """
    for i in range(9):
        f[i] = np.roll(f[i], CX[i], axis=1)  # Roll in x-direction
        f[i] = np.roll(f[i], CY[i], axis=0)  # Roll in y-direction

    return f


def compute_macroscopic(f):
    """Compute density and velocity from distribution functions"""
    rho = np.sum(f, axis=0)
    ux = np.sum(f * CX.reshape(9, 1, 1), axis=0) / rho
    uy = np.sum(f * CY.reshape(9, 1, 1), axis=0) / rho
    return rho, ux, uy


def collision(f, rho, ux, uy):
    """
    Collision step: BGK approximation
    f_i(x,t+dt) = f_i - omega * (f_i - f_i^eq)
    """
    feq = equilibrium(rho, ux, uy)
    f += OMEGA * (feq - f)
    return f


def apply_boundary_conditions(f, obstacle):
    """Apply boundary conditions"""
    # Inlet (left): constant velocity
    rho_inlet = 1.0
    ux_inlet = U_INLET
    uy_inlet = 0.0
    f[:, :, 0] = equilibrium(
        rho_inlet * np.ones((NY, 1)),
        ux_inlet * np.ones((NY, 1)),
        uy_inlet * np.ones((NY, 1))
    )[:, :, 0]

    # Outlet (right): copy from previous column
    f[:, :, -1] = f[:, :, -2]

    # Top and bottom walls: bounce-back
    # Bottom wall
    f[2, 0, :] = f[4, 0, :]
    f[5, 0, :] = f[7, 0, :]
    f[6, 0, :] = f[8, 0, :]

    # Top wall
    f[4, -1, :] = f[2, -1, :]
    f[7, -1, :] = f[5, -1, :]
    f[8, -1, :] = f[6, -1, :]

    # Obstacle: bounce-back
    for i in range(9):
        f[i, obstacle] = f[OPP[i], obstacle]

    return f


def compute_vorticity(ux, uy):
    """Compute vorticity (curl of velocity field)"""
    duy_dx = np.zeros_like(ux)
    dux_dy = np.zeros_like(ux)

    duy_dx[:, 1:-1] = (uy[:, 2:] - uy[:, :-2]) / 2.0
    dux_dy[1:-1, :] = (ux[2:, :] - ux[:-2, :]) / 2.0

    vorticity = duy_dx - dux_dy
    return vorticity


def simulate_step(f, obstacle):
    """Perform one simulation step"""
    # 1. Streaming
    f = stream(f)

    # 2. Apply boundary conditions
    f = apply_boundary_conditions(f, obstacle)

    # 3. Compute macroscopic variables
    rho, ux, uy = compute_macroscopic(f)

    # 4. Collision
    f = collision(f, rho, ux, uy)

    return f, rho, ux, uy


def main():
    """Main simulation loop with visualization"""
    print("Initializing Lattice Boltzmann simulation...")
    print(f"Grid: {NX} x {NY}")
    print(f"Inlet velocity: {U_INLET}")
    print(f"Viscosity: {VISCOSITY}")
    print(f"Reynolds number: ~{U_INLET * 2 * OBSTACLE_R / VISCOSITY:.1f}")

    # Initialize
    f, rho, ux, uy, obstacle = initialize()

    # Setup visualization
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(0, NX)
    ax.set_ylim(0, NY)
    ax.set_aspect('equal')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title('Lattice Boltzmann Wind Tunnel - Von Kármán Vortex Street')

    # Initial vorticity plot
    vorticity = compute_vorticity(ux, uy)
    im = ax.imshow(vorticity, cmap='RdBu', origin='lower',
                   extent=[0, NX, 0, NY], vmin=-0.05, vmax=0.05)

    # Draw obstacle
    circle = Circle((OBSTACLE_X, OBSTACLE_Y), OBSTACLE_R,
                    color='gray', zorder=10)
    ax.add_patch(circle)

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, label='Vorticity')

    # Step counter
    step_text = ax.text(0.02, 0.95, '', transform=ax.transAxes,
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    step_counter = [0]

    def update(frame):
        nonlocal f, rho, ux, uy

        # Run multiple steps per frame for speed
        for _ in range(5):
            f, rho, ux, uy = simulate_step(f, obstacle)
            step_counter[0] += 1

        # Update visualization
        vorticity = compute_vorticity(ux, uy)
        vorticity[obstacle] = 0  # Mask obstacle

        im.set_array(vorticity)
        step_text.set_text(f'Step: {step_counter[0]}')

        return [im, step_text]

    # Animate
    anim = FuncAnimation(fig, update, frames=1000,
                         interval=50, blit=True, repeat=True)

    plt.tight_layout()
    plt.show()

    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
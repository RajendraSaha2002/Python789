import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

# --- Configuration ---
# Gravitational Constant (approximate for solar system scales to keep numbers manageable)
# Using AU for distance, Years for time, and Solar Masses for mass reduces G to:
# G = 4 * pi^2  (approx 39.478)
G = 39.478

# Simulation settings
DT = 0.01  # Time step (in years)
STEPS = 500  # Number of steps to simulate for the animation duration
NUM_BODIES = 4  # Default bodies (Sun, Earth, Mars, Jupiter)


class NBodySimulator:
    def __init__(self, masses, positions, velocities, names=None):
        """
        Initialize the N-Body simulation.

        Args:
            masses (np.array): Shape (N, 1) array of masses.
            positions (np.array): Shape (N, 3) array of initial positions (x, y, z).
            velocities (np.array): Shape (N, 3) array of initial velocities (vx, vy, vz).
            names (list): List of names for the bodies (optional).
        """
        self.masses = np.array(masses).reshape(-1, 1)
        self.pos = np.array(positions, dtype=float)
        self.vel = np.array(velocities, dtype=float)
        self.acc = np.zeros_like(self.pos)
        self.num_bodies = len(masses)
        self.names = names if names else [f"Body {i}" for i in range(self.num_bodies)]
        self.history = [self.pos.copy()]

        # Initial acceleration calculation
        self.update_acceleration()

    def update_acceleration(self):
        """
        Calculate acceleration for all bodies using Newton's Law of Universal Gravitation.
        Vectorized implementation using NumPy broadcasting for O(N^2) complexity without loops.

        Formula: a_i = sum_j (G * m_j * r_ij / |r_ij|^3)
        """
        # r_ij is the vector pointing from body i to body j
        # We create a matrix where index [i, j] is pos[j] - pos[i]
        # pos shape: (N, 3) -> r_matrix shape: (N, N, 3)
        # Broadcasting: (N, 1, 3) - (1, N, 3) = (N, N, 3)
        r_matrix = self.pos[np.newaxis, :, :] - self.pos[:, np.newaxis, :]

        # Calculate distances (epsilon added to avoid division by zero for self-interaction)
        epsilon = 1e-10
        dist = np.linalg.norm(r_matrix, axis=2)
        dist[dist == 0] = epsilon  # Avoid division by zero diagonal

        # Calculate 1/r^3 term
        inv_dist3 = 1.0 / (dist ** 3)

        # Force magnitude scaling: G * m_j * 1/r^3
        # We need to broadcast masses across the correct axis
        # self.masses.T is (1, N), broadcasting against (N, N)
        acceleration_magnitude = G * self.masses.T * inv_dist3

        # Zero out the diagonal (self-interaction)
        np.fill_diagonal(acceleration_magnitude, 0)

        # Calculate acceleration vectors: sum((G * m_j / r^3) * r_vec)
        # We multiply the scalar magnitude matrix (N, N) with the vector matrix (N, N, 3)
        # The result is (N, N, 3), which we sum over the second axis (j) to get (N, 3)
        self.acc = np.sum(acceleration_magnitude[:, :, np.newaxis] * r_matrix, axis=1)

    def step_velocity_verlet(self, dt):
        """
        Advance the simulation by one time step using the Velocity Verlet integrator.
        Verlet is a symplectic integrator, offering better energy conservation than Euler or RK4 for orbits.

        1. v(t + 0.5*dt) = v(t) + 0.5 * a(t) * dt
        2. r(t + dt)     = r(t) + v(t + 0.5*dt) * dt
        3. a(t + dt)     = force(r(t + dt)) / m
        4. v(t + dt)     = v(t + 0.5*dt) + 0.5 * a(t + dt) * dt
        """
        # Half-step velocity update
        self.vel += 0.5 * self.acc * dt

        # Full-step position update
        self.pos += self.vel * dt

        # Calculate new forces/acceleration based on new positions
        self.update_acceleration()

        # Final half-step velocity update
        self.vel += 0.5 * self.acc * dt

        # Store history
        self.history.append(self.pos.copy())


def create_solar_system():
    """
    Creates a simplified solar system (Sun, Earth, Mars, Jupiter).
    Units: Mass in Solar Masses, Distance in AU, Velocity in AU/Year.
    """
    # Masses (approximate relative to Sun)
    masses = [
        1.0,  # Sun
        3.003e-6,  # Earth
        3.213e-7,  # Mars
        9.543e-4  # Jupiter
    ]

    # Initial Positions (AU) - starting on x-axis for simplicity
    positions = [
        [0.0, 0.0, 0.0],  # Sun
        [1.0, 0.0, 0.0],  # Earth
        [1.524, 0.0, 0.0],  # Mars
        [5.203, 0.0, 0.0]  # Jupiter
    ]

    # Initial Velocities (AU/Year) - perpendicular to position for circular(ish) orbits
    # v = sqrt(GM/r) roughly
    # Earth v approx 2*pi AU/year
    velocities = [
        [0.0, 0.0, 0.0],  # Sun (Stationary-ish)
        [0.0, 6.28, 0.0],  # Earth
        [0.0, 5.08, 0.2],  # Mars (slight z-inclination)
        [0.0, 2.75, 0.0]  # Jupiter
    ]

    names = ["Sun", "Earth", "Mars", "Jupiter"]

    return masses, positions, velocities, names


def run_simulation():
    # Setup
    print("Initializing Solar System Simulation...")
    masses, positions, velocities, names = create_solar_system()
    sim = NBodySimulator(masses, positions, velocities, names)

    # Pre-calculate simulation steps for smoother animation
    print(f"Calculating {STEPS} steps...")
    for _ in range(STEPS):
        sim.step_velocity_verlet(DT)

    # Convert history to numpy array for easier slicing: (Steps, Bodies, 3)
    history_np = np.array(sim.history)

    # Visualization
    print("Generating Animation...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot background
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')

    # Axis settings
    limit = 6.0  # AU
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_zlim(-limit, limit)
    ax.set_xlabel("X (AU)", color='white')
    ax.set_ylabel("Y (AU)", color='white')
    ax.set_zlabel("Z (AU)", color='white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.tick_params(axis='z', colors='white')

    # Colors for planets
    colors = ['yellow', 'blue', 'red', 'orange']
    sizes = [100, 20, 15, 60]  # Visual size only

    # Initialize lines and points
    lines = [ax.plot([], [], [], '-', color=colors[i], lw=1)[0] for i in range(sim.num_bodies)]
    points = [ax.plot([], [], [], 'o', color=colors[i], markersize=np.sqrt(sizes[i]))[0] for i in range(sim.num_bodies)]

    # Add grid text
    time_text = ax.text2D(0.05, 0.95, '', transform=ax.transAxes, color='white')

    def init():
        for line, point in zip(lines, points):
            line.set_data([], [])
            line.set_3d_properties([])
            point.set_data([], [])
            point.set_3d_properties([])
        time_text.set_text('')
        return lines + points + [time_text]

    def update(frame):
        # We'll use a trail length for the lines
        trail = 50
        start = max(0, frame - trail)

        current_time = frame * DT
        time_text.set_text(f'Time: {current_time:.2f} Years')

        for i in range(sim.num_bodies):
            # Update Orbit Trail
            # Matplotlib 3D plot needs separate x, y, z arrays
            x_trail = history_np[start:frame + 1, i, 0]
            y_trail = history_np[start:frame + 1, i, 1]
            z_trail = history_np[start:frame + 1, i, 2]

            lines[i].set_data(x_trail, y_trail)
            lines[i].set_3d_properties(z_trail)

            # Update Current Planet Position
            points[i].set_data([history_np[frame, i, 0]], [history_np[frame, i, 1]])
            points[i].set_3d_properties([history_np[frame, i, 2]])

        return lines + points + [time_text]

    ani = FuncAnimation(fig, update, frames=len(history_np), init_func=init, blit=False, interval=20)

    plt.title("N-Body Gravity Simulation (Velocity Verlet)", color='white')
    plt.show()


if __name__ == "__main__":
    run_simulation()
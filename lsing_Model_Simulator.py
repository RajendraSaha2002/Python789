import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from numba import jit

# --- Configuration ---
GRID_SIZE = 100  # Size of the NxN lattice
J = 1.0  # Interaction strength (Ferromagnetic if > 0)
KB = 1.0  # Boltzmann constant (normalized)
STEPS_PER_FRAME = 1  # Number of Monte Carlo sweeps per animation frame
START_TEMP = 4.0  # Starting temperature (High - Random)
END_TEMP = 1.0  # Ending temperature (Low - Ordered)
FRAMES = 300  # Total animation frames
CRITICAL_TEMP = 2.269  # Theoretical Tc for 2D square lattice


# --- The Physics (Numba Accelerated) ---
# We use @jit(nopython=True) to compile this function to machine code.
# Without Numba, the double loops over the grid would be extremely slow.

@jit(nopython=True)
def metropolis_step(lattice, T, J, steps=1):
    """
    Performs 'steps' Monte Carlo sweeps using the Metropolis-Hastings algorithm.
    One sweep is defined as N*N attempted flips.
    """
    N = lattice.shape[0]

    for _ in range(steps):
        for _ in range(N * N):
            # 1. Pick a random lattice site
            x = np.random.randint(0, N)
            y = np.random.randint(0, N)

            spin = lattice[x, y]

            # 2. Calculate sum of nearest neighbors (Periodic Boundary Conditions)
            # using modulo (%) to wrap around edges
            neighbor_sum = (
                    lattice[(x + 1) % N, y] +
                    lattice[(x - 1 + N) % N, y] +
                    lattice[x, (y + 1) % N] +
                    lattice[x, (y - 1 + N) % N]
            )

            # 3. Calculate energy change if we flipped this spin
            # H = -J * sum(sigma_i * sigma_j)
            # dE = E_flipped - E_current
            # Since spin is just flipping sign, dE = 2 * J * spin * neighbor_sum
            dE = 2 * J * spin * neighbor_sum

            # 4. Metropolis Criterion
            # If dE < 0, energy decreases (favorable), flip it.
            # If dE > 0, flip with probability exp(-dE / kT).
            if dE < 0 or np.random.random() < np.exp(-dE / (KB * T)):
                lattice[x, y] = -spin

    return lattice


@jit(nopython=True)
def calculate_magnetization(lattice):
    """Calculate the average magnetization of the lattice."""
    return np.abs(np.sum(lattice)) / (lattice.shape[0] * lattice.shape[1])


# --- Simulation & Visualization ---

def run_simulation():
    print(f"Initializing {GRID_SIZE}x{GRID_SIZE} Ising Model...")
    print("Using Numba for acceleration.")

    # Initialize random lattice (+1 or -1)
    # np.random.choice generates 0s and 1s, we map 0 -> -1
    lattice = np.random.choice([-1, 1], size=(GRID_SIZE, GRID_SIZE))

    # Setup Plot
    fig, (ax_img, ax_stats) = plt.subplots(2, 1, figsize=(7, 9), height_ratios=[3, 1])
    plt.subplots_adjust(hspace=0.3)

    # 1. Heatmap for the lattice
    # cmap='coolwarm' puts -1 as blue and +1 as red
    img = ax_img.imshow(lattice, cmap='coolwarm', animated=True, interpolation='nearest')
    ax_img.set_title(f"2D Ising Model\nTemperature: {START_TEMP:.2f}")
    ax_img.set_xticks([])
    ax_img.set_yticks([])

    # 2. Stats plot (Temperature vs Magnetization)
    temps = np.linspace(START_TEMP, END_TEMP, FRAMES)
    mags = []

    line_mag, = ax_stats.plot([], [], 'b-', label='Magnetization')
    point_curr, = ax_stats.plot([], [], 'ro')  # Current state marker

    # Add critical temperature line
    ax_stats.axvline(x=CRITICAL_TEMP, color='k', linestyle='--', alpha=0.5, label='Critical Temp (Tc)')

    ax_stats.set_xlim(START_TEMP, END_TEMP)  # Reversed axis usually looks nice for cooling, or standard
    ax_stats.set_xlim(min(START_TEMP, END_TEMP), max(START_TEMP, END_TEMP))
    ax_stats.invert_xaxis()  # High T on left, Low T on right (Cooling direction)
    ax_stats.set_ylim(0, 1.1)
    ax_stats.set_xlabel("Temperature (T)")
    ax_stats.set_ylabel("Avg Magnetization |M|")
    ax_stats.legend(loc='upper right')
    ax_stats.grid(True, alpha=0.3)

    def init():
        return img, line_mag, point_curr

    def update(frame):
        nonlocal lattice

        # Determine current temperature based on frame
        # Linear cooling schedule
        current_temp = temps[frame]

        # Perform Monte Carlo steps (Physics Update)
        # We perform multiple sweeps per frame to speed up equilibration visually
        lattice = metropolis_step(lattice, current_temp, J, steps=STEPS_PER_FRAME)

        # Calculate stats
        mag = calculate_magnetization(lattice)
        mags.append(mag)

        # Update Visuals
        img.set_array(lattice)
        ax_img.set_title(f"2D Ising Model\nTemperature: {current_temp:.2f} (Cooling)")

        # Update graph
        # X-data needs to match the length of Y-data (mags)
        current_temps_slice = temps[:len(mags)]
        line_mag.set_data(current_temps_slice, mags)
        point_curr.set_data([current_temp], [mag])

        return img, line_mag, point_curr

    print("Starting Animation...")
    ani = FuncAnimation(fig, update, frames=FRAMES, init_func=init, blit=False, interval=50)

    plt.show()


if __name__ == "__main__":
    # Check for Numba
    try:
        import numba

        run_simulation()
    except ImportError:
        print("Error: Numba is not installed.")
        print("Please install it using: pip install numba")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.sparse import diags
from scipy.sparse.linalg import splu

# --- Configuration ---
# System Parameters (Atomic Units: hbar=1, m=1)
HBAR = 1.0
MASS = 1.0
L = 100.0  # Length of the simulation domain
N = 1000  # Number of spatial grid points
DX = L / N  # Spatial step size
DT = 0.05  # Time step size
FRAMES = 400  # Animation frames
STEPS_PER_FRAME = 5  # Physics steps per animation frame

# --- Initialization ---
x = np.linspace(0, L, N)

# 1. Define the Potential V(x)
# A rectangular barrier in the middle
V_HEIGHT = 1.0
V_WIDTH = 4.0
V_CENTER = L / 2
V = np.zeros(N)
# Create barrier
barrier_mask = (x > V_CENTER - V_WIDTH / 2) & (x < V_CENTER + V_WIDTH / 2)
V[barrier_mask] = V_HEIGHT

# 2. Define Initial Wave Packet Psi(x, 0)
# Gaussian wave packet moving to the right
SIGMA = 5.0  # Width of the packet
X0 = L / 4  # Starting position
K0 = 1.3  # Initial momentum (determines energy)
# Energy approx = k^2/2. If E < V_HEIGHT, classical reflection happens.

# Normalization constant
norm_factor = 1.0 / np.sqrt(SIGMA * np.sqrt(np.pi))
# Wave function: Gaussian envelope * Plane wave (momentum)
psi = norm_factor * np.exp(-0.5 * ((x - X0) / SIGMA) ** 2) * np.exp(1j * K0 * x)

# --- Matrix Setup (Crank-Nicolson) ---
# We solve: (I + i*dt/2H * H) Psi(t+dt) = (I - i*dt/2H * H) Psi(t)
# Equation form: A * x = b

# Hamiltonian construction using Finite Difference Method for second derivative
# d2/dx2 ~ (f(x+dx) - 2f(x) + f(x-dx)) / dx^2
kin_factor = -HBAR ** 2 / (2 * MASS * DX ** 2)

# Main diagonal elements: -2*kin_factor + V[i]
main_diag = -2 * kin_factor * np.ones(N) + V
# Off diagonal elements: kin_factor
off_diag = kin_factor * np.ones(N - 1)

# Construct Sparse Hamiltonian Matrix
H = diags([off_diag, main_diag, off_diag], [-1, 0, 1], format='csc')

# Identity Matrix
I = diags([np.ones(N)], [0], format='csc')

# Crank-Nicolson Matrices
# factor = i * dt / (2 * hbar)
cn_factor = 1j * DT / (2 * HBAR)

A_implicit = I + cn_factor * H  # Left side matrix (to be inverted/solved)
A_explicit = I - cn_factor * H  # Right side matrix (just multiplication)

# Pre-compute the LU decomposition of the implicit matrix for fast solving
# This is crucial for performance.
solve_A = splu(A_implicit).solve

# --- Visualization Setup ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_facecolor('black')
fig.patch.set_facecolor('black')

# Plot setup
ax.set_xlim(0, L)
ax.set_ylim(-0.1, 0.5)  # Scale Y to fit probability density
ax.set_xlabel("Position (x)", color='white')
ax.set_ylabel("Probability Density |Ψ|²", color='white')
ax.tick_params(colors='white')
ax.grid(color='gray', linestyle='--', alpha=0.3)

# 1. Plot the Potential Barrier (Scaled for visibility)
# We scale V to match the plot range roughly
v_plot_scale = 0.3 / V_HEIGHT
ax.plot(x, V * v_plot_scale, 'r-', linewidth=2, label=f'Potential Barrier (V={V_HEIGHT})', alpha=0.7)
ax.fill_between(x, 0, V * v_plot_scale, color='red', alpha=0.2)

# 2. Plot the Probability Density
line_prob, = ax.plot([], [], 'c-', linewidth=2, label='Probability Density')
fill_prob = ax.fill_between([], [], color='cyan', alpha=0.3)

# Add text for energy comparison
E_approx = 0.5 * K0 ** 2  # E = p^2/2m (mass=1)
ax.text(0.02, 0.95, f"Particle Energy (E) ≈ {E_approx:.2f}", transform=ax.transAxes, color='cyan')
ax.text(0.02, 0.90, f"Barrier Height (V) = {V_HEIGHT:.2f}", transform=ax.transAxes, color='red')
status_text = ax.text(0.02, 0.85, "Tunneling Status: Approaching", transform=ax.transAxes, color='white')

ax.legend(loc='upper right')


def init():
    line_prob.set_data([], [])
    return line_prob, status_text


def update(frame):
    global psi, fill_prob

    # Evolve the system multiple small steps for every animation frame
    for _ in range(STEPS_PER_FRAME):
        # 1. Calculate RHS: b = A_explicit * psi
        b = A_explicit.dot(psi)
        # 2. Solve LHS: A_implicit * psi_new = b
        psi = solve_A(b)

    # Calculate Probability Density: |psi|^2
    # psi is complex, so we take abs()**2
    prob_density = np.abs(psi) ** 2

    # Update Line
    line_prob.set_data(x, prob_density)

    # Update Fill (requires removing old collection and adding new one)
    fill_prob.remove()
    fill_prob = ax.fill_between(x, 0, prob_density, color='cyan', alpha=0.3)

    # Simple status logic
    total_prob = np.sum(prob_density * DX)
    prob_right = np.sum(prob_density[x > V_CENTER] * DX)

    if prob_right > 0.01:
        status_text.set_text(f"Tunneling Status: Transmission {(prob_right / total_prob) * 100:.1f}%")
    else:
        status_text.set_text("Tunneling Status: Impact/Reflection")

    return line_prob, fill_prob, status_text


ani = FuncAnimation(fig, update, frames=FRAMES, init_func=init, interval=30, blit=False)
plt.title("Quantum Tunneling: Time-Dependent Schrödinger Equation", color='white')
plt.show()
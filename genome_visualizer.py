import psycopg2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'genome_db',
    'port': 5432
}

# Store the original "Healthy" genome for diff checking
REFERENCE_GENOME = []


def get_genome():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT position_index, base_pair FROM genome_sequence ORDER BY position_index")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB Error: {e}")
        return []


def init_reference():
    global REFERENCE_GENOME
    print("Loading Reference Genome...")
    REFERENCE_GENOME = get_genome()
    print(f"Reference Loaded: {len(REFERENCE_GENOME)} base pairs.")


# --- 3D MATH FOR DNA HELIX ---
def generate_helix_points(genome_data):
    n = len(genome_data)
    t = np.linspace(0, 4 * np.pi, n)  # 2 turns
    x = np.cos(t)
    y = np.sin(t)
    z = np.linspace(0, 10, n)

    # Second strand (offset by PI)
    x2 = np.cos(t + np.pi)
    y2 = np.sin(t + np.pi)

    colors = []

    # Diff Logic
    for i in range(n):
        current_bp = genome_data[i][1]

        # Check against reference
        if i < len(REFERENCE_GENOME):
            ref_bp = REFERENCE_GENOME[i][1]
            if current_bp != ref_bp:
                colors.append('red')  # MUTATION DETECTED
            else:
                colors.append('blue')  # HEALTHY
        else:
            colors.append('blue')

    return x, y, z, x2, y2, colors


# --- ANIMATION LOOP ---
def update_graph(num, ax):
    ax.clear()

    # 1. Fetch Live Data
    live_genome = get_genome()
    if not live_genome: return

    # 2. Math
    x1, y1, z, x2, y2, colors = generate_helix_points(live_genome)

    # 3. Render
    # Strand 1
    ax.plot(x1, y1, z, color='gray', alpha=0.5)
    # Strand 2
    ax.plot(x2, y2, z, color='gray', alpha=0.5)

    # Base Pairs (The Rungs)
    for i in range(len(z)):
        c = colors[i]
        size = 50 if c == 'red' else 20
        # Draw line between strands
        ax.plot([x1[i], x2[i]], [y1[i], y2[i]], [z[i], z[i]], color=c, linewidth=2)
        # Draw molecule
        ax.scatter(x1[i], y1[i], z[i], color=c, s=size)
        ax.scatter(x2[i], y2[i], z[i], color=c, s=size)

        # Label Mutation
        if c == 'red':
            ax.text(x1[i], y1[i], z[i], f" MUTATION! ({live_genome[i][1]})", color='red')

    ax.set_title("LIVE GENOME MONITORING (CRISPR-WATCH)")
    ax.set_zlim(0, 10)
    ax.axis('off')  # Hide axes for cleaner look


if __name__ == "__main__":
    init_reference()

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Animate
    ani = animation.FuncAnimation(fig, update_graph, fargs=(ax,), interval=1000)
    plt.show()
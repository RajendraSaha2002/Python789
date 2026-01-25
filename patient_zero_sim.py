import socket
import threading
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.animation import FuncAnimation
import random

# --- CONFIGURATION ---
GRID_SIZE = 20
HOST = '0.0.0.0'
PORT = 8888

# --- SIMULATION STATE ---
# 0 = Healthy (Low CPU), 100 = Crashed
# Infection adds complexity_score to CPU load
cpu_grid = np.zeros((GRID_SIZE, GRID_SIZE))
infection_status = np.zeros((GRID_SIZE, GRID_SIZE))  # 0=Clean, 1=Infected

# The virus parameters currently active
active_virus_complexity = 0
is_spreading = False


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[PATIENT ZERO] Listening on {PORT}...")
    except Exception as e:
        print(f"[ERROR] Port Bind Failed: {e}")
        return

    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_infection, args=(client,)).start()


def handle_infection(client_socket):
    global active_virus_complexity, is_spreading
    try:
        data = client_socket.recv(1024).decode('utf-8').strip()
        if data:
            print(f"[ALERT] Payload Received. Viral Complexity: {data}")

            # Reset / New Infection
            active_virus_complexity = int(data)

            # Infect Patient Zero (Center of Grid)
            center = GRID_SIZE // 2
            infection_status[center, center] = 1
            is_spreading = True

    except Exception as e:
        print(f"[ERROR] Handshake failed: {e}")
    finally:
        client_socket.close()


# --- BIOLOGICAL SPREAD LOGIC ---
def update_grid(frame):
    global cpu_grid, infection_status

    if not is_spreading:
        # Base state: Random low noise
        cpu_grid = np.random.randint(0, 10, (GRID_SIZE, GRID_SIZE))

        plt.clf()
        sns.heatmap(cpu_grid, vmin=0, vmax=100, cmap="Greens", cbar=False)
        plt.title("NETWORK STATUS: HEALTHY")
        return

    # Spread Logic
    # Copy current state to avoid modifying while iterating
    new_infections = infection_status.copy()

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if infection_status[r, c] == 1:
                # Apply CPU Load based on Virus Complexity
                # Random fluctuation + complexity
                load = active_virus_complexity + random.randint(-5, 10)
                cpu_grid[r, c] = min(100, max(0, load))

                # Attempt to infect neighbors (Up, Down, Left, Right)
                # Higher complexity = Slower spread (heavy payload), Lower = Faster
                spread_chance = 0.8 if active_virus_complexity < 50 else 0.3

                if random.random() < spread_chance:
                    # Random neighbor
                    nr, nc = r + random.randint(-1, 1), c + random.randint(-1, 1)
                    if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                        new_infections[nr, nc] = 1

    infection_status = new_infections

    # Visualization
    plt.clf()
    # Using 'inferno' colormap: Black/Purple (Safe) -> Orange/Yellow (High Load)
    ax = sns.heatmap(cpu_grid, vmin=0, vmax=100, cmap="inferno", cbar=True)

    infected_count = np.sum(infection_status)
    plt.title(f"VIRAL OUTBREAK IN PROGRESS\nComplexity: {active_virus_complexity} | Infected Nodes: {infected_count}")


# --- MAIN ---
if __name__ == "__main__":
    # Start Listener in Background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Start Animation Loop
    fig = plt.figure(figsize=(8, 6))
    ani = FuncAnimation(fig, update_grid, interval=200)  # Update every 200ms
    plt.show()
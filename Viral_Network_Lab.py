import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import random

# --- Configuration & States ---
NUM_NODES = 500
AVG_DEGREE = 2  # parameter for Barabasi-Albert (m)

# States
STATE_SUSCEPTIBLE = 0
STATE_INFECTED = 1
STATE_RECOVERED = 2
STATE_DECEASED = 3
STATE_VACCINATED = 4

# Colors
COLOR_MAP = {
    STATE_SUSCEPTIBLE: '#3498db',  # Blue
    STATE_INFECTED: '#e74c3c',  # Red
    STATE_RECOVERED: '#95a5a6',  # Gray
    STATE_DECEASED: '#2c3e50',  # Black (Dark Blue/Grey)
    STATE_VACCINATED: '#2ecc71'  # Green
}


class EpidemicModel:
    def __init__(self, n_nodes, vaccination_rate, vax_strategy, infection_prob, mortality_rate, recovery_rate):
        self.n_nodes = n_nodes
        self.infection_prob = infection_prob
        self.mortality_rate = mortality_rate
        self.recovery_rate = recovery_rate

        # 1. Generate Scale-Free Network (Barabasi-Albert)
        # This creates hubs (super-spreaders) automatically
        self.G = nx.barabasi_albert_graph(n_nodes, AVG_DEGREE)

        # Calculate Layout once (spring layout looks best for organic networks)
        # Storing this allows the animation to keep nodes in place while colors change
        self.pos = nx.spring_layout(self.G, seed=42, k=0.15)

        # Initialize States
        self.states = np.zeros(n_nodes, dtype=int)  # All Susceptible (0)

        # 2. Apply Vaccination
        num_vax = int(n_nodes * vaccination_rate)
        if num_vax > 0:
            if vax_strategy == "Random":
                # Pick random nodes
                vax_indices = np.random.choice(n_nodes, num_vax, replace=False)
                self.states[vax_indices] = STATE_VACCINATED

            elif vax_strategy == "Targeted (Hubs)":
                # Pick nodes with highest degree (connections)
                degrees = dict(self.G.degree())
                # Sort by degree descending
                sorted_nodes = sorted(degrees, key=degrees.get, reverse=True)
                vax_indices = sorted_nodes[:num_vax]
                self.states[vax_indices] = STATE_VACCINATED

        # 3. Patient Zero
        # Find a random susceptible node to infect
        susceptible = np.where(self.states == STATE_SUSCEPTIBLE)[0]
        if len(susceptible) > 0:
            patient_zero = np.random.choice(susceptible)
            self.states[patient_zero] = STATE_INFECTED

        self.history_infected = []
        self.history_deceased = []
        self.steps = 0

    def step(self):
        """Perform one time step of the simulation."""
        new_states = self.states.copy()

        # Get all currently infected nodes
        infected_nodes = np.where(self.states == STATE_INFECTED)[0]

        for node in infected_nodes:
            # A. Try to Infect Neighbors
            neighbors = list(self.G.neighbors(node))
            for neighbor in neighbors:
                if self.states[neighbor] == STATE_SUSCEPTIBLE:
                    if random.random() < self.infection_prob:
                        new_states[neighbor] = STATE_INFECTED

            # B. Check for Death or Recovery
            # Mortality check happens first
            if random.random() < self.mortality_rate:
                new_states[node] = STATE_DECEASED
            elif random.random() < self.recovery_rate:
                new_states[node] = STATE_RECOVERED

        self.states = new_states
        self.steps += 1

        # Stats
        total_inf = np.sum(self.states == STATE_INFECTED)
        total_dead = np.sum(self.states == STATE_DECEASED)
        self.history_infected.append(total_inf)
        self.history_deceased.append(total_dead)

        return total_inf == 0  # Return True if pandemic is over


class SimulationRunner:
    def __init__(self, root):
        self.root = root
        self.root.title("Virtual Lab: Viral Outbreak Simulator")
        self.root.geometry("400x600")

        self.create_gui()

    def create_gui(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Title
        tk.Label(self.root, text="Pandemic Parameters", font=("Arial", 16, "bold")).pack(pady=10)

        # Frame for Sliders
        frame = ttk.Frame(self.root)
        frame.pack(padx=20, pady=10, fill="x")

        # Transmission Probability
        tk.Label(frame, text="Transmission Probability (per contact):").pack(anchor="w")
        self.slider_trans = ttk.Scale(frame, from_=0.01, to=1.0, value=0.15)
        self.slider_trans.pack(fill="x", pady=5)

        # Mortality Rate
        tk.Label(frame, text="Mortality Rate (per step):").pack(anchor="w")
        self.slider_mortality = ttk.Scale(frame, from_=0.0, to=0.2, value=0.01)
        self.slider_mortality.pack(fill="x", pady=5)

        # Vaccination Rate
        tk.Label(frame, text="Vaccination Coverage (%):").pack(anchor="w")
        self.slider_vax_rate = ttk.Scale(frame, from_=0.0, to=1.0, value=0.0)
        self.slider_vax_rate.pack(fill="x", pady=5)

        # Vaccination Strategy
        tk.Label(frame, text="Vaccination Strategy:").pack(anchor="w", pady=(15, 0))
        self.vax_strat_var = tk.StringVar(value="Random")
        ttk.Radiobutton(frame, text="Random Distribution (Low Efficacy)",
                        variable=self.vax_strat_var, value="Random").pack(anchor="w")
        ttk.Radiobutton(frame, text="Targeted Hubs (High Efficacy)",
                        variable=self.vax_strat_var, value="Targeted (Hubs)").pack(anchor="w")

        # Run Button
        ttk.Button(self.root, text="INITIALIZE SIMULATION", command=self.run_simulation).pack(pady=30, fill="x",
                                                                                              padx=40)

        # Legend
        legend_frame = tk.LabelFrame(self.root, text="Legend", padx=10, pady=10)
        legend_frame.pack(padx=20, fill="x")

        self.add_legend_item(legend_frame, "Susceptible", COLOR_MAP[STATE_SUSCEPTIBLE])
        self.add_legend_item(legend_frame, "Infected", COLOR_MAP[STATE_INFECTED])
        self.add_legend_item(legend_frame, "Recovered", COLOR_MAP[STATE_RECOVERED])
        self.add_legend_item(legend_frame, "Deceased", COLOR_MAP[STATE_DECEASED])
        self.add_legend_item(legend_frame, "Vaccinated", COLOR_MAP[STATE_VACCINATED])

    def add_legend_item(self, parent, text, color):
        f = tk.Frame(parent)
        f.pack(side="left", expand=True)
        tk.Label(f, bg=color, width=2).pack(side="left")
        tk.Label(f, text=text, font=("Arial", 8)).pack(side="left", padx=2)

    def run_simulation(self):
        # Get params
        trans_prob = self.slider_trans.get()
        mortality = self.slider_mortality.get()
        vax_rate = self.slider_vax_rate.get()
        vax_strat = self.vax_strat_var.get()
        recovery_rate = 0.05  # Fixed for simplicity

        # Initialize Model
        model = EpidemicModel(NUM_NODES, vax_rate, vax_strat, trans_prob, mortality, recovery_rate)

        # Setup Plot
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_title(f"Network Outbreak: {vax_strat} Vax")
        ax.axis('off')

        # Draw edges (static)
        nx.draw_networkx_edges(model.G, model.pos, alpha=0.2, ax=ax)

        # Nodes placeholder
        nodes_drawing = nx.draw_networkx_nodes(
            model.G,
            model.pos,
            node_size=50,
            node_color=[COLOR_MAP[s] for s in model.states],
            ax=ax
        )

        text_stats = ax.text(0.02, 0.95, "", transform=ax.transAxes, fontsize=12,
                             bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        def update(frame):
            if frame == 0: return nodes_drawing, text_stats  # Start pause

            # Step Model
            done = model.step()

            # Update Colors
            colors = [COLOR_MAP[s] for s in model.states]
            nodes_drawing.set_color(colors)

            # Update Stats Text
            counts = {
                "Infected": np.sum(model.states == STATE_INFECTED),
                "Recovered": np.sum(model.states == STATE_RECOVERED),
                "Deceased": np.sum(model.states == STATE_DECEASED),
                "Susceptible": np.sum(model.states == STATE_SUSCEPTIBLE)
            }

            stats = f"Step: {model.steps}\n" \
                    f"Infected: {counts['Infected']}\n" \
                    f"Deceased: {counts['Deceased']}\n" \
                    f"Recovered: {counts['Recovered']}"

            text_stats.set_text(stats)

            if done:
                self.anim.event_source.stop()

            return nodes_drawing, text_stats

        self.anim = FuncAnimation(fig, update, frames=500, interval=100, blit=False)
        plt.show()


if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationRunner(root)
    root.mainloop()
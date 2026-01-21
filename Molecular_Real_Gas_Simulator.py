"""
Molecular Dynamics (MD) Real Gas Simulator
Simulates Argon atoms with Lennard-Jones potential
Demonstrates phase transitions: Gas ↔ Liquid ↔ Solid
Uses Velocity Verlet integration for accurate dynamics
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import tkinter as tk
from tkinter import ttk
from collections import deque


class MolecularDynamics:
    def __init__(self, num_atoms=100):
        # Physical constants for Argon
        self.epsilon = 1.0  # Energy parameter (normalized)
        self.sigma = 1.0  # Distance parameter (normalized)
        self.mass = 1.0  # Atomic mass (normalized)

        # Simulation parameters
        self.num_atoms = num_atoms
        self.dt = 0.005  # Time step
        self.box_size = 15.0  # Simulation box size

        # Cutoff for Lennard-Jones potential (for efficiency)
        self.r_cutoff = 2.5 * self.sigma

        # State variables
        self.positions = None
        self.velocities = None
        self.forces = None
        self.accelerations = None

        # Thermodynamic quantities
        self.kinetic_energy = 0.0
        self.potential_energy = 0.0
        self.temperature = 1.0
        self.pressure = 0.0

        # History for plotting
        self.history_length = 200
        self.time_history = deque(maxlen=self.history_length)
        self.energy_history = deque(maxlen=self.history_length)
        self.temp_history = deque(maxlen=self.history_length)
        self.pressure_history = deque(maxlen=self.history_length)
        self.time = 0.0

        self.initialize_system()

    def initialize_system(self):
        """Initialize atom positions and velocities"""
        # Place atoms on a lattice
        n_per_dim = int(np.ceil(self.num_atoms ** (1 / 3)))
        spacing = self.box_size / (n_per_dim + 1)

        positions = []
        for i in range(n_per_dim):
            for j in range(n_per_dim):
                for k in range(n_per_dim):
                    if len(positions) < self.num_atoms:
                        pos = np.array([
                            (i + 1) * spacing - self.box_size / 2,
                            (j + 1) * spacing - self.box_size / 2,
                            (k + 1) * spacing - self.box_size / 2
                        ])
                        positions.append(pos)

        self.positions = np.array(positions[:self.num_atoms])

        # Initialize random velocities (Maxwell-Boltzmann distribution)
        self.velocities = np.random.randn(self.num_atoms, 3)

        # Remove center of mass motion
        self.velocities -= np.mean(self.velocities, axis=0)

        # Scale velocities to target temperature
        self.rescale_velocities(self.temperature)

        # Initialize forces
        self.forces = np.zeros((self.num_atoms, 3))
        self.compute_forces()

    def lennard_jones_force(self, r_vec, r_mag):
        """
        Compute Lennard-Jones force between two atoms
        F = -dV/dr = 24*epsilon * [(2*(sigma/r)^12 - (sigma/r)^6) / r] * r_vec/r
        """
        if r_mag > self.r_cutoff or r_mag < 0.01:
            return np.zeros(3)

        sigma_r6 = (self.sigma / r_mag) ** 6
        sigma_r12 = sigma_r6 ** 2

        force_magnitude = 24 * self.epsilon * (2 * sigma_r12 - sigma_r6) / r_mag ** 2
        force = force_magnitude * r_vec

        return force

    def lennard_jones_potential(self, r_mag):
        """Compute Lennard-Jones potential energy"""
        if r_mag > self.r_cutoff or r_mag < 0.01:
            return 0.0

        sigma_r6 = (self.sigma / r_mag) ** 6
        sigma_r12 = sigma_r6 ** 2

        return 4 * self.epsilon * (sigma_r12 - sigma_r6)

    def compute_forces(self):
        """Compute forces on all atoms using Lennard-Jones potential"""
        self.forces = np.zeros((self.num_atoms, 3))
        self.potential_energy = 0.0

        # Pairwise interactions
        for i in range(self.num_atoms):
            for j in range(i + 1, self.num_atoms):
                # Vector from i to j
                r_vec = self.positions[j] - self.positions[i]

                # Apply periodic boundary conditions (minimum image convention)
                r_vec = r_vec - self.box_size * np.round(r_vec / self.box_size)

                r_mag = np.linalg.norm(r_vec)

                if r_mag < self.r_cutoff and r_mag > 0.01:
                    # Compute force
                    force = self.lennard_jones_force(r_vec, r_mag)

                    # Newton's third law
                    self.forces[i] += force
                    self.forces[j] -= force

                    # Accumulate potential energy
                    self.potential_energy += self.lennard_jones_potential(r_mag)

    def apply_boundary_conditions(self):
        """Apply reflecting boundary conditions"""
        half_box = self.box_size / 2

        for i in range(self.num_atoms):
            for dim in range(3):
                if self.positions[i, dim] < -half_box:
                    self.positions[i, dim] = -half_box
                    self.velocities[i, dim] = abs(self.velocities[i, dim])
                elif self.positions[i, dim] > half_box:
                    self.positions[i, dim] = half_box
                    self.velocities[i, dim] = -abs(self.velocities[i, dim])

    def velocity_verlet_step(self):
        """
        Perform one time step using Velocity Verlet integration
        More accurate than standard Verlet for velocity-dependent properties
        """
        # Update positions: r(t+dt) = r(t) + v(t)*dt + 0.5*a(t)*dt^2
        self.positions += self.velocities * self.dt + 0.5 * (self.forces / self.mass) * self.dt ** 2

        # Store old forces
        old_forces = self.forces.copy()

        # Compute new forces
        self.compute_forces()

        # Update velocities: v(t+dt) = v(t) + 0.5*(a(t) + a(t+dt))*dt
        self.velocities += 0.5 * (old_forces + self.forces) / self.mass * self.dt

        # Apply boundary conditions
        self.apply_boundary_conditions()

        # Update time
        self.time += self.dt

    def compute_temperature(self):
        """Compute instantaneous temperature from kinetic energy"""
        # T = (2/3) * KE / (N * k_B), with k_B = 1 in reduced units
        self.kinetic_energy = 0.5 * self.mass * np.sum(self.velocities ** 2)
        self.temperature = (2.0 / 3.0) * self.kinetic_energy / self.num_atoms
        return self.temperature

    def compute_pressure(self):
        """Compute pressure using virial theorem"""
        # Simplified pressure calculation
        # P = (N*k_B*T)/V + virial_term
        volume = self.box_size ** 3

        # Ideal gas contribution
        ideal_term = self.num_atoms * self.temperature / volume

        # Virial contribution (approximate)
        virial = 0.0
        for i in range(self.num_atoms):
            for j in range(i + 1, self.num_atoms):
                r_vec = self.positions[j] - self.positions[i]
                r_vec = r_vec - self.box_size * np.round(r_vec / self.box_size)
                r_mag = np.linalg.norm(r_vec)

                if r_mag < self.r_cutoff and r_mag > 0.01:
                    force = self.lennard_jones_force(r_vec, r_mag)
                    virial += np.dot(r_vec, force)

        virial_term = virial / (3.0 * volume)
        self.pressure = ideal_term + virial_term
        return self.pressure

    def rescale_velocities(self, target_temp):
        """Rescale velocities to target temperature (thermostat)"""
        current_temp = self.compute_temperature()
        if current_temp > 0:
            scale_factor = np.sqrt(target_temp / current_temp)
            self.velocities *= scale_factor
            self.temperature = target_temp

    def change_box_size(self, new_size):
        """Change box size (affects pressure/density)"""
        scale_factor = new_size / self.box_size
        self.positions *= scale_factor
        self.box_size = new_size
        self.compute_forces()

    def step(self):
        """Perform one MD step and update thermodynamic quantities"""
        self.velocity_verlet_step()
        self.compute_temperature()
        self.compute_pressure()

        # Update history
        self.time_history.append(self.time)
        total_energy = self.kinetic_energy + self.potential_energy
        self.energy_history.append(total_energy)
        self.temp_history.append(self.temperature)
        self.pressure_history.append(self.pressure)


class MDSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Molecular Dynamics: Real Gas Simulator")
        self.root.geometry("1400x800")

        self.md = MolecularDynamics(num_atoms=80)
        self.is_running = False
        self.animation = None

        self.setup_ui()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - 3D visualization
        left_frame = ttk.LabelFrame(main_frame, text="3D Molecular View", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 3D plot
        self.fig_3d = plt.Figure(figsize=(8, 8))
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_xlim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_ylim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_zlim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_xlabel('X')
        self.ax_3d.set_ylabel('Y')
        self.ax_3d.set_zlabel('Z')
        self.ax_3d.set_title('Argon Atoms - Lennard-Jones Potential')

        # Initial scatter plot
        self.scatter = self.ax_3d.scatter(
            self.md.positions[:, 0],
            self.md.positions[:, 1],
            self.md.positions[:, 2],
            c='blue', s=100, alpha=0.6
        )

        # Draw box
        self.draw_box()

        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=left_frame)
        self.canvas_3d.draw()
        self.canvas_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Right panel - Controls and plots
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))

        # Control panel
        control_frame = ttk.LabelFrame(right_frame, text="Simulation Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Title
        title_label = ttk.Label(control_frame, text="MD Real Gas Simulator",
                                font=("Arial", 14, "bold"))
        title_label.pack(pady=5)

        # Temperature control
        temp_frame = ttk.Frame(control_frame)
        temp_frame.pack(fill=tk.X, pady=10)

        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT)
        self.temp_var = tk.DoubleVar(value=1.0)
        self.temp_scale = ttk.Scale(temp_frame, from_=0.1, to=5.0,
                                    variable=self.temp_var, orient=tk.HORIZONTAL,
                                    length=200, command=self.update_temp_label)
        self.temp_scale.pack(side=tk.LEFT, padx=5)
        self.temp_label = ttk.Label(temp_frame, text="1.00", width=6)
        self.temp_label.pack(side=tk.LEFT)

        ttk.Button(control_frame, text="Apply Temperature",
                   command=self.apply_temperature).pack(pady=5)

        # Box size control (pressure)
        box_frame = ttk.Frame(control_frame)
        box_frame.pack(fill=tk.X, pady=10)

        ttk.Label(box_frame, text="Box Size (Density):").pack(side=tk.LEFT)
        self.box_var = tk.DoubleVar(value=15.0)
        self.box_scale = ttk.Scale(box_frame, from_=10.0, to=20.0,
                                   variable=self.box_var, orient=tk.HORIZONTAL,
                                   length=200, command=self.update_box_label)
        self.box_scale.pack(side=tk.LEFT, padx=5)
        self.box_label = ttk.Label(box_frame, text="15.0", width=6)
        self.box_label.pack(side=tk.LEFT)

        ttk.Button(control_frame, text="Apply Box Size",
                   command=self.apply_box_size).pack(pady=5)

        # Simulation controls
        sim_frame = ttk.Frame(control_frame)
        sim_frame.pack(pady=10)

        self.start_button = ttk.Button(sim_frame, text="Start Simulation",
                                       command=self.start_simulation, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(sim_frame, text="Stop",
                                      command=self.stop_simulation, width=10,
                                      state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Reset System",
                   command=self.reset_system, width=15).pack(pady=5)

        # Thermodynamic info
        info_frame = ttk.LabelFrame(control_frame, text="Thermodynamic Properties",
                                    padding="10")
        info_frame.pack(fill=tk.X, pady=10)

        self.info_labels = {}
        properties = ['Temperature', 'Pressure', 'Kinetic Energy',
                      'Potential Energy', 'Total Energy']

        for prop in properties:
            frame = ttk.Frame(info_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{prop}:", width=15).pack(side=tk.LEFT)
            label = ttk.Label(frame, text="0.00", foreground="blue", width=10)
            label.pack(side=tk.LEFT)
            self.info_labels[prop] = label

        # Phase indicator
        self.phase_label = ttk.Label(info_frame, text="Phase: Gas",
                                     font=("Arial", 11, "bold"),
                                     foreground="green")
        self.phase_label.pack(pady=5)

        # Plots frame
        plots_frame = ttk.LabelFrame(right_frame, text="System Properties", padding="10")
        plots_frame.pack(fill=tk.BOTH, expand=True)

        # Create plots
        self.fig_plots, self.axes = plt.subplots(3, 1, figsize=(6, 8))
        self.fig_plots.tight_layout(pad=3.0)

        # Energy plot
        self.axes[0].set_title('Total Energy')
        self.axes[0].set_xlabel('Time')
        self.axes[0].set_ylabel('Energy')
        self.axes[0].grid(True, alpha=0.3)
        self.energy_line, = self.axes[0].plot([], [], 'b-', linewidth=2)

        # Temperature plot
        self.axes[1].set_title('Temperature')
        self.axes[1].set_xlabel('Time')
        self.axes[1].set_ylabel('T')
        self.axes[1].grid(True, alpha=0.3)
        self.temp_line, = self.axes[1].plot([], [], 'r-', linewidth=2)

        # Pressure plot
        self.axes[2].set_title('Pressure')
        self.axes[2].set_xlabel('Time')
        self.axes[2].set_ylabel('P')
        self.axes[2].grid(True, alpha=0.3)
        self.pressure_line, = self.axes[2].plot([], [], 'g-', linewidth=2)

        self.canvas_plots = FigureCanvasTkAgg(self.fig_plots, master=plots_frame)
        self.canvas_plots.draw()
        self.canvas_plots.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def draw_box(self):
        """Draw simulation box"""
        half = self.md.box_size / 2
        # Draw box edges
        for x in [-half, half]:
            for y in [-half, half]:
                self.ax_3d.plot([x, x], [y, y], [-half, half], 'k-', alpha=0.3)
        for x in [-half, half]:
            for z in [-half, half]:
                self.ax_3d.plot([x, x], [-half, half], [z, z], 'k-', alpha=0.3)
        for y in [-half, half]:
            for z in [-half, half]:
                self.ax_3d.plot([-half, half], [y, y], [z, z], 'k-', alpha=0.3)

    def update_temp_label(self, value):
        self.temp_label.config(text=f"{float(value):.2f}")

    def update_box_label(self, value):
        self.box_label.config(text=f"{float(value):.1f}")

    def apply_temperature(self):
        """Apply temperature change to system"""
        target_temp = self.temp_var.get()
        self.md.rescale_velocities(target_temp)

    def apply_box_size(self):
        """Apply box size change"""
        new_size = self.box_var.get()
        self.md.change_box_size(new_size)
        self.ax_3d.clear()
        self.ax_3d.set_xlim(-new_size / 2, new_size / 2)
        self.ax_3d.set_ylim(-new_size / 2, new_size / 2)
        self.ax_3d.set_zlim(-new_size / 2, new_size / 2)
        self.draw_box()
        self.update_3d_plot()

    def determine_phase(self):
        """Estimate phase based on temperature and density"""
        temp = self.md.temperature
        density = self.md.num_atoms / (self.md.box_size ** 3)

        # Rough phase boundaries for Lennard-Jones
        if temp > 1.5:
            return "Gas", "green"
        elif temp > 0.7 and density < 0.3:
            return "Gas", "green"
        elif temp < 0.5:
            return "Solid", "blue"
        else:
            return "Liquid", "orange"

    def update_info(self):
        """Update thermodynamic information display"""
        self.info_labels['Temperature'].config(text=f"{self.md.temperature:.3f}")
        self.info_labels['Pressure'].config(text=f"{self.md.pressure:.3f}")
        self.info_labels['Kinetic Energy'].config(text=f"{self.md.kinetic_energy:.3f}")
        self.info_labels['Potential Energy'].config(text=f"{self.md.potential_energy:.3f}")
        total_e = self.md.kinetic_energy + self.md.potential_energy
        self.info_labels['Total Energy'].config(text=f"{total_e:.3f}")

        phase, color = self.determine_phase()
        self.phase_label.config(text=f"Phase: {phase}", foreground=color)

    def update_3d_plot(self):
        """Update 3D scatter plot"""
        self.scatter._offsets3d = (
            self.md.positions[:, 0],
            self.md.positions[:, 1],
            self.md.positions[:, 2]
        )
        self.canvas_3d.draw_idle()

    def update_plots(self):
        """Update time-series plots"""
        if len(self.md.time_history) > 1:
            times = list(self.md.time_history)

            # Energy
            self.energy_line.set_data(times, list(self.md.energy_history))
            self.axes[0].relim()
            self.axes[0].autoscale_view()

            # Temperature
            self.temp_line.set_data(times, list(self.md.temp_history))
            self.axes[1].relim()
            self.axes[1].autoscale_view()

            # Pressure
            self.pressure_line.set_data(times, list(self.md.pressure_history))
            self.axes[2].relim()
            self.axes[2].autoscale_view()

            self.canvas_plots.draw_idle()

    def simulation_step(self):
        """Perform one simulation step"""
        if self.is_running:
            # Perform multiple steps for speed
            for _ in range(5):
                self.md.step()

            self.update_3d_plot()
            self.update_plots()
            self.update_info()

            self.root.after(10, self.simulation_step)

    def start_simulation(self):
        """Start the simulation"""
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.simulation_step()

    def stop_simulation(self):
        """Stop the simulation"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def reset_system(self):
        """Reset the simulation"""
        self.stop_simulation()
        self.md = MolecularDynamics(num_atoms=80)
        self.temp_var.set(1.0)
        self.box_var.set(15.0)

        self.ax_3d.clear()
        self.ax_3d.set_xlim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_ylim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_zlim(-self.md.box_size / 2, self.md.box_size / 2)
        self.ax_3d.set_xlabel('X')
        self.ax_3d.set_ylabel('Y')
        self.ax_3d.set_zlabel('Z')
        self.ax_3d.set_title('Argon Atoms - Lennard-Jones Potential')

        self.scatter = self.ax_3d.scatter(
            self.md.positions[:, 0],
            self.md.positions[:, 1],
            self.md.positions[:, 2],
            c='blue', s=100, alpha=0.6
        )

        self.draw_box()
        self.canvas_3d.draw()

        # Clear plots
        for line in [self.energy_line, self.temp_line, self.pressure_line]:
            line.set_data([], [])
        self.canvas_plots.draw()

        self.update_info()


def main():
    root = tk.Tk()
    app = MDSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
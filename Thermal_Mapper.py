import matplotlib.pyplot as plt
import numpy as np
import random
import time

# --- CONFIGURATION ---
GRID_SIZE = 5  # 5x5 Grid (25 Racks)
TEMP_THRESHOLD = 80.0  # Max safe temperature in Celsius
BASE_TEMP = 25.0  # Ambient room temperature
HEAT_PER_VM = 8.5  # Every VM adds this many degrees


class DataCenterManager:
    def __init__(self):
        # 1. Track VM Distribution: {(row, col): [list of VM IDs]}
        self.racks = {}
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                # Start with a random number of VMs on each rack
                self.racks[(r, c)] = [f"VM-{random.randint(1000, 9999)}" for _ in range(random.randint(1, 6))]

        self.temperatures = np.zeros((GRID_SIZE, GRID_SIZE))
        self.update_heat_map()

    def update_heat_map(self):
        """Calculates temperatures based on current VM load."""
        for (r, c), vms in self.racks.items():
            # Temperature = Base + (VMs * Heat Factor) + Random noise (fans, airflow)
            noise = random.uniform(-2.0, 2.0)
            self.temperatures[r, c] = BASE_TEMP + (len(vms) * HEAT_PER_VM) + noise

    def get_coolest_rack(self):
        """Finds the rack with the lowest current temperature."""
        flat_idx = np.argmin(self.temperatures)
        return divmod(flat_idx, GRID_SIZE)

    def rebalance_workload(self):
        """Logic: Moves VMs from hot racks to the coolest available rack."""
        migrations = []
        hot_racks = np.argwhere(self.temperatures > TEMP_THRESHOLD)

        if len(hot_racks) == 0:
            return None

        for r_hot, c_hot in hot_racks:
            # While this rack is too hot and has VMs to move
            while self.temperatures[r_hot, c_hot] > TEMP_THRESHOLD and self.racks[(r_hot, c_hot)]:
                # Find current coolest spot
                r_cool, c_cool = self.get_coolest_rack()

                # Move 1 VM
                vm_to_move = self.racks[(r_hot, c_hot)].pop()
                self.racks[(r_cool, c_cool)].append(vm_to_move)

                migrations.append(f"Moved {vm_to_move} from ({r_hot},{c_hot}) -> ({r_cool},{c_cool})")

                # Recalculate heat for these two specifically so we don't over-stack the cool one
                self.update_heat_map()

        return migrations

    def visualize(self, step):
        plt.clf()
        plt.title(f"Data Center Thermal Map - Cycle {step}\n(Threshold: {TEMP_THRESHOLD}°C)")

        # Create heatmap
        im = plt.imshow(self.temperatures, cmap='YlOrRd', interpolation='nearest', vmin=20, vmax=100)

        # Add labels for VM counts
        for (r, c), vms in self.racks.items():
            color = "white" if self.temperatures[r, c] > 60 else "black"
            plt.text(c, r, f"VMs: {len(vms)}\n{self.temperatures[r, c]:.1f}°C",
                     ha="center", va="center", color=color, fontsize=8, fontweight='bold')

        plt.colorbar(im, label="Temperature °C")
        plt.pause(1.5)


# --- MAIN SIMULATION ---
def run_simulation():
    manager = DataCenterManager()
    plt.figure(figsize=(10, 8))

    print("--- SERVER RACK THERMAL MONITORING STARTED ---")

    for cycle in range(1, 11):
        # 1. Update Map
        manager.update_heat_map()

        # 2. Check for Critical status
        hot_count = np.sum(manager.temperatures > TEMP_THRESHOLD)
        print(f"\nCycle {cycle}: {hot_count} Racks over threshold.")

        # 3. Visualize current state
        manager.visualize(cycle)

        # 4. Trigger Rebalance Logic
        logs = manager.rebalance_workload()
        if logs:
            print(f"!!! CRITICAL HEAT DETECTED. Executing {len(logs)} migrations...")
            for log in logs[:3]:  # Print first 3 logs
                print(f"  > {log}")
            if len(logs) > 3: print(f"  > ... and {len(logs) - 3} others.")
        else:
            print("System Stable. No migrations required.")

        # 5. Simulate new work arriving to keep things dynamic
        if random.random() > 0.5:
            target = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
            manager.racks[target].append(f"NEW-VM-{random.randint(100, 999)}")
            print(f"Injecting new workload to Rack {target}")

    plt.show()


if __name__ == "__main__":
    run_simulation()
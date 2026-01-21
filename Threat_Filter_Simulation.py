import random
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# --- Configuration ---
NUM_ROCKETS = 100
INTERCEPTOR_COST = 50000  # $50k per shot
CITY_NAME = "Tel Aviv (Sector 4)"


class ThreatFilterSim:
    def __init__(self):
        # Define a complex city shape (Polygon coordinates)
        # Not just a square, to show off the algorithm's precision
        self.city_coords = [
            (30, 30), (30, 80), (50, 90), (80, 80),
            (90, 50), (80, 20), (50, 10), (40, 20)
        ]
        self.city_polygon = Polygon(self.city_coords)

        # Bounding box for random generation (0-100 grid)
        self.min_x, self.min_y = 0, 0
        self.max_x, self.max_y = 100, 100

        self.threats = []
        self.safe_hits = []

    def generate_impacts(self):
        """Generates random impact coordinates representing enemy rockets."""
        print(f"--- RADAR TRACKING STARTED: {NUM_ROCKETS} INCOMING ---")

        for _ in range(NUM_ROCKETS):
            # Random coordinate
            x = random.uniform(self.min_x, self.max_x)
            y = random.uniform(self.min_y, self.max_y)
            point = Point(x, y)

            # THE CORE LOGIC: Point in Polygon Check
            # shapely.contains is highly optimized C-based geometry logic
            if self.city_polygon.contains(point):
                self.threats.append(point)
                decision = "INTERCEPT"
            else:
                self.safe_hits.append(point)
                decision = "IGNORE"

            # Log the first few for demo
            if _ < 5:
                print(f"TGT-{_:03d} at ({x:.1f}, {y:.1f}) -> {decision}")

    def generate_report(self):
        """Calculates financial efficiency."""
        num_threats = len(self.threats)
        num_safe = len(self.safe_hits)

        cost_naive = NUM_ROCKETS * INTERCEPTOR_COST
        cost_smart = num_threats * INTERCEPTOR_COST
        savings = cost_naive - cost_smart

        print("\n" + "=" * 40)
        print(f"MISSION REPORT: {CITY_NAME}")
        print("=" * 40)
        print(f"Total Incoming:      {NUM_ROCKETS}")
        print(f"Threats Identified:  {num_threats} (INTERCEPTED)")
        print(f"Safe Impacts:        {num_safe} (IGNORED)")
        print("-" * 40)
        print(f"Cost without Logic:  ${cost_naive:,}")
        print(f"Cost with Geofencing: ${cost_smart:,}")
        print(f"TAXPAYER SAVINGS:    ${savings:,}")
        print("=" * 40)

        if savings > 0:
            print(f"By ignoring harmless rockets, you saved enough logic")
            print(f"money to buy {int(savings / INTERCEPTOR_COST)} more interceptors.")

    def visualize(self):
        """Plots the scenario."""
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_title(
            f"Iron Dome Geofencing Logic\n{len(self.threats)} Threats Intercepted | {len(self.safe_hits)} Safe Impacts Ignored")
        ax.set_xlim(self.min_x, self.max_x)
        ax.set_ylim(self.min_y, self.max_y)
        ax.set_facecolor('#1a1a2e')  # Dark background

        # 1. Draw City
        x, y = self.city_polygon.exterior.xy
        ax.fill(x, y, alpha=0.3, fc='#0f3460', ec='#e94560', linewidth=3, label='Defended Zone')

        # 2. Plot Safe Hits (Green Dots)
        if self.safe_hits:
            sx = [p.x for p in self.safe_hits]
            sy = [p.y for p in self.safe_hits]
            ax.scatter(sx, sy, c='#00ff00', s=30, alpha=0.7, label='Safe Impact (Open Field)')

        # 3. Plot Threats (Red Dots)
        if self.threats:
            tx = [p.x for p in self.threats]
            ty = [p.y for p in self.threats]
            ax.scatter(tx, ty, c='#ff0000', s=60, marker='x', linewidth=2, label='Threat (Intercepted)')

        # Legend & Layout
        ax.legend(loc='upper right', facecolor='#16213e', labelcolor='white')
        ax.grid(color='#16213e', linestyle='--')

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    sim = ThreatFilterSim()
    sim.generate_impacts()
    sim.generate_report()
    sim.visualize()
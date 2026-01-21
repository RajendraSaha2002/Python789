import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
import random

# --- Configuration ---
NUM_TARGETS = 5
SENSOR_NOISE = 2.0  # Standard deviation of error (km)
MERGE_THRESHOLD = 5.0  # Max distance to consider tracks the same (km) -> DBSCAN Epsilon


class RadarNetwork:
    def __init__(self):
        # Ground Truth: Where the planes actually are
        self.ground_truth = []
        # Observations: What the radars *think* they see
        # Format: {'radar_id': 'A', 'pos': [x, y]}
        self.raw_feeds = []

    def generate_scenario(self):
        """Creates Ground Truth targets and simulates noisy radar detections."""
        print(f"--- SIMULATING RADAR ENVIRONMENT ---")
        self.ground_truth = []
        self.raw_feeds = []

        # 1. Create Real Targets (spread out on a 100x100km grid)
        for i in range(NUM_TARGETS):
            tx = random.uniform(0, 100)
            ty = random.uniform(0, 100)
            self.ground_truth.append([tx, ty])
            print(f"Actual Target #{i + 1} at: ({tx:.1f}, {ty:.1f})")

        # 2. Simulate Sensors (A, B, C)
        # Each sensor sees the targets but with random error
        sensors = ['Radar A', 'Radar B', 'Radar C']

        for t_idx, true_pos in enumerate(self.ground_truth):
            for sensor in sensors:
                # 10% chance a radar misses the target completely (Blind spot)
                if random.random() < 0.1:
                    continue

                # Add Noise (Gaussian Error)
                noise_x = np.random.normal(0, SENSOR_NOISE)
                noise_y = np.random.normal(0, SENSOR_NOISE)

                obs_x = true_pos[0] + noise_x
                obs_y = true_pos[1] + noise_y

                self.raw_feeds.append({
                    'sensor': sensor,
                    'pos': [obs_x, obs_y],
                    'true_id': t_idx  # For debugging visual verification only
                })

        print(f"Total Raw Tracks Generated: {len(self.raw_feeds)}")
        return self.raw_feeds


class FusionEngine:
    def __init__(self, merge_dist):
        self.eps = merge_dist

    def correlate_tracks(self, raw_data):
        """
        The Core Logic: Uses DBSCAN to cluster close points.
        Returns: List of Fused Tracks (Centroids).
        """
        if not raw_data:
            return []

        # 1. Extract coordinates for Scikit-Learn
        X = np.array([d['pos'] for d in raw_data])

        # 2. Run DBSCAN
        # eps: The maximum distance between two samples for one to be considered as in the neighborhood of the other.
        # min_samples: 1 ensures even a single isolated radar hit becomes a track (no noise filtering).
        clustering = DBSCAN(eps=self.eps, min_samples=1).fit(X)
        labels = clustering.labels_

        # 3. Fuse Data (Calculate Centroids)
        fused_tracks = []
        unique_labels = set(labels)

        print(f"\n--- FUSION PROCESSING ---")
        for label in unique_labels:
            if label == -1:
                # Noise (Shouldn't happen with min_samples=1)
                continue

            # Get all points belonging to this cluster
            cluster_mask = (labels == label)
            cluster_points = X[cluster_mask]

            # Calculate Average Position (Centroid)
            # This averages out the errors from Radar A, B, and C
            centroid = np.mean(cluster_points, axis=0)

            fused_tracks.append({
                'id': f"SIAP-{label + 100}",  # Assign system ID
                'pos': centroid,
                'source_count': len(cluster_points)
            })

            print(f"Track {label}: Merged {len(cluster_points)} reports -> System Track SIAP-{label + 100}")

        return fused_tracks


def visualize_situation(raw_feeds, fused_tracks):
    plt.figure(figsize=(10, 8))
    plt.title(f"Multi-Sensor Data Fusion (DBSCAN Epsilon: {MERGE_THRESHOLD}km)")
    plt.xlabel("Sector X (km)")
    plt.ylabel("Sector Y (km)")
    plt.grid(True, linestyle='--', alpha=0.6)

    # 1. Plot Raw Feeds (The Ghost Tracks)
    # We color code by Sensor to show the confusion
    colors = {'Radar A': 'red', 'Radar B': 'blue', 'Radar C': 'orange'}

    for feed in raw_feeds:
        plt.scatter(
            feed['pos'][0], feed['pos'][1],
            c=colors[feed['sensor']],
            alpha=0.4,
            s=50,
            label=feed['sensor']  # Label logic handled below to avoid duplicates
        )

    # Hack to show legend only once per sensor
    markers = [plt.Line2D([0, 0], [0, 0], color=color, marker='o', linestyle='') for color in colors.values()]
    plt.legend(markers, colors.keys(), loc='upper left')

    # 2. Plot Fused Solutions (The SIAP)
    for track in fused_tracks:
        pos = track['pos']
        # Green 'X' marks the spot
        plt.scatter(pos[0], pos[1], c='green', marker='x', s=200, linewidth=3, zorder=10)

        # Draw range ring logic (Visualizing the correlation gate)
        circle = plt.Circle((pos[0], pos[1]), MERGE_THRESHOLD / 2, color='green', fill=False, linestyle=':')
        plt.gca().add_patch(circle)

        # Annotate
        plt.text(pos[0] + 2, pos[1] + 2, f"{track['id']}\n({track['source_count']} Sensors)",
                 color='green', fontsize=9, fontweight='bold')

    # Dummy entry for Legend
    plt.scatter([], [], c='green', marker='x', s=100, label='Fused SIAP Solution')

    plt.xlim(-10, 110)
    plt.ylim(-10, 110)
    plt.show()


if __name__ == "__main__":
    # 1. Setup
    radar_net = RadarNetwork()
    fusion_core = FusionEngine(merge_dist=MERGE_THRESHOLD)

    # 2. Generate Data
    raw_data = radar_net.generate_scenario()

    # 3. Process
    siap_output = fusion_core.correlate_tracks(raw_data)

    # 4. Display
    visualize_situation(raw_data, siap_output)
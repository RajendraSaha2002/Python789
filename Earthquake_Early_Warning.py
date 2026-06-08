import math
import time
from dataclasses import dataclass
from typing import List, Dict, Optional

# --- Configuration Constants ---
P_WAVE_VELOCITY = 6.0  # km/s
S_WAVE_VELOCITY = 3.5  # km/s
CONSENSUS_THRESHOLD = 3  # Minimum number of triggered sensors required to verify an event
SPATIAL_RADIUS_KM = 30.0  # Radius within which triggers must cluster
TEMPORAL_WINDOW_SEC = 2.5  # Maximum time gap between triggers to count as a cluster


@dataclass
class SensorNode:
    id: str
    x: float  # Grid Coordinate X (km)
    y: float  # Grid Coordinate Y (km)
    is_triggered: bool = False
    trigger_time: Optional[float] = None


@dataclass
class TargetCity:
    name: str
    x: float
    y: float


class EEWEngine:
    def __init__(self, sensors: List[SensorNode]):
        self.sensors: Dict[str, SensorNode] = {s.id: s for s in sensors}
        self.active_triggers: List[SensorNode] = []
        self.alert_issued: bool = False
        self.estimated_epicenter: Optional[tuple] = None
        self.event_start_time: Optional[float] = None

    def calculate_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculates straight-line distance between two grid points in kilometers."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def process_node_trigger(self, node_id: str, timestamp: float) -> Optional[dict]:
        """
        Ingests incoming sensor trigger data and evaluates network consensus.
        """
        if node_id not in self.sensors:
            return None

        node = self.sensors[node_id]
        if node.is_triggered:
            return None  # Ignore duplicate trigger packets

        node.is_triggered = True
        node.trigger_time = timestamp
        self.active_triggers.append(node)

        print(f"[SENSOR EVENT] Node {node_id} triggered at T + {timestamp:.2f} s")

        # Evaluate Consensus if an alert hasn't been fired yet
        if not self.alert_issued:
            return self._evaluate_consensus(node)
        return None

    def _evaluate_consensus(self, latest_node: SensorNode) -> Optional[dict]:
        """
        Checks if the latest trigger forms a spatial-temporal cluster with previous triggers.
        """
        cluster = [latest_node]

        for node in self.active_triggers:
            if node.id == latest_node.id:
                continue

            # Check time proximity
            time_gap = abs(latest_node.trigger_time - node.trigger_time)
            # Check physical proximity
            distance = self.calculate_distance(latest_node.x, latest_node.y, node.x, node.y)

            if time_gap <= TEMPORAL_WINDOW_SEC and distance <= SPATIAL_RADIUS_KM:
                cluster.append(node)

        # Trigger pre-alert if threshold met
        if len(cluster) >= CONSENSUS_THRESHOLD:
            self.alert_issued = True
            # Estimate epicenter roughly by averaging cluster coordinates
            avg_x = sum(n.x for n in cluster) / len(cluster)
            avg_y = sum(n.y for n in cluster) / len(cluster)
            self.estimated_epicenter = (avg_x, avg_y)

            # Back-calculate approximate earthquake start time based on first triggered node
            first_node = min(cluster, key=lambda n: n.trigger_time)
            dist_to_epicenter = self.calculate_distance(first_node.x, first_node.y, avg_x, avg_y)
            self.event_start_time = first_node.trigger_time - (dist_to_epicenter / P_WAVE_VELOCITY)

            return {
                "status": "CRITICAL_ALERT",
                "estimated_epicenter": self.estimated_epicenter,
                "event_start_time": self.event_start_time,
                "nodes_involved": [n.id for n in cluster]
            }

        return None


# =====================================================================
# SIMULATION RUNTIME
# =====================================================================
if __name__ == "__main__":
    print("Initializing Earthquake Early Warning Consensus Network...")

    # 1. Deploy static sensor array grid (representing deployed IoT nodes or client clusters)
    network_sensors = [
        SensorNode("Sensor_A", x=10.0, y=12.0),
        SensorNode("Sensor_B", x=15.0, y=25.0),
        SensorNode("Sensor_C", x=22.0, y=10.0),
        SensorNode("Sensor_D", x=30.0, y=35.0),
        SensorNode("Sensor_E", x=5.0, y=40.0),
    ]

    # 2. Define a vulnerable metropolitan area down-line
    target = TargetCity("Metro_Center", x=120.0, y=110.0)

    engine = EEWEngine(network_sensors)

    # 3. Simulate a real-world seismic event occurrence
    # Earthquake strikes at Epicenter (X=0, Y=0) at system clock T=0
    quake_x, quake_y = 0.0, 0.0
    print(f"\n[CRITICAL] Earthquake occurs at Epicenter (0.0, 0.0) at T=0.00s")
    print(f"Calculating wave propagation paths...\n" + "-" * 60)

    # Generate timeline of when P-waves physically reach our sensors
    timeline = []
    for sensor in network_sensors:
        dist = engine.calculate_distance(quake_x, quake_y, sensor.x, sensor.y)
        p_arrival = dist / P_WAVE_VELOCITY
        timeline.append((p_arrival, sensor.id))

    # Sort timeline so events happen in chronological order
    timeline.sort()

    # 4. Stream data packets into the engine as the physics engine plays out
    alert_payload = None
    for arrival_time, sensor_id in timeline:
        # Pass data packet to central engine
        result = engine.process_node_trigger(sensor_id, arrival_time)
        if result and result["status"] == "CRITICAL_ALERT":
            alert_payload = result
            print(f"\n[!!!] SYSTEM PRE-ALERT ISSUED AT T + {arrival_time:.2f} SECONDS [!!!]")
            print(f"-> Verified by network cluster: {result['nodes_involved']}")
            print(
                f"-> Calculated Epicenter: X: {result['estimated_epicenter'][0]:.2f}, Y: {result['estimated_epicenter'][1]:.2f}")
            break

    # 5. Calculate down-line warning lead time for the metropolitan target city
    if alert_payload:
        city_dist_to_epicenter = engine.calculate_distance(quake_x, quake_y, target.x, target.y)

        # S-waves carry the destructive shaking force
        s_wave_arrival_at_city = city_dist_to_epicenter / S_WAVE_VELOCITY
        alert_delivery_time = max(alert_payload["nodes_involved"], key=lambda nid: engine.sensors[nid].trigger_time)
        alert_delivery_timestamp = engine.sensors[alert_delivery_time].trigger_time

        warning_window = s_wave_arrival_at_city - alert_delivery_timestamp

        print("\n" + "=" * 60)
        print(f"TARGET ANALYSIS: {target.name}")
        print(f"Distance from Epicenter: {city_dist_to_epicenter:.2f} km")
        print(f"Destructive S-Wave Arrival Estimated: T + {s_wave_arrival_at_city:.2f} s")
        print(f"Alert Broadcast Arrives at Device:  T + {alert_delivery_timestamp:.2f} s")
        print("-" * 60)

        if warning_window > 0:
            print(f"RESULT: SUCCESS. Users receive a {warning_window:.2f} second warning window.")
        else:
            print("RESULT: BLIND ZONE. Destructive waves reached the target before network consensus could be reached.")
        print("=" * 60)
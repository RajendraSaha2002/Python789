import math
import statistics
import time
from dataclasses import dataclass


@dataclass
class NetworkFlow:
    flow_id: int
    packet_rate: float
    byte_ratio: float
    port_entropy: float
    is_simulated_anomaly: bool = False

    def features(self):
        return (
            self.packet_rate,
            self.byte_ratio,
            self.port_entropy,
        )


@dataclass
class DetectionResult:
    flow: NetworkFlow
    lof_score: float
    is_anomaly: bool


class LocalOutlierFactor:
    """
    Pure-Python Local Outlier Factor implementation.

    A score near 1.0 is normal.
    A score above the threshold is more likely anomalous.
    """

    def __init__(self, n_neighbors=20, contamination=0.02):
        if not isinstance(n_neighbors, int) or n_neighbors < 2:
            raise ValueError("n_neighbors must be an integer >= 2.")

        if not 0 < contamination < 1:
            raise ValueError("contamination must be between 0 and 1.")

        self.n_neighbors = n_neighbors
        self.contamination = contamination

        self.training_data = []
        self.normalized_data = []
        self.means = ()
        self.standard_deviations = ()
        self.neighbor_indices = []
        self.k_distances = []
        self.local_reachability_densities = []
        self.lof_scores = []
        self.threshold = 1.0

    @staticmethod
    def euclidean_distance(first, second):
        """Calculate Euclidean distance between equal-length vectors."""
        if len(first) != len(second):
            raise ValueError("Vectors must have equal dimensions.")

        return math.sqrt(
            sum(
                (a - b) ** 2
                for a, b in zip(first, second)
            )
        )

    def _calculate_standardization_values(self, vectors):
        """Calculate mean and standard deviation for every feature."""
        dimensions = len(vectors[0])
        means = []
        standard_deviations = []

        for dimension in range(dimensions):
            values = [vector[dimension] for vector in vectors]
            mean = statistics.fmean(values)

            if len(values) > 1:
                standard_deviation = statistics.stdev(values)
            else:
                standard_deviation = 1.0

            if standard_deviation == 0:
                standard_deviation = 1.0

            means.append(mean)
            standard_deviations.append(standard_deviation)

        return tuple(means), tuple(standard_deviations)

    def _normalize_vector(self, vector):
        """Apply z-score normalization using training-set statistics."""
        return tuple(
            (value - mean) / standard_deviation
            for value, mean, standard_deviation in zip(
                vector,
                self.means,
                self.standard_deviations,
            )
        )

    def _find_neighbors(self, vectors):
        """
        Find k nearest neighbors for every vector.

        This is an exact brute-force implementation intended for learning
        and moderate data sizes.
        """
        total_vectors = len(vectors)
        neighbors = []
        k_distances = []

        for current_index, current_vector in enumerate(vectors):
            distances = []

            for other_index, other_vector in enumerate(vectors):
                if current_index == other_index:
                    continue

                distance = self.euclidean_distance(
                    current_vector,
                    other_vector,
                )

                distances.append((distance, other_index))

            distances.sort(key=lambda item: item[0])

            nearest = distances[:self.n_neighbors]
            neighbor_indexes = [index for _, index in nearest]

            neighbors.append(neighbor_indexes)
            k_distances.append(nearest[-1][0])

        return neighbors, k_distances

    def _calculate_local_reachability_density(
        self,
        vectors,
        neighbors,
        k_distances,
    ):
        """
        LRD(p) = 1 / average(reachability_distance(p, neighbor)).
        """
        densities = []
        minimum_distance = 1e-12

        for point_index, point_neighbors in enumerate(neighbors):
            point = vectors[point_index]
            reachability_distances = []

            for neighbor_index in point_neighbors:
                raw_distance = self.euclidean_distance(
                    point,
                    vectors[neighbor_index],
                )

                reachability_distance = max(
                    k_distances[neighbor_index],
                    raw_distance,
                )

                reachability_distances.append(reachability_distance)

            average_reachability_distance = statistics.fmean(
                reachability_distances
            )

            density = 1.0 / max(
                average_reachability_distance,
                minimum_distance,
            )

            densities.append(density)

        return densities

    def _calculate_lof_scores(self, neighbors, densities):
        """
        LOF(p) = average(LRD(neighbor) / LRD(p)).
        """
        scores = []
        minimum_density = 1e-12

        for point_index, point_neighbors in enumerate(neighbors):
            point_density = max(densities[point_index], minimum_density)

            neighbor_density_ratios = [
                densities[neighbor_index] / point_density
                for neighbor_index in point_neighbors
            ]

            scores.append(statistics.fmean(neighbor_density_ratios))

        return scores

    def fit(self, flows):
        """Train LOF using a list of NetworkFlow objects."""
        if not isinstance(flows, list) or not flows:
            raise ValueError("flows must be a non-empty list.")

        if len(flows) <= self.n_neighbors:
            raise ValueError(
                "Number of flows must be greater than n_neighbors."
            )

        for flow in flows:
            if not isinstance(flow, NetworkFlow):
                raise ValueError("All items in flows must be NetworkFlow objects.")

        self.training_data = flows
        raw_vectors = [flow.features() for flow in flows]

        self.means, self.standard_deviations = (
            self._calculate_standardization_values(raw_vectors)
        )

        self.normalized_data = [
            self._normalize_vector(vector)
            for vector in raw_vectors
        ]

        self.neighbor_indices, self.k_distances = self._find_neighbors(
            self.normalized_data
        )

        self.local_reachability_densities = (
            self._calculate_local_reachability_density(
                self.normalized_data,
                self.neighbor_indices,
                self.k_distances,
            )
        )

        self.lof_scores = self._calculate_lof_scores(
            self.neighbor_indices,
            self.local_reachability_densities,
        )

        sorted_scores = sorted(self.lof_scores)
        threshold_index = int(
            (1.0 - self.contamination) * (len(sorted_scores) - 1)
        )

        self.threshold = sorted_scores[threshold_index]

        return self

    def get_results(self):
        """Return detection results for all fitted training flows."""
        if not self.training_data:
            raise RuntimeError("Call fit() before requesting results.")

        return [
            DetectionResult(
                flow=flow,
                lof_score=score,
                is_anomaly=score >= self.threshold,
            )
            for flow, score in zip(self.training_data, self.lof_scores)
        ]


class DeterministicRandom:
    """
    Small deterministic pseudo-random number generator.

    This keeps the script within the requested standard-library modules.
    """

    def __init__(self, seed=123456789):
        self.state = seed

    def random(self):
        self.state = (1103515245 * self.state + 12345) % (2 ** 31)
        return self.state / (2 ** 31)

    def uniform(self, minimum, maximum):
        return minimum + (maximum - minimum) * self.random()

    def normal(self, mean=0.0, standard_deviation=1.0):
        """
        Approximate normal distribution using Box-Muller transform.
        """
        first = max(self.random(), 1e-12)
        second = self.random()

        z_score = math.sqrt(-2.0 * math.log(first)) * math.cos(
            2.0 * math.pi * second
        )

        return mean + standard_deviation * z_score


def generate_network_flows(total_flows=5000, anomaly_ratio=0.02):
    """Generate normal and anomalous simulated network-flow feature vectors."""
    if total_flows < 100:
        raise ValueError("total_flows must be at least 100.")

    if not 0 < anomaly_ratio < 1:
        raise ValueError("anomaly_ratio must be between 0 and 1.")

    random_generator = DeterministicRandom(seed=20260712)
    anomaly_count = max(1, int(total_flows * anomaly_ratio))
    normal_count = total_flows - anomaly_count

    flows = []

    for flow_id in range(normal_count):
        packet_rate = max(
            1.0,
            random_generator.normal(mean=250.0, standard_deviation=45.0),
        )

        byte_ratio = min(
            8.0,
            max(
                0.1,
                random_generator.normal(mean=1.35, standard_deviation=0.30),
            ),
        )

        port_entropy = min(
            8.0,
            max(
                0.0,
                random_generator.normal(mean=2.40, standard_deviation=0.45),
            ),
        )

        flows.append(
            NetworkFlow(
                flow_id=flow_id,
                packet_rate=packet_rate,
                byte_ratio=byte_ratio,
                port_entropy=port_entropy,
                is_simulated_anomaly=False,
            )
        )

    for offset in range(anomaly_count):
        flow_id = normal_count + offset

        anomaly_type = offset % 3

        if anomaly_type == 0:
            packet_rate = random_generator.uniform(1200.0, 3500.0)
            byte_ratio = random_generator.uniform(0.1, 0.4)
            port_entropy = random_generator.uniform(0.0, 1.0)

        elif anomaly_type == 1:
            packet_rate = random_generator.uniform(5.0, 35.0)
            byte_ratio = random_generator.uniform(6.0, 15.0)
            port_entropy = random_generator.uniform(6.0, 8.0)

        else:
            packet_rate = random_generator.uniform(700.0, 1600.0)
            byte_ratio = random_generator.uniform(3.5, 8.0)
            port_entropy = random_generator.uniform(6.5, 8.0)

        flows.append(
            NetworkFlow(
                flow_id=flow_id,
                packet_rate=packet_rate,
                byte_ratio=byte_ratio,
                port_entropy=port_entropy,
                is_simulated_anomaly=True,
            )
        )

    return flows


def print_summary(results, elapsed_seconds, threshold):
    """Print anomaly-detection and benchmark information."""
    detected_anomalies = [
        result
        for result in results
        if result.is_anomaly
    ]

    true_anomalies = [
        result
        for result in results
        if result.flow.is_simulated_anomaly
    ]

    true_positives = [
        result
        for result in detected_anomalies
        if result.flow.is_simulated_anomaly
    ]

    false_positives = [
        result
        for result in detected_anomalies
        if not result.flow.is_simulated_anomaly
    ]

    false_negatives = [
        result
        for result in true_anomalies
        if not result.is_anomaly
    ]

    print("\nLOF ANOMALY DETECTION SUMMARY")
    print("-" * 60)
    print(f"Total flows analysed:      {len(results)}")
    print(f"LOF threshold:             {threshold:.4f}")
    print(f"Detected anomalies:        {len(detected_anomalies)}")
    print(f"Simulated anomalies:       {len(true_anomalies)}")
    print(f"True positives:            {len(true_positives)}")
    print(f"False positives:           {len(false_positives)}")
    print(f"False negatives:           {len(false_negatives)}")
    print(f"Execution time:            {elapsed_seconds:.3f} seconds")

    print("\nTOP 10 MOST ANOMALOUS FLOWS")
    print("-" * 60)

    top_results = sorted(
        results,
        key=lambda result: result.lof_score,
        reverse=True,
    )[:10]

    for result in top_results:
        flow = result.flow
        simulated_label = (
            "SIMULATED ANOMALY"
            if flow.is_simulated_anomaly
            else "normal simulation"
        )

        print(
            f"Flow {flow.flow_id:>4} | "
            f"LOF={result.lof_score:>7.3f} | "
            f"packet_rate={flow.packet_rate:>8.2f} | "
            f"byte_ratio={flow.byte_ratio:>5.2f} | "
            f"port_entropy={flow.port_entropy:>5.2f} | "
            f"{simulated_label}"
        )


def main():
    total_flows = 5000
    n_neighbors = 20
    contamination = 0.02

    print("Generating simulated network flows...")
    flows = generate_network_flows(
        total_flows=total_flows,
        anomaly_ratio=contamination,
    )

    print("Training Local Outlier Factor model...")
    start_time = time.perf_counter()

    detector = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination,
    )

    detector.fit(flows)
    results = detector.get_results()

    elapsed_seconds = time.perf_counter() - start_time

    print_summary(
        results=results,
        elapsed_seconds=elapsed_seconds,
        threshold=detector.threshold,
    )


if __name__ == "__main__":
    main()
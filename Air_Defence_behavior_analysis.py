""
class BehaviorAnalyzer:
    HIGH_SPEED_THRESHOLD = 150.0
    SWARM_THRESHOLD = 5

    def __init__(self, db):
        self.db = db

    def run_pattern_detection(self):
        threats = self.db.get_all_threats()
        for threat in threats:
            level = self._classify(threat)
            self.db.update_threat_level(threat["id"], level)

    def _classify(self, threat):
        flags = (threat.get("behavior_flags") or "").split(",")
        score = 0

        if threat.get("speed", 0) > self.HIGH_SPEED_THRESHOLD:
            score += 2
        if threat.get("unit_count", 0) >= self.SWARM_THRESHOLD:
            score += 3
        if "erratic" in flags:
            score += 2
        if "jamming_detected" in flags:
            score += 3
        if "stealth_mode" in flags:
            score += 2
        if "high_speed" in flags:
            score += 1

        if score >= 5:
            return "CRITICAL"
        elif score >= 3:
            return "HIGH"
        elif score >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    def analyze_single(self, threat_data):
        return self._classify(threat_data)
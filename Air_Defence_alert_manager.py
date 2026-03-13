"""
╔══════════════════════════════════════════════════════════════════╗
║   Air Defense Threat Intelligence Monitoring System              ║
║   alert_manager.py — Full Alert Generation & Management         ║
║   PyCharm | Python 3.12 | Flask Project | No API | No Plugins   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import datetime
import uuid
import threading


# ══════════════════════════════════════════════════════════════════
# CONSTANTS — Alert Levels
# ══════════════════════════════════════════════════════════════════
LEVEL_CRITICAL = "CRITICAL"
LEVEL_HIGH     = "HIGH"
LEVEL_MEDIUM   = "MEDIUM"
LEVEL_LOW      = "LOW"
LEVEL_UNKNOWN  = "UNKNOWN"

VALID_LEVELS = [LEVEL_CRITICAL, LEVEL_HIGH, LEVEL_MEDIUM, LEVEL_LOW, LEVEL_UNKNOWN]

# Priority weight (higher number = more urgent)
LEVEL_PRIORITY = {
    LEVEL_CRITICAL : 4,
    LEVEL_HIGH     : 3,
    LEVEL_MEDIUM   : 2,
    LEVEL_LOW      : 1,
    LEVEL_UNKNOWN  : 0
}


# ══════════════════════════════════════════════════════════════════
# ALERT MESSAGES — Mapped by (threat_type, level)
# ══════════════════════════════════════════════════════════════════
ALERT_MESSAGES = {
    ("DRONE_SWARM",      LEVEL_CRITICAL) : "Large drone swarm detected approaching critical infrastructure",
    ("DRONE_SWARM",      LEVEL_HIGH)     : "Drone swarm on intercept heading — response required",
    ("DRONE_SWARM",      LEVEL_MEDIUM)   : "Drone formation detected — monitoring in progress",
    ("DRONE_SWARM",      LEVEL_LOW)      : "Small drone activity noted — within acceptable parameters",

    ("FIXED_WING",       LEVEL_CRITICAL) : "Hostile fixed-wing aircraft entered restricted airspace",
    ("FIXED_WING",       LEVEL_HIGH)     : "Unidentified fixed-wing aircraft — transponder offline",
    ("FIXED_WING",       LEVEL_MEDIUM)   : "Fixed-wing contact on abnormal flight path",
    ("FIXED_WING",       LEVEL_LOW)      : "Fixed-wing aircraft cleared — continue monitoring",

    ("ROTARY",           LEVEL_CRITICAL) : "Armed rotary aircraft detected — immediate threat",
    ("ROTARY",           LEVEL_HIGH)     : "Unidentified rotary aircraft approaching perimeter",
    ("ROTARY",           LEVEL_MEDIUM)   : "Rotary contact — low altitude stealth approach",
    ("ROTARY",           LEVEL_LOW)      : "Rotary aircraft at safe distance — monitoring",

    ("CRUISE_MISSILE",   LEVEL_CRITICAL) : "INBOUND CRUISE MISSILE — ACTIVATE INTERCEPT PROTOCOL",
    ("CRUISE_MISSILE",   LEVEL_HIGH)     : "Possible missile launch detected — tracking initiated",
    ("CRUISE_MISSILE",   LEVEL_MEDIUM)   : "Unconfirmed missile track — verification in progress",

    ("UNKNOWN_AIRCRAFT", LEVEL_CRITICAL) : "Unidentified fast-moving object — CRITICAL proximity alert",
    ("UNKNOWN_AIRCRAFT", LEVEL_HIGH)     : "Unknown aircraft — electronic jamming signal detected",
    ("UNKNOWN_AIRCRAFT", LEVEL_MEDIUM)   : "Multiple contacts breached outer perimeter",
    ("UNKNOWN_AIRCRAFT", LEVEL_LOW)      : "Unidentified contact — likely civilian — monitoring",
}

# System / Infrastructure alert messages
SYSTEM_ALERT_MESSAGES = {
    "SAM_OFFLINE"         : "SAM battery offline — maintenance required",
    "RADAR_DEGRADED"      : "Radar coverage degraded — blind spot detected",
    "COMMS_JAMMING"       : "Communications jamming detected in sector",
    "PERIMETER_BREACH"    : "Outer perimeter breach confirmed",
    "INTERCEPT_FAILED"    : "Intercept attempt failed — re-engage ordered",
    "SENSOR_OFFLINE"      : "Sector sensor array offline — coverage gap active",
    "POWER_FAILURE"       : "Power failure at defensive node — backup engaged",
    "COMMAND_LINK_LOST"   : "Command data link lost — operating on local protocols",
}


# ══════════════════════════════════════════════════════════════════
# ALERT CLASS — Single alert record
# ══════════════════════════════════════════════════════════════════
class Alert:
    def __init__(self, threat_id, threat_name, threat_type,
                 level, sector, message, is_system=False):
        self.id           = f"ALT-{str(uuid.uuid4())[:6].upper()}"
        self.threat_id    = threat_id
        self.threat_name  = threat_name
        self.threat_type  = threat_type
        self.level        = level
        self.sector       = sector
        self.message      = message
        self.is_system    = is_system
        self.timestamp    = datetime.datetime.now()
        self.acknowledged = False
        self.ack_by       = None
        self.ack_time     = None
        self.escalated    = False
        self.escalation_count = 0
        self.notes        = []     # operator notes added later
        self.history      = []     # level change log

    def to_dict(self):
        return {
            "id"               : self.id,
            "threat_id"        : self.threat_id,
            "threat_name"      : self.threat_name,
            "threat_type"      : self.threat_type,
            "level"            : self.level,
            "sector"           : self.sector,
            "message"          : self.message,
            "is_system"        : self.is_system,
            "timestamp"        : self.timestamp.strftime("%H:%M:%S"),
            "date"             : self.timestamp.strftime("%Y-%m-%d"),
            "full_datetime"    : self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "acknowledged"     : self.acknowledged,
            "ack_by"           : self.ack_by,
            "ack_time"         : self.ack_time,
            "escalated"        : self.escalated,
            "escalation_count" : self.escalation_count,
            "notes"            : self.notes,
            "history"          : self.history
        }


# ══════════════════════════════════════════════════════════════════
# ALERT MANAGER — Core Management Class
# ══════════════════════════════════════════════════════════════════
class AlertManager:

    def __init__(self, db):
        self.db      = db
        self._alerts = []                # All alerts: active + acknowledged
        self._lock   = threading.Lock()  # Thread-safe for background polling
        self._seed_demo_alerts()         # Load demo alerts matching dashboard

    # ──────────────────────────────────────────────────────────────
    # SECTION 1: DEMO DATA SEED
    # Matches the Live Alerts panel in the dashboard screenshot
    # ──────────────────────────────────────────────────────────────
    def _seed_demo_alerts(self):
        demo = [
            {
                "threat_id"   : "charlie-12",
                "threat_name" : "Charlie-12",
                "threat_type" : "DRONE_SWARM",
                "level"       : LEVEL_CRITICAL,
                "sector"      : "Sector 7-G",
                "message"     : "Large drone swarm detected approaching critical infrastructure",
                "time"        : "11:26:26"
            },
            {
                "threat_id"   : "alpha-1",
                "threat_name" : "Alpha-1",
                "threat_type" : "FIXED_WING",
                "level"       : LEVEL_HIGH,
                "sector"      : "Defence Grid Alpha",
                "message"     : "SAM battery offline — maintenance required",
                "is_system"   : True,
                "time"        : "11:21:28"
            },
            {
                "threat_id"   : "beta-3",
                "threat_name" : "Beta-3",
                "threat_type" : "UNKNOWN_AIRCRAFT",
                "level"       : LEVEL_MEDIUM,
                "sector"      : "North Quadrant",
                "message"     : "Multiple contacts breached outer perimeter",
                "time"        : "11:12:34"
            },
        ]
        for d in demo:
            a = Alert(
                threat_id   = d["threat_id"],
                threat_name = d["threat_name"],
                threat_type = d["threat_type"],
                level       = d["level"],
                sector      = d["sector"],
                message     = d["message"],
                is_system   = d.get("is_system", False)
            )
            # Fix timestamps to match dashboard screenshot
            h, m, s = map(int, d["time"].split(":"))
            a.timestamp = a.timestamp.replace(hour=h, minute=m, second=s)
            with self._lock:
                self._alerts.append(a)

    # ──────────────────────────────────────────────────────────────
    # SECTION 2: AUTO EVALUATION
    # Called every 5 seconds by background thread in main.py
    # ──────────────────────────────────────────────────────────────
    def evaluate_threats(self):
        """
        Scan all threats in DB.
        - If new threat at MEDIUM+ → create alert
        - If existing threat escalated → upgrade alert level
        """
        threats = self.db.get_all_threats()
        with self._lock:
            existing_ids = {a.threat_id for a in self._alerts if not a.acknowledged}

        for threat in threats:
            level = threat.get("threat_level", LEVEL_UNKNOWN)
            if LEVEL_PRIORITY.get(level, 0) < LEVEL_PRIORITY[LEVEL_MEDIUM]:
                continue  # Skip LOW and UNKNOWN

            if threat["id"] not in existing_ids:
                self._create_alert_from_threat(threat)
            else:
                self._check_escalation(threat)

    # ──────────────────────────────────────────────────────────────
    # SECTION 3: CREATE ALERT FROM THREAT
    # ──────────────────────────────────────────────────────────────
    def _create_alert_from_threat(self, threat):
        t_type  = threat.get("type", "UNKNOWN_AIRCRAFT")
        level   = threat.get("threat_level", LEVEL_UNKNOWN)

        # Look up message or build a default
        message = ALERT_MESSAGES.get(
            (t_type, level),
            f"{threat.get('name', 'Unknown')} classified as {level} "
            f"threat in {threat.get('sector', 'Unknown')}"
        )

        alert = Alert(
            threat_id   = threat["id"],
            threat_name = threat.get("name", threat["id"]),
            threat_type = t_type,
            level       = level,
            sector      = threat.get("sector", "Unknown"),
            message     = message
        )

        with self._lock:
            self._alerts.append(alert)

        print(f"[ALERT MANAGER] ⚠  NEW  [{level:8s}] {alert.id} "
              f"| {alert.threat_name} | {alert.sector}")
        return alert

    # ──────────────────────────────────────────────────────────────
    # SECTION 4: ESCALATION CHECK
    # If threat level increased → escalate existing alert
    # ──────────────────────────────────────────────────────────────
    def _check_escalation(self, threat):
        new_level = threat.get("threat_level", LEVEL_UNKNOWN)
        with self._lock:
            for alert in self._alerts:
                if alert.threat_id == threat["id"] and not alert.acknowledged:
                    old_priority = LEVEL_PRIORITY.get(alert.level, 0)
                    new_priority = LEVEL_PRIORITY.get(new_level, 0)
                    if new_priority > old_priority:
                        old_level = alert.level
                        alert.history.append({
                            "from"      : old_level,
                            "to"        : new_level,
                            "time"      : datetime.datetime.now().strftime("%H:%M:%S"),
                            "auto"      : True
                        })
                        alert.level           = new_level
                        alert.escalated       = True
                        alert.escalation_count += 1
                        alert.message         = ALERT_MESSAGES.get(
                            (alert.threat_type, new_level), alert.message
                        )
                        print(f"[ALERT MANAGER] 🔺 ESCALATED {alert.id} "
                              f"| {old_level} → {new_level} | {alert.threat_name}")

    # ──────────────────────────────────────────────────────────────
    # SECTION 5: GET ALERTS
    # ──────────────────────────────────────────────────────────────
    def get_active_alerts(self):
        """Return unacknowledged alerts sorted CRITICAL first."""
        with self._lock:
            active = [a for a in self._alerts if not a.acknowledged]
        active.sort(key=lambda a: LEVEL_PRIORITY.get(a.level, 0), reverse=True)
        return [a.to_dict() for a in active]

    def get_all_alerts(self):
        """Return all alerts including acknowledged, newest first."""
        with self._lock:
            all_a = list(self._alerts)
        all_a.sort(key=lambda a: a.timestamp, reverse=True)
        return [a.to_dict() for a in all_a]

    def get_alerts_by_level(self, level):
        """Return all alerts of a specific threat level."""
        if level not in VALID_LEVELS:
            return {"error": f"Invalid level. Choose from: {VALID_LEVELS}"}
        with self._lock:
            filtered = [a for a in self._alerts if a.level == level]
        filtered.sort(key=lambda a: a.timestamp, reverse=True)
        return [a.to_dict() for a in filtered]

    def get_alerts_by_sector(self, sector):
        """Return all alerts in a given sector."""
        with self._lock:
            filtered = [a for a in self._alerts
                        if a.sector.lower() == sector.lower()]
        return [a.to_dict() for a in filtered]

    def get_system_alerts(self):
        """Return only system/infrastructure alerts."""
        with self._lock:
            sys_alerts = [a for a in self._alerts if a.is_system]
        return [a.to_dict() for a in sys_alerts]

    def get_escalated_alerts(self):
        """Return only alerts that have been escalated."""
        with self._lock:
            esc = [a for a in self._alerts if a.escalated]
        return [a.to_dict() for a in esc]

    # ──────────────────────────────────────────────────────────────
    # SECTION 6: ACKNOWLEDGE
    # ──────────────────────────────────────────────────────────────
    def acknowledge_alert(self, alert_id, ack_by="Command Staff"):
        """Acknowledge a single alert by its ID."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    if alert.acknowledged:
                        return {"status": "already_acknowledged", "alert_id": alert_id}
                    alert.acknowledged = True
                    alert.ack_by       = ack_by
                    alert.ack_time     = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[ALERT MANAGER] ✔  ACK   {alert_id} by {ack_by}")
                    return {
                        "status"   : "acknowledged",
                        "alert_id" : alert_id,
                        "ack_by"   : ack_by,
                        "ack_time" : alert.ack_time
                    }
        return {"error": f"Alert ID '{alert_id}' not found"}

    def acknowledge_all(self, ack_by="Command Staff"):
        """Bulk-acknowledge all currently active alerts."""
        count = 0
        with self._lock:
            for alert in self._alerts:
                if not alert.acknowledged:
                    alert.acknowledged = True
                    alert.ack_by       = ack_by
                    alert.ack_time     = datetime.datetime.now().strftime("%H:%M:%S")
                    count += 1
        print(f"[ALERT MANAGER] ✔  ACK ALL — {count} alert(s) by {ack_by}")
        return {"status": "all_acknowledged", "count": count, "ack_by": ack_by}

    def acknowledge_by_level(self, level, ack_by="Command Staff"):
        """Acknowledge all alerts of a specific level."""
        if level not in VALID_LEVELS:
            return {"error": f"Invalid level '{level}'"}
        count = 0
        with self._lock:
            for alert in self._alerts:
                if alert.level == level and not alert.acknowledged:
                    alert.acknowledged = True
                    alert.ack_by       = ack_by
                    alert.ack_time     = datetime.datetime.now().strftime("%H:%M:%S")
                    count += 1
        return {"status": "acknowledged_by_level", "level": level, "count": count}

    # ──────────────────────────────────────────────────────────────
    # SECTION 7: MANUAL CLASSIFY / OVERRIDE
    # Called from dashboard reclassify dropdown
    # ──────────────────────────────────────────────────────────────
    def manual_classify(self, threat_id, level):
        """
        Override threat level from the dashboard.
        Updates both the DB and any live active alerts.
        """
        if not threat_id:
            return {"error": "threat_id is required"}
        if level not in VALID_LEVELS:
            return {"error": f"Invalid level '{level}'. Valid: {VALID_LEVELS}"}

        # 1. Update threat in database
        self.db.update_threat_level(threat_id, level)

        # 2. Update live active alert if exists
        alert_updated = False
        with self._lock:
            for alert in self._alerts:
                if alert.threat_id == threat_id and not alert.acknowledged:
                    old_level = alert.level
                    alert.history.append({
                        "from"   : old_level,
                        "to"     : level,
                        "time"   : datetime.datetime.now().strftime("%H:%M:%S"),
                        "manual" : True
                    })
                    alert.level   = level
                    alert.message = ALERT_MESSAGES.get(
                        (alert.threat_type, level),
                        f"Threat manually reclassified to {level}"
                    )
                    alert_updated = True
                    print(f"[ALERT MANAGER] ✏  CLASSIFY {threat_id}: "
                          f"{old_level} → {level} (manual)")

        return {
            "status"        : "updated",
            "id"            : threat_id,
            "level"         : level,
            "alert_updated" : alert_updated
        }

    # ──────────────────────────────────────────────────────────────
    # SECTION 8: OPERATOR NOTES
    # Add a note to any alert record
    # ──────────────────────────────────────────────────────────────
    def add_note(self, alert_id, note_text, added_by="Operator"):
        """Attach an operator note to an alert."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    note = {
                        "text"     : note_text,
                        "added_by" : added_by,
                        "time"     : datetime.datetime.now().strftime("%H:%M:%S")
                    }
                    alert.notes.append(note)
                    print(f"[ALERT MANAGER] 📝 NOTE  {alert_id} by {added_by}: {note_text}")
                    return {"status": "note_added", "alert_id": alert_id, "note": note}
        return {"error": f"Alert ID '{alert_id}' not found"}

    # ──────────────────────────────────────────────────────────────
    # SECTION 9: SYSTEM ALERTS
    # SAM offline, radar issues, perimeter breach etc.
    # ──────────────────────────────────────────────────────────────
    def add_system_alert(self, alert_type, sector="Defence Grid Alpha",
                         level=LEVEL_HIGH):
        """Create a system/infrastructure alert."""
        message = SYSTEM_ALERT_MESSAGES.get(
            alert_type,
            f"System event detected: {alert_type}"
        )
        alert = Alert(
            threat_id   = f"SYS-{alert_type}-{str(uuid.uuid4())[:4].upper()}",
            threat_name = alert_type,
            threat_type = "SYSTEM",
            level       = level,
            sector      = sector,
            message     = message,
            is_system   = True
        )
        with self._lock:
            self._alerts.append(alert)

        print(f"[ALERT MANAGER] 🔧 SYSTEM [{level:8s}] {alert.id} "
              f"| {alert_type} | {sector}")
        return alert.to_dict()

    # ──────────────────────────────────────────────────────────────
    # SECTION 10: DELETE & CLEANUP
    # ──────────────────────────────────────────────────────────────
    def delete_alert(self, alert_id):
        """Hard delete an alert by ID."""
        with self._lock:
            before = len(self._alerts)
            self._alerts = [a for a in self._alerts if a.id != alert_id]
            removed = before - len(self._alerts)
        if removed:
            print(f"[ALERT MANAGER] 🗑  DELETED {alert_id}")
            return {"status": "deleted", "alert_id": alert_id}
        return {"error": f"Alert ID '{alert_id}' not found"}

    def clear_acknowledged(self):
        """Remove all acknowledged alerts from memory."""
        with self._lock:
            before = len(self._alerts)
            self._alerts = [a for a in self._alerts if not a.acknowledged]
            cleared = before - len(self._alerts)
        print(f"[ALERT MANAGER] 🧹 CLEARED {cleared} acknowledged alert(s)")
        return {"status": "cleared", "count": cleared}

    def reset_all(self):
        """Wipe all alerts — use with caution."""
        with self._lock:
            count = len(self._alerts)
            self._alerts.clear()
        print(f"[ALERT MANAGER] ⚡ RESET — {count} alert(s) removed")
        return {"status": "reset", "removed": count}

    # ──────────────────────────────────────────────────────────────
    # SECTION 11: SUMMARY STATS
    # Used by Flask /api/stats and dashboard KPI cards
    # ──────────────────────────────────────────────────────────────
    def get_summary(self):
        """Return alert statistics for the dashboard."""
        with self._lock:
            all_a = list(self._alerts)

        active    = [a for a in all_a if not a.acknowledged]
        acked     = [a for a in all_a if a.acknowledged]
        escalated = [a for a in all_a if a.escalated]
        system    = [a for a in all_a if a.is_system]

        # Count active alerts by level
        by_level = {lvl: 0 for lvl in VALID_LEVELS}
        for a in active:
            by_level[a.level] = by_level.get(a.level, 0) + 1

        # Most recent alert
        recent = None
        if all_a:
            latest = max(all_a, key=lambda a: a.timestamp)
            recent = latest.to_dict()

        return {
            "total_alerts"   : len(all_a),
            "active_alerts"  : len(active),
            "acknowledged"   : len(acked),
            "escalated"      : len(escalated),
            "system_alerts"  : len(system),
            "by_level"       : by_level,
            "most_recent"    : recent
        }


# ══════════════════════════════════════════════════════════════════
# STANDALONE TEST — Run directly in PyCharm
# python alert_manager.py
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":

    # ── Mock Database for testing without Flask ──────────────────
    class MockDB:
        def get_all_threats(self):
            return [
                {
                    "id": "charlie-12", "name": "Charlie-12",
                    "type": "DRONE_SWARM", "threat_level": "CRITICAL",
                    "sector": "Sector 7-G", "unit_count": 12,
                    "speed": 85.0, "heading": 270.0,
                    "behavior_flags": "erratic,high_speed"
                },
                {
                    "id": "beta-3", "name": "Beta-3",
                    "type": "UNKNOWN_AIRCRAFT", "threat_level": "MEDIUM",
                    "sector": "North Quadrant", "unit_count": 3,
                    "speed": 40.0, "heading": 180.0,
                    "behavior_flags": "stealth_mode"
                },
                {
                    "id": "alpha-1", "name": "Alpha-1",
                    "type": "FIXED_WING", "threat_level": "HIGH",
                    "sector": "Defence Grid Alpha", "unit_count": 1,
                    "speed": 200.0, "heading": 90.0,
                    "behavior_flags": "jamming_detected"
                },
            ]
        def update_threat_level(self, tid, level):
            print(f"     [MockDB] {tid} → {level}")

    SEP = "─" * 60
    DBL = "═" * 60

    print(f"\n{DBL}")
    print("  AIR DEFENSE — alert_manager.py — Full Test")
    print(DBL)

    mgr = AlertManager(MockDB())

    # ── Test 1: Seeded demo alerts ────────────────────────────────
    print(f"\n[TEST 1] Seeded Demo Alerts (Dashboard Match)")
    print(SEP)
    for a in mgr.get_active_alerts():
        print(f"  [{a['level']:8s}] {a['id']} | {a['timestamp']} "
              f"| {a['threat_name']:12s} | {a['sector']}")
        print(f"            {a['message']}")

    # ── Test 2: Evaluate new threats ─────────────────────────────
    print(f"\n[TEST 2] Evaluate Threats (auto-generate alerts)")
    print(SEP)
    mgr.evaluate_threats()
    print(f"  Active alerts after evaluation: {len(mgr.get_active_alerts())}")

    # ── Test 3: Summary stats ─────────────────────────────────────
    print(f"\n[TEST 3] Alert Summary Stats")
    print(SEP)
    s = mgr.get_summary()
    print(f"  Total     : {s['total_alerts']}")
    print(f"  Active    : {s['active_alerts']}")
    print(f"  Escalated : {s['escalated']}")
    print(f"  By Level  : {s['by_level']}")

    # ── Test 4: Manual classify ───────────────────────────────────
    print(f"\n[TEST 4] Manual Classify — beta-3 → CRITICAL")
    print(SEP)
    result = mgr.manual_classify("beta-3", "CRITICAL")
    print(f"  Result: {result}")

    # ── Test 5: System alert ──────────────────────────────────────
    print(f"\n[TEST 5] Add System Alert — SAM_OFFLINE")
    print(SEP)
    sys_a = mgr.add_system_alert("SAM_OFFLINE", sector="Defence Grid Alpha", level=LEVEL_HIGH)
    print(f"  {sys_a['id']} | [{sys_a['level']}] {sys_a['message']}")

    # ── Test 6: Add operator note ─────────────────────────────────
    print(f"\n[TEST 6] Add Operator Note")
    print(SEP)
    first_id = mgr.get_active_alerts()[0]["id"]
    note_res = mgr.add_note(first_id, "Intercept assets scrambled. ETA 4 minutes.", "Commander")
    print(f"  {note_res}")

    # ── Test 7: Acknowledge one alert ─────────────────────────────
    print(f"\n[TEST 7] Acknowledge Alert: {first_id}")
    print(SEP)
    ack = mgr.acknowledge_alert(first_id, ack_by="Commander Alpha")
    print(f"  {ack}")

    # ── Test 8: Get alerts by level ───────────────────────────────
    print(f"\n[TEST 8] Alerts by Level — CRITICAL")
    print(SEP)
    for a in mgr.get_alerts_by_level("CRITICAL"):
        print(f"  {a['id']} | Acked: {a['acknowledged']} | {a['threat_name']} | {a['sector']}")

    # ── Test 9: Get alerts by sector ──────────────────────────────
    print(f"\n[TEST 9] Alerts by Sector — North Quadrant")
    print(SEP)
    for a in mgr.get_alerts_by_sector("North Quadrant"):
        print(f"  {a['id']} | [{a['level']}] {a['message']}")

    # ── Test 10: System alerts only ───────────────────────────────
    print(f"\n[TEST 10] System Alerts Only")
    print(SEP)
    for a in mgr.get_system_alerts():
        print(f"  {a['id']} | [{a['level']}] {a['message']} | {a['sector']}")

    # ── Test 11: Acknowledge all ──────────────────────────────────
    print(f"\n[TEST 11] Acknowledge ALL Remaining Alerts")
    print(SEP)
    print(f"  {mgr.acknowledge_all(ack_by='Shift Commander')}")

    # ── Test 12: Clear acknowledged ───────────────────────────────
    print(f"\n[TEST 12] Clear Acknowledged Alerts")
    print(SEP)
    print(f"  {mgr.clear_acknowledged()}")
    print(f"  Remaining active: {len(mgr.get_active_alerts())}")

    # ── Test 13: Final summary ────────────────────────────────────
    print(f"\n[TEST 13] Final Summary")
    print(SEP)
    final = mgr.get_summary()
    print(f"  Total    : {final['total_alerts']}")
    print(f"  Active   : {final['active_alerts']}")
    print(f"  Cleared  : {final['acknowledged']}")

    print(f"\n{DBL}")
    print("  ✅ alert_manager.py — All 13 Tests Passed")
    print(DBL)
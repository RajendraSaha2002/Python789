"""
╔══════════════════════════════════════════════════════════════╗
║   Air Defense Threat Intelligence Monitoring System          ║
║   intelligence_report.py — Report Generation & Analysis     ║
║   PyCharm | Python 3.12 | No external API | No plugins      ║
╚══════════════════════════════════════════════════════════════╝
"""

import datetime
import uuid


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
REPORT_VERSION  = "1.0"
CLASSIFICATION  = "TOP SECRET // NOFORN"
SYSTEM_NAME     = "Air Defense Threat Intelligence Monitoring System"

LEVEL_PRIORITY = {
    "CRITICAL" : 4,
    "HIGH"     : 3,
    "MEDIUM"   : 2,
    "LOW"      : 1,
    "UNKNOWN"  : 0
}

# Threat type human-readable labels
TYPE_LABELS = {
    "DRONE_SWARM"     : "Drone Swarm",
    "FIXED_WING"      : "Fixed-Wing Aircraft",
    "ROTARY"          : "Rotary Aircraft",
    "CRUISE_MISSILE"  : "Cruise Missile",
    "UNKNOWN_AIRCRAFT": "Unknown Aircraft",
    "SYSTEM"          : "System Event",
}

# Behavior flag descriptions
BEHAVIOR_DESCRIPTIONS = {
    "erratic"           : "Erratic / unpredictable flight path",
    "high_speed"        : "High-speed approach detected",
    "stealth_mode"      : "Low radar cross-section / stealth mode",
    "jamming_detected"  : "Electronic jamming signal detected",
    "formation_flight"  : "Coordinated formation flight pattern",
    "low_altitude"      : "Low-altitude terrain-following flight",
    "transponder_off"   : "Transponder disabled / ADS-B silent",
    "loitering"         : "Loitering pattern — possible ISR mission",
}


# ══════════════════════════════════════════════════════════════
# REPORT SECTION BUILDERS
# ══════════════════════════════════════════════════════════════
class IntelligenceReport:
    def __init__(self, db):
        self.db = db

    # ──────────────────────────────────────────────────────────
    # MASTER REPORT — Full intelligence summary (JSON)
    # Used by Flask /api/report endpoint
    # ──────────────────────────────────────────────────────────
    def generate_summary(self):
        threats    = self.db.get_all_threats()
        now        = datetime.datetime.now()
        report_id  = f"RPT-{str(uuid.uuid4())[:8].upper()}"

        # Categorize by level
        critical  = [t for t in threats if t.get("threat_level") == "CRITICAL"]
        high      = [t for t in threats if t.get("threat_level") == "HIGH"]
        medium    = [t for t in threats if t.get("threat_level") == "MEDIUM"]
        low       = [t for t in threats if t.get("threat_level") == "LOW"]
        unknown   = [t for t in threats if t.get("threat_level") == "UNKNOWN"]

        return {
            # ── Header ──
            "report_id"         : report_id,
            "report_version"    : REPORT_VERSION,
            "classification"    : CLASSIFICATION,
            "system"            : SYSTEM_NAME,
            "report_time"       : now.isoformat(),
            "report_date"       : now.strftime("%Y-%m-%d"),
            "report_timestamp"  : now.strftime("%H:%M:%S"),

            # ── Executive Summary ──
            "executive_summary" : self._executive_summary(threats, critical, high),

            # ── Threat Counts ──
            "summary": {
                "total_tracked"  : len(threats),
                "critical_count" : len(critical),
                "high_count"     : len(high),
                "medium_count"   : len(medium),
                "low_count"      : len(low),
                "unknown_count"  : len(unknown),
                "threat_index"   : self._threat_index(threats),
            },

            # ── Threat Sections ──
            "critical_threats"  : [self._threat_detail(t) for t in critical],
            "high_threats"      : [self._threat_detail(t) for t in high],
            "medium_threats"    : [self._threat_detail(t) for t in medium],
            "low_threats"       : [self._threat_detail(t) for t in low],

            # ── Analysis Sections ──
            "sector_analysis"   : self._sector_analysis(threats),
            "type_analysis"     : self._type_analysis(threats),
            "behavior_analysis" : self._behavior_analysis(threats),
            "pattern_summary"   : self._pattern_summary(threats),

            # ── Recommendations ──
            "recommendations"   : self._recommendations(critical, high, medium),

            # ── Disposition ──
            "disposition"       : self._disposition(threats),
        }

    # ──────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY — Short text paragraph
    # ──────────────────────────────────────────────────────────
    def _executive_summary(self, threats, critical, high):
        if not threats:
            return "No active threats detected. Airspace status: NOMINAL."

        total = len(threats)
        lines = []

        if critical:
            names = ", ".join(t["name"] for t in critical[:3])
            lines.append(
                f"CRITICAL ALERT: {len(critical)} critical-level threat(s) detected — {names}. "
                f"Immediate response action recommended."
            )
        if high:
            names = ", ".join(t["name"] for t in high[:3])
            lines.append(
                f"HIGH PRIORITY: {len(high)} high-level threat(s) require urgent attention — {names}."
            )
        lines.append(
            f"Total of {total} aircraft/contacts currently tracked across all monitored sectors."
        )

        sectors = list({t.get("sector","Unknown") for t in threats})
        lines.append(f"Active sectors under monitoring: {', '.join(sectors)}.")

        return " ".join(lines)

    # ──────────────────────────────────────────────────────────
    # THREAT DETAIL — Per-threat data block
    # ──────────────────────────────────────────────────────────
    def _threat_detail(self, t):
        flags    = [f.strip() for f in (t.get("behavior_flags") or "").split(",") if f.strip()]
        flag_desc = [BEHAVIOR_DESCRIPTIONS.get(f, f) for f in flags]

        return {
            "id"            : t.get("id"),
            "name"          : t.get("name"),
            "type"          : t.get("type"),
            "type_label"    : TYPE_LABELS.get(t.get("type"), t.get("type")),
            "threat_level"  : t.get("threat_level"),
            "sector"        : t.get("sector"),
            "unit_count"    : t.get("unit_count", 1),
            "speed_kts"     : t.get("speed", 0),
            "heading_deg"   : t.get("heading", 0),
            "coordinates"   : {
                "lat": t.get("lat", 0.0),
                "lng": t.get("lng", 0.0)
            },
            "behavior_flags"       : flags,
            "behavior_descriptions": flag_desc,
            "last_seen"     : t.get("timestamp", "Unknown"),
            "risk_score"    : self._compute_risk_score(t),
            "brief"         : self._threat_brief_text(t),
        }

    # ──────────────────────────────────────────────────────────
    # ONE-LINE THREAT BRIEF TEXT
    # ──────────────────────────────────────────────────────────
    def _threat_brief_text(self, t):
        type_label = TYPE_LABELS.get(t.get("type"), "Unknown")
        return (
            f"{t.get('name','Unknown')} — {type_label}, "
            f"{t.get('unit_count',1)} unit(s), "
            f"{t.get('sector','Unknown')}, "
            f"Speed: {t.get('speed',0)} kts, "
            f"Heading: {t.get('heading',0)}°"
        )

    # ──────────────────────────────────────────────────────────
    # RISK SCORE — 0 to 100
    # ──────────────────────────────────────────────────────────
    def _compute_risk_score(self, t):
        score = 0
        level = t.get("threat_level", "UNKNOWN")
        flags = [f.strip() for f in (t.get("behavior_flags") or "").split(",") if f.strip()]

        # Base score from threat level
        level_scores = {"CRITICAL": 60, "HIGH": 40, "MEDIUM": 20, "LOW": 5, "UNKNOWN": 0}
        score += level_scores.get(level, 0)

        # Unit count contribution (max +15)
        units = t.get("unit_count", 1)
        score += min(units * 2, 15)

        # Speed contribution (max +10)
        speed = t.get("speed", 0)
        if speed > 200: score += 10
        elif speed > 100: score += 5

        # Behavior flags (+3 each, max +15)
        dangerous_flags = {"erratic", "jamming_detected", "stealth_mode", "high_speed", "loitering"}
        score += min(len(dangerous_flags & set(flags)) * 3, 15)

        return min(score, 100)

    # ──────────────────────────────────────────────────────────
    # THREAT INDEX — Overall airspace threat score
    # ──────────────────────────────────────────────────────────
    def _threat_index(self, threats):
        if not threats:
            return {"score": 0, "label": "NOMINAL", "color": "green"}

        scores = [self._compute_risk_score(t) for t in threats]
        avg    = sum(scores) / len(scores)
        peak   = max(scores)
        index  = round((avg * 0.4) + (peak * 0.6))

        if index >= 75:   label, color = "CRITICAL",  "red"
        elif index >= 50: label, color = "ELEVATED",  "orange"
        elif index >= 25: label, color = "GUARDED",   "yellow"
        else:             label, color = "NOMINAL",   "green"

        return {"score": index, "label": label, "color": color}

    # ──────────────────────────────────────────────────────────
    # SECTOR ANALYSIS — Threats grouped by sector
    # ──────────────────────────────────────────────────────────
    def _sector_analysis(self, threats):
        sectors = {}
        for t in threats:
            sec = t.get("sector", "Unknown")
            if sec not in sectors:
                sectors[sec] = {
                    "sector"       : sec,
                    "threat_count" : 0,
                    "highest_level": "UNKNOWN",
                    "threats"      : []
                }
            sectors[sec]["threat_count"] += 1
            sectors[sec]["threats"].append(t.get("name"))

            # Track highest level in sector
            cur_priority = LEVEL_PRIORITY.get(sectors[sec]["highest_level"], 0)
            new_priority = LEVEL_PRIORITY.get(t.get("threat_level", "UNKNOWN"), 0)
            if new_priority > cur_priority:
                sectors[sec]["highest_level"] = t.get("threat_level")

        # Sort by highest threat level
        result = sorted(
            sectors.values(),
            key=lambda s: LEVEL_PRIORITY.get(s["highest_level"], 0),
            reverse=True
        )
        return result

    # ──────────────────────────────────────────────────────────
    # TYPE ANALYSIS — Breakdown by aircraft type
    # ──────────────────────────────────────────────────────────
    def _type_analysis(self, threats):
        types = {}
        for t in threats:
            ttype = t.get("type", "UNKNOWN")
            if ttype not in types:
                types[ttype] = {
                    "type"       : ttype,
                    "type_label" : TYPE_LABELS.get(ttype, ttype),
                    "count"      : 0,
                    "total_units": 0,
                    "avg_speed"  : 0,
                    "_speeds"    : []
                }
            types[ttype]["count"]       += 1
            types[ttype]["total_units"] += t.get("unit_count", 1)
            types[ttype]["_speeds"].append(t.get("speed", 0))

        # Calculate avg speed
        result = []
        for ttype, data in types.items():
            speeds = data.pop("_speeds")
            data["avg_speed"] = round(sum(speeds) / len(speeds), 1) if speeds else 0
            result.append(data)

        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    # ──────────────────────────────────────────────────────────
    # BEHAVIOR ANALYSIS — Most common threat behaviors
    # ──────────────────────────────────────────────────────────
    def _behavior_analysis(self, threats):
        flag_counts = {}
        for t in threats:
            flags = [f.strip() for f in (t.get("behavior_flags") or "").split(",") if f.strip()]
            for flag in flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        result = []
        for flag, count in sorted(flag_counts.items(), key=lambda x: x[1], reverse=True):
            result.append({
                "flag"        : flag,
                "description" : BEHAVIOR_DESCRIPTIONS.get(flag, flag),
                "occurrences" : count,
                "threat_level": "HIGH" if flag in {"jamming_detected", "erratic"} else "MEDIUM"
            })
        return result

    # ──────────────────────────────────────────────────────────
    # PATTERN SUMMARY — Detected tactical patterns
    # ──────────────────────────────────────────────────────────
    def _pattern_summary(self, threats):
        patterns = []
        flags_all = []
        for t in threats:
            flags_all += [f.strip() for f in (t.get("behavior_flags") or "").split(",") if f.strip()]

        # Swarm attack pattern
        swarms = [t for t in threats if t.get("type") == "DRONE_SWARM"]
        if swarms:
            total_units = sum(t.get("unit_count", 1) for t in swarms)
            patterns.append({
                "pattern"    : "SWARM_ATTACK",
                "label"      : "Drone Swarm Attack Pattern",
                "confidence" : "HIGH" if total_units >= 10 else "MEDIUM",
                "detail"     : f"{len(swarms)} swarm group(s) with {total_units} total units detected.",
                "action"     : "Deploy anti-drone countermeasures immediately."
            })

        # Electronic warfare pattern
        if "jamming_detected" in flags_all:
            patterns.append({
                "pattern"    : "ELECTRONIC_WARFARE",
                "label"      : "Electronic Warfare / Jamming",
                "confidence" : "HIGH",
                "detail"     : "Active jamming signals indicate coordinated EW operation.",
                "action"     : "Switch to backup comms. Activate ECCM protocols."
            })

        # Stealth infiltration pattern
        if "stealth_mode" in flags_all or "transponder_off" in flags_all:
            patterns.append({
                "pattern"    : "STEALTH_INFILTRATION",
                "label"      : "Stealth Infiltration Approach",
                "confidence" : "MEDIUM",
                "detail"     : "Low-observable aircraft detected. Radar cross-section minimization active.",
                "action"     : "Activate secondary radar. Deploy IR/optical tracking."
            })

        # Multi-sector saturation
        sectors = {t.get("sector") for t in threats}
        if len(sectors) >= 3:
            patterns.append({
                "pattern"    : "MULTI_SECTOR_SATURATION",
                "label"      : "Multi-Sector Saturation Attack",
                "confidence" : "MEDIUM",
                "detail"     : f"Threats detected across {len(sectors)} sectors simultaneously.",
                "action"     : "Reinforce all sector boundaries. Request additional intercept assets."
            })

        if not patterns:
            patterns.append({
                "pattern"    : "NO_PATTERN",
                "label"      : "No Coordinated Pattern Detected",
                "confidence" : "HIGH",
                "detail"     : "Individual isolated contacts. No coordinated attack signature.",
                "action"     : "Continue standard monitoring protocols."
            })

        return patterns

    # ──────────────────────────────────────────────────────────
    # RECOMMENDATIONS — Actionable command guidance
    # ──────────────────────────────────────────────────────────
    def _recommendations(self, critical, high, medium):
        recs = []
        priority = 1

        if critical:
            names = ", ".join(t["name"] for t in critical)
            recs.append({
                "priority"  : priority,
                "level"     : "IMMEDIATE",
                "action"    : f"Scramble intercept assets for critical threat(s): {names}.",
                "rationale" : "Critical-level threats pose direct risk to protected infrastructure."
            })
            priority += 1

            # Check for drone swarms specifically
            swarms = [t for t in critical if t.get("type") == "DRONE_SWARM"]
            if swarms:
                recs.append({
                    "priority"  : priority,
                    "level"     : "IMMEDIATE",
                    "action"    : "Activate anti-drone countermeasures and close-in weapon systems.",
                    "rationale" : f"Swarm of {sum(t.get('unit_count',1) for t in swarms)} units detected."
                })
                priority += 1

        if high:
            recs.append({
                "priority"  : priority,
                "level"     : "URGENT",
                "action"    : "Restore all offline SAM batteries and defensive systems.",
                "rationale" : "Degraded defensive coverage creates exploitable gaps."
            })
            priority += 1
            recs.append({
                "priority"  : priority,
                "level"     : "URGENT",
                "action"    : "Increase radar sweep frequency. Deploy mobile radar units to blind spots.",
                "rationale" : "High-priority threats require continuous track maintenance."
            })
            priority += 1

        if medium:
            recs.append({
                "priority"  : priority,
                "level"     : "ADVISORY",
                "action"    : "Increase perimeter patrol and reinforce outer defensive positions.",
                "rationale" : "Medium-level contacts have breached outer perimeter."
            })
            priority += 1

        if not critical and not high:
            recs.append({
                "priority"  : priority,
                "level"     : "ROUTINE",
                "action"    : "Maintain standard monitoring posture. No immediate action required.",
                "rationale" : "Situation is within acceptable threat parameters."
            })

        # Always-present standing recommendation
        recs.append({
            "priority"  : priority + 1,
            "level"     : "STANDING",
            "action"    : "Submit updated intelligence to command within 30 minutes.",
            "rationale" : "Continuous reporting ensures command situational awareness."
        })

        return recs

    # ──────────────────────────────────────────────────────────
    # DISPOSITION — Current posture summary
    # ──────────────────────────────────────────────────────────
    def _disposition(self, threats):
        total    = len(threats)
        critical = sum(1 for t in threats if t.get("threat_level") == "CRITICAL")
        high     = sum(1 for t in threats if t.get("threat_level") == "HIGH")

        if critical > 0:
            posture = "WEAPONS FREE"
            status  = "ENGAGED"
            color   = "red"
        elif high > 0:
            posture = "WEAPONS TIGHT"
            status  = "ELEVATED READINESS"
            color   = "orange"
        elif total > 0:
            posture = "WEAPONS HOLD"
            status  = "MONITORING"
            color   = "yellow"
        else:
            posture = "WEAPONS SAFE"
            status  = "NOMINAL"
            color   = "green"

        return {
            "posture"          : posture,
            "status"           : status,
            "color"            : color,
            "total_tracked"    : total,
            "assessed_at"      : datetime.datetime.now().strftime("%H:%M:%S"),
            "next_review_in"   : "15 minutes",
        }

    # ──────────────────────────────────────────────────────────
    # PLAIN TEXT REPORT — For terminal / log output
    # ──────────────────────────────────────────────────────────
    def generate_text_report(self):
        r    = self.generate_summary()
        now  = r["report_time"]
        sep  = "─" * 62
        dbl  = "═" * 62

        lines = [
            dbl,
            f"  {CLASSIFICATION}",
            f"  {SYSTEM_NAME}",
            f"  Report ID  : {r['report_id']}",
            f"  Generated  : {now}",
            dbl,
            "",
            "  EXECUTIVE SUMMARY",
            sep,
            f"  {r['executive_summary']}",
            "",
            "  THREAT OVERVIEW",
            sep,
            f"  Total Tracked  : {r['summary']['total_tracked']}",
            f"  ├─ CRITICAL    : {r['summary']['critical_count']}",
            f"  ├─ HIGH        : {r['summary']['high_count']}",
            f"  ├─ MEDIUM      : {r['summary']['medium_count']}",
            f"  └─ LOW/UNKNOWN : {r['summary']['low_count'] + r['summary']['unknown_count']}",
            f"  Threat Index   : {r['summary']['threat_index']['score']}/100 "
            f"[{r['summary']['threat_index']['label']}]",
            "",
        ]

        # Critical threats
        if r["critical_threats"]:
            lines += ["  ▶ CRITICAL THREATS", sep]
            for t in r["critical_threats"]:
                lines.append(f"  [{t['id']}] {t['name']} — {t['sector']}")
                lines.append(f"      Type: {t['type_label']} | Units: {t['unit_count']} | Speed: {t['speed_kts']} kts")
                lines.append(f"      Risk Score: {t['risk_score']}/100")
                lines.append(f"      Behaviors: {', '.join(t['behavior_descriptions']) or 'None'}")
                lines.append("")

        # High threats
        if r["high_threats"]:
            lines += ["  ▶ HIGH PRIORITY THREATS", sep]
            for t in r["high_threats"]:
                lines.append(f"  [{t['id']}] {t['name']} — {t['sector']}")
                lines.append(f"      Type: {t['type_label']} | Units: {t['unit_count']} | Speed: {t['speed_kts']} kts")
                lines.append(f"      Risk Score: {t['risk_score']}/100")
                lines.append("")

        # Patterns
        lines += ["  ▶ DETECTED PATTERNS", sep]
        for p in r["pattern_summary"]:
            lines.append(f"  [{p['confidence']}] {p['label']}")
            lines.append(f"      {p['detail']}")
            lines.append(f"      ACTION: {p['action']}")
            lines.append("")

        # Recommendations
        lines += ["  ▶ RECOMMENDATIONS", sep]
        for rec in r["recommendations"]:
            lines.append(f"  [{rec['priority']}] [{rec['level']}] {rec['action']}")
        lines.append("")

        # Disposition
        disp = r["disposition"]
        lines += [
            "  ▶ CURRENT DISPOSITION",
            sep,
            f"  Posture : {disp['posture']}",
            f"  Status  : {disp['status']}",
            f"  Assessed: {disp['assessed_at']}",
            f"  Review  : {disp['next_review_in']}",
            "",
            dbl,
            f"  END OF REPORT — {r['report_id']}",
            dbl,
        ]

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# STANDALONE TEST — Run directly to verify
# python intelligence_report.py
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    class MockDB:
        def get_all_threats(self):
            return [
                {
                    "id": "charlie-12", "name": "Charlie-12",
                    "type": "DRONE_SWARM", "threat_level": "CRITICAL",
                    "sector": "Sector 7-G", "unit_count": 12,
                    "speed": 85.0, "heading": 270.0,
                    "lat": 34.05, "lng": -118.25,
                    "timestamp": "2024-01-01T11:26:26",
                    "behavior_flags": "erratic,high_speed"
                },
                {
                    "id": "alpha-1", "name": "Alpha-1",
                    "type": "FIXED_WING", "threat_level": "HIGH",
                    "sector": "Defence Grid Alpha", "unit_count": 1,
                    "speed": 200.0, "heading": 90.0,
                    "lat": 34.08, "lng": -118.20,
                    "timestamp": "2024-01-01T11:21:28",
                    "behavior_flags": "jamming_detected,transponder_off"
                },
                {
                    "id": "beta-3", "name": "Beta-3",
                    "type": "UNKNOWN_AIRCRAFT", "threat_level": "MEDIUM",
                    "sector": "North Quadrant", "unit_count": 3,
                    "speed": 40.0, "heading": 180.0,
                    "lat": 34.10, "lng": -118.30,
                    "timestamp": "2024-01-01T11:12:34",
                    "behavior_flags": "stealth_mode,loitering"
                },
            ]

    print("\n")
    reporter = IntelligenceReport(MockDB())

    # ── Test 1: Full JSON summary
    print("[TEST 1] JSON Summary Report")
    summary = reporter.generate_summary()
    print(f"  Report ID       : {summary['report_id']}")
    print(f"  Total Tracked   : {summary['summary']['total_tracked']}")
    print(f"  Critical        : {summary['summary']['critical_count']}")
    print(f"  Threat Index    : {summary['summary']['threat_index']}")
    print(f"  Patterns Found  : {len(summary['pattern_summary'])}")
    print(f"  Recommendations : {len(summary['recommendations'])}")
    print(f"  Disposition     : {summary['disposition']['posture']} / {summary['disposition']['status']}")
    print()

    # ── Test 2: Sector analysis
    print("[TEST 2] Sector Analysis")
    for sec in summary["sector_analysis"]:
        print(f"  {sec['sector']:25s} | {sec['highest_level']:8s} | {sec['threat_count']} threat(s)")
    print()

    # ── Test 3: Behavior analysis
    print("[TEST 3] Behavior Analysis")
    for b in summary["behavior_analysis"]:
        print(f"  {b['flag']:20s} | x{b['occurrences']} | {b['description']}")
    print()

    # ── Test 4: Risk scores
    print("[TEST 4] Threat Risk Scores")
    for t in summary["critical_threats"] + summary["high_threats"] + summary["medium_threats"]:
        print(f"  {t['name']:12s} | {t['threat_level']:8s} | Risk: {t['risk_score']:3d}/100 | {t['brief']}")
    print()

    # ── Test 5: Full plain text report
    print("[TEST 5] Plain Text Report")
    print(reporter.generate_text_report())
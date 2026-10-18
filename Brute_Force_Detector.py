import os
import sys
import re
import csv
import json
import time
import sqlite3
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Iterator


# ==============================================================================
# 1. CONSTANTS, ENUMS & TERMINAL COLOR PALETTE
# ==============================================================================

class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class AuthStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INVALID_USER = "INVALID_USER"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ==============================================================================
# 2. DATA MODELS & CONFIGURATION
# ==============================================================================

@dataclass
class LogEvent:
    """Normalized Authentication Event Model."""
    timestamp: datetime
    source_ip: str
    username: str
    service: str
    status: AuthStatus
    port: int = 0
    failure_reason: str = ""
    raw_message: str = ""


@dataclass
class SecurityAlert:
    """Security Incident & Alert Dossier."""
    alert_id: str
    timestamp: datetime
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    source_ip: str
    target_usernames: List[str]
    event_count: int
    window_seconds: int
    summary: str
    mitigation_recommendation: str


@dataclass
class DetectionConfig:
    """Configurable correlation time windows and trigger thresholds."""
    # Rule 1: High-Frequency Single-Target Brute Force
    brute_force_window_sec: int = 60
    brute_force_failure_threshold: int = 5

    # Rule 2: Horizontal Password Spraying (Single IP -> Multiple Usernames)
    spray_window_sec: int = 180
    spray_unique_users_threshold: int = 4

    # Rule 3: Distributed Credential Stuffing (Multiple IPs -> Single Username)
    stuffing_window_sec: int = 120
    stuffing_unique_ips_threshold: int = 4

    # Rule 4: Total Authentication Rate Flood (Denial of Service / Rapid Brute Force)
    rate_flood_window_sec: int = 30
    rate_flood_threshold: int = 25

    # Rule 5: Successful Compromise After Failures (Failure count threshold prior to success)
    compromise_prior_failure_threshold: int = 4
    compromise_lookback_window_sec: int = 300


# ==============================================================================
# 3. RELATIONAL PERSISTENCE (SQLite3 Database)
# ==============================================================================

class DatabaseManager:
    """Manages indexed relational storage for raw authentication events and alerts."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript("""
                                    CREATE TABLE IF NOT EXISTS auth_logs
                                    (
                                        id
                                        INTEGER
                                        PRIMARY
                                        KEY
                                        AUTOINCREMENT,
                                        timestamp
                                        TEXT
                                        NOT
                                        NULL,
                                        source_ip
                                        TEXT
                                        NOT
                                        NULL,
                                        username
                                        TEXT
                                        NOT
                                        NULL,
                                        service
                                        TEXT
                                        NOT
                                        NULL,
                                        status
                                        TEXT
                                        NOT
                                        NULL,
                                        port
                                        INTEGER
                                        DEFAULT
                                        0,
                                        failure_reason
                                        TEXT,
                                        raw_message
                                        TEXT
                                    );

                                    CREATE TABLE IF NOT EXISTS security_alerts
                                    (
                                        alert_id
                                        TEXT
                                        PRIMARY
                                        KEY,
                                        timestamp
                                        TEXT
                                        NOT
                                        NULL,
                                        rule_id
                                        TEXT
                                        NOT
                                        NULL,
                                        rule_name
                                        TEXT
                                        NOT
                                        NULL,
                                        severity
                                        TEXT
                                        NOT
                                        NULL,
                                        source_ip
                                        TEXT
                                        NOT
                                        NULL,
                                        target_usernames
                                        TEXT
                                        NOT
                                        NULL,
                                        event_count
                                        INTEGER
                                        NOT
                                        NULL,
                                        window_seconds
                                        INTEGER
                                        NOT
                                        NULL,
                                        summary
                                        TEXT
                                        NOT
                                        NULL,
                                        mitigation
                                        TEXT
                                        NOT
                                        NULL
                                    );

                                    CREATE INDEX IF NOT EXISTS idx_logs_ts ON auth_logs(timestamp);
                                    CREATE INDEX IF NOT EXISTS idx_logs_ip ON auth_logs(source_ip);
                                    CREATE INDEX IF NOT EXISTS idx_logs_user ON auth_logs(username);
                                    CREATE INDEX IF NOT EXISTS idx_logs_status ON auth_logs(status);
                                    """)

    def insert_events(self, events: List[LogEvent]) -> None:
        with self.conn:
            self.conn.executemany("""
                                  INSERT INTO auth_logs (timestamp, source_ip, username, service, status, port,
                                                         failure_reason, raw_message)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                                  """, [
                                      (
                                          e.timestamp.isoformat(),
                                          e.source_ip,
                                          e.username,
                                          e.service,
                                          e.status.value,
                                          e.port,
                                          e.failure_reason,
                                          e.raw_message
                                      ) for e in events
                                  ])

    def insert_alerts(self, alerts: List[SecurityAlert]) -> None:
        with self.conn:
            self.conn.executemany("""
                INSERT OR REPLACE INTO security_alerts (
                    alert_id, timestamp, rule_id, rule_name, severity, source_ip,
                    target_usernames, event_count, window_seconds, summary, mitigation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    a.alert_id,
                    a.timestamp.isoformat(),
                    a.rule_id,
                    a.rule_name,
                    a.severity.value,
                    a.source_ip,
                    json.dumps(a.target_usernames),
                    a.event_count,
                    a.window_seconds,
                    a.summary,
                    a.mitigation_recommendation
                ) for a in alerts
            ])

    def fetch_all_alerts(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM security_alerts ORDER BY timestamp ASC;")
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["target_usernames"] = json.loads(item["target_usernames"])
            results.append(item)
        return results

    def fetch_telemetry_metrics(self) -> Dict[str, Any]:
        with self.conn:
            total_logs = self.conn.execute("SELECT COUNT(*) FROM auth_logs;").fetchone()[0]
            total_failures = self.conn.execute(
                "SELECT COUNT(*) FROM auth_logs WHERE status IN ('FAILURE', 'INVALID_USER');"
            ).fetchone()[0]
            total_success = self.conn.execute(
                "SELECT COUNT(*) FROM auth_logs WHERE status = 'SUCCESS';"
            ).fetchone()[0]
            total_alerts = self.conn.execute("SELECT COUNT(*) FROM security_alerts;").fetchone()[0]

            top_ips = self.conn.execute("""
                                        SELECT source_ip, COUNT(*) as cnt
                                        FROM auth_logs
                                        WHERE status IN ('FAILURE', 'INVALID_USER')
                                        GROUP BY source_ip
                                        ORDER BY cnt DESC LIMIT 5;
                                        """).fetchall()

            top_users = self.conn.execute("""
                                          SELECT username, COUNT(*) as cnt
                                          FROM auth_logs
                                          WHERE status IN ('FAILURE', 'INVALID_USER')
                                          GROUP BY username
                                          ORDER BY cnt DESC LIMIT 5;
                                          """).fetchall()

        return {
            "total_logs": total_logs,
            "total_failures": total_failures,
            "total_success": total_success,
            "total_alerts": total_alerts,
            "top_malicious_ips": [(row["source_ip"], row["cnt"]) for row in top_ips],
            "top_targeted_users": [(row["username"], row["cnt"]) for row in top_users]
        }


# ==============================================================================
# 4. MULTI-FORMAT LOG PARSER ENGINE
# ==============================================================================

class LogParser:
    """Ingests and normalizes various authentication log formats using regular expressions."""

    # 1. OpenSSH / Syslog standard failed patterns
    SSH_FAILED_PWD = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"sshd\[(?P<pid>\d+)\]:\s+Failed password for (invalid user )?(?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)",
        re.IGNORECASE
    )

    # 2. OpenSSH / Syslog accepted login
    SSH_ACCEPTED_PWD = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"sshd\[(?P<pid>\d+)\]:\s+Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)",
        re.IGNORECASE
    )

    # 3. OpenSSH Invalid User Pre-Check
    SSH_INVALID_USER = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"sshd\[(?P<pid>\d+)\]:\s+Invalid user (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})",
        re.IGNORECASE
    )

    # 4. Fallback Regex for Generic IP and Username extractions
    GENERIC_IP = re.compile(r"\b(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\b")
    GENERIC_USER = re.compile(r"\b(?:user|username|account|login)[:=\s]+(?P<user>[A-Za-z0-9_\.\-]+)", re.IGNORECASE)

    MONTH_MAP = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    @classmethod
    def parse_syslog_timestamp(cls, month_str: str, day_str: str, time_str: str) -> datetime:
        """Converts syslog date headers (e.g. 'Oct 24 14:02:19') to absolute datetime."""
        now = datetime.now()
        month = cls.MONTH_MAP.get(month_str, now.month)
        day = int(day_str)
        t_parts = [int(p) for p in time_str.split(":")]

        # Calculate year assumption (handles year rollover)
        dt = datetime(now.year, month, day, t_parts[0], t_parts[1], t_parts[2])
        if dt > now + timedelta(days=1):
            dt = datetime(now.year - 1, month, day, t_parts[0], t_parts[1], t_parts[2])
        return dt

    @classmethod
    def parse_line(cls, line: str) -> Optional[LogEvent]:
        """Examines a single log string and normalizes it into a LogEvent object."""
        line = line.strip()
        if not line:
            return None

        # Strategy 1: JSON Formatted Authentication Event
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
                status_raw = data.get("status", "FAILURE").upper()
                status = AuthStatus.SUCCESS if "SUCCESS" in status_raw else AuthStatus.FAILURE
                return LogEvent(
                    timestamp=ts,
                    source_ip=data.get("source_ip", data.get("ip", "127.0.0.1")),
                    username=data.get("username", data.get("user", "unknown")),
                    service=data.get("service", "app-auth"),
                    status=status,
                    port=int(data.get("port", 0)),
                    failure_reason=data.get("reason", ""),
                    raw_message=line
                )
            except Exception:
                pass  # Fall through to standard syslog regexes

        # Strategy 2: OpenSSH Failed Password
        m_failed = cls.SSH_FAILED_PWD.search(line)
        if m_failed:
            ts = cls.parse_syslog_timestamp(m_failed.group("month"), m_failed.group("day"), m_failed.group("time"))
            user = m_failed.group("user")
            ip = m_failed.group("ip")
            port = int(m_failed.group("port"))
            is_invalid = "invalid user" in line.lower()
            return LogEvent(
                timestamp=ts,
                source_ip=ip,
                username=user,
                service="sshd",
                status=AuthStatus.INVALID_USER if is_invalid else AuthStatus.FAILURE,
                port=port,
                failure_reason="Bad password" if not is_invalid else "User does not exist",
                raw_message=line
            )

        # Strategy 3: OpenSSH Accepted Password / PublicKey
        m_ok = cls.SSH_ACCEPTED_PWD.search(line)
        if m_ok:
            ts = cls.parse_syslog_timestamp(m_ok.group("month"), m_ok.group("day"), m_ok.group("time"))
            return LogEvent(
                timestamp=ts,
                source_ip=m_ok.group("ip"),
                username=m_ok.group("user"),
                service="sshd",
                status=AuthStatus.SUCCESS,
                port=int(m_ok.group("port")),
                failure_reason="",
                raw_message=line
            )

        # Strategy 4: OpenSSH Invalid User Pre-Check
        m_inv = cls.SSH_INVALID_USER.search(line)
        if m_inv:
            ts = cls.parse_syslog_timestamp(m_inv.group("month"), m_inv.group("day"), m_inv.group("time"))
            return LogEvent(
                timestamp=ts,
                source_ip=m_inv.group("ip"),
                username=m_inv.group("user"),
                service="sshd",
                status=AuthStatus.INVALID_USER,
                port=0,
                failure_reason="Non-existent account targeted",
                raw_message=line
            )

        # Strategy 5: Generic Fallback Parser
        m_ip = cls.GENERIC_IP.search(line)
        m_user = cls.GENERIC_USER.search(line)
        if m_ip and ("fail" in line.lower() or "denied" in line.lower() or "invalid" in line.lower()):
            ip = m_ip.group("ip")
            user = m_user.group("user") if m_user else "unknown"
            return LogEvent(
                timestamp=datetime.now(),
                source_ip=ip,
                username=user,
                service="generic-auth",
                status=AuthStatus.FAILURE,
                port=0,
                failure_reason="Generic authentication failure match",
                raw_message=line
            )

        return None


# ==============================================================================
# 5. BEHAVIORAL DETECTION & CORRELATION ENGINE
# ==============================================================================

class BruteForceDetector:
    """
    Correlates streaming and historical log events using temporal sliding windows
    to detect targeted brute-force, horizontal spraying, and credential stuffing.
    """

    def __init__(self, config: DetectionConfig):
        self.config = config

        # In-memory sliding windows: Key -> deque of LogEvents
        self.ip_failure_window: Dict[str, deque] = defaultdict(deque)
        self.ip_all_window: Dict[str, deque] = defaultdict(deque)
        self.user_failure_window: Dict[str, deque] = defaultdict(deque)

        # Track persistent failure history per IP: user -> count
        self.ip_user_failure_history: Dict[Tuple[str, str], int] = defaultdict(int)

        # Set of generated alert IDs to prevent duplicate spamming
        self.generated_alert_ids = set()

    def process_event(self, event: LogEvent) -> List[SecurityAlert]:
        """Ingests a normalized event, updates sliding windows, and applies correlation rules."""
        alerts: List[SecurityAlert] = []
        cur_time = event.timestamp

        # ----------------------------------------------------------------------
        # Update Sliding Windows
        # ----------------------------------------------------------------------
        # 1. Total Activity Window (For Rate Flooding / Denial of Service)
        all_hist = self.ip_all_window[event.source_ip]
        all_hist.append(event)
        self._prune_window(all_hist, cur_time, self.config.rate_flood_window_sec)

        # Handle Failures
        if event.status in (AuthStatus.FAILURE, AuthStatus.INVALID_USER):
            # IP failure window
            ip_fail_hist = self.ip_failure_window[event.source_ip]
            ip_fail_hist.append(event)
            self._prune_window(ip_fail_hist, cur_time,
                               max(self.config.brute_force_window_sec, self.config.spray_window_sec))

            # User failure window
            u_fail_hist = self.user_failure_window[event.username]
            u_fail_hist.append(event)
            self._prune_window(u_fail_hist, cur_time, self.config.stuffing_window_sec)

            # Cumulative counter for compromise correlation
            self.ip_user_failure_history[(event.source_ip, event.username)] += 1

        # ----------------------------------------------------------------------
        # EVALUATE DETECTION RULES
        # ----------------------------------------------------------------------

        # RULE 1: High-Frequency Single-Target Brute Force
        if event.status in (AuthStatus.FAILURE, AuthStatus.INVALID_USER):
            bf_alert = self._eval_rule_single_target_bruteforce(event, cur_time)
            if bf_alert:
                alerts.append(bf_alert)

        # RULE 2: Horizontal Password Spraying
        if event.status in (AuthStatus.FAILURE, AuthStatus.INVALID_USER):
            spray_alert = self._eval_rule_password_spraying(event, cur_time)
            if spray_alert:
                alerts.append(spray_alert)

        # RULE 3: Distributed Credential Stuffing
        if event.status in (AuthStatus.FAILURE, AuthStatus.INVALID_USER):
            stuffing_alert = self._eval_rule_credential_stuffing(event, cur_time)
            if stuffing_alert:
                alerts.append(stuffing_alert)

        # RULE 4: Velocity Flood / Gateway Authentication Flood
        flood_alert = self._eval_rule_rate_flood(event, cur_time)
        if flood_alert:
            alerts.append(flood_alert)

        # RULE 5: Potential Account Compromise Post-Brute-Force
        if event.status == AuthStatus.SUCCESS:
            comp_alert = self._eval_rule_compromise_post_bruteforce(event, cur_time)
            if comp_alert:
                alerts.append(comp_alert)

        return alerts

    def _prune_window(self, queue: deque, current_time: datetime, window_sec: int) -> None:
        """Removes events that have aged out of the sliding temporal window."""
        cutoff = current_time - timedelta(seconds=window_sec)
        while queue and queue[0].timestamp < cutoff:
            queue.popleft()

    def _eval_rule_single_target_bruteforce(self, event: LogEvent, cur_time: datetime) -> Optional[SecurityAlert]:
        """Detects repeated authentication failures from one IP against a single user."""
        cutoff = cur_time - timedelta(seconds=self.config.brute_force_window_sec)
        recent_failures = [
            e for e in self.ip_failure_window[event.source_ip]
            if e.timestamp >= cutoff and e.username.lower() == event.username.lower()
        ]

        if len(recent_failures) >= self.config.brute_force_failure_threshold:
            alert_id = f"BF-TARGET-{event.source_ip}-{event.username.lower()}-{cur_time.strftime('%Y%m%d%H%M')}"
            if alert_id in self.generated_alert_ids:
                return None
            self.generated_alert_ids.add(alert_id)

            return SecurityAlert(
                alert_id=alert_id,
                timestamp=cur_time,
                rule_id="RULE-001",
                rule_name="Targeted Single-User Brute Force",
                severity=AlertSeverity.HIGH,
                source_ip=event.source_ip,
                target_usernames=[event.username],
                event_count=len(recent_failures),
                window_seconds=self.config.brute_force_window_sec,
                summary=f"IP {event.source_ip} triggered {len(recent_failures)} failed logins against '{event.username}' in {self.config.brute_force_window_sec}s.",
                mitigation_recommendation="Implement immediate firewall drop rule (iptables/nftables) and force MFA for target account."
            )
        return None

    def _eval_rule_password_spraying(self, event: LogEvent, cur_time: datetime) -> Optional[SecurityAlert]:
        """Detects one IP hitting multiple distinct accounts (horizontal spray)."""
        cutoff = cur_time - timedelta(seconds=self.config.spray_window_sec)
        recent_failures = [
            e for e in self.ip_failure_window[event.source_ip]
            if e.timestamp >= cutoff
        ]
        unique_users = {e.username.lower() for e in recent_failures if e.username}

        if len(unique_users) >= self.config.spray_unique_users_threshold:
            alert_id = f"SPRAY-{event.source_ip}-{cur_time.strftime('%Y%m%d%H%M')}"
            if alert_id in self.generated_alert_ids:
                return None
            self.generated_alert_ids.add(alert_id)

            return SecurityAlert(
                alert_id=alert_id,
                timestamp=cur_time,
                rule_id="RULE-002",
                rule_name="Horizontal Password Spraying Campaign",
                severity=AlertSeverity.CRITICAL,
                source_ip=event.source_ip,
                target_usernames=sorted(list(unique_users)),
                event_count=len(recent_failures),
                window_seconds=self.config.spray_window_sec,
                summary=f"IP {event.source_ip} targeted {len(unique_users)} distinct accounts across {len(recent_failures)} attempts in {self.config.spray_window_sec}s.",
                mitigation_recommendation="Null-route attacker IP at upstream perimeter; review active sessions for targeted accounts."
            )
        return None

    def _eval_rule_credential_stuffing(self, event: LogEvent, cur_time: datetime) -> Optional[SecurityAlert]:
        """Detects multiple distributed IPs pounding a single target account."""
        cutoff = cur_time - timedelta(seconds=self.config.stuffing_window_sec)
        recent_failures = [
            e for e in self.user_failure_window[event.username]
            if e.timestamp >= cutoff
        ]
        unique_ips = {e.source_ip for e in recent_failures}

        if len(unique_ips) >= self.config.stuffing_unique_ips_threshold:
            alert_id = f"STUFF-{event.username.lower()}-{cur_time.strftime('%Y%m%d%H%M')}"
            if alert_id in self.generated_alert_ids:
                return None
            self.generated_alert_ids.add(alert_id)

            return SecurityAlert(
                alert_id=alert_id,
                timestamp=cur_time,
                rule_id="RULE-003",
                rule_name="Distributed Credential Stuffing",
                severity=AlertSeverity.HIGH,
                source_ip="DISTRIBUTED_BOTNET",
                target_usernames=[event.username],
                event_count=len(recent_failures),
                window_seconds=self.config.stuffing_window_sec,
                summary=f"Account '{event.username}' targeted by {len(unique_ips)} disparate IP addresses within {self.config.stuffing_window_sec}s.",
                mitigation_recommendation="Apply CAPTCHA challenge on authentication endpoints and enable anomaly risk scoring."
            )
        return None

    def _eval_rule_rate_flood(self, event: LogEvent, cur_time: datetime) -> Optional[SecurityAlert]:
        """Detects rapid-fire submission floods from a single origin."""
        all_recent = self.ip_all_window[event.source_ip]
        if len(all_recent) >= self.config.rate_flood_threshold:
            alert_id = f"FLOOD-{event.source_ip}-{cur_time.strftime('%Y%m%d%H%M')}"
            if alert_id in self.generated_alert_ids:
                return None
            self.generated_alert_ids.add(alert_id)

            return SecurityAlert(
                alert_id=alert_id,
                timestamp=cur_time,
                rule_id="RULE-004",
                rule_name="Authentication Rate Flooding / Denial of Service",
                severity=AlertSeverity.MEDIUM,
                source_ip=event.source_ip,
                target_usernames=["MULTI"],
                event_count=len(all_recent),
                window_seconds=self.config.rate_flood_window_sec,
                summary=f"IP {event.source_ip} reached {len(all_recent)} requests within {self.config.rate_flood_window_sec}s.",
                mitigation_recommendation="Enact rate limiting on API ingress gateway (Nginx/Envoy limit_req)."
            )
        return None

    def _eval_rule_compromise_post_bruteforce(self, event: LogEvent, cur_time: datetime) -> Optional[SecurityAlert]:
        """Detects a successful login directly following repeated failed attempts from the same source."""
        key = (event.source_ip, event.username)
        prior_fails = self.ip_user_failure_history.get(key, 0)

        if prior_fails >= self.config.compromise_prior_failure_threshold:
            alert_id = f"COMPROMISE-{event.source_ip}-{event.username.lower()}-{cur_time.strftime('%Y%m%d%H%M%S')}"
            if alert_id in self.generated_alert_ids:
                return None
            self.generated_alert_ids.add(alert_id)

            # Reset history after flagging
            self.ip_user_failure_history[key] = 0

            return SecurityAlert(
                alert_id=alert_id,
                timestamp=cur_time,
                rule_id="RULE-005",
                rule_name="Critical Account Compromise Post-Brute-Force",
                severity=AlertSeverity.CRITICAL,
                source_ip=event.source_ip,
                target_usernames=[event.username],
                event_count=prior_fails + 1,
                window_seconds=self.config.compromise_lookback_window_sec,
                summary=f"SUCCESSFUL login for '{event.username}' from IP {event.source_ip} immediately following {prior_fails} consecutive failures!",
                mitigation_recommendation="REVOKE ACTIVE TOKEN IMMEDIATELY! Terminate user session, quarantine host, initiate credential reset."
            )
        return None


# ==============================================================================
# 6. SYNTHETIC LOG BENCHMARK GENERATOR
# ==============================================================================

class SyntheticLogGenerator:
    """Generates realistic authentication logs containing benign and attack vectors."""

    @classmethod
    def generate_benchmark_log(cls, output_path: str) -> None:
        """Writes a comprehensive test auth log with four distinct threat scenarios."""
        now = datetime.now() - timedelta(minutes=10)
        logs = []

        def log_line(dt: datetime, msg: str) -> str:
            return f"{dt.strftime('%b %d %H:%M:%S')} internal-gateway sshd[{1000 + dt.second}]: {msg}"

        # 1. Normal benign authentications
        logs.append(log_line(now, "Accepted publickey for admin from 10.0.0.15 port 49210 ssh2"))
        now += timedelta(seconds=2)
        logs.append(log_line(now, "Accepted password for jdoe from 192.168.1.50 port 51234 ssh2"))
        now += timedelta(seconds=1)

        # 2. Targeted Brute-Force: 198.51.100.23 -> root (8 failures)
        attacker_ip_1 = "198.51.100.23"
        for i in range(8):
            now += timedelta(seconds=1)
            logs.append(log_line(now, f"Failed password for root from {attacker_ip_1} port {40000 + i} ssh2"))

        # 3. Horizontal Password Spraying: 203.0.113.77 -> 6 distinct users
        now += timedelta(seconds=5)
        attacker_ip_2 = "203.0.113.77"
        spray_targets = ["alice", "bob", "carol", "dave", "finance", "backup"]
        for user in spray_targets:
            now += timedelta(seconds=2)
            logs.append(log_line(now, f"Failed password for {user} from {attacker_ip_2} port 55100 ssh2"))

        # 4. Distributed Credential Stuffing: 5 disparate IPs -> executive account
        now += timedelta(seconds=10)
        target_exec = "cfo_exec"
        stuffing_ips = [
            "192.0.2.11", "192.0.2.12", "192.0.2.13", "192.0.2.14", "192.0.2.15"
        ]
        for ip in stuffing_ips:
            now += timedelta(seconds=1)
            logs.append(log_line(now, f"Failed password for invalid user {target_exec} from {ip} port 38290 ssh2"))

        # 5. Targeted Brute Force Leading to COMPROMISE: 198.51.100.99 -> sarah_dev
        now += timedelta(seconds=5)
        attacker_ip_3 = "198.51.100.99"
        for i in range(5):
            now += timedelta(seconds=1)
            logs.append(log_line(now, f"Failed password for sarah_dev from {attacker_ip_3} port {45000 + i} ssh2"))

        # Attacker guesses the password correctly!
        now += timedelta(seconds=2)
        logs.append(log_line(now, f"Accepted password for sarah_dev from {attacker_ip_3} port 45010 ssh2"))

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(logs) + "\n")


# ==============================================================================
# 7. TELEMETRY, DASHBOARD & REPORT EXPORTERS
# ==============================================================================

class Reporter:
    """Renders SOC forensic dashboards and outputs CSV and JSON dossiers."""

    @staticmethod
    def print_alert(alert: SecurityAlert) -> None:
        """Displays real-time high-visibility alert cards to stdout."""
        sev_color = {
            AlertSeverity.INFO: ANSI.CYAN,
            AlertSeverity.LOW: ANSI.BLUE,
            AlertSeverity.MEDIUM: ANSI.YELLOW,
            AlertSeverity.HIGH: ANSI.RED,
            AlertSeverity.CRITICAL: ANSI.BG_RED + ANSI.WHITE
        }.get(alert.severity, ANSI.WHITE)

        print(f"\n{sev_color}{ANSI.BOLD} [!] SECURITY ALERT: {alert.rule_name} [{alert.severity.value}] {ANSI.RESET}")
        print(f" Timestamp    : {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" Source IP    : {ANSI.YELLOW}{alert.source_ip}{ANSI.RESET}")
        print(f" Targets      : {ANSI.CYAN}{', '.join(alert.target_usernames)}{ANSI.RESET}")
        print(f" Event Count  : {alert.event_count} failures in {alert.window_seconds}s window")
        print(f" Details      : {alert.summary}")
        print(f" Mitigation   : {ANSI.GREEN}{alert.mitigation_recommendation}{ANSI.RESET}")
        print(f"{ANSI.DIM}{'-' * 80}{ANSI.RESET}")

    @staticmethod
    def print_summary_dashboard(metrics: Dict[str, Any], alerts: List[SecurityAlert]) -> None:
        """Prints a comprehensive tabular security analytics summary."""
        print(
            f"\n{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.WHITE}              BRUTE-FORCE DETECTION & LOG TELEMETRY AUDIT                      {ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f" Total Log Events Analyzed : {ANSI.BOLD}{metrics['total_logs']:<10}{ANSI.RESET} | Failed Logins Logged  : {ANSI.RED}{metrics['total_failures']}{ANSI.RESET}")
        print(
            f" Successful Authentications : {ANSI.GREEN}{metrics['total_success']:<10}{ANSI.RESET} | Security Alerts Raised : {ANSI.BOLD}{ANSI.YELLOW}{len(alerts)}{ANSI.RESET}")
        print(f"--------------------------------------------------------------------------------")

        # Severity breakdown
        counts = Counter(a.severity.value for a in alerts)
        print(f" Alert Severity Breakdown:")
        print(
            f"  • CRITICAL: {ANSI.RED}{counts.get('CRITICAL', 0)}{ANSI.RESET}  | HIGH: {ANSI.MAGENTA}{counts.get('HIGH', 0)}{ANSI.RESET}  | MEDIUM: {ANSI.YELLOW}{counts.get('MEDIUM', 0)}{ANSI.RESET}  | LOW: {counts.get('LOW', 0)}")
        print(f"--------------------------------------------------------------------------------")

        # Top Attackers Table
        print(f" {ANSI.BOLD}{'Top Offending IPs':<25} | {'Failure Count':<15}{ANSI.RESET}")
        print(f" ----------------------------------------------------")
        for ip, cnt in metrics["top_malicious_ips"]:
            print(f" {ip:<25} | {cnt:<15}")

        print(f"\n {ANSI.BOLD}{'Top Targeted Accounts':<25} | {'Attempt Count':<15}{ANSI.RESET}")
        print(f" ----------------------------------------------------")
        for user, cnt in metrics["top_targeted_users"]:
            print(f" {user:<25} | {cnt:<15}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}\n")

    @staticmethod
    def export_csv(alerts: List[SecurityAlert], file_path: str) -> None:
        """Exports all security alerts to standard CSV."""
        if not alerts:
            return
        keys = ["alert_id", "timestamp", "rule_id", "rule_name", "severity", "source_ip", "target_usernames",
                "event_count", "window_seconds", "summary", "mitigation_recommendation"]
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for a in alerts:
                writer.writerow([
                    a.alert_id,
                    a.timestamp.isoformat(),
                    a.rule_id,
                    a.rule_name,
                    a.severity.value,
                    a.source_ip,
                    ";".join(a.target_usernames),
                    a.event_count,
                    a.window_seconds,
                    a.summary,
                    a.mitigation_recommendation
                ])
        print(f"{ANSI.GREEN}[✓] CSV security report generated: {file_path}{ANSI.RESET}")

    @staticmethod
    def export_json(alerts: List[SecurityAlert], file_path: str) -> None:
        """Exports all security incidents to structured JSON format."""
        data = []
        for a in alerts:
            d = asdict(a)
            d["timestamp"] = a.timestamp.isoformat()
            d["severity"] = a.severity.value
            data.append(d)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"{ANSI.GREEN}[✓] JSON security incident dossier exported: {file_path}{ANSI.RESET}")


# ==============================================================================
# 8. ORCHESTRATION PIPELINE
# ==============================================================================

class SecurityPipeline:
    """Orchestrates parsing, correlation, persistence, and report generation."""

    def __init__(self, config: DetectionConfig, db_path: str = ":memory:"):
        self.config = config
        self.db = DatabaseManager(db_path)
        self.detector = BruteForceDetector(config)

    def analyze_stream(self, lines: Iterator[str], verbose: bool = True) -> List[SecurityAlert]:
        """Parses a line-by-line stream of raw logs and evaluates correlation rules."""
        parsed_events: List[LogEvent] = []
        triggered_alerts: List[SecurityAlert] = []

        for line in lines:
            event = LogParser.parse_line(line)
            if event:
                parsed_events.append(event)
                alerts = self.detector.process_event(event)
                for alert in alerts:
                    triggered_alerts.append(alert)
                    if verbose:
                        Reporter.print_alert(alert)

        # Batch persist to SQLite
        self.db.insert_events(parsed_events)
        self.db.insert_alerts(triggered_alerts)

        return triggered_alerts

    def analyze_file(self, file_path: str, verbose: bool = True) -> List[SecurityAlert]:
        """Analyzes an entire log file located on disk."""
        if not os.path.exists(file_path):
            print(f"{ANSI.RED}[!] File not found: {file_path}{ANSI.RESET}")
            return []

        print(f"{ANSI.CYAN}[*] Processing Authentication Log: {file_path}{ANSI.RESET}")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return self.analyze_stream(f, verbose=verbose)


# ==============================================================================
# 9. CLI ENTRYPOINT & DEMO MODE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Enterprise Brute-Force & Password Spraying Detection Suite"
    )
    parser.add_argument("logfile", nargs="?", help="Path to raw authentication log file (/var/log/auth.log)")
    parser.add_argument("--demo", action="store_true",
                        help="Generate synthetic test logs and run live interactive demo")
    parser.add_argument("--db", default=":memory:", help="Path to SQLite database (default: in-memory)")
    parser.add_argument("--export-csv", help="Destination path for CSV report")
    parser.add_argument("--export-json", help="Destination path for JSON dossier")
    parser.add_argument("--quiet", action="store_true", help="Suppress real-time alert output")

    args = parser.parse_args()
    config = DetectionConfig()
    pipeline = SecurityPipeline(config, db_path=args.db)

    # 1. Self-Contained Demo Mode
    if args.demo or not args.logfile:
        demo_log_file = "synthetic_auth.log"
        print(f"{ANSI.BOLD}{ANSI.YELLOW}[*] No input log specified or --demo enabled.{ANSI.RESET}")
        print(f"{ANSI.BOLD}[*] Generating realistic forensic benchmark logs -> '{demo_log_file}'...{ANSI.RESET}")
        SyntheticLogGenerator.generate_benchmark_log(demo_log_file)

        alerts = pipeline.analyze_file(demo_log_file, verbose=not args.quiet)
        metrics = pipeline.db.fetch_telemetry_metrics()
        Reporter.print_summary_dashboard(metrics, alerts)

        # Default demo exports
        csv_dest = args.export_csv or "security_alerts.csv"
        json_dest = args.export_json or "security_alerts.json"
        Reporter.export_csv(alerts, csv_dest)
        Reporter.export_json(alerts, json_dest)

        # Cleanup synthetic log if run in automatic demo mode
        if not args.logfile and os.path.exists(demo_log_file):
            os.remove(demo_log_file)
        return

    # 2. Targeted Production Log Analysis
    alerts = pipeline.analyze_file(args.logfile, verbose=not args.quiet)
    metrics = pipeline.db.fetch_telemetry_metrics()
    Reporter.print_summary_dashboard(metrics, alerts)

    if args.export_csv:
        Reporter.export_csv(alerts, args.export_csv)
    if args.export_json:
        Reporter.export_json(alerts, args.export_json)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Analysis interrupted by operator.{ANSI.RESET}")
        sys.exit(0)
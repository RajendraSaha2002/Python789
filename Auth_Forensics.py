import os
import sys
import re
import csv
import json
import time
import sqlite3
import datetime
import math
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Iterator


# ==============================================================================
# 1. CONSTANTS, ENUMS & TERMINAL PALETTE
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
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class EventType(Enum):
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    INVALID_USER = "INVALID_USER"
    SESSION_OPEN = "SESSION_OPEN"
    SESSION_CLOSE = "SESSION_CLOSE"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    UNKNOWN = "UNKNOWN"


class SequenceClassification(Enum):
    TARGETED_BRUTE_FORCE = "TARGETED_BRUTE_FORCE"
    HORIZONTAL_SPRAY = "HORIZONTAL_SPRAY"
    DISTRIBUTED_STUFFING = "DISTRIBUTED_STUFFING"
    POST_FAILURE_BREACH = "POST_FAILURE_BREACH"
    BENIGN_TRAFFIC = "BENIGN_TRAFFIC"


# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

@dataclass
class NormalizedEvent:
    """Normalized atomic authentication log event."""
    timestamp: datetime.datetime
    source_ip: str
    username: str
    event_type: EventType
    service: str
    port: int = 0
    raw_message: str = ""
    session_id: Optional[str] = None


@dataclass
class ReconstructedSequence:
    """A reconstructed contiguous sequence of related authentication attempts."""
    sequence_id: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    source_ip: str
    target_users: List[str]
    total_attempts: int
    failure_count: int
    success_count: int
    classification: SequenceClassification
    duration_seconds: float
    culminated_in_breach: bool = False


# ==============================================================================
# 3. RELATIONAL FORENSIC STORAGE (SQLite3)
# ==============================================================================

class ForensicDatabase:
    """Manages indexed relational storage for raw events, profiles, and sequences."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript("""
                                    CREATE TABLE IF NOT EXISTS forensic_events
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
                                        event_type
                                        TEXT
                                        NOT
                                        NULL,
                                        service
                                        TEXT
                                        NOT
                                        NULL,
                                        port
                                        INTEGER
                                        DEFAULT
                                        0,
                                        raw_message
                                        TEXT,
                                        session_id
                                        TEXT
                                    );

                                    CREATE TABLE IF NOT EXISTS reconstructed_sequences
                                    (
                                        sequence_id
                                        TEXT
                                        PRIMARY
                                        KEY,
                                        start_time
                                        TEXT
                                        NOT
                                        NULL,
                                        end_time
                                        TEXT
                                        NOT
                                        NULL,
                                        source_ip
                                        TEXT
                                        NOT
                                        NULL,
                                        target_users
                                        TEXT
                                        NOT
                                        NULL,
                                        total_attempts
                                        INTEGER
                                        NOT
                                        NULL,
                                        failure_count
                                        INTEGER
                                        NOT
                                        NULL,
                                        success_count
                                        INTEGER
                                        NOT
                                        NULL,
                                        classification
                                        TEXT
                                        NOT
                                        NULL,
                                        duration_seconds
                                        REAL
                                        NOT
                                        NULL,
                                        culminated_in_breach
                                        INTEGER
                                        DEFAULT
                                        0
                                    );

                                    CREATE INDEX IF NOT EXISTS idx_events_ts ON forensic_events(timestamp);
                                    CREATE INDEX IF NOT EXISTS idx_events_ip ON forensic_events(source_ip);
                                    CREATE INDEX IF NOT EXISTS idx_events_user ON forensic_events(username);
                                    CREATE INDEX IF NOT EXISTS idx_events_type ON forensic_events(event_type);
                                    """)

    def insert_events(self, events: List[NormalizedEvent]) -> None:
        with self.conn:
            self.conn.executemany("""
                                  INSERT INTO forensic_events (timestamp, source_ip, username, event_type, service,
                                                               port, raw_message, session_id)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                                  """, [
                                      (
                                          e.timestamp.isoformat(),
                                          e.source_ip,
                                          e.username,
                                          e.event_type.value,
                                          e.service,
                                          e.port,
                                          e.raw_message,
                                          e.session_id
                                      ) for e in events
                                  ])

    def insert_sequences(self, sequences: List[ReconstructedSequence]) -> None:
        with self.conn:
            self.conn.executemany("""
                INSERT OR REPLACE INTO reconstructed_sequences (
                    sequence_id, start_time, end_time, source_ip, target_users,
                    total_attempts, failure_count, success_count, classification,
                    duration_seconds, culminated_in_breach
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    s.sequence_id,
                    s.start_time.isoformat(),
                    s.end_time.isoformat(),
                    s.source_ip,
                    json.dumps(s.target_users),
                    s.total_attempts,
                    s.failure_count,
                    s.success_count,
                    s.classification.value,
                    s.duration_seconds,
                    1 if s.culminated_in_breach else 0
                ) for s in sequences
            ])

    def query_events(
            self,
            username: Optional[str] = None,
            source_ip: Optional[str] = None,
            event_type: Optional[str] = None,
            since: Optional[datetime.datetime] = None,
            limit: int = 100
    ) -> List[sqlite3.Row]:
        """Parameterized search across forensic events."""
        clauses = []
        params = []

        if username:
            clauses.append("username LIKE ?")
            params.append(f"%{username}%")
        if source_ip:
            clauses.append("source_ip LIKE ?")
            params.append(f"%{source_ip}%")
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM forensic_events {where_sql} ORDER BY timestamp ASC LIMIT {limit};"
        return self.conn.execute(sql, params).fetchall()

    def get_account_summaries(self) -> List[Dict[str, Any]]:
        """Calculates account-level forensic risk metrics."""
        with self.conn:
            cursor = self.conn.execute("""
                                       SELECT username,
                                              MIN(timestamp)                                                                  as first_seen,
                                              MAX(timestamp)                                                                  as last_seen,
                                              COUNT(*)                                                                        as total_attempts,
                                              SUM(CASE WHEN event_type IN ('AUTH_FAILURE', 'INVALID_USER') THEN 1 ELSE 0 END) as failure_count,
                                              SUM(CASE WHEN event_type = 'AUTH_SUCCESS' THEN 1 ELSE 0 END)                    as success_count,
                                              COUNT(DISTINCT source_ip)                                                       as distinct_ips
                                       FROM forensic_events
                                       WHERE username != 'unknown'
                                       GROUP BY username
                                       ORDER BY failure_count DESC;
                                       """)
            return [dict(row) for row in cursor.fetchall()]

    def get_source_ip_summaries(self) -> List[Dict[str, Any]]:
        """Calculates origin IP forensic profiles."""
        with self.conn:
            cursor = self.conn.execute("""
                                       SELECT source_ip,
                                              MIN(timestamp)                                                                  as first_seen,
                                              MAX(timestamp)                                                                  as last_seen,
                                              COUNT(*)                                                                        as total_attempts,
                                              SUM(CASE WHEN event_type IN ('AUTH_FAILURE', 'INVALID_USER') THEN 1 ELSE 0 END) as failure_count,
                                              SUM(CASE WHEN event_type = 'AUTH_SUCCESS' THEN 1 ELSE 0 END)                    as success_count,
                                              COUNT(DISTINCT username)                                                        as distinct_users_targeted
                                       FROM forensic_events
                                       GROUP BY source_ip
                                       ORDER BY total_attempts DESC;
                                       """)
            return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# 4. MULTI-DIALECT LOG INGESTION & REGEX PARSERS
# ==============================================================================

class LogIngestionEngine:
    """Parses diverse authentication formats (OpenSSH syslog, JSON, and CSV)."""

    # 1. OpenSSH Failed password
    SSH_FAILED = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"sshd\[(?P<pid>\d+)\]:\s+Failed password for (invalid user )?(?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)",
        re.IGNORECASE
    )

    # 2. OpenSSH Accepted Login
    SSH_ACCEPTED = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"sshd\[(?P<pid>\d+)\]:\s+Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)",
        re.IGNORECASE
    )

    # 3. OpenSSH Session Open/Close
    SSH_SESSION = re.compile(
        r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+"
        r"systemd-logind\[\d+\]:\s+New session (?P<sess>\S+) of user (?P<user>\S+)",
        re.IGNORECASE
    )

    # 4. Fallback Generic IP & User
    GENERIC_IP = re.compile(r"\b(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\b")
    GENERIC_USER = re.compile(r"\b(?:user|account|login)[:=\s]+(?P<user>[A-Za-z0-9_\.\-]+)", re.IGNORECASE)

    MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

    @classmethod
    def _parse_syslog_timestamp(cls, month_str: str, day_str: str, time_str: str) -> datetime.datetime:
        now = datetime.datetime.now()
        month = cls.MONTHS.get(month_str, now.month)
        day = int(day_str)
        t_parts = [int(p) for p in time_str.split(":")]

        dt = datetime.datetime(now.year, month, day, t_parts[0], t_parts[1], t_parts[2])
        if dt > now + datetime.timedelta(days=1):
            dt = datetime.datetime(now.year - 1, month, day, t_parts[0], t_parts[1], t_parts[2])
        return dt

    @classmethod
    def parse_line(cls, line: str) -> Optional[NormalizedEvent]:
        line = line.strip()
        if not line:
            return None

        # Strategy A: JSON Ingestion
        if line.startswith("{") and line.endswith("}"):
            try:
                d = json.loads(line)
                ts = datetime.datetime.fromisoformat(d.get("timestamp", datetime.datetime.now().isoformat()))
                status_raw = d.get("status", "FAILURE").upper()
                event_type = EventType.AUTH_SUCCESS if "SUCCESS" in status_raw else EventType.AUTH_FAILURE
                return NormalizedEvent(
                    timestamp=ts,
                    source_ip=d.get("source_ip", d.get("ip", "127.0.0.1")),
                    username=d.get("username", d.get("user", "unknown")),
                    event_type=event_type,
                    service=d.get("service", "api-gateway"),
                    port=int(d.get("port", 0)),
                    raw_message=line,
                    session_id=d.get("session_id")
                )
            except Exception:
                pass

        # Strategy B: OpenSSH Failed Password
        m_failed = cls.SSH_FAILED.search(line)
        if m_failed:
            ts = cls._parse_syslog_timestamp(m_failed.group("month"), m_failed.group("day"), m_failed.group("time"))
            is_invalid = "invalid user" in line.lower()
            return NormalizedEvent(
                timestamp=ts,
                source_ip=m_failed.group("ip"),
                username=m_failed.group("user"),
                event_type=EventType.INVALID_USER if is_invalid else EventType.AUTH_FAILURE,
                service="sshd",
                port=int(m_failed.group("port")),
                raw_message=line
            )

        # Strategy C: OpenSSH Accepted
        m_ok = cls.SSH_ACCEPTED.search(line)
        if m_ok:
            ts = cls._parse_syslog_timestamp(m_ok.group("month"), m_ok.group("day"), m_ok.group("time"))
            return NormalizedEvent(
                timestamp=ts,
                source_ip=m_ok.group("ip"),
                username=m_ok.group("user"),
                event_type=EventType.AUTH_SUCCESS,
                service="sshd",
                port=int(m_ok.group("port")),
                raw_message=line
            )

        # Strategy D: OpenSSH Session Hook
        m_sess = cls.SSH_SESSION.search(line)
        if m_sess:
            ts = cls._parse_syslog_timestamp(m_sess.group("month"), m_sess.group("day"), m_sess.group("time"))
            return NormalizedEvent(
                timestamp=ts,
                source_ip="127.0.0.1",
                username=m_sess.group("user"),
                event_type=EventType.SESSION_OPEN,
                service="systemd-logind",
                port=0,
                raw_message=line,
                session_id=m_sess.group("sess")
            )

        # Strategy E: Generic Heuristic Fallback
        m_ip = cls.GENERIC_IP.search(line)
        m_user = cls.GENERIC_USER.search(line)
        if m_ip:
            ip = m_ip.group("ip")
            user = m_user.group("user") if m_user else "unknown"
            lower_line = line.lower()
            event_type = EventType.AUTH_SUCCESS if "accepted" in lower_line or "success" in lower_line else EventType.AUTH_FAILURE
            return NormalizedEvent(
                timestamp=datetime.datetime.now(),
                source_ip=ip,
                username=user,
                event_type=event_type,
                service="generic-auth",
                port=0,
                raw_message=line
            )

        return None

    @classmethod
    def ingest_file(cls, filepath: str) -> List[NormalizedEvent]:
        events = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                ev = cls.parse_line(line)
                if ev:
                    events.append(ev)
        return events


# ==============================================================================
# 5. FORENSIC CORRELATION & SEQUENCE RECONSTRUCTION ENGINE
# ==============================================================================

class TimelineCorrelator:
    """Reconstructs contiguous attack sequences and temporal bursts from raw events."""

    def __init__(self, max_idle_gap_seconds: int = 180):
        self.max_idle_gap = max_idle_gap_seconds

    def reconstruct_sequences(self, events: List[NormalizedEvent]) -> List[ReconstructedSequence]:
        """Groups chronological events per origin IP into discrete attack campaigns."""
        if not events:
            return []

        # Sort strictly ascending by timestamp
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        # Partition events by Source IP
        ip_clusters: Dict[str, List[NormalizedEvent]] = defaultdict(list)
        for ev in sorted_events:
            ip_clusters[ev.source_ip].append(ev)

        sequences: List[ReconstructedSequence] = []
        seq_counter = 1

        for ip, cluster in ip_clusters.items():
            current_batch: List[NormalizedEvent] = []

            for ev in cluster:
                if not current_batch:
                    current_batch.append(ev)
                    continue

                prev_ev = current_batch[-1]
                gap = (ev.timestamp - prev_ev.timestamp).total_seconds()

                if gap <= self.max_idle_gap:
                    current_batch.append(ev)
                else:
                    # Inactivity threshold breached; finalize sequence
                    if len(current_batch) >= 2 or current_batch[0].event_type == EventType.AUTH_FAILURE:
                        seq = self._compile_sequence(f"SEQ-{seq_counter:04d}", ip, current_batch)
                        sequences.append(seq)
                        seq_counter += 1
                    current_batch = [ev]

            if current_batch:
                seq = self._compile_sequence(f"SEQ-{seq_counter:04d}", ip, current_batch)
                sequences.append(seq)
                seq_counter += 1

        return sorted(sequences, key=lambda s: s.start_time)

    def _compile_sequence(self, seq_id: str, ip: str, batch: List[NormalizedEvent]) -> ReconstructedSequence:
        start_t = batch[0].timestamp
        end_t = batch[-1].timestamp
        duration = max(1.0, (end_t - start_t).total_seconds())

        fails = sum(1 for e in batch if e.event_type in (EventType.AUTH_FAILURE, EventType.INVALID_USER))
        successes = sum(1 for e in batch if e.event_type == EventType.AUTH_SUCCESS)
        users = sorted(list({e.username for e in batch if e.username != "unknown"}))

        # Check for Post-Failure Breach Pattern
        # (Consecutive failures ending directly in a success from the same sequence)
        culminated_in_breach = False
        if fails >= 3 and batch[-1].event_type == EventType.AUTH_SUCCESS:
            culminated_in_breach = True

        # Classification Logic
        classification = SequenceClassification.BENIGN_TRAFFIC
        if culminated_in_breach:
            classification = SequenceClassification.POST_FAILURE_BREACH
        elif len(users) >= 4 and fails >= 4:
            classification = SequenceClassification.HORIZONTAL_SPRAY
        elif len(users) == 1 and fails >= 5:
            classification = SequenceClassification.TARGETED_BRUTE_FORCE
        elif fails >= 8:
            classification = SequenceClassification.DISTRIBUTED_STUFFING

        return ReconstructedSequence(
            sequence_id=seq_id,
            start_time=start_t,
            end_time=end_t,
            source_ip=ip,
            target_users=users,
            total_attempts=len(batch),
            failure_count=fails,
            success_count=successes,
            classification=classification,
            duration_seconds=duration,
            culminated_in_breach=culminated_in_breach
        )


# ==============================================================================
# 6. SYNTHETIC MULTI-STAGE FORENSIC LOG GENERATOR
# ==============================================================================

class SyntheticForensicScenario:
    """Generates realistic authentication logs modeling an actual multi-stage intrusion."""

    @classmethod
    def generate_incident_log(cls, output_path: str) -> None:
        t0 = datetime.datetime.now() - datetime.timedelta(hours=2)
        lines = []

        def log_line(dt: datetime.datetime, daemon: str, msg: str) -> str:
            return f"{dt.strftime('%b %d %H:%M:%S')} internal-srv01 {daemon}[{1200 + dt.second}]: {msg}"

        # 1. Normal Baseline Traffic
        lines.append(log_line(t0, "sshd", "Accepted publickey for sysadmin from 10.10.1.10 port 41234 ssh2"))
        t0 += datetime.timedelta(minutes=5)
        lines.append(log_line(t0, "sshd", "Accepted password for dev_alex from 192.168.1.105 port 50220 ssh2"))
        t0 += datetime.timedelta(seconds=2)
        lines.append(log_line(t0, "systemd-logind", "New session c1 of user dev_alex"))

        # 2. Attack Vector 1: Targeted Brute-Force against 'service_api' from 198.51.100.44
        t_bf = t0 + datetime.timedelta(minutes=10)
        attacker_1 = "198.51.100.44"
        for i in range(12):
            t_bf += datetime.timedelta(seconds=2)
            lines.append(
                log_line(t_bf, "sshd", f"Failed password for service_api from {attacker_1} port {38000 + i} ssh2"))

        # 3. Attack Vector 2: Horizontal Password Spraying from 203.0.113.88
        t_spray = t_bf + datetime.timedelta(minutes=20)
        attacker_2 = "203.0.113.88"
        users = ["alice", "bob", "carol", "david", "elena", "frank", "hr_manager"]
        for u in users:
            t_spray += datetime.timedelta(seconds=3)
            lines.append(log_line(t_spray, "sshd", f"Failed password for {u} from {attacker_2} port 49012 ssh2"))

        # 4. Attack Vector 3: High-Priority Breach (Targeted failures culminating in compromise)
        t_breach = t_spray + datetime.timedelta(minutes=30)
        attacker_3 = "192.0.2.77"
        victim = "jdoe"
        # 6 failed password attempts
        for i in range(6):
            t_breach += datetime.timedelta(seconds=2)
            lines.append(
                log_line(t_breach, "sshd", f"Failed password for {victim} from {attacker_3} port {52000 + i} ssh2"))

        # 7th attempt succeeds!
        t_breach += datetime.timedelta(seconds=3)
        lines.append(log_line(t_breach, "sshd", f"Accepted password for {victim} from {attacker_3} port 52007 ssh2"))
        lines.append(log_line(t_breach, "systemd-logind", f"New session c2 of user {victim}"))

        # 5. Subsequent Off-Hours Lateral Movement
        t_lateral = t_breach + datetime.timedelta(minutes=15)
        lines.append(log_line(t_lateral, "sshd", f"Accepted publickey for root from 192.0.2.77 port 52099 ssh2"))
        lines.append(log_line(t_lateral, "systemd-logind", "New session c3 of user root"))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ==============================================================================
# 7. FORENSIC DOSSIER COMPILER & EXPORTERS
# ==============================================================================

class ForensicReporter:
    """Outputs forensic timelines to console, CSV, and formal Markdown reports."""

    @staticmethod
    def print_timeline(events: List[sqlite3.Row], limit: int = 50) -> None:
        print(
            f"\n{ANSI.BOLD}{ANSI.CYAN}--- [ RECONSTRUCTED FORENSIC TIMELINE (Displaying {min(len(events), limit)} events) ] ---{ANSI.RESET}\n")
        print(
            f"{ANSI.BOLD}{'Timestamp':<24} | {'Status':<16} | {'Source IP':<16} | {'Target User':<16} | {'Details'}{ANSI.RESET}")
        print("-" * 105)

        for row in events[:limit]:
            ev_type = row["event_type"]
            color = ANSI.GREEN if ev_type == "AUTH_SUCCESS" else (
                ANSI.RED if "FAIL" in ev_type or "INVALID" in ev_type else ANSI.WHITE)
            user = row["username"]
            ip = row["source_ip"]
            ts = row["timestamp"]
            msg = row["raw_message"][:45] + "..." if len(row["raw_message"]) > 45 else row["raw_message"]

            print(
                f"{ts:<24} | {color}{ev_type:<16}{ANSI.RESET} | {ANSI.YELLOW}{ip:<16}{ANSI.RESET} | {ANSI.CYAN}{user:<16}{ANSI.RESET} | {msg}")

    @staticmethod
    def print_sequences(sequences: List[ReconstructedSequence]) -> None:
        print(f"\n{ANSI.BOLD}{ANSI.MAGENTA}--- [ RECONSTRUCTED ADVERSARIAL ATTACK SEQUENCES ] ---{ANSI.RESET}\n")
        print(
            f"{ANSI.BOLD}{'Seq ID':<10} | {'Classification':<24} | {'Source IP':<16} | {'Fail/Succ':<10} | {'Duration':<9} | {'Target Users'}{ANSI.RESET}")
        print("-" * 105)

        for s in sequences:
            class_str = s.classification.value
            color = ANSI.RED if s.culminated_in_breach or s.classification != SequenceClassification.BENIGN_TRAFFIC else ANSI.GREEN
            if s.culminated_in_breach:
                class_str = f"{ANSI.BG_RED}{ANSI.WHITE}BREACH COMPROMISE{ANSI.RESET}"

            t_users = ", ".join(s.target_users[:3])
            if len(s.target_users) > 3:
                t_users += f" (+{len(s.target_users) - 3} more)"

            rate = f"{s.failure_count}/{s.success_count}"
            dur = f"{s.duration_seconds:.1f}s"

            print(
                f"{s.sequence_id:<10} | {color}{class_str:<24}{ANSI.RESET} | {ANSI.YELLOW}{s.source_ip:<16}{ANSI.RESET} | {rate:<10} | {dur:<9} | {t_users}")

    @staticmethod
    def export_timeline_csv(events: List[sqlite3.Row], output_path: str) -> None:
        """Exports raw chronological forensic events to standard CSV."""
        if not events:
            return
        keys = events[0].keys()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for row in events:
                writer.writerow(list(row))
        print(f"{ANSI.GREEN}[✓] Forensic timeline CSV exported: {output_path}{ANSI.RESET}")

    @staticmethod
    def export_markdown_dossier(
            db: ForensicDatabase,
            sequences: List[ReconstructedSequence],
            output_path: str
    ) -> None:
        """Compiles a formal DFIR incident investigation report in Markdown format."""
        acct_sums = db.get_account_summaries()
        ip_sums = db.get_source_ip_summaries()

        md = [
            "# DIGITAL FORENSICS INCIDENT INVESTIGATION REPORT",
            f"**Generated On:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "**Case Reference:** AUTH-IR-2024-991A",
            "**Evidence Source:** Ingested Local Authentication Logs",
            "",
            "## 1. EXECUTIVE INCIDENT SUMMARY",
            "An automated forensic reconstruction of authentication telemetry was conducted.",
            f"A total of **{len(sequences)}** distinct activity sequences were reconstructed.",
            ""
        ]

        # Breaches
        breaches = [s for s in sequences if s.culminated_in_breach]
        if breaches:
            md.append("### ⚠️ CRITICAL COMPROMISE INDICATORS (IoCs)")
            for b in breaches:
                md.append(f"- **COMPROMISED ACCOUNT:** `{', '.join(b.target_users)}` by IP `{b.source_ip}`")
                md.append(f"  - **Incident Timeline:** `{b.start_time}` to `{b.end_time}`")
                md.append(
                    f"  - **Mechanism:** {b.failure_count} consecutive credential failures immediately followed by an authorized session establishment.")
            md.append("")

        # Reconstructed Campaigns
        md.append("## 2. RECONSTRUCTED ATTACK CAMPAIGNS")
        md.append("| Sequence ID | Classification | Source IP | Fails/Success | Duration | Target Accounts |")
        md.append("|---|---|---|---|---|---|")
        for s in sequences:
            md.append(
                f"| {s.sequence_id} | {s.classification.value} | {s.source_ip} | {s.failure_count}/{s.success_count} | {s.duration_seconds:.1f}s | {', '.join(s.target_users)} |")
        md.append("")

        # Account Profiles
        md.append("## 3. ACCOUNT-LEVEL IMPACT ASSESSMENT")
        md.append("| Username | Total Attempts | Failed | Successful | Distinct IPs | First Seen | Last Seen |")
        md.append("|---|---|---|---|---|---|---|")
        for a in acct_sums:
            md.append(
                f"| `{a['username']}` | {a['total_attempts']} | {a['failure_count']} | {a['success_count']} | {a['distinct_ips']} | {a['first_seen']} | {a['last_seen']} |")
        md.append("")

        # IP Profiles
        md.append("## 4. THREAT ACTOR IP REPUTATION PROFILES")
        md.append("| Source IP | Total Attempts | Failed | Distinct Users Targeted | First Seen | Last Seen |")
        md.append("|---|---|---|---|---|---|")
        for ip in ip_sums:
            md.append(
                f"| `{ip['source_ip']}` | {ip['total_attempts']} | {ip['failure_count']} | {ip['distinct_users_targeted']} | {ip['first_seen']} | {ip['last_seen']} |")
        md.append("")

        md.append("## 5. FORENSIC REMEDIATION RECOMMENDATIONS")
        md.append(
            "1. **Isolate Compromised Accounts:** Revoke active tokens, purge Kerberos tickets, and force password resets for accounts identified in Section 1.")
        md.append("2. **Perimeter Null-Routing:** Ban attacker IPs identified in Section 4 across edge firewalls.")
        md.append(
            "3. **Multi-Factor Authentication (MFA):** Enforce FIDO2 / TOTP to neutralize credential-guessing vectors.")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
        print(f"{ANSI.GREEN}[✓] Incident Dossier (Markdown) compiled successfully: {output_path}{ANSI.RESET}")


# ==============================================================================
# 8. INTERACTIVE FORENSIC QUERY SHELL
# ==============================================================================

class ForensicShell:
    """Command-line forensic workbench for ad-hoc queries and incident exploration."""

    def __init__(self, db: ForensicDatabase, sequences: List[ReconstructedSequence]):
        self.db = db
        self.sequences = sequences

    def run_cli_loop(self) -> None:
        print(
            f"\n{ANSI.BOLD}{ANSI.CYAN}================================================================================{ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.WHITE}              AUTHENTICATION LOG FORENSIC INVESTIGATION SHELL                   {ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.CYAN}================================================================================{ANSI.RESET}")
        print("Commands:")
        print("  timeline                     - Display chronological event sequence")
        print("  timeline --user <name>       - Filter timeline by account username")
        print("  timeline --ip <ip>           - Filter timeline by source IP")
        print("  timeline --status <status>   - Filter (AUTH_SUCCESS, AUTH_FAILURE, INVALID_USER)")
        print("  sequences                    - Display reconstructed attack bursts & campaigns")
        print("  accounts                     - View account-level impact & risk summaries")
        print("  actors                       - View attacker IP profile statistics")
        print("  export-csv <filename>        - Export all events to CSV file")
        print("  export-report <filename>     - Compile formal DFIR Markdown report")
        print("  exit / quit                  - Exit forensic workbench\n")

        while True:
            try:
                cmd_line = input(f"{ANSI.BOLD}dfir-forensics > {ANSI.RESET}").strip()
                if not cmd_line:
                    continue

                tokens = cmd_line.split()
                primary = tokens[0].lower()

                if primary in ("exit", "quit", "q"):
                    print(f"{ANSI.GREEN}[✓] Forensic analysis session terminated.{ANSI.RESET}")
                    break

                elif primary == "timeline":
                    u = None
                    ip = None
                    st = None
                    i = 1
                    while i < len(tokens):
                        if tokens[i] == "--user" and i + 1 < len(tokens):
                            u = tokens[i + 1]
                            i += 2
                        elif tokens[i] == "--ip" and i + 1 < len(tokens):
                            ip = tokens[i + 1]
                            i += 2
                        elif tokens[i] == "--status" and i + 1 < len(tokens):
                            st = tokens[i + 1].upper()
                            i += 2
                        else:
                            i += 1

                    events = self.db.query_events(username=u, source_ip=ip, event_type=st, limit=100)
                    ForensicReporter.print_timeline(events, limit=100)

                elif primary == "sequences":
                    ForensicReporter.print_sequences(self.sequences)

                elif primary == "accounts":
                    sums = self.db.get_account_summaries()
                    print(f"\n{ANSI.BOLD}{ANSI.CYAN}--- [ ACCOUNT-LEVEL FORENSIC SUMMARY ] ---{ANSI.RESET}\n")
                    print(
                        f"{ANSI.BOLD}{'Username':<18} | {'Total':<7} | {'Failed':<8} | {'Success':<8} | {'Distinct IPs':<14} | {'First Seen':<20} | {'Last Seen'}{ANSI.RESET}")
                    print("-" * 105)
                    for a in sums:
                        color = ANSI.RED if a["failure_count"] >= 5 else ANSI.WHITE
                        print(
                            f"{color}{a['username']:<18}{ANSI.RESET} | {a['total_attempts']:<7} | {a['failure_count']:<8} | {a['success_count']:<8} | {a['distinct_ips']:<14} | {a['first_seen'][:19]:<20} | {a['last_seen'][:19]}")

                elif primary == "actors":
                    sums = self.db.get_source_ip_summaries()
                    print(f"\n{ANSI.BOLD}{ANSI.YELLOW}--- [ SOURCE IP REPUTATION & THREAT ACTORS ] ---{ANSI.RESET}\n")
                    print(
                        f"{ANSI.BOLD}{'Source IP':<18} | {'Attempts':<9} | {'Failures':<9} | {'Targeted Users':<16} | {'First Seen':<20} | {'Last Seen'}{ANSI.RESET}")
                    print("-" * 105)
                    for s in sums:
                        color = ANSI.RED if s["failure_count"] >= 5 else ANSI.WHITE
                        print(
                            f"{color}{s['source_ip']:<18}{ANSI.RESET} | {s['total_attempts']:<9} | {s['failure_count']:<9} | {s['distinct_users_targeted']:<16} | {s['first_seen'][:19]:<20} | {s['last_seen'][:19]}")

                elif primary == "export-csv":
                    path = tokens[1] if len(tokens) > 1 else "forensic_timeline.csv"
                    events = self.db.query_events(limit=100000)
                    ForensicReporter.export_timeline_csv(events, path)

                elif primary == "export-report":
                    path = tokens[1] if len(tokens) > 1 else "incident_investigation_dossier.md"
                    ForensicReporter.export_markdown_dossier(self.db, self.sequences, path)

                else:
                    print(
                        f"{ANSI.RED}[!] Unknown command: '{primary}'. Type 'timeline', 'sequences', 'accounts', or 'exit'.{ANSI.RESET}")

            except KeyboardInterrupt:
                print(f"\n{ANSI.YELLOW}[!] Session interrupted.{ANSI.RESET}")
                break


# ==============================================================================
# 9. PROGRAM ENTRYPOINT
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Enterprise Authentication Log Forensics & Timeline Reconstruction Suite"
    )
    parser.add_argument("logfile", nargs="?", help="Path to local authentication log file")
    parser.add_argument("--demo", action="store_true", help="Generate synthetic multi-stage intrusion log and run demo")
    parser.add_argument("--db", default=":memory:", help="SQLite database destination (default: in-memory)")
    parser.add_argument("--export-csv", help="Auto-export timeline to specified CSV file")
    parser.add_argument("--export-report", help="Auto-export formal Markdown dossier")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Run analysis and exit without entering interactive shell")

    args = parser.parse_args()
    db = ForensicDatabase(args.db)
    correlator = TimelineCorrelator(max_idle_gap_seconds=180)

    # 1. Demo Mode: Generate Synthetic Multi-Stage Incident
    if args.demo or not args.logfile:
        demo_log = "synthetic_incident_auth.log"
        print(f"{ANSI.YELLOW}[*] No input log specified or --demo flag active.{ANSI.RESET}")
        print(f"[*] Generating realistic forensic intrusion log: '{demo_log}'...")
        SyntheticForensicScenario.generate_incident_log(demo_log)

        events = LogIngestionEngine.ingest_file(demo_log)
        print(f"{ANSI.GREEN}[✓] Ingested and parsed {len(events)} events from synthetic log.{ANSI.RESET}")

        # Cleanup file if auto-generated
        if not args.logfile and os.path.exists(demo_log):
            os.remove(demo_log)
    else:
        # 2. Production Log Ingestion
        if not os.path.exists(args.logfile):
            print(f"{ANSI.RED}[!] Error: File '{args.logfile}' does not exist.{ANSI.RESET}")
            sys.exit(1)
        events = LogIngestionEngine.ingest_file(args.logfile)
        print(f"{ANSI.GREEN}[✓] Successfully parsed {len(events)} events from '{args.logfile}'.{ANSI.RESET}")

    # Store normalized events
    db.insert_events(events)

    # Reconstruct Attack Sequences
    sequences = correlator.reconstruct_sequences(events)
    db.insert_sequences(sequences)

    # Display Reconstructed Sequences Table
    ForensicReporter.print_sequences(sequences)

    # Handle automated CLI exports
    if args.export_csv:
        all_ev = db.query_events(limit=100000)
        ForensicReporter.export_timeline_csv(all_ev, args.export_csv)
    if args.export_report:
        ForensicReporter.export_markdown_dossier(db, sequences, args.export_report)

    # Launch Interactive Shell if not in quiet/non-interactive mode
    if not args.non_interactive:
        shell = ForensicShell(db, sequences)
        shell.run_cli_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Forensics analysis halted by operator.{ANSI.RESET}")
        sys.exit(0)
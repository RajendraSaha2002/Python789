import os
import sys
import time
import math
import random
import sqlite3
import datetime
import hashlib
import hmac
import json
import csv
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque, Counter
from typing import Dict, List, Tuple, Optional, Any, Set


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
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class ThreatSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DefenseAction(Enum):
    ALLOW = "ALLOW"
    INJECT_DELAY = "INJECT_DELAY"
    CHALLENGE_CAPTCHA = "CHALLENGE_CAPTCHA"
    BLOCK_IP = "BLOCK_IP"
    BAN_SUBNET = "BAN_SUBNET"


class AuthResult(Enum):
    SUCCESS = "SUCCESS"
    FAILED_BAD_PASSWORD = "FAILED_BAD_PASSWORD"
    FAILED_UNKNOWN_USER = "FAILED_UNKNOWN_USER"
    FAILED_CANARY_HIT = "FAILED_CANARY_HIT"
    BLOCKED_BY_DEFENSE = "BLOCKED_BY_DEFENSE"


# ==============================================================================
# 2. DATA MODELS & CONFIGURATION
# ==============================================================================

@dataclass
class DefensePolicy:
    """Configurable thresholds for risk scoring and automated response."""
    # Sliding time window intervals (seconds)
    ip_velocity_window_sec: int = 60
    subnet_velocity_window_sec: int = 120
    user_targeting_window_sec: int = 120

    # Thresholds
    max_requests_per_ip: int = 6
    max_users_per_subnet: int = 4
    max_ips_per_user: int = 3

    # Risk Score Action Gates (0-100)
    score_threshold_delay: int = 30
    score_threshold_captcha: int = 60
    score_threshold_block: int = 80

    # Durations (seconds)
    ip_ban_duration_sec: int = 300
    subnet_ban_duration_sec: int = 600


@dataclass
class RiskBreakdown:
    """Detailed vector breakdown of risk score calculations."""
    ip_velocity_score: float = 0.0
    subnet_cluster_score: float = 0.0
    user_targeting_score: float = 0.0
    ua_anomaly_score: float = 0.0
    canary_penalty: float = 0.0
    total_score: float = 0.0


@dataclass
class SecurityIncident:
    """Structured security incident report."""
    incident_id: str
    timestamp: str
    severity: ThreatSeverity
    rule_name: str
    source_ip: str
    subnet: str
    target_account: str
    risk_score: float
    action_taken: DefenseAction
    details: str


# ==============================================================================
# 3. RELATIONAL FORENSIC STORAGE (SQLite3)
# ==============================================================================

class DatabaseManager:
    """Thread-safe SQLite database manager holding persistent users and event logs."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

    def _init_database(self) -> None:
        with self.conn:
            self.conn.executescript("""
                                    CREATE TABLE IF NOT EXISTS users
                                    (
                                        id
                                        INTEGER
                                        PRIMARY
                                        KEY
                                        AUTOINCREMENT,
                                        username
                                        TEXT
                                        UNIQUE
                                        NOT
                                        NULL,
                                        password_hash
                                        TEXT
                                        NOT
                                        NULL,
                                        salt
                                        TEXT
                                        NOT
                                        NULL,
                                        is_canary
                                        INTEGER
                                        DEFAULT
                                        0,
                                        created_at
                                        TIMESTAMP
                                        DEFAULT
                                        CURRENT_TIMESTAMP
                                    );

                                    CREATE TABLE IF NOT EXISTS login_events
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
                                        subnet
                                        TEXT
                                        NOT
                                        NULL,
                                        username
                                        TEXT
                                        NOT
                                        NULL,
                                        user_agent
                                        TEXT
                                        NOT
                                        NULL,
                                        status
                                        TEXT
                                        NOT
                                        NULL,
                                        risk_score
                                        REAL
                                        NOT
                                        NULL,
                                        action_taken
                                        TEXT
                                        NOT
                                        NULL,
                                        details
                                        TEXT
                                    );

                                    CREATE TABLE IF NOT EXISTS perimeter_bans
                                    (
                                        target_identifier
                                        TEXT
                                        PRIMARY
                                        KEY,
                                        ban_type
                                        TEXT
                                        NOT
                                        NULL, -- 'IP' or 'SUBNET'
                                        banned_until
                                        TIMESTAMP
                                        NOT
                                        NULL,
                                        reason
                                        TEXT
                                        NOT
                                        NULL,
                                        strikes
                                        INTEGER
                                        DEFAULT
                                        1
                                    );

                                    CREATE INDEX IF NOT EXISTS idx_events_ts ON login_events(timestamp);
                                    CREATE INDEX IF NOT EXISTS idx_events_ip ON login_events(source_ip);
                                    CREATE INDEX IF NOT EXISTS idx_events_subnet ON login_events(subnet);
                                    CREATE INDEX IF NOT EXISTS idx_events_user ON login_events(username);
                                    """)

    def insert_user(self, username: str, password_hash: str, salt: str, is_canary: bool = False) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (username, password_hash, salt, is_canary) VALUES (?, ?, ?, ?);",
                (username.lower().strip(), password_hash, salt, 1 if is_canary else 0)
            )

    def log_event(self, event_data: Dict[str, Any]) -> None:
        with self.conn:
            self.conn.execute("""
                              INSERT INTO login_events (timestamp, source_ip, subnet, username, user_agent, status,
                                                        risk_score, action_taken, details)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                              """, (
                                  event_data["timestamp"],
                                  event_data["source_ip"],
                                  event_data["subnet"],
                                  event_data["username"],
                                  event_data["user_agent"],
                                  event_data["status"],
                                  event_data["risk_score"],
                                  event_data["action_taken"],
                                  event_data["details"]
                              ))

    def add_ban(self, identifier: str, ban_type: str, banned_until: datetime.datetime, reason: str) -> None:
        with self.conn:
            self.conn.execute("""
                              INSERT INTO perimeter_bans (target_identifier, ban_type, banned_until, reason, strikes)
                              VALUES (?, ?, ?, ?, 1) ON CONFLICT(target_identifier) DO
                              UPDATE SET
                                  banned_until = excluded.banned_until,
                                  reason = excluded.reason,
                                  strikes = strikes + 1;
                              """, (identifier, ban_type, banned_until.isoformat(), reason))

    def is_banned(self, ip: str, subnet: str, now: datetime.datetime) -> Tuple[bool, Optional[str], Optional[str]]:
        """Checks if either the discrete IP or its parent /24 subnet is banned."""
        with self.conn:
            row = self.conn.execute("""
                                    SELECT target_identifier, ban_type, banned_until, reason
                                    FROM perimeter_bans
                                    WHERE target_identifier IN (?, ?);
                                    """, (ip, subnet)).fetchone()

            if row:
                until = datetime.datetime.fromisoformat(row["banned_until"])
                if now < until:
                    return True, row["ban_type"], row["reason"]
                else:
                    # Expired ban cleanup
                    self.conn.execute("DELETE FROM perimeter_bans WHERE target_identifier = ?;",
                                      (row["target_identifier"],))
        return False, None, None

    def get_telemetry_aggregations(self) -> Dict[str, Any]:
        with self.conn:
            total_reqs = self.conn.execute("SELECT COUNT(*) FROM login_events;").fetchone()[0]
            if total_reqs == 0:
                return {}

            total_blocked = self.conn.execute(
                "SELECT COUNT(*) FROM login_events WHERE action_taken IN ('BLOCK_IP', 'BAN_SUBNET');"
            ).fetchone()[0]
            total_challenges = self.conn.execute(
                "SELECT COUNT(*) FROM login_events WHERE action_taken = 'CHALLENGE_CAPTCHA';"
            ).fetchone()[0]
            total_success = self.conn.execute(
                "SELECT COUNT(*) FROM login_events WHERE status = 'SUCCESS';"
            ).fetchone()[0]
            avg_risk = self.conn.execute("SELECT AVG(risk_score) FROM login_events;").fetchone()[0] or 0.0

            top_subnets = self.conn.execute("""
                                            SELECT subnet, COUNT(*) as cnt
                                            FROM login_events
                                            WHERE status != 'SUCCESS'
                                            GROUP BY subnet
                                            ORDER BY cnt DESC LIMIT 5;
                                            """).fetchall()

            top_targeted = self.conn.execute("""
                                             SELECT username, COUNT(*) as cnt
                                             FROM login_events
                                             WHERE status != 'SUCCESS'
                                             GROUP BY username
                                             ORDER BY cnt DESC LIMIT 5;
                                             """).fetchall()

        return {
            "total_requests": total_reqs,
            "total_blocked": total_blocked,
            "total_challenges": total_challenges,
            "total_success": total_success,
            "avg_risk_score": avg_risk,
            "top_subnets": [(r["subnet"], r["cnt"]) for r in top_subnets],
            "top_targeted": [(r["username"], r["cnt"]) for r in top_targeted]
        }


# ==============================================================================
# 4. MULTI-FACTOR BEHAVIORAL RISK SCORING ENGINE
# ==============================================================================

class RiskScoringEngine:
    """
    Computes real-time multi-attribute threat scores (0-100) based on velocity,
    subnet clustering, distributed inversion, and honeypot interaction.
    """

    SUSPICIOUS_UA_PATTERNS = ["python", "curl", "headless", "phantom", "bot", "crawler", "aiohttp"]

    def __init__(self, policy: DefensePolicy):
        self.policy = policy

        # Sliding-window deques: Key -> deque of (timestamp, metadata)
        self.ip_window: Dict[str, deque] = defaultdict(deque)
        self.subnet_window: Dict[str, deque] = defaultdict(deque)
        self.user_window: Dict[str, deque] = defaultdict(deque)

    @staticmethod
    def extract_subnet(ip: str) -> str:
        """Derives /24 CIDR prefix (e.g., '198.51.100.45' -> '198.51.100.0/24')."""
        octets = ip.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
        return ip

    def calculate_risk(
            self,
            now: datetime.datetime,
            ip: str,
            subnet: str,
            username: str,
            user_agent: str,
            is_canary_account: bool
    ) -> Tuple[float, RiskBreakdown, List[str]]:
        """Calculates multi-vector risk score normalized between 0.0 and 100.0."""
        breakdown = RiskBreakdown()
        reasons = []

        # Vector 1: Honeypot / Canary Account Violation (Max Penalty)
        if is_canary_account:
            breakdown.canary_penalty = 100.0
            reasons.append("CRITICAL: Targeted confirmed Honeypot / Canary credentials from breached leak dump!")
            breakdown.total_score = 100.0
            return 100.0, breakdown, reasons

        # Vector 2: Single IP Velocity Check
        ip_hist = self.ip_window[ip]
        self._prune_deque(ip_hist, now, self.policy.ip_velocity_window_sec)
        ip_count = len(ip_hist)

        if ip_count >= self.policy.max_requests_per_ip:
            factor = min(35.0, 15.0 + (ip_count - self.policy.max_requests_per_ip) * 4.0)
            breakdown.ip_velocity_score = factor
            reasons.append(f"High-frequency IP velocity ({ip_count} requests in {self.policy.ip_velocity_window_sec}s)")

        # Vector 3: Subnet /24 Horizontal Dispersion Clustering
        subnet_hist = self.subnet_window[subnet]
        self._prune_deque(subnet_hist, now, self.policy.subnet_velocity_window_sec)
        unique_users_in_subnet = {item[1] for item in subnet_hist}

        if len(unique_users_in_subnet) >= self.policy.max_users_per_subnet:
            factor = min(40.0, 20.0 + (len(unique_users_in_subnet) - self.policy.max_users_per_subnet) * 5.0)
            breakdown.subnet_cluster_score = factor
            reasons.append(
                f"Distributed /24 Subnet Sweep ({len(unique_users_in_subnet)} target accounts across {subnet})")

        # Vector 4: Distributed Account Focus (Single user hit by multiple disparate IPs)
        user_hist = self.user_window[username]
        self._prune_deque(user_hist, now, self.policy.user_targeting_window_sec)
        unique_ips_on_user = {item[1] for item in user_hist}

        if len(unique_ips_on_user) >= self.policy.max_ips_per_user:
            factor = min(35.0, 15.0 + (len(unique_ips_on_user) - self.policy.max_ips_per_user) * 5.0)
            breakdown.user_targeting_score = factor
            reasons.append(f"Distributed attack targeting account '{username}' from {len(unique_ips_on_user)} IPs")

        # Vector 5: User-Agent Signature Entropy & Known Tooling
        ua_lower = user_agent.lower()
        if any(tool in ua_lower for tool in self.SUSPICIOUS_UA_PATTERNS) or len(user_agent) < 15:
            breakdown.ua_anomaly_score = 25.0
            reasons.append(f"Automated bot signature or headless User-Agent detected ('{user_agent[:24]}...')")

        # Composite Cumulative Score
        raw_score = (
                breakdown.ip_velocity_score +
                breakdown.subnet_cluster_score +
                breakdown.user_targeting_score +
                breakdown.ua_anomaly_score
        )
        total_score = min(100.0, raw_score)
        breakdown.total_score = total_score

        return total_score, breakdown, reasons

    def record_activity(self, now: datetime.datetime, ip: str, subnet: str, username: str) -> None:
        """Appends approved or processed events into the sliding-window state."""
        self.ip_window[ip].append((now, username))
        self.subnet_window[subnet].append((now, username))
        self.user_window[username].append((now, ip))

    def _prune_deque(self, q: deque, now: datetime.datetime, window_sec: int) -> None:
        cutoff = now - datetime.timedelta(seconds=window_sec)
        while q and q[0][0] < cutoff:
            q.popleft()


# ==============================================================================
# 5. DEFENSE GATEWAY & AUTHENTICATION SERVICE
# ==============================================================================

class CredentialStuffingGateway:
    """Enterprise authentication gateway orchestrating real-time defense actions."""

    def __init__(self, db: DatabaseManager, policy: DefensePolicy):
        self.db = db
        self.policy = policy
        self.risk_engine = RiskScoringEngine(policy)
        self.incidents: List[SecurityIncident] = []

    def evaluate_and_authenticate(
            self,
            now: datetime.datetime,
            ip: str,
            username: str,
            password: str,
            user_agent: str
    ) -> Tuple[AuthResult, DefenseAction, float, str]:
        """
        Executes end-to-end access evaluation:
        Perimeter Bans -> Behavioral Risk Scoring -> Automated Mitigations -> Credential Verification.
        """
        uname = username.lower().strip()
        subnet = RiskScoringEngine.extract_subnet(ip)

        # 1. Perimeter Defense Check (Active IP or Subnet Bans)
        is_banned, ban_type, reason = self.db.is_banned(ip, subnet, now)
        if is_banned:
            details = f"Connection dropped: {ban_type} is currently banned ({reason})"
            self.db.log_event({
                "timestamp": now.isoformat(), "source_ip": ip, "subnet": subnet, "username": uname,
                "user_agent": user_agent, "status": AuthResult.BLOCKED_BY_DEFENSE.value,
                "risk_score": 100.0, "action_taken": DefenseAction.BLOCK_IP.value, "details": details
            })
            return AuthResult.BLOCKED_BY_DEFENSE, DefenseAction.BLOCK_IP, 100.0, details

        # 2. Check if targeted user is an active Honeypot / Canary
        user_row = self.db.conn.execute("SELECT * FROM users WHERE username = ?;", (uname,)).fetchone()
        is_canary = bool(user_row["is_canary"]) if user_row else False

        # 3. Multi-Factor Risk Calculation
        risk_score, breakdown, reasons = self.risk_engine.calculate_risk(
            now, ip, subnet, uname, user_agent, is_canary
        )

        # 4. Determine Dynamic Defense Action based on score gates
        action = DefenseAction.ALLOW
        if risk_score >= self.policy.score_threshold_block:
            action = DefenseAction.BLOCK_IP if not is_canary and breakdown.subnet_cluster_score < 25 else DefenseAction.BAN_SUBNET
        elif risk_score >= self.policy.score_threshold_captcha:
            action = DefenseAction.CHALLENGE_CAPTCHA
        elif risk_score >= self.policy.score_threshold_delay:
            action = DefenseAction.INJECT_DELAY

        # 5. Apply Enforcement Actions
        if action in (DefenseAction.BLOCK_IP, DefenseAction.BAN_SUBNET):
            ban_target = ip if action == DefenseAction.BLOCK_IP else subnet
            ban_dur = self.policy.ip_ban_duration_sec if action == DefenseAction.BLOCK_IP else self.policy.subnet_ban_duration_sec
            ban_until = now + datetime.timedelta(seconds=ban_dur)

            self.db.add_ban(ban_target, action.value, ban_until, "; ".join(reasons))
            self._raise_incident(now, action, risk_score, ip, subnet, uname, "; ".join(reasons))

            details = f"Offensive traffic terminated. Action: {action.value} on {ban_target}"
            self.db.log_event({
                "timestamp": now.isoformat(), "source_ip": ip, "subnet": subnet, "username": uname,
                "user_agent": user_agent, "status": AuthResult.BLOCKED_BY_DEFENSE.value,
                "risk_score": risk_score, "action_taken": action.value, "details": details
            })
            return AuthResult.BLOCKED_BY_DEFENSE, action, risk_score, details

        # Update sliding window state for ongoing traffic
        self.risk_engine.record_activity(now, ip, subnet, uname)

        # 6. Verify Credentials
        if not user_row:
            status = AuthResult.FAILED_UNKNOWN_USER
            details = "Authentication failed: Account not found in active directory."
        elif is_canary:
            status = AuthResult.FAILED_CANARY_HIT
            details = "Honeypot canary breached! Incident flagged and attacker quarantined."
        else:
            # PBKDF2 hash verification
            expected_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), user_row["salt"].encode("utf-8"), 100_000
            ).hex()
            if hmac.compare_digest(expected_hash, user_row["password_hash"]):
                status = AuthResult.SUCCESS
                details = "Authentication successful. Access token granted."
            else:
                status = AuthResult.FAILED_BAD_PASSWORD
                details = "Authentication failed: Invalid credentials provided."

        self.db.log_event({
            "timestamp": now.isoformat(), "source_ip": ip, "subnet": subnet, "username": uname,
            "user_agent": user_agent, "status": status.value, "risk_score": risk_score,
            "action_taken": action.value, "details": details
        })

        return status, action, risk_score, details

    def _raise_incident(
            self,
            now: datetime.datetime,
            action: DefenseAction,
            score: float,
            ip: str,
            subnet: str,
            user: str,
            details: str
    ) -> None:
        severity = ThreatSeverity.CRITICAL if score >= 85 else ThreatSeverity.HIGH
        incident_id = f"INC-{now.strftime('%H%M%S')}-{secrets_hex_compat()}"
        self.incidents.append(SecurityIncident(
            incident_id=incident_id,
            timestamp=now.isoformat(),
            severity=severity,
            rule_name="Automated Perimeter Defense Trigger",
            source_ip=ip,
            subnet=subnet,
            target_account=user,
            risk_score=score,
            action_taken=action,
            details=details
        ))


def secrets_hex_compat() -> str:
    """Generates random 4-byte hex string."""
    return f"{random.randint(0x1000, 0xFFFF):04x}"


# ==============================================================================
# 6. SYNTHETIC EVENT GENERATOR & ADVERSARIAL WORKLOADS
# ==============================================================================

class SyntheticTrafficGenerator:
    """Generates multi-scenario baseline and attack traffic workloads."""

    BOT_USER_AGENTS = [
        "python-requests/2.31.0",
        "curl/7.88.1",
        "Mozilla/5.0 (HeadlessChrome/120.0.0.0)",
        "Go-http-client/1.1",
        "CustomCredentialTester/2.0"
    ]

    LEGIT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]

    @classmethod
    def populate_user_directory(cls, db: DatabaseManager, count: int = 40) -> List[Tuple[str, str]]:
        """Seeds standard enterprise accounts and hidden honeypot canary accounts."""
        credentials = []
        for i in range(1, count + 1):
            uname = f"staff_{i:02d}"
            pwd = f"CorporatePass2024#{i}"
            salt = secrets_hex_compat()
            h = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt.encode(), 100_000).hex()
            db.insert_user(uname, h, salt, is_canary=False)
            credentials.append((uname, pwd))

        # Seed 3 Honeypot / Canary Accounts (Known leaked dummy records)
        for canary in ["canary_admin", "dev_backup_service", "legacy_portal_user"]:
            salt = secrets_hex_compat()
            h = hashlib.pbkdf2_hmac("sha256", b"CanaryP@ssword99!", salt.encode(), 100_000).hex()
            db.insert_user(canary, h, salt, is_canary=True)

        return credentials

    @classmethod
    def run_simulation_suite(cls, gateway: CredentialStuffingGateway, user_creds: List[Tuple[str, str]]) -> None:
        """Executes a chronological battery of legitimate and hostile traffic vectors."""
        print_section("EXECUTION: Multi-Scenario Credential-Stuffing Simulation")
        t0 = datetime.datetime.now()

        # Phase 1: Legitimate Authorized Users (Normal Behavior)
        print(f"[*] Phase 1: Ingesting Legitimate Staff Traffic (Clean Baselines)...")
        for i in range(8):
            u, p = random.choice(user_creds)
            legit_ip = f"192.168.10.{100 + i}"
            ua = random.choice(cls.LEGIT_USER_AGENTS)
            t = t0 + datetime.timedelta(seconds=i * 2)

            res, act, score, det = gateway.evaluate_and_authenticate(t, legit_ip, u, p, ua)
            print(
                f"  [LEGIT] {u:<16} from {legit_ip:<15} -> {ANSI.GREEN}{res.value:<22}{ANSI.RESET} (Risk: {score:.1f})")

        # Phase 2: Concentrated Single-Source Brute-Force (High IP Velocity)
        t_phase2 = t0 + datetime.timedelta(seconds=30)
        attacker_ip = "198.51.100.88"
        print(
            f"\n{ANSI.BOLD}{ANSI.YELLOW}[*] Phase 2: High-Velocity Single-Source Brute-Force from {attacker_ip}...{ANSI.RESET}")

        target_u = "staff_05"
        for i in range(8):
            t = t_phase2 + datetime.timedelta(seconds=i * 3)
            guess_pwd = f"WrongPassword_{i}"
            res, act, score, det = gateway.evaluate_and_authenticate(t, attacker_ip, target_u, guess_pwd,
                                                                     cls.BOT_USER_AGENTS[0])

            color = ANSI.RED if act == DefenseAction.BLOCK_IP else (
                ANSI.YELLOW if act != DefenseAction.ALLOW else ANSI.RESET)
            print(
                f"  [ATTACK] Target: {target_u:<10} | Guess #{i + 1} | Score: {score:4.1f} | Action: {color}{act.value:<18}{ANSI.RESET}")
            if act == DefenseAction.BLOCK_IP:
                print(
                    f"  {ANSI.RED}{ANSI.BOLD}>>> AUTOMATED DEFENSE TRIGGERED: IP {attacker_ip} firewalled! <<<{ANSI.RESET}")
                break

        # Phase 3: Distributed Credential-Stuffing Botnet (/24 Subnet Sweep)
        t_phase3 = t0 + datetime.timedelta(seconds=90)
        botnet_subnet = "203.0.113."
        print(
            f"\n{ANSI.BOLD}{ANSI.MAGENTA}[*] Phase 3: Distributed Credential-Stuffing Botnet (/24 Subnet Sweep)...{ANSI.RESET}")
        print(f"  Botnet rotating across 8 distinct node IPs targeting separate accounts...\n")

        for i in range(8):
            t = t_phase3 + datetime.timedelta(seconds=i * 2)
            bot_ip = f"{botnet_subnet}{10 + i}"
            target_user = user_creds[i][0]
            stuffed_pwd = "LeakedDumpPassword2023!"
            ua = cls.BOT_USER_AGENTS[i % len(cls.BOT_USER_AGENTS)]

            res, act, score, det = gateway.evaluate_and_authenticate(t, bot_ip, target_user, stuffed_pwd, ua)
            color = ANSI.RED if act in (DefenseAction.BLOCK_IP, DefenseAction.BAN_SUBNET) else ANSI.YELLOW
            print(
                f"  [BOTNET] IP: {bot_ip:<15} -> Target: {target_user:<10} | Score: {score:4.1f} | Action: {color}{act.value:<18}{ANSI.RESET}")

            if act == DefenseAction.BAN_SUBNET:
                print(
                    f"  {ANSI.BG_RED}{ANSI.WHITE} >>> THREAT NEUTRALIZED: Entire /24 Subnet {botnet_subnet}0/24 Banned! <<< {ANSI.RESET}")
                break

        # Phase 4: Honeypot / Canary Account Breach Ingestion
        t_phase4 = t0 + datetime.timedelta(seconds=130)
        canary_ip = "192.0.2.77"
        print(
            f"\n{ANSI.BOLD}{ANSI.RED}[*] Phase 4: Adversary Testing Leaked Combo List against Canary Trap Account...{ANSI.RESET}")

        res, act, score, det = gateway.evaluate_and_authenticate(
            t_phase4, canary_ip, "dev_backup_service", "CanaryP@ssword99!", cls.BOT_USER_AGENTS[2]
        )
        print(
            f"  [CANARY TRAP] Target: 'dev_backup_service' from {canary_ip} -> Score: {ANSI.BOLD}{ANSI.RED}{score:.1f}{ANSI.RESET}")
        print(f"  Action Enacted: {ANSI.BG_RED}{ANSI.WHITE} {act.value} {ANSI.RESET} ({det})")


# ==============================================================================
# 7. TELEMETRY, DASHBOARD & REPORT EXPORTERS
# ==============================================================================

class TelemetryDashboard:
    """SOC analytics visualizer and formal report compiler."""

    @staticmethod
    def render_console_dashboard(db: DatabaseManager, incidents: List[SecurityIncident]) -> None:
        metrics = db.get_telemetry_aggregations()
        if not metrics:
            print(f"{ANSI.YELLOW}No event logs recorded.{ANSI.RESET}")
            return

        print(
            f"\n{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.WHITE}         CREDENTIAL-STUFFING DEFENSE: TELEMETRY & AUDIT DASHBOARD               {ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f" Total Logins Evaluated    : {ANSI.BOLD}{metrics['total_requests']:<10}{ANSI.RESET} | Authorized Sessions : {ANSI.GREEN}{metrics['total_success']}{ANSI.RESET}")
        print(
            f" Ingress Threats Dropped    : {ANSI.BOLD}{ANSI.RED}{metrics['total_blocked']:<10}{ANSI.RESET} | CAPTCHA Challenges   : {ANSI.YELLOW}{metrics['total_challenges']}{ANSI.RESET}")
        print(
            f" System Average Risk Score  : {ANSI.CYAN}{metrics['avg_risk_score']:4.1f} / 100{ANSI.RESET} | Active Security Incidents: {ANSI.MAGENTA}{len(incidents)}{ANSI.RESET}")
        print(f"--------------------------------------------------------------------------------")

        # Risk distribution table
        print(f" Top Adversarial /24 Subnets Identified:")
        for subnet, count in metrics["top_subnets"]:
            print(f"  • Subnet: {ANSI.YELLOW}{subnet:<18}{ANSI.RESET} | Failed Strike Volume: {count}")

        print(f"\n Top Targeted Corporate Accounts:")
        for user, count in metrics["top_targeted"]:
            print(f"  • Account: {ANSI.CYAN}{user:<18}{ANSI.RESET} | Attack Replay Count  : {count}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}\n")

    @staticmethod
    def export_reports(db: DatabaseManager, incidents: List[SecurityIncident], prefix: str = "security_audit") -> None:
        """Exports raw forensic logs to CSV and incident dossier to JSON."""
        # 1. Export Incidents to JSON
        json_file = f"{prefix}_incidents.json"
        incident_dicts = [asdict(inc) for inc in incidents]
        for inc in incident_dicts:
            inc["severity"] = inc["severity"].value
            inc["action_taken"] = inc["action_taken"].value

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(incident_dicts, f, indent=2)
        print(f"{ANSI.GREEN}[✓] Incident report exported to '{json_file}'.{ANSI.RESET}")

        # 2. Export Raw Events to CSV
        csv_file = f"{prefix}_events.csv"
        with db.conn:
            cursor = db.conn.execute("SELECT * FROM login_events;")
            rows = cursor.fetchall()
            if rows:
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(rows[0].keys())
                    writer.writerows([tuple(r) for r in rows])
                print(f"{ANSI.GREEN}[✓] Raw forensic event log exported to '{csv_file}'.{ANSI.RESET}")


def print_banner(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.WHITE}  {title.upper()}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}\n")


def print_section(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.YELLOW}--- [ {title} ] ---{ANSI.RESET}\n")


# ==============================================================================
# 8. INTERACTIVE MANAGEMENT WORKBENCH
# ==============================================================================

class DefenseWorkbenchApp:
    """Interactive management console for policy modification and live verification."""

    def __init__(self):
        self.policy = DefensePolicy()
        self.db = DatabaseManager()
        self.gateway = CredentialStuffingGateway(self.db, self.policy)
        self.user_creds = SyntheticTrafficGenerator.populate_user_directory(self.db, count=30)

    def main_menu(self) -> None:
        while True:
            print_banner("Credential-Stuffing Defense & Risk Scoring Platform")
            print(" 1. Run Complete Automated Threat Simulation (Botnet, Brute-Force, Canary)")
            print(" 2. Manual Login Evaluation (Inject Custom Attempt & View Risk Scoring)")
            print(" 3. View SOC Forensic Telemetry & Analytics Dashboard")
            print(" 4. Reconfigure Risk Policy Gates & Time-Window Thresholds")
            print(" 5. Inspect Active Perimeter IP & Subnet Firewall Bans")
            print(" 6. Export Security Reports (JSON Dossier & CSV Audit Trail)")
            print(" 0. Terminate Application")
            print(f"{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")

            choice = input(f"{ANSI.BOLD}Select Operation [0-6]: {ANSI.RESET}").strip()

            if choice == "1":
                SyntheticTrafficGenerator.run_simulation_suite(self.gateway, self.user_creds)
                TelemetryDashboard.render_console_dashboard(self.db, self.gateway.incidents)
            elif choice == "2":
                self._manual_login_eval()
            elif choice == "3":
                TelemetryDashboard.render_console_dashboard(self.db, self.gateway.incidents)
            elif choice == "4":
                self._tune_policies()
            elif choice == "5":
                self._display_bans()
            elif choice == "6":
                TelemetryDashboard.export_reports(self.db, self.gateway.incidents)
            elif choice == "0":
                print(f"\n{ANSI.GREEN}[✓] Simulator closed cleanly.{ANSI.RESET}")
                sys.exit(0)
            else:
                print(f"{ANSI.RED}[!] Invalid choice.{ANSI.RESET}")

            input(f"\n{ANSI.DIM}Press Enter to return to main menu...{ANSI.RESET}")

    def _manual_login_eval(self) -> None:
        print_section("MANUAL LOGIN INGESTION & RISK SCORING")
        ip = input("Enter Source IP (default: 198.51.100.99): ").strip() or "198.51.100.99"
        user = input("Enter Target Account (e.g., staff_01 or canary_admin): ").strip() or "staff_01"
        pwd = input("Enter Candidate Password: ").strip() or "DummyP@ssword123"
        ua = input("Enter User-Agent (default: Mozilla/5.0): ").strip() or "Mozilla/5.0"

        now = datetime.datetime.now()
        res, act, score, det = self.gateway.evaluate_and_authenticate(now, ip, user, pwd, ua)

        color = ANSI.GREEN if res == AuthResult.SUCCESS else ANSI.RED
        print(f"\n{ANSI.BOLD}Evaluation Result:{ANSI.RESET}")
        print(f"  • Authentication Status : {color}{res.value}{ANSI.RESET}")
        print(f"  • Composite Risk Score  : {ANSI.BOLD}{score:.1f} / 100{ANSI.RESET}")
        print(f"  • Defensive Enforcement : {ANSI.YELLOW}{act.value}{ANSI.RESET}")
        print(f"  • Forensic Log Details  : {det}")

    def _tune_policies(self) -> None:
        print_section("RECONFIGURE POLICY THRESHOLDS")
        print(
            f"1. IP Velocity Trigger Gate  (Current: {self.policy.max_requests_per_ip} reqs / {self.policy.ip_velocity_window_sec}s)")
        print(
            f"2. Subnet Churn Trigger Gate (Current: {self.policy.max_users_per_subnet} accounts / {self.policy.subnet_velocity_window_sec}s)")
        print(f"3. Blocking Score Threshold  (Current: Score >= {self.policy.score_threshold_block})")

        opt = input("Select setting to update (1-3) or 'q' to return: ").strip()
        if opt == "1":
            self.policy.max_requests_per_ip = int(input("Enter new limit: "))
        elif opt == "2":
            self.policy.max_users_per_subnet = int(input("Enter new limit: "))
        elif opt == "3":
            self.policy.score_threshold_block = int(input("Enter new risk score threshold (0-100): "))
        print(f"{ANSI.GREEN}[✓] Policy parameters updated successfully.{ANSI.RESET}")

    def _display_bans(self) -> None:
        print_section("ACTIVE PERIMETER FIREWALL BANS")
        with self.db.conn:
            rows = self.db.conn.execute("SELECT * FROM perimeter_bans;").fetchall()
            if not rows:
                print("No active IP or Subnet firewall bans.")
                return

            print(f"{ANSI.BOLD}{'Identifier':<20} | {'Type':<8} | {'Banned Until':<24} | {'Reason'}{ANSI.RESET}")
            print("-" * 80)
            for r in rows:
                print(f"{r['target_identifier']:<20} | {r['ban_type']:<8} | {r['banned_until']:<24} | {r['reason']}")


# ==============================================================================
# 9. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    try:
        app = DefenseWorkbenchApp()
        # Non-interactive automated execution flag
        if len(sys.argv) > 1 and sys.argv[1] in ("--auto", "-a", "--demo"):
            SyntheticTrafficGenerator.run_simulation_suite(app.gateway, app.user_creds)
            TelemetryDashboard.render_console_dashboard(app.db, app.gateway.incidents)
            TelemetryDashboard.export_reports(app.db, app.gateway.incidents, prefix="automated_audit")
            sys.exit(0)

        app.main_menu()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Simulator terminated by operator.{ANSI.RESET}")
        sys.exit(0)
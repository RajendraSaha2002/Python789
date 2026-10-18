import sqlite3
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque, Counter
import hashlib
import hmac
import secrets
import threading
import dataclasses
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional, Any
import json
import math
import sys
import os


# ==============================================================================
# 1. CONSTANTS, ENUMS & TERMINAL COLOR PALETTE
# ==============================================================================

class ANSI:
    """Terminal ANSI Escape Codes for Forensic Highlighting."""
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


class LoginStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED_INVALID_CREDENTIALS = "FAILED_INVALID_CREDENTIALS"
    FAILED_USER_NOT_FOUND = "FAILED_USER_NOT_FOUND"
    BLOCKED_ACCOUNT_LOCKED_SOFT = "BLOCKED_ACCOUNT_LOCKED_SOFT"
    BLOCKED_ACCOUNT_LOCKED_HARD = "BLOCKED_ACCOUNT_LOCKED_HARD"
    BLOCKED_IP_RATE_LIMITED = "BLOCKED_IP_RATE_LIMITED"
    BLOCKED_IP_BLACKLISTED = "BLOCKED_IP_BLACKLISTED"
    BLOCKED_PROGRESSIVE_DELAY = "BLOCKED_PROGRESSIVE_DELAY"


class ThreatLevel(Enum):
    BENIGN = "BENIGN"
    SUSPICIOUS = "SUSPICIOUS"
    ATTACK_IN_PROGRESS = "ATTACK_IN_PROGRESS"
    CRITICAL_BREACH_ATTEMPT = "CRITICAL_BREACH_ATTEMPT"


# ==============================================================================
# 2. CONFIGURATION & POLICY ENGINE
# ==============================================================================

@dataclasses.dataclass
class SecurityPolicy:
    """Configurable system defense policies and threshold parameters."""
    # Attempt limits before soft lockout
    max_failed_attempts_soft: int = 5
    # Soft lockout base cooldown (seconds)
    soft_lockout_base_seconds: int = 15
    # Attempt limits before hard administrative lockout
    max_failed_attempts_hard: int = 10
    # Hard lockout duration (seconds, e.g., 24 hours = 86400)
    hard_lockout_seconds: int = 86400

    # Sliding window IP rate limits
    ip_window_seconds: int = 60
    ip_max_requests_per_window: int = 15

    # Progressive Delay settings (Artificial latency injection)
    enable_progressive_delay: bool = True
    delay_trigger_threshold: int = 3
    delay_multiplier_seconds: float = 0.5  # delay = (attempts - threshold) * multiplier
    max_injected_delay_seconds: float = 3.0

    # Password Spraying Detection
    spray_window_seconds: int = 120
    spray_unique_users_threshold: int = 4

    # IP Automatic Ban Duration (seconds)
    ip_ban_duration_seconds: int = 300


# ==============================================================================
# 3. RELATIONAL DATABASE STORAGE (SQLite3)
# ==============================================================================

class DatabaseManager:
    """
    Thread-safe SQLite database manager holding persistent user credentials,
    audit records, and defensive blacklist entries.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Provides thread-local SQLite connection with high-performance WAL journaling."""
        if not hasattr(self._local, "connection"):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Enable PRAGMA performance flags
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.connection = conn
        return self._local.connection

    def _init_database(self) -> None:
        """Initializes relational schemas and access indices."""
        conn = self.get_connection()
        with conn:
            conn.executescript("""
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
                                   failed_attempts
                                   INTEGER
                                   DEFAULT
                                   0,
                                   soft_lock_until
                                   TIMESTAMP,
                                   hard_lock_until
                                   TIMESTAMP,
                                   is_active
                                   INTEGER
                                   DEFAULT
                                   1,
                                   created_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP,
                                   updated_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP
                               );

                               CREATE TABLE IF NOT EXISTS login_logs
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   timestamp
                                   TIMESTAMP
                                   NOT
                                   NULL,
                                   ip_address
                                   TEXT
                                   NOT
                                   NULL,
                                   username
                                   TEXT
                                   NOT
                                   NULL,
                                   status
                                   TEXT
                                   NOT
                                   NULL,
                                   injected_delay_ms
                                   REAL
                                   DEFAULT
                                   0.0,
                                   threat_level
                                   TEXT
                                   NOT
                                   NULL,
                                   user_agent
                                   TEXT
                                   NOT
                                   NULL,
                                   details
                                   TEXT
                               );

                               CREATE TABLE IF NOT EXISTS ip_blacklist
                               (
                                   ip_address
                                   TEXT
                                   PRIMARY
                                   KEY,
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
                                   1,
                                   created_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP
                               );

                               CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON login_logs(timestamp);
                               CREATE INDEX IF NOT EXISTS idx_logs_ip ON login_logs(ip_address);
                               CREATE INDEX IF NOT EXISTS idx_logs_username ON login_logs(username);
                               """)

    def reset_all_data(self) -> None:
        """Wipes and re-initializes tables for fresh simulation runs."""
        conn = self.get_connection()
        with conn:
            conn.execute("DELETE FROM login_logs;")
            conn.execute("DELETE FROM ip_blacklist;")
            conn.execute("DELETE FROM users;")


# ==============================================================================
# 4. IN-MEMORY DEFENSE & RATE LIMITING ENGINE
# ==============================================================================

class SlidingWindowGovernor:
    """Thread-safe Sliding-Window Rate Limiter & Behavioral Attack Detector."""

    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
        self._lock = threading.Lock()
        # IP -> deque of request timestamps
        self.ip_request_history: Dict[str, deque] = defaultdict(deque)
        # IP -> deque of (timestamp, target_username)
        self.ip_spray_history: Dict[str, deque] = defaultdict(deque)

    def is_ip_rate_limited(self, ip: str, current_time: float) -> bool:
        """Checks sliding window request counter for a single IP."""
        with self._lock:
            history = self.ip_request_history[ip]
            cutoff = current_time - self.policy.ip_window_seconds

            # Prune obsolete events outside the window
            while history and history[0] < cutoff:
                history.popleft()

            if len(history) >= self.policy.ip_max_requests_per_window:
                return True

            history.append(current_time)
            return False

    def detect_password_spraying(self, ip: str, username: str, current_time: float) -> bool:
        """
        Detects low-and-slow horizontal password spraying:
        Single IP hitting multiple distinct accounts within spray window.
        """
        with self._lock:
            spray_records = self.ip_spray_history[ip]
            cutoff = current_time - self.policy.spray_window_seconds

            while spray_records and spray_records[0][0] < cutoff:
                spray_records.popleft()

            spray_records.append((current_time, username))

            unique_targets = {target for _, target in spray_records}
            return len(unique_targets) >= self.policy.spray_unique_users_threshold

    def clear(self) -> None:
        """Resets all active sliding windows."""
        with self._lock:
            self.ip_request_history.clear()
            self.ip_spray_history.clear()


# ==============================================================================
# 5. AUTHENTICATION & LOGIN DEFENSE SERVICE
# ==============================================================================

class AuthenticationService:
    """
    Core security orchestrator enforcing PBKDF2 hashing, progressive delay,
    adaptive lockout rules, and automated IP banishment.
    """

    def __init__(self, db: DatabaseManager, policy: SecurityPolicy):
        self.db = db
        self.policy = policy
        self.governor = SlidingWindowGovernor(policy)
        self._auth_lock = threading.Lock()

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Calculates PBKDF2-HMAC-SHA256 hash using 100,000 iterations."""
        if salt is None:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            iterations=100_000
        ).hex()
        return pwd_hash, salt

    def register_user(self, username: str, password: str) -> bool:
        """Provisions a new system user with salted credential hashing."""
        pwd_hash, salt = self.hash_password(password)
        conn = self.db.get_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?);",
                    (username.lower().strip(), pwd_hash, salt)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def is_ip_blacklisted(self, ip: str, now: datetime) -> Tuple[bool, Optional[str]]:
        """Verifies if an IP address is currently blocked in the database."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT banned_until, reason FROM ip_blacklist WHERE ip_address = ?;",
            (ip,)
        ).fetchone()

        if row:
            banned_until = datetime.fromisoformat(row["banned_until"])
            if now < banned_until:
                return True, row["reason"]
            else:
                # Ban expired; prune record
                with conn:
                    conn.execute("DELETE FROM ip_blacklist WHERE ip_address = ?;", (ip,))
        return False, None

    def blacklist_ip(self, ip: str, reason: str, duration_seconds: int, now: datetime) -> None:
        """Enforces a hard boundary firewall ban on a hostile IP."""
        banned_until = (now + timedelta(seconds=duration_seconds)).isoformat()
        conn = self.db.get_connection()
        with conn:
            conn.execute("""
                         INSERT INTO ip_blacklist (ip_address, banned_until, reason, strikes)
                         VALUES (?, ?, ?, 1) ON CONFLICT(ip_address) DO
                         UPDATE SET
                             banned_until = excluded.banned_until,
                             reason = excluded.reason,
                             strikes = strikes + 1;
                         """, (ip, banned_until, reason))

    def unlock_account(self, username: str) -> bool:
        """Administrative reset of an account's failed attempts and lockouts."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.execute("""
                                  UPDATE users
                                  SET failed_attempts = 0,
                                      soft_lock_until = NULL,
                                      hard_lock_until = NULL
                                  WHERE username = ?;
                                  """, (username.lower().strip(),))
            return cursor.rowcount > 0

    def calculate_progressive_delay(self, failed_attempts: int) -> float:
        """Calculates artificial latency injection for consecutive failures."""
        if not self.policy.enable_progressive_delay:
            return 0.0
        if failed_attempts < self.policy.delay_trigger_threshold:
            return 0.0

        excess = failed_attempts - self.policy.delay_trigger_threshold + 1
        delay = excess * self.policy.delay_multiplier_seconds
        return min(delay, self.policy.max_injected_delay_seconds)

    def authenticate(
            self,
            username: str,
            password: str,
            ip_address: str,
            user_agent: str = "Standard-Client/1.0"
    ) -> Tuple[LoginStatus, str, float]:
        """
        Executes complete login authentication flow evaluating all defensive
        checkpoints: IP Blacklist -> Rate Limit -> Progressive Delay -> Account Lock -> Credential Check.
        """
        now = datetime.utcnow()
        current_epoch = time.time()
        start_mono = time.monotonic()
        uname = username.lower().strip()

        # Checkpoint 1: IP Blacklist Verification
        is_banned, ban_reason = self.is_ip_blacklisted(ip_address, now)
        if is_banned:
            self._log_event(now, ip_address, uname, LoginStatus.BLOCKED_IP_BLACKLISTED, 0.0,
                            ThreatLevel.CRITICAL_BREACH_ATTEMPT, user_agent, f"IP Banned: {ban_reason}")
            return LoginStatus.BLOCKED_IP_BLACKLISTED, f"Connection rejected: IP blacklisted ({ban_reason}).", 0.0

        # Checkpoint 2: Sliding-Window IP Rate Limiter
        if self.governor.is_ip_rate_limited(ip_address, current_epoch):
            # Rate limit breached; assign strike and evaluate ban
            self.blacklist_ip(ip_address, "Sliding-Window Rate Limit Exhaustion",
                              self.policy.ip_ban_duration_seconds, now)
            self._log_event(now, ip_address, uname, LoginStatus.BLOCKED_IP_RATE_LIMITED, 0.0,
                            ThreatLevel.ATTACK_IN_PROGRESS, user_agent, "Rate limit exceeded (IP auto-banned)")
            return LoginStatus.BLOCKED_IP_RATE_LIMITED, "Rate limit exceeded. Temporary IP block enacted.", 0.0

        # Checkpoint 3: Behavioral Anomaly Inspection (Password Spraying)
        if self.governor.detect_password_spraying(ip_address, uname, current_epoch):
            self.blacklist_ip(ip_address, "Horizontal Password Spraying Detected",
                              self.policy.ip_ban_duration_seconds * 2, now)
            self._log_event(now, ip_address, uname, LoginStatus.BLOCKED_IP_BLACKLISTED, 0.0,
                            ThreatLevel.CRITICAL_BREACH_ATTEMPT, user_agent, "Horizontal spraying signature identified")
            return LoginStatus.BLOCKED_IP_BLACKLISTED, "Security threat identified: IP blacklisted for account spraying.", 0.0

        # Synchronize database state evaluation per user
        conn = self.db.get_connection()
        user_row = conn.execute("SELECT * FROM users WHERE username = ?;", (uname,)).fetchone()

        if not user_row:
            # User non-existent; simulate timing resistance to mitigate user enumeration
            _ = hashlib.pbkdf2_hmac("sha256", password.encode(), b"dummy_salt_bytes", 100_000)
            self._log_event(now, ip_address, uname, LoginStatus.FAILED_USER_NOT_FOUND, 0.0,
                            ThreatLevel.SUSPICIOUS, user_agent, "Invalid account targeted")
            return LoginStatus.FAILED_USER_NOT_FOUND, "Invalid credentials provided.", 0.0

        # Checkpoint 4: Hard Administrative Lockout Check
        if user_row["hard_lock_until"]:
            hard_until = datetime.fromisoformat(user_row["hard_lock_until"])
            if now < hard_until:
                self._log_event(now, ip_address, uname, LoginStatus.BLOCKED_ACCOUNT_LOCKED_HARD, 0.0,
                                ThreatLevel.ATTACK_IN_PROGRESS, user_agent,
                                "Attempt on administratively locked account")
                return LoginStatus.BLOCKED_ACCOUNT_LOCKED_HARD, "Account locked permanently due to severe violations. Contact Administrator.", 0.0

        # Checkpoint 5: Transient Soft Lockout Check
        if user_row["soft_lock_until"]:
            soft_until = datetime.fromisoformat(user_row["soft_lock_until"])
            if now < soft_until:
                remaining = int((soft_until - now).total_seconds())
                self._log_event(now, ip_address, uname, LoginStatus.BLOCKED_ACCOUNT_LOCKED_SOFT, 0.0,
                                ThreatLevel.ATTACK_IN_PROGRESS, user_agent,
                                f"Account in soft cooldown. Remaining: {remaining}s")
                return LoginStatus.BLOCKED_ACCOUNT_LOCKED_SOFT, f"Account temporarily restricted. Retry in {remaining} seconds.", 0.0

        # Checkpoint 6: Progressive Delay Injection
        failed_count = user_row["failed_attempts"]
        injected_delay = self.calculate_progressive_delay(failed_count)
        if injected_delay > 0.0:
            time.sleep(injected_delay)

        # Checkpoint 7: Cryptographic Hash Verification
        input_hash = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=user_row["salt"].encode("utf-8"),
            iterations=100_000
        ).hex()

        is_valid = hmac.compare_digest(input_hash, user_row["password_hash"])
        total_latency_ms = (time.monotonic() - start_mono) * 1000.0

        with conn:
            if is_valid:
                # Reset failure state upon valid authentication
                conn.execute("""
                             UPDATE users
                             SET failed_attempts = 0,
                                 soft_lock_until = NULL,
                                 hard_lock_until = NULL,
                                 updated_at      = ?
                             WHERE id = ?;
                             """, (now.isoformat(), user_row["id"]))

                self._log_event(now, ip_address, uname, LoginStatus.SUCCESS, total_latency_ms,
                                ThreatLevel.BENIGN, user_agent, "Legitimate session established")
                return LoginStatus.SUCCESS, "Authentication successful. Access granted.", total_latency_ms

            else:
                new_failed = failed_count + 1
                soft_lock_ts = None
                hard_lock_ts = None
                status = LoginStatus.FAILED_INVALID_CREDENTIALS
                msg = f"Invalid credentials. Failed attempts: {new_failed}."

                # Escalate to Hard Lockout
                if new_failed >= self.policy.max_failed_attempts_hard:
                    hard_lock_ts = (now + timedelta(seconds=self.policy.hard_lockout_seconds)).isoformat()
                    status = LoginStatus.BLOCKED_ACCOUNT_LOCKED_HARD
                    msg = f"Maximum attempts ({self.policy.max_failed_attempts_hard}) exceeded. Account placed under Hard Administrative Lock."

                # Escalate to Soft Lockout (Exponential Escaping Duration)
                elif new_failed >= self.policy.max_failed_attempts_soft:
                    multiplier = 2 ** (new_failed - self.policy.max_failed_attempts_soft)
                    soft_seconds = self.policy.soft_lockout_base_seconds * multiplier
                    soft_lock_ts = (now + timedelta(seconds=soft_seconds)).isoformat()
                    status = LoginStatus.BLOCKED_ACCOUNT_LOCKED_SOFT
                    msg = f"Failed attempt limit reached. Account locked for {soft_seconds}s cooldown."

                conn.execute("""
                             UPDATE users
                             SET failed_attempts = ?,
                                 soft_lock_until = ?,
                                 hard_lock_until = ?,
                                 updated_at      = ?
                             WHERE id = ?;
                             """, (new_failed, soft_lock_ts, hard_lock_ts, now.isoformat(), user_row["id"]))

                threat = ThreatLevel.SUSPICIOUS if new_failed < self.policy.max_failed_attempts_soft else ThreatLevel.ATTACK_IN_PROGRESS
                self._log_event(now, ip_address, uname, status, total_latency_ms, threat, user_agent, msg)
                return status, msg, total_latency_ms

    def _log_event(
            self,
            timestamp: datetime,
            ip: str,
            username: str,
            status: LoginStatus,
            latency_ms: float,
            threat: ThreatLevel,
            user_agent: str,
            details: str
    ) -> None:
        """Commits immutable authentication audit trail record."""
        conn = self.db.get_connection()
        with conn:
            conn.execute("""
                         INSERT INTO login_logs (timestamp, ip_address, username, status, injected_delay_ms,
                                                 threat_level, user_agent, details)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                         """, (
                             timestamp.isoformat(),
                             ip,
                             username,
                             status.value,
                             latency_ms,
                             threat.value,
                             user_agent,
                             details
                         ))


# ==============================================================================
# 6. ATTACK SIMULATION WORKLOAD GENERATOR
# ==============================================================================

class AttackSimulator:
    """
    Automated actor simulating both realistic threat actors and legitimate enterprise
    workloads against the configured authentication gateway.
    """

    def __init__(self, auth_service: AuthenticationService):
        self.auth = auth_service
        self.stop_signal = threading.Event()

    def simulate_targeted_brute_force(
            self,
            target_user: str,
            attacker_ip: str,
            num_attempts: int = 15,
            interval_ms: int = 100
    ) -> None:
        """Simulates single-target high-velocity dictionary password guessing."""
        print(f"\n{ANSI.BOLD}{ANSI.RED}[+] LAUNCHING TARGETED BRUTE-FORCE ATTACK{ANSI.RESET}")
        print(
            f"Target Account: {ANSI.CYAN}{target_user}{ANSI.RESET} | Attacker IP: {ANSI.YELLOW}{attacker_ip}{ANSI.RESET} | Iterations: {num_attempts}")

        common_passwords = [
            "123456", "password", "12345678", "qwerty", "123456789", "12345",
            "111111", "1234567", "dragon", "welcome", "ninja", "superman",
            "football", "letmein", "master", "shadow", "monkey", "sunshine"
        ]

        for i in range(num_attempts):
            if self.stop_signal.is_set():
                break
            pwd = common_passwords[i % len(common_passwords)]
            status, msg, latency = self.auth.authenticate(
                username=target_user,
                password=pwd,
                ip_address=attacker_ip,
                user_agent="Hydra-Engine/9.2"
            )

            color = ANSI.RED if "BLOCKED" in status.value or "FAILED" in status.value else ANSI.GREEN
            print(
                f"  Attempt {i + 1:02d} | Pwd: '{pwd:<10}' | Status: {color}{status.value:<28}{ANSI.RESET} | Latency: {latency:.1f}ms")
            time.sleep(interval_ms / 1000.0)

    def simulate_password_spraying(
            self,
            target_users: List[str],
            attacker_ip: str,
            spray_password: str = "CompanyAutumn2024!"
    ) -> None:
        """Simulates horizontal password spraying across multiple enterprise accounts."""
        print(f"\n{ANSI.BOLD}{ANSI.MAGENTA}[+] LAUNCHING HORIZONTAL PASSWORD SPRAYING ATTACK{ANSI.RESET}")
        print(
            f"Target Roster: {len(target_users)} users | Attacker IP: {ANSI.YELLOW}{attacker_ip}{ANSI.RESET} | Credential: '{spray_password}'")

        for idx, user in enumerate(target_users):
            if self.stop_signal.is_set():
                break
            status, msg, latency = self.auth.authenticate(
                username=user,
                password=spray_password,
                ip_address=attacker_ip,
                user_agent="SprayingBot/3.4 (Automated)"
            )
            color = ANSI.RED if "BLOCKED" in status.value else ANSI.YELLOW
            print(f"  Target: {user:<14} | Result: {color}{status.value:<28}{ANSI.RESET} | Detail: {msg}")
            time.sleep(0.15)

    def simulate_slow_and_low(
            self,
            target_user: str,
            attacker_ip: str,
            cycles: int = 4
    ) -> None:
        """Simulates stealth low-frequency guessing intended to evade sliding windows."""
        print(f"\n{ANSI.BOLD}{ANSI.YELLOW}[+] LAUNCHING SLOW-AND-LOW EVASION ATTACK{ANSI.RESET}")
        print(f"Target: {ANSI.CYAN}{target_user}{ANSI.RESET} | Mode: Interval Spacing > Base Soft Cooldown")

        evasion_passwords = ["Summer2023!", "Winter2023!", "Spring2024!", "Autumn2024!"]
        for i in range(min(cycles, len(evasion_passwords))):
            pwd = evasion_passwords[i]
            status, msg, latency = self.auth.authenticate(
                username=target_user,
                password=pwd,
                ip_address=attacker_ip,
                user_agent="StealthScraper/1.0"
            )
            print(f"  [Cycle {i + 1}] Sent guess '{pwd}' from {attacker_ip} -> {status.value} ({msg})")
            if i < cycles - 1:
                sleep_interval = 2.0  # Simulated condensed cooldown wait
                print(f"  {ANSI.DIM}Waiting {sleep_interval}s before next stealth transmission...{ANSI.RESET}")
                time.sleep(sleep_interval)

    def simulate_legitimate_traffic(
            self,
            credentials: List[Tuple[str, str, str]]
    ) -> None:
        """Simulates authorized enterprise staff accessing system resources with rare typos."""
        print(f"\n{ANSI.BOLD}{ANSI.GREEN}[+] SIMULATING AUTHORIZED EMPLOYEE LOGIN TRAFFIC{ANSI.RESET}")
        for user, correct_pwd, workstation_ip in credentials:
            # 25% chance of an accidental initial typo
            if secrets.randbelow(100) < 25:
                typo_pwd = correct_pwd + "!"
                status, msg, _ = self.auth.authenticate(user, typo_pwd, workstation_ip, "Workstation-OSX/14.2")
                print(
                    f"  User {ANSI.CYAN}{user:<10}{ANSI.RESET} mistyped password! -> {ANSI.YELLOW}{status.value}{ANSI.RESET}")
                time.sleep(0.3)

            # Legitimate successful login
            status, msg, latency = self.auth.authenticate(user, correct_pwd, workstation_ip, "Workstation-OSX/14.2")
            print(
                f"  User {ANSI.CYAN}{user:<10}{ANSI.RESET} entered correct password -> {ANSI.GREEN}{status.value}{ANSI.RESET} ({latency:.1f}ms)")
            time.sleep(0.1)


# ==============================================================================
# 7. FORENSIC TELEMETRY & REPORTING ENGINE
# ==============================================================================

class TelemetryReporter:
    """Generates analytical dashboards, statistical aggregations, and audit dossiers."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_console_dashboard(self) -> None:
        """Displays interactive, color-coded terminal forensic summary."""
        conn = self.db.get_connection()

        total_requests = conn.execute("SELECT COUNT(*) FROM login_logs;").fetchone()[0]
        if total_requests == 0:
            print(f"{ANSI.YELLOW}[!] No audit telemetry records logged.{ANSI.RESET}")
            return

        successes = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE status = ?;",
            (LoginStatus.SUCCESS.value,)
        ).fetchone()[0]

        soft_locks = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE status = ?;",
            (LoginStatus.BLOCKED_ACCOUNT_LOCKED_SOFT.value,)
        ).fetchone()[0]

        hard_locks = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE status = ?;",
            (LoginStatus.BLOCKED_ACCOUNT_LOCKED_HARD.value,)
        ).fetchone()[0]

        ip_rate_blocks = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE status = ?;",
            (LoginStatus.BLOCKED_IP_RATE_LIMITED.value,)
        ).fetchone()[0]

        ip_blacklist_blocks = conn.execute(
            "SELECT COUNT(*) FROM login_logs WHERE status = ?;",
            (LoginStatus.BLOCKED_IP_BLACKLISTED.value,)
        ).fetchone()[0]

        avg_latency = conn.execute("SELECT AVG(injected_delay_ms) FROM login_logs;").fetchone()[0] or 0.0

        total_defended = soft_locks + hard_locks + ip_rate_blocks + ip_blacklist_blocks
        defense_rate = (total_defended / (total_requests - successes) * 100) if (
                                                                                            total_requests - successes) > 0 else 100.0

        print(
            f"\n{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.WHITE}              LOGIN DEFENSE SYSTEM: TELEMETRY & AUDIT METRICS                  {ANSI.RESET}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}")
        print(
            f" Total Logins Processed     : {ANSI.BOLD}{total_requests:<10}{ANSI.RESET} | Successful Logins         : {ANSI.GREEN}{successes}{ANSI.RESET}")
        print(
            f" Total Threats Neutralized   : {ANSI.BOLD}{ANSI.RED}{total_defended:<10}{ANSI.RESET} | Attack Defense Efficiency : {ANSI.CYAN}{defense_rate:.1f}%{ANSI.RESET}")
        print(
            f" Average Response Latency   : {ANSI.BOLD}{avg_latency:.2f} ms{ANSI.RESET}   | Active IP Blacklists      : {ANSI.YELLOW}{self._get_active_ip_bans()}{ANSI.RESET}")
        print(f"--------------------------------------------------------------------------------")
        print(f" Defensive Countermeasure Breakdown:")
        print(f"  • Transient Soft Lockout Interceptions : {ANSI.YELLOW}{soft_locks}{ANSI.RESET}")
        print(f"  • Permanent Hard Administrative Blocks : {ANSI.RED}{hard_locks}{ANSI.RESET}")
        print(f"  • Sliding-Window Rate Limit Throttles  : {ANSI.MAGENTA}{ip_rate_blocks}{ANSI.RESET}")
        print(f"  • Boundary Firewall IP Drops           : {ANSI.RED}{ip_blacklist_blocks}{ANSI.RESET}")
        print(f"--------------------------------------------------------------------------------")

        # User account status table
        print(
            f"{ANSI.BOLD}{'Account Name':<16} | {'Failed Att':<10} | {'Soft Lock Status':<20} | {'Hard Lock Status':<20}{ANSI.RESET}")
        print(f"-" * 78)
        users = conn.execute(
            "SELECT username, failed_attempts, soft_lock_until, hard_lock_until FROM users;").fetchall()
        for u in users:
            soft_str = f"{ANSI.YELLOW}ACTIVE{ANSI.RESET}" if u["soft_lock_until"] else f"{ANSI.GREEN}CLEAN{ANSI.RESET}"
            hard_str = f"{ANSI.RED}LOCKED{ANSI.RESET}" if u["hard_lock_until"] else f"{ANSI.GREEN}CLEAN{ANSI.RESET}"
            print(f" {u['username']:<15} | {u['failed_attempts']:<10} | {soft_str:<29} | {hard_str:<29}")
        print(
            f"{ANSI.BOLD}{ANSI.BLUE}================================================================================{ANSI.RESET}\n")

    def _get_active_ip_bans(self) -> int:
        conn = self.db.get_connection()
        return conn.execute("SELECT COUNT(*) FROM ip_blacklist;").fetchone()[0]

    def export_json_audit_log(self, filepath: str) -> None:
        """Exports raw security event logs to JSON for external SIEM analysis."""
        conn = self.db.get_connection()
        rows = conn.execute("SELECT * FROM login_logs ORDER BY id ASC;").fetchall()
        log_records = [dict(row) for row in rows]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log_records, f, indent=2)
        print(
            f"{ANSI.GREEN}[✓] Forensic audit logs exported successfully to '{filepath}' ({len(log_records)} records).{ANSI.RESET}")


# ==============================================================================
# 8. INTERACTIVE MANAGEMENT INTERFACE & ORCHESTRATOR
# ==============================================================================

class SecurityConsoleApp:
    """Master interactive terminal harness for policy tuning and scenario execution."""

    def __init__(self):
        self.policy = SecurityPolicy()
        self.db = DatabaseManager()
        self.auth = AuthenticationService(self.db, self.policy)
        self.simulator = AttackSimulator(self.auth)
        self.reporter = TelemetryReporter(self.db)
        self._seed_default_identities()

    def _seed_default_identities(self) -> None:
        """Provisions sandbox users with strong initial credentials."""
        self.default_credentials = [
            ("alice", "SecurePassword@123", "192.168.1.101"),
            ("bob", "EnterpriseShield#2024", "192.168.1.102"),
            ("carol", "Correct-Horse-Battery", "192.168.1.103"),
            ("david", "QuantumSafePass!99", "192.168.1.104"),
            ("admin", "SuperSecretRootAdminPass!", "192.168.1.10")
        ]
        for uname, pwd, _ in self.default_credentials:
            self.auth.register_user(uname, pwd)

    def print_menu(self) -> None:
        print(f"\n{ANSI.BOLD}{ANSI.CYAN}--- LOGIN BRUTE-FORCE DEFENSE PLATFORM ---{ANSI.RESET}")
        print(f" 1. Run Complete Automated Simulation (Brute Force + Spray + Legitimate)")
        print(f" 2. Run Targeted Single-Account Brute Force Attack")
        print(f" 3. Run Horizontal Password Spraying Campaign")
        print(f" 4. Run Slow-and-Low Stealth Evasion Attack")
        print(f" 5. Simulate Legitimate Staff Login Traffic")
        print(f" 6. Manual Interactive Login Authentication")
        print(f" 7. View Live Forensic Analytics & Telemetry Dashboard")
        print(f" 8. Reconfigure Security Defenses & Policy Limits")
        print(f" 9. Administratively Unlock an Account / Flush IP Bans")
        print(f"10. Export Security Audit Logs to JSON")
        print(f" 0. Terminate Platform")
        print(f"{ANSI.CYAN}------------------------------------------{ANSI.RESET}")

    def run_interactive(self) -> None:
        print(f"{ANSI.BOLD}{ANSI.GREEN}[✓] Defense Platform Initialized. 5 default accounts provisioned.{ANSI.RESET}")

        while True:
            self.print_menu()
            choice = input(f"{ANSI.BOLD}Select Operation [0-10]: {ANSI.RESET}").strip()

            if choice == "1":
                self._run_all_scenarios()
            elif choice == "2":
                user = input("Target Username (default: alice): ").strip() or "alice"
                ip = input("Attacker IP (default: 198.51.100.55): ").strip() or "198.51.100.55"
                self.simulator.simulate_targeted_brute_force(user, ip, num_attempts=15)
                self.reporter.generate_console_dashboard()
            elif choice == "3":
                targets = ["alice", "bob", "carol", "david", "admin"]
                ip = input("Attacker IP (default: 203.0.113.88): ").strip() or "203.0.113.88"
                self.simulator.simulate_password_spraying(targets, ip)
                self.reporter.generate_console_dashboard()
            elif choice == "4":
                user = input("Target Username (default: bob): ").strip() or "bob"
                ip = input("Attacker IP (default: 192.0.2.77): ").strip() or "192.0.2.77"
                self.simulator.simulate_slow_and_low(user, ip)
                self.reporter.generate_console_dashboard()
            elif choice == "5":
                self.simulator.simulate_legitimate_traffic(self.default_credentials)
                self.reporter.generate_console_dashboard()
            elif choice == "6":
                self._manual_login()
            elif choice == "7":
                self.reporter.generate_console_dashboard()
            elif choice == "8":
                self._tune_security_policy()
            elif choice == "9":
                self._administrative_unlock()
            elif choice == "10":
                filename = input(
                    "Enter export file path (default: security_audit_export.json): ").strip() or "security_audit_export.json"
                self.reporter.export_json_audit_log(filename)
            elif choice == "0":
                print(f"{ANSI.YELLOW}[+] Terminating simulator. Zero residual memory artifacts.{ANSI.RESET}")
                sys.exit(0)
            else:
                print(f"{ANSI.RED}[!] Invalid selection.{ANSI.RESET}")

    def _manual_login(self) -> None:
        print(f"\n{ANSI.BOLD}[*] MANUAL AUTHENTICATION PROMPT{ANSI.RESET}")
        uname = input("Username: ").strip()
        pwd = input("Password: ").strip()
        ip = input("Client IP Address (default: 127.0.0.1): ").strip() or "127.0.0.1"

        status, message, latency = self.auth.authenticate(uname, pwd, ip, "Manual-CLI-Console")
        color = ANSI.GREEN if status == LoginStatus.SUCCESS else ANSI.RED
        print(f"\nResult: {color}{status.value}{ANSI.RESET}")
        print(f"Message: {message}")
        print(f"Response Latency: {latency:.2f} ms")

    def _tune_security_policy(self) -> None:
        print(f"\n{ANSI.BOLD}[*] RECONFIGURE DEFENSE POLICIES{ANSI.RESET}")
        print(f"1. Current Soft Lockout Attempt Threshold: {self.policy.max_failed_attempts_soft}")
        print(f"2. Current Hard Lockout Attempt Threshold: {self.policy.max_failed_attempts_hard}")
        print(f"3. Current IP Sliding-Window Max Requests : {self.policy.ip_max_requests_per_window}")
        print(f"4. Toggle Progressive Latency Delay      : {self.policy.enable_progressive_delay}")

        opt = input("Select policy parameter to modify (1-4) or 'q' to return: ").strip()
        if opt == "1":
            val = int(input("Enter new integer limit: "))
            self.policy.max_failed_attempts_soft = max(1, val)
        elif opt == "2":
            val = int(input("Enter new integer limit: "))
            self.policy.max_failed_attempts_hard = max(self.policy.max_failed_attempts_soft + 1, val)
        elif opt == "3":
            val = int(input("Enter new max requests per window: "))
            self.policy.ip_max_requests_per_window = max(1, val)
        elif opt == "4":
            self.policy.enable_progressive_delay = not self.policy.enable_progressive_delay
            print(f"Progressive delay set to: {self.policy.enable_progressive_delay}")

    def _administrative_unlock(self) -> None:
        print(f"\n{ANSI.BOLD}[*] ADMINISTRATIVE UNLOCK UTILITY{ANSI.RESET}")
        target = input("Enter username to reset lockouts, or 'FLUSH_IPS' to wipe ban list: ").strip()
        if target.upper() == "FLUSH_IPS":
            conn = self.db.get_connection()
            with conn:
                conn.execute("DELETE FROM ip_blacklist;")
            self.auth.governor.clear()
            print(f"{ANSI.GREEN}[✓] All active IP blacklist records purged.{ANSI.RESET}")
        else:
            if self.auth.unlock_account(target):
                print(f"{ANSI.GREEN}[✓] Account '{target}' has been unlocked and failed counters reset.{ANSI.RESET}")
            else:
                print(f"{ANSI.RED}[!] Account '{target}' not found.{ANSI.RESET}")

    def _run_all_scenarios(self) -> None:
        """Runs the entire multi-vector demonstration pipeline."""
        print(f"\n{ANSI.BG_BLUE}{ANSI.WHITE} >>> INITIATING END-TO-END SECURITY WORKLOAD WORKBENCH <<< {ANSI.RESET}")
        # Phase 1: Legitimate traffic
        self.simulator.simulate_legitimate_traffic(self.default_credentials[:3])
        # Phase 2: Brute force target
        self.simulator.simulate_targeted_brute_force("alice", "198.51.100.44", num_attempts=12)
        # Phase 3: Horizontal Spraying
        self.simulator.simulate_password_spraying(["alice", "bob", "carol", "david", "admin"], "203.0.113.99")
        # Phase 4: Slow and low
        self.simulator.simulate_slow_and_low("carol", "192.0.2.111", cycles=3)
        # Phase 5: Display metrics
        self.reporter.generate_console_dashboard()


# ==============================================================================
# 9. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    try:
        app = SecurityConsoleApp()

        # If run non-interactively or with '--auto', execute the test suite and exit
        if len(sys.argv) > 1 and sys.argv[1] in ("--auto", "-a", "--demo"):
            print(f"{ANSI.BOLD}[*] Non-interactive flag detected. Running automated campaign...{ANSI.RESET}")
            app._run_all_scenarios()
            app.reporter.export_json_audit_log("automated_security_audit.json")
            sys.exit(0)

        app.run_interactive()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Interrupted by operator. Session terminated cleanly.{ANSI.RESET}")
        sys.exit(0)
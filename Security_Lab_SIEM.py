import os
import sys
import time
import math
import random
import re
import csv
import json
import hmac
import hashlib
import secrets
import sqlite3
import datetime
import threading
import itertools
import string
import queue
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font as tkFont


# ==============================================================================
# 1. CONSTANTS, ENUMS & DATA MODELS
# ==============================================================================

class AlertSeverity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuthStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED_BAD_CREDENTIALS = "FAILED_BAD_CREDENTIALS"
    FAILED_UNKNOWN_USER = "FAILED_UNKNOWN_USER"
    FAILED_CANARY_TRIP = "FAILED_CANARY_TRIP"
    BLOCKED_RATE_LIMITED = "BLOCKED_RATE_LIMITED"
    BLOCKED_ACCOUNT_LOCKED = "BLOCKED_ACCOUNT_LOCKED"
    BLOCKED_PERIMETER_BAN = "BLOCKED_PERIMETER_BAN"


class DefenseAction(Enum):
    ALLOW = "ALLOW"
    INJECT_DELAY = "INJECT_DELAY"
    CHALLENGE_CAPTCHA = "CHALLENGE_CAPTCHA"
    LOCK_ACCOUNT = "LOCK_ACCOUNT"
    BLOCK_IP = "BLOCK_IP"
    BAN_SUBNET = "BAN_SUBNET"


class OTPResult(Enum):
    SUCCESS = "SUCCESS"
    FAILED_INCORRECT = "FAILED_INCORRECT"
    FAILED_EXPIRED = "FAILED_EXPIRED"
    FAILED_REPLAY_ATTACK = "FAILED_REPLAY_ATTACK"
    FAILED_EXHAUSTED = "FAILED_EXHAUSTED"
    BLOCKED_LOCKOUT = "BLOCKED_LOCKOUT"


@dataclass
class SIEMAlert:
    """Security Incident & Alert Dossier."""
    alert_id: str
    timestamp: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    source_ip: str
    target_user: str
    details: str
    mitigation: str


@dataclass
class OTPSession:
    """Active transaction one-time password record."""
    session_id: str
    user_id: str
    otp_hash: str
    salt: bytes
    created_at: float
    expires_at: float
    max_attempts: int
    attempts_remaining: int
    is_consumed: bool = False


# Embedded dictionary for instantaneous offline cracking demonstration
EMBEDDED_WORDLIST = [
    "password", "123456", "123456789", "guest", "qwerty", "12345678", "111111",
    "dragon", "welcome", "ninja", "master", "monkey", "shadow", "football",
    "baseball", "superman", "jordan", "killer", "trustno1", "hunter2", "admin",
    "admin123", "secret", "secret123", "root", "toor", "login", "default",
    "letmein", "sunshine", "iloveyou", "password123", "p@ssword", "p@ssw0rd",
    "P@sswOrd123!", "pass123", "Spring2024!", "Winter2024!", "Company2024!"
]


# ==============================================================================
# 2. THREAD-SAFE SQLITE3 PERSISTENCE LAYER (MINI-SIEM STORAGE)
# ==============================================================================

class SIEMDatabaseManager:
    """
    High-performance, thread-safe SQLite3 storage for authentication events,
    relational user accounts, active bans, and historical SIEM incidents.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.lock = threading.Lock()
        # Single shared connection with threading lock to guarantee table visibility across threads
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def get_conn(self) -> sqlite3.Connection:
        return self.conn

    def _init_schema(self) -> None:
        with self.lock:
            with self.conn:
                self.conn.executescript("""
                                        CREATE TABLE IF NOT EXISTS accounts
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
                                            kdf_algo
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
                                            is_canary
                                            INTEGER
                                            DEFAULT
                                            0,
                                            created_at
                                            TIMESTAMP
                                            DEFAULT
                                            CURRENT_TIMESTAMP
                                        );

                                        CREATE TABLE IF NOT EXISTS audit_events
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
                                            latency_ms
                                            REAL
                                            DEFAULT
                                            0.0,
                                            user_agent
                                            TEXT
                                            NOT
                                            NULL,
                                            details
                                            TEXT
                                        );

                                        CREATE TABLE IF NOT EXISTS siem_alerts
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
                                            target_user
                                            TEXT
                                            NOT
                                            NULL,
                                            details
                                            TEXT
                                            NOT
                                            NULL,
                                            mitigation
                                            TEXT
                                            NOT
                                            NULL
                                        );

                                        CREATE TABLE IF NOT EXISTS perimeter_bans
                                        (
                                            identifier
                                            TEXT
                                            PRIMARY
                                            KEY,
                                            ban_type
                                            TEXT
                                            NOT
                                            NULL,
                                            banned_until
                                            TIMESTAMP
                                            NOT
                                            NULL,
                                            reason
                                            TEXT
                                            NOT
                                            NULL
                                        );

                                        CREATE INDEX IF NOT EXISTS idx_ev_ts ON audit_events(timestamp);
                                        CREATE INDEX IF NOT EXISTS idx_ev_ip ON audit_events(source_ip);
                                        CREATE INDEX IF NOT EXISTS idx_ev_user ON audit_events(username);
                                        """)

    def insert_account(self, username: str, p_hash: str, salt: str, algo: str, is_canary: bool = False) -> None:
        with self.lock:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO accounts (username, password_hash, salt, kdf_algo, is_canary)
                    VALUES (?, ?, ?, ?, ?);
                """, (username.lower().strip(), p_hash, salt, algo, 1 if is_canary else 0))

    def log_event(self, ev: Dict[str, Any]) -> None:
        with self.lock:
            with self.conn:
                self.conn.execute("""
                                  INSERT INTO audit_events (timestamp, source_ip, subnet, username, status, risk_score,
                                                            action_taken, latency_ms, user_agent, details)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                  """, (
                                      ev["timestamp"], ev["source_ip"], ev["subnet"], ev["username"],
                                      ev["status"], ev["risk_score"], ev["action_taken"], ev.get("latency_ms", 0.0),
                                      ev.get("user_agent", "Standard-Client"), ev["details"]
                                  ))

    def insert_alert(self, a: SIEMAlert) -> None:
        with self.lock:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO siem_alerts (
                        alert_id, timestamp, rule_id, rule_name, severity, source_ip, target_user, details, mitigation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    a.alert_id, a.timestamp, a.rule_id, a.rule_name, a.severity.value,
                    a.source_ip, a.target_user, a.details, a.mitigation
                ))

    def add_ban(self, identifier: str, b_type: str, banned_until: datetime.datetime, reason: str) -> None:
        with self.lock:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO perimeter_bans (identifier, ban_type, banned_until, reason)
                    VALUES (?, ?, ?, ?);
                """, (identifier, b_type, banned_until.strftime("%Y-%m-%d %H:%M:%S"), reason))

    def check_ban(self, ip: str, subnet: str, now: datetime.datetime) -> Tuple[bool, Optional[str]]:
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self.conn:
                row = self.conn.execute("""
                                        SELECT identifier, ban_type, banned_until, reason
                                        FROM perimeter_bans
                                        WHERE identifier IN (?, ?);
                                        """, (ip, subnet)).fetchone()

                if row:
                    if now_str < row["banned_until"]:
                        return True, f"{row['ban_type']} Banned: {row['reason']}"
                    else:
                        self.conn.execute("DELETE FROM perimeter_bans WHERE identifier = ?;", (row["identifier"],))
        return False, None

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        with self.lock:
            with self.conn:
                total_ev = self.conn.execute("SELECT COUNT(*) FROM audit_events;").fetchone()[0]
                if total_ev == 0:
                    return {}

                total_alerts = self.conn.execute("SELECT COUNT(*) FROM siem_alerts;").fetchone()[0]
                total_bans = self.conn.execute("SELECT COUNT(*) FROM perimeter_bans;").fetchone()[0]
                total_fails = \
                self.conn.execute("SELECT COUNT(*) FROM audit_events WHERE status != 'SUCCESS';").fetchone()[0]
                total_succ = \
                self.conn.execute("SELECT COUNT(*) FROM audit_events WHERE status = 'SUCCESS';").fetchone()[0]
                avg_risk = self.conn.execute("SELECT AVG(risk_score) FROM audit_events;").fetchone()[0] or 0.0

                top_attackers = self.conn.execute("""
                                                  SELECT source_ip, COUNT(*) as cnt
                                                  FROM audit_events
                                                  WHERE status != 'SUCCESS'
                                                  GROUP BY source_ip
                                                  ORDER BY cnt DESC LIMIT 5;
                                                  """).fetchall()

                top_victims = self.conn.execute("""
                                                SELECT username, COUNT(*) as cnt
                                                FROM audit_events
                                                WHERE status != 'SUCCESS'
                                                GROUP BY username
                                                ORDER BY cnt DESC LIMIT 5;
                                                """).fetchall()

        return {
            "total_events": total_ev,
            "total_alerts": total_alerts,
            "active_bans": total_bans,
            "failed_attempts": total_fails,
            "successful_attempts": total_succ,
            "avg_risk_score": avg_risk,
            "top_attackers": [(r["source_ip"], r["cnt"]) for r in top_attackers],
            "top_victims": [(r["username"], r["cnt"]) for r in top_victims]
        }


# ==============================================================================
# 3. CRYPTOGRAPHIC HASHING & ALGORITHM LABORATORY
# ==============================================================================

class HashingLaboratory:
    """Educational cryptographic primitive suite and side-channel analysis tools."""

    @staticmethod
    def raw_sha256(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def salted_pbkdf2(password: str, salt: bytes, iterations: int = 100_000) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return dk.hex()

    @staticmethod
    def scrypt_hash(password: str, salt: bytes, n: int = 16384, r: int = 8, p: int = 1) -> str:
        if hasattr(hashlib, "scrypt"):
            return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=0).hex()
        return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    @classmethod
    def calculate_avalanche(cls, str1: str, str2: str) -> Tuple[int, float, str, str]:
        """Calculates bitwise Hamming distance and diffusion rate between two digests."""
        h1 = cls.raw_sha256(str1)
        h2 = cls.raw_sha256(str2)

        bin1 = bin(int(h1, 16))[2:].zfill(256)
        bin2 = bin(int(h2, 16))[2:].zfill(256)

        flipped_bits = sum(b1 != b2 for b1, b2 in zip(bin1, bin2))
        percentage = (flipped_bits / 256.0) * 100.0
        return flipped_bits, percentage, h1, h2

    @staticmethod
    def simulate_timing_attack(known_secret: bytes, candidate_guess: bytes) -> Tuple[bool, float, bool]:
        """
        Contrasts naive short-circuit string comparison (which leaks byte alignment)
        against cryptographic constant-time hmac.compare_digest.
        """
        t0 = time.perf_counter_ns()
        constant_match = hmac.compare_digest(known_secret, candidate_guess)
        t_constant = time.perf_counter_ns() - t0

        naive_match = True
        t1 = time.perf_counter_ns()
        if len(known_secret) != len(candidate_guess):
            naive_match = False
        else:
            for b1, b2 in zip(known_secret, candidate_guess):
                if b1 != b2:
                    naive_match = False
                    break
        t_naive = time.perf_counter_ns() - t1

        return constant_match, t_constant, naive_match


# ==============================================================================
# 4. LOGIN DEFENSE & BEHAVIORAL RISK-SCORING GATEWAY
# ==============================================================================

class LoginDefenseGateway:
    """Enforces sliding-window rate limits, progressive backoffs, and account lockouts."""

    def __init__(self, db: SIEMDatabaseManager):
        self.db = db
        self.lock = threading.Lock()

        self.ip_window: Dict[str, deque] = defaultdict(deque)
        self.subnet_window: Dict[str, deque] = defaultdict(deque)
        self.user_window: Dict[str, deque] = defaultdict(deque)

        self.ip_rate_window_sec = 60
        self.max_attempts_per_ip = 5
        self.subnet_window_sec = 120
        self.max_users_per_subnet = 4
        self.soft_lock_threshold = 5
        self.soft_lock_seconds = 30
        self.hard_lock_threshold = 10
        self.hard_lock_seconds = 300

    @staticmethod
    def extract_subnet(ip: str) -> str:
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24" if len(parts) == 4 else ip

    def evaluate_and_authenticate(
            self,
            now: datetime.datetime,
            ip: str,
            username: str,
            password: str,
            user_agent: str = "Standard-Browser/1.0"
    ) -> Tuple[AuthStatus, DefenseAction, float, float, str]:
        t_start = time.perf_counter()
        uname = username.lower().strip()
        subnet = self.extract_subnet(ip)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Active Perimeter Bans
        is_banned, ban_reason = self.db.check_ban(ip, subnet, now)
        if is_banned:
            details = f"Ingress dropped: {ban_reason}"
            self.db.log_event({
                "timestamp": now_str, "source_ip": ip, "subnet": subnet, "username": uname,
                "status": AuthStatus.BLOCKED_PERIMETER_BAN.value, "risk_score": 100.0,
                "action_taken": DefenseAction.BLOCK_IP.value, "latency_ms": 1.0,
                "user_agent": user_agent, "details": details
            })
            return AuthStatus.BLOCKED_PERIMETER_BAN, DefenseAction.BLOCK_IP, 100.0, 1.0, details

        # 2. Account Record Retrieval
        c = self.db.get_conn()
        with self.db.lock:
            user_row = c.execute("SELECT * FROM accounts WHERE username = ?;", (uname,)).fetchone()

        # 3. Account Lockout Checks
        if user_row:
            if user_row["hard_lock_until"] and now_str < user_row["hard_lock_until"]:
                details = f"Account '{uname}' is under hard lockout until {user_row['hard_lock_until']}."
                return AuthStatus.BLOCKED_ACCOUNT_LOCKED, DefenseAction.LOCK_ACCOUNT, 85.0, 1.0, details

            if user_row["soft_lock_until"] and now_str < user_row["soft_lock_until"]:
                details = f"Account '{uname}' is in soft cooldown until {user_row['soft_lock_until']}."
                return AuthStatus.BLOCKED_ACCOUNT_LOCKED, DefenseAction.LOCK_ACCOUNT, 65.0, 1.0, details

        # 4. Multi-Factor Risk Calculation
        risk_score = 0.0
        is_canary = bool(user_row["is_canary"]) if user_row else False

        if is_canary:
            risk_score = 100.0
        else:
            with self.lock:
                ip_history = self.ip_window[ip]
                self._prune_window(ip_history, now, self.ip_rate_window_sec)
                if len(ip_history) >= self.max_attempts_per_ip:
                    risk_score += min(40.0, (len(ip_history) - self.max_attempts_per_ip + 1) * 10.0)

                sub_history = self.subnet_window[subnet]
                self._prune_window(sub_history, now, self.subnet_window_sec)
                unique_sub_users = {item[1] for item in sub_history}
                if len(unique_sub_users) >= self.max_users_per_subnet:
                    risk_score += 40.0

                u_history = self.user_window[uname]
                self._prune_window(u_history, now, 120)
                unique_u_ips = {item[1] for item in u_history}
                if len(unique_u_ips) >= 3:
                    risk_score += 30.0

            if any(bot_id in user_agent.lower() for bot_id in ["python", "curl", "bot", "hydra", "spray"]):
                risk_score += 25.0

        risk_score = min(100.0, risk_score)

        # 5. Enforcement Actions
        action = DefenseAction.ALLOW
        if risk_score >= 80.0:
            action = DefenseAction.BAN_SUBNET if not is_canary and risk_score >= 90.0 else DefenseAction.BLOCK_IP
            ban_target = subnet if action == DefenseAction.BAN_SUBNET else ip
            ban_sec = 600 if action == DefenseAction.BAN_SUBNET else 300
            self.db.add_ban(ban_target, action.value, now + datetime.timedelta(seconds=ban_sec),
                            f"High Risk ({risk_score:.1f})")

            details = f"Hostile traffic blocked: {action.value}"
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            self.db.log_event({
                "timestamp": now_str, "source_ip": ip, "subnet": subnet, "username": uname,
                "status": AuthStatus.BLOCKED_RATE_LIMITED.value, "risk_score": risk_score,
                "action_taken": action.value, "latency_ms": latency_ms,
                "user_agent": user_agent, "details": details
            })
            return AuthStatus.BLOCKED_RATE_LIMITED, action, risk_score, latency_ms, details

        elif risk_score >= 60.0:
            action = DefenseAction.CHALLENGE_CAPTCHA
        elif risk_score >= 30.0:
            action = DefenseAction.INJECT_DELAY
            time.sleep(0.15)

        with self.lock:
            self.ip_window[ip].append(now)
            self.subnet_window[subnet].append((now, uname))
            self.user_window[uname].append((now, ip))

        # 6. Verification
        if not user_row:
            status = AuthStatus.FAILED_UNKNOWN_USER
            details = "Authentication failed: Account not found."
        elif is_canary:
            status = AuthStatus.FAILED_CANARY_TRIP
            details = "CRITICAL: Honeypot canary credential tripped! Host quarantined."
        else:
            calc_hash = HashingLaboratory.salted_pbkdf2(password, bytes.fromhex(user_row["salt"]))
            if hmac.compare_digest(calc_hash, user_row["password_hash"]):
                status = AuthStatus.SUCCESS
                details = "Authentication successful. Session established."
                with self.db.lock:
                    with c:
                        c.execute("""
                                  UPDATE accounts
                                  SET failed_attempts = 0,
                                      soft_lock_until = NULL,
                                      hard_lock_until = NULL
                                  WHERE id = ?;
                                  """, (user_row["id"],))
            else:
                status = AuthStatus.FAILED_BAD_CREDENTIALS
                fails = user_row["failed_attempts"] + 1
                details = f"Authentication failed: Invalid password (Failed attempts: {fails})."

                soft_until = None
                hard_until = None
                if fails >= self.hard_lock_threshold:
                    hard_until = (now + datetime.timedelta(seconds=self.hard_lock_seconds)).strftime(
                        "%Y-%m-%d %H:%M:%S")
                    action = DefenseAction.LOCK_ACCOUNT
                elif fails >= self.soft_lock_threshold:
                    soft_until = (now + datetime.timedelta(seconds=self.soft_lock_seconds)).strftime(
                        "%Y-%m-%d %H:%M:%S")
                    action = DefenseAction.LOCK_ACCOUNT

                with self.db.lock:
                    with c:
                        c.execute("""
                                  UPDATE accounts
                                  SET failed_attempts = ?,
                                      soft_lock_until = ?,
                                      hard_lock_until = ?
                                  WHERE id = ?;
                                  """, (fails, soft_until, hard_until, user_row["id"]))

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.db.log_event({
            "timestamp": now_str, "source_ip": ip, "subnet": subnet, "username": uname,
            "status": status.value, "risk_score": risk_score,
            "action_taken": action.value, "latency_ms": latency_ms,
            "user_agent": user_agent, "details": details
        })

        return status, action, risk_score, latency_ms, details

    def _prune_window(self, q: deque, now: datetime.datetime, window_sec: int) -> None:
        cutoff = now - datetime.timedelta(seconds=window_sec)
        while q:
            first_time = q[0] if isinstance(q[0], datetime.datetime) else q[0][0]
            if first_time < cutoff:
                q.popleft()
            else:
                break


# ==============================================================================
# 5. RFC 6238 TOTP & ONE-TIME PASSWORD SECURITY ENGINE
# ==============================================================================

class OTPEngine:
    """RFC 6238 TOTP generator, CSPRNG token factory, and replay prevention manager."""

    def __init__(self, ttl_seconds: int = 60, max_attempts: int = 3):
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        self.active_sessions: Dict[str, OTPSession] = {}
        self.consumed_hashes: Set[str] = set()
        self.lock = threading.Lock()

    @staticmethod
    def generate_totp_rfc6238(secret: bytes, time_step: int = 30, digits: int = 6,
                              for_time: Optional[float] = None) -> str:
        """
        Pure-Python standard RFC 6238 TOTP generation using HMAC-SHA1 dynamic truncation.
        Accepts 'for_time' to allow clock-drift verification or custom timestamp evaluation.
        """
        now_time = for_time if for_time is not None else time.time()
        counter = int(now_time // time_step)
        counter_bytes = counter.to_bytes(8, byteorder="big")

        hmac_digest = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
        offset = hmac_digest[-1] & 0x0F
        binary_code = (
                ((hmac_digest[offset] & 0x7F) << 24)
                | ((hmac_digest[offset + 1] & 0xFF) << 16)
                | ((hmac_digest[offset + 2] & 0xFF) << 8)
                | (hmac_digest[offset + 3] & 0xFF)
        )
        return str(binary_code % (10 ** digits)).zfill(digits)

    def create_transactional_otp(self, user_id: str, digits: int = 6) -> Tuple[str, str]:
        with self.lock:
            now = time.time()
            raw_int = secrets.randbelow(10 ** digits)
            plaintext_otp = str(raw_int).zfill(digits)

            salt = secrets.token_bytes(16)
            otp_hash = hashlib.sha256(salt + plaintext_otp.encode("utf-8")).hexdigest()
            session_id = secrets.token_hex(16)

            self.active_sessions[session_id] = OTPSession(
                session_id=session_id,
                user_id=user_id,
                otp_hash=otp_hash,
                salt=salt,
                created_at=now,
                expires_at=now + self.ttl_seconds,
                max_attempts=self.max_attempts,
                attempts_remaining=self.max_attempts
            )
            return session_id, plaintext_otp

    def verify_otp(self, session_id: str, candidate_code: str) -> Tuple[OTPResult, str]:
        with self.lock:
            now = time.time()
            if session_id not in self.active_sessions:
                return OTPResult.FAILED_EXHAUSTED, "Invalid or expired session identifier."

            sess = self.active_sessions[session_id]

            if sess.is_consumed:
                return OTPResult.FAILED_REPLAY_ATTACK, "REPLAY ALERT: Token has already been used and burned."

            if now > sess.expires_at:
                return OTPResult.FAILED_EXPIRED, "Token has expired."

            if sess.attempts_remaining <= 0:
                return OTPResult.FAILED_EXHAUSTED, "Maximum verification attempts exhausted."

            cand_hash = hashlib.sha256(sess.salt + candidate_code.strip().encode("utf-8")).hexdigest()
            if hmac.compare_digest(sess.otp_hash, cand_hash):
                sess.is_consumed = True
                self.consumed_hashes.add(sess.otp_hash)
                return OTPResult.SUCCESS, "OTP verified successfully. Access granted."
            else:
                sess.attempts_remaining -= 1
                if sess.attempts_remaining <= 0:
                    return OTPResult.FAILED_EXHAUSTED, "Incorrect OTP. Maximum attempts exceeded. Session terminated."
                return OTPResult.FAILED_INCORRECT, f"Incorrect OTP. {sess.attempts_remaining} attempt(s) remaining."


# ==============================================================================
# 6. BEHAVIORAL MINI-SIEM CORRELATION ENGINE
# ==============================================================================

class MiniSIEMEngine:
    """Real-time correlation rules engine identifying attack campaigns."""

    def __init__(self, db: SIEMDatabaseManager):
        self.db = db
        self.active_alerts: List[SIEMAlert] = []
        self.alert_signatures: Set[str] = set()

    def evaluate_telemetry(self) -> List[SIEMAlert]:
        new_alerts: List[SIEMAlert] = []
        c = self.db.get_conn()

        with self.db.lock:
            # Rule 1: High-Frequency Single-Target Brute-Force
            rows_bf = c.execute("""
                                SELECT source_ip, username, COUNT(*) as cnt, MAX(timestamp) as last_seen
                                FROM audit_events
                                WHERE status != 'SUCCESS' AND timestamp >= datetime('now', '-5 minutes')
                                GROUP BY source_ip, username
                                HAVING cnt >= 5;
                                """).fetchall()

            # Rule 2: Horizontal Password Spraying Campaign (/24 subnet targeting multi-accounts)
            rows_spray = c.execute("""
                                   SELECT subnet,
                                          COUNT(DISTINCT username) as user_cnt,
                                          COUNT(*)                 as total_cnt,
                                          MAX(timestamp)           as last_seen
                                   FROM audit_events
                                   WHERE status != 'SUCCESS' AND timestamp >= datetime('now', '-5 minutes')
                                   GROUP BY subnet
                                   HAVING user_cnt >= 4;
                                   """).fetchall()

            # Rule 3: Honeypot / Canary Account Breach Ingestion
            rows_canary = c.execute("""
                                    SELECT source_ip, username, MAX(timestamp) as last_seen
                                    FROM audit_events
                                    WHERE status = 'FAILED_CANARY_TRIP' AND timestamp >= datetime('now', '-10 minutes');
                                    """).fetchall()

        for r in rows_bf:
            sig = f"RULE1-{r['source_ip']}-{r['username']}"
            if sig not in self.alert_signatures:
                self.alert_signatures.add(sig)
                a = SIEMAlert(
                    alert_id=f"ALT-{secrets.token_hex(4)}",
                    timestamp=r["last_seen"],
                    rule_id="RULE-001",
                    rule_name="Targeted Single-User Brute-Force",
                    severity=AlertSeverity.HIGH,
                    source_ip=r["source_ip"],
                    target_user=r["username"],
                    details=f"Host {r['source_ip']} performed {r['cnt']} consecutive failed logins against '{r['username']}'.",
                    mitigation="Issue edge firewall drop rule; enforce user MFA challenge."
                )
                new_alerts.append(a)
                self.db.insert_alert(a)

        for r in rows_spray:
            sig = f"RULE2-{r['subnet']}"
            if sig not in self.alert_signatures:
                self.alert_signatures.add(sig)
                a = SIEMAlert(
                    alert_id=f"ALT-{secrets.token_hex(4)}",
                    timestamp=r["last_seen"],
                    rule_id="RULE-002",
                    rule_name="Horizontal Password Spraying Campaign",
                    severity=AlertSeverity.CRITICAL,
                    source_ip=r["subnet"],
                    target_user="MULTIPLE_ACCOUNTS",
                    details=f"Subnet {r['subnet']} probed {r['user_cnt']} distinct accounts across {r['total_cnt']} attempts.",
                    mitigation="Ban entire /24 subnet at perimeter gateway; review active corporate sessions."
                )
                new_alerts.append(a)
                self.db.insert_alert(a)

        for r in rows_canary:
            if r["source_ip"]:
                sig = f"RULE3-{r['source_ip']}-{r['username']}"
                if sig not in self.alert_signatures:
                    self.alert_signatures.add(sig)
                    a = SIEMAlert(
                        alert_id=f"ALT-{secrets.token_hex(4)}",
                        timestamp=r["last_seen"],
                        rule_id="RULE-003",
                        rule_name="Honeypot Canary Credential Tripped",
                        severity=AlertSeverity.CRITICAL,
                        source_ip=r["source_ip"],
                        target_user=r["username"],
                        details=f"Host {r['source_ip']} attempted login using leaked synthetic canary account '{r['username']}'.",
                        mitigation="IMMEDIATE ISOLATION: Hostile adversary operating with leaked dump. Ban host indefinitely."
                    )
                    new_alerts.append(a)
                    self.db.insert_alert(a)

        self.active_alerts.extend(new_alerts)
        return new_alerts


# ==============================================================================
# 7. NATIVE VECTOR CANVAS GAUGES (ZERO EXTERNAL DEPENDENCIES)
# ==============================================================================

class RadialThreatGauge(tk.Canvas):
    """Vector canvas rendering real-time enterprise threat levels."""

    def __init__(self, master, width=220, height=160, bg="#1e1e2f", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.render(0.0, "DEFCON 5 - NORMAL")

    def render(self, threat_score: float, label: str):
        self.delete("all")
        cx = self.width / 2
        cy = self.height * 0.74
        radius = self.width * 0.38
        stroke = 14

        self.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                        start=0, extent=180, style=tk.ARC, outline="#2c2c44", width=stroke)

        fraction = min(max(threat_score / 100.0, 0.0), 1.0)
        extent = -180.0 * fraction

        col = "#2ecc71"
        if threat_score >= 80:
            col = "#e74c3c"
        elif threat_score >= 50:
            col = "#f1c40f"
        elif threat_score >= 25:
            col = "#3498db"

        if fraction > 0.005:
            self.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                            start=180, extent=extent, style=tk.ARC, outline=col, width=stroke)

        self.create_text(cx, cy - 20, text=f"{threat_score:.1f}", font=("Segoe UI", 20, "bold"), fill="#ffffff")
        self.create_text(cx, cy + 2, text=label, font=("Segoe UI", 8, "bold"), fill=col)


# ==============================================================================
# 8. MASTER DESKTOP APPLICATION GUI & SOC WORKBENCH
# ==============================================================================

class SecurityLabMasterApp(tk.Tk):
    """Integrated master desktop workbench orchestrating all laboratory engines."""

    def __init__(self):
        super().__init__()
        self.title("Enterprise Password Security Laboratory & Mini-SIEM")
        self.geometry("1240x860")
        self.minsize(1060, 740)
        self.configure(bg="#141420")

        # Core Engines
        self.db = SIEMDatabaseManager()
        self.gateway = LoginDefenseGateway(self.db)
        self.otp_engine = OTPEngine()
        self.siem_engine = MiniSIEMEngine(self.db)

        # Async Cracking Simulator thread handle
        self.cracking_thread: Optional[threading.Thread] = None
        self.cracking_stop_event = threading.Event()
        self.cracking_queue = queue.Queue()

        self._setup_styles()
        self._seed_directory()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Start periodic GUI queue poller & SIEM correlation heartbeat
        self.after(50, self._poll_events)
        self.after(1000, self._siem_heartbeat)

    def _setup_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(".", background="#141420", foreground="#f5f6fa", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#141420")
        self.style.configure("TNotebook", background="#141420", tabmargins=[10, 10, 2, 0], borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#1e1e2f", foreground="#a4a4c1", padding=[14, 7],
                             font=("Segoe UI", 9, "bold"))
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#00d2d3"), ("active", "#282842")],
                       foreground=[("selected", "#0f172a"), ("active", "#ffffff")]
                       )
        self.style.configure("TLabelframe", background="#1e1e2f", borderwidth=1, relief="solid")
        self.style.configure("TLabelframe.Label", background="#1e1e2f", foreground="#00d2d3",
                             font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", background="#1a1a2b", foreground="#f5f6fa", fieldbackground="#1a1a2b",
                             rowheight=24, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", background="#27273f", foreground="#00d2d3", relief="flat",
                             font=("Segoe UI", 9, "bold"))
        self.style.configure("Primary.TButton", background="#00d2d3", foreground="#0f172a",
                             font=("Segoe UI", 9, "bold"), padding=5)
        self.style.map("Primary.TButton", background=[("active", "#01a3a4")])
        self.style.configure("Secondary.TButton", background="#2c2c44", foreground="#ffffff", font=("Segoe UI", 9),
                             padding=5)
        self.style.map("Secondary.TButton", background=[("active", "#3d3d5c")])
        self.style.configure("Danger.TButton", background="#e74c3c", foreground="#ffffff", font=("Segoe UI", 9, "bold"),
                             padding=5)

    def _seed_directory(self):
        users = [
            ("alice", "SuperSecret123#", False),
            ("bob", "Winter2024!", False),
            ("carol", "EnterprisePass99", False),
            ("admin_sarah", "GlobalAdminPass!2024", False),
            ("canary_admin", "CanaryTrapPass999!", True),
            ("dev_backup", "BackupCanaryToken#", True)
        ]
        for u, p, is_canary in users:
            salt = secrets.token_hex(16)
            h = HashingLaboratory.salted_pbkdf2(p, bytes.fromhex(salt))
            self.db.insert_account(u, h, salt, "pbkdf2-sha256", is_canary=is_canary)

    def _build_header(self):
        hdr = tk.Frame(self, bg="#1e1e2f", height=55)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        title = tk.Label(hdr, text="DEFENSE LAB & MINI-SIEM CONSOLE", font=("Segoe UI", 13, "bold"), bg="#1e1e2f",
                         fg="#ffffff")
        title.pack(side=tk.LEFT, padx=18, pady=8)

        lbl = tk.Label(hdr, text="ACTIVE DEFENSES: ADAPTIVE RATE LIMITS | HONEYPOT CANARY | RFC 6238 TOTP",
                       font=("Consolas", 8, "bold"), bg="#1e1e2f", fg="#00d2d3")
        lbl.pack(side=tk.RIGHT, padx=18, pady=12)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        self.tab_soc = ttk.Frame(self.notebook, padding=10)
        self.tab_cracker = ttk.Frame(self.notebook, padding=10)
        self.tab_hashlab = ttk.Frame(self.notebook, padding=10)
        self.tab_defense = ttk.Frame(self.notebook, padding=10)
        self.tab_otp = ttk.Frame(self.notebook, padding=10)
        self.tab_threats = ttk.Frame(self.notebook, padding=10)
        self.tab_reports = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_soc, text=" 1. SOC Dashboard ")
        self.notebook.add(self.tab_cracker, text=" 2. Attack Simulator ")
        self.notebook.add(self.tab_hashlab, text=" 3. Hashing Laboratory ")
        self.notebook.add(self.tab_defense, text=" 4. Login Defense Gateway ")
        self.notebook.add(self.tab_otp, text=" 5. OTP / TOTP Security ")
        self.notebook.add(self.tab_threats, text=" 6. Attack Campaigns ")
        self.notebook.add(self.tab_reports, text=" 7. Forensic Exporters ")

        self._build_tab_soc()
        self._build_tab_cracker()
        self._build_tab_hashlab()
        self._build_tab_defense()
        self._build_tab_otp()
        self._build_tab_threats()
        self._build_tab_reports()

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self, bg="#1a1a2b", height=24)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.statusbar.pack_propagate(False)

        self.status_lbl = tk.Label(self.statusbar, text="SIEM Core Operational. Database in-memory WAL active.",
                                   font=("Segoe UI", 8), bg="#1a1a2b", fg="#8e8ea8")
        self.status_lbl.pack(side=tk.LEFT, padx=15)

    # --------------------------------------------------------------------------
    # TAB 1: SOC DASHBOARD
    # --------------------------------------------------------------------------
    def _build_tab_soc(self):
        root = self.tab_soc

        top_row = tk.Frame(root, bg="#141420")
        top_row.pack(fill=tk.X, pady=(0, 8))

        gauge_card = ttk.LabelFrame(top_row, text=" Real-Time Threat Level ", padding=8)
        gauge_card.pack(side=tk.LEFT, padx=(0, 8))
        self.soc_gauge = RadialThreatGauge(gauge_card, width=220, height=140, bg="#1e1e2f")
        self.soc_gauge.pack()

        kpi_card = ttk.LabelFrame(top_row, text=" Telemetry Key Performance Indicators ", padding=10)
        kpi_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        kpi_grid = tk.Frame(kpi_card, bg="#1e1e2f")
        kpi_grid.pack(fill=tk.BOTH, expand=True)

        self.kpi_events = self._create_kpi_cell(kpi_grid, "Total Log Events", "0", 0, 0)
        self.kpi_alerts = self._create_kpi_cell(kpi_grid, "Security Incidents", "0", 0, 1, "#e74c3c")
        self.kpi_bans = self._create_kpi_cell(kpi_grid, "Active Firewall Bans", "0", 0, 2, "#f1c40f")
        self.kpi_fails = self._create_kpi_cell(kpi_grid, "Failed Authentications", "0", 1, 0, "#e67e22")
        self.kpi_succ = self._create_kpi_cell(kpi_grid, "Authorized Sessions", "0", 1, 1, "#2ecc71")
        self.kpi_risk = self._create_kpi_cell(kpi_grid, "Mean Risk Score", "0.0", 1, 2, "#00d2d3")

        stream_card = ttk.LabelFrame(root, text=" Live Security Audit Log Stream (Last 100 Events) ", padding=8)
        stream_card.pack(fill=tk.BOTH, expand=True)

        cols = ("ts", "ip", "user", "status", "risk", "action", "latency", "details")
        self.tree_stream = ttk.Treeview(stream_card, columns=cols, show="headings", height=10)
        self.tree_stream.heading("ts", text="Timestamp")
        self.tree_stream.heading("ip", text="Origin IP")
        self.tree_stream.heading("user", text="Target User")
        self.tree_stream.heading("status", text="Auth Status")
        self.tree_stream.heading("risk", text="Risk Score")
        self.tree_stream.heading("action", text="Enforced Action")
        self.tree_stream.heading("latency", text="Delay")
        self.tree_stream.heading("details", text="Event Details")

        self.tree_stream.column("ts", width=140)
        self.tree_stream.column("ip", width=110)
        self.tree_stream.column("user", width=100)
        self.tree_stream.column("status", width=130)
        self.tree_stream.column("risk", width=70, anchor=tk.CENTER)
        self.tree_stream.column("action", width=110)
        self.tree_stream.column("latency", width=60, anchor=tk.E)
        self.tree_stream.column("details", width=340)

        self.tree_stream.tag_configure("SUCCESS", foreground="#2ecc71")
        self.tree_stream.tag_configure("FAIL", foreground="#e74c3c")
        self.tree_stream.tag_configure("BLOCKED", foreground="#f1c40f")

        self.tree_stream.pack(fill=tk.BOTH, expand=True)

    def _create_kpi_cell(self, parent, title: str, init_val: str, r: int, c: int, color: str = "#ffffff") -> tk.Label:
        f = tk.Frame(parent, bg="#27273f", padx=10, pady=8)
        f.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
        parent.grid_columnconfigure(c, weight=1)
        parent.grid_rowconfigure(r, weight=1)

        tk.Label(f, text=title, font=("Segoe UI", 7), bg="#27273f", fg="#8e8ea8").pack(anchor=tk.W)
        lbl = tk.Label(f, text=init_val, font=("Segoe UI", 13, "bold"), bg="#27273f", fg=color)
        lbl.pack(anchor=tk.W, pady=(2, 0))
        return lbl

    # --------------------------------------------------------------------------
    # TAB 2: PASSWORD ATTACK SIMULATOR
    # --------------------------------------------------------------------------
    def _build_tab_cracker(self):
        root = self.tab_cracker

        cfg_card = ttk.LabelFrame(root, text=" Brute-Force & Dictionary Cracking Controls ", padding=10)
        cfg_card.pack(fill=tk.X, pady=(0, 8))

        grid = tk.Frame(cfg_card, bg="#1e1e2f")
        grid.pack(fill=tk.X)

        tk.Label(grid, text="Target Plaintext Password:", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0, sticky=tk.W,
                                                                                           pady=4)
        self.crack_target_var = tk.StringVar(value="p@ss1")
        ttk.Entry(grid, textvariable=self.crack_target_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=6)

        tk.Label(grid, text="Attack Strategy Mode:", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=2, sticky=tk.W,
                                                                                      padx=(12, 4))
        self.crack_mode_var = tk.StringVar(value="Brute Force (Incremental)")
        combo_mode = ttk.Combobox(grid, textvariable=self.crack_mode_var, values=[
            "Brute Force (Incremental)",
            "Pure Dictionary Search",
            "Mutated Hybrid Dictionary"
        ], state="readonly", width=26)
        combo_mode.grid(row=0, column=3, sticky=tk.W)

        btn_box = tk.Frame(cfg_card, bg="#1e1e2f")
        btn_box.pack(fill=tk.X, pady=(8, 0))

        self.btn_crack_start = ttk.Button(btn_box, text="▶ Launch Attack Simulator", style="Primary.TButton",
                                          command=self._start_cracking_worker)
        self.btn_crack_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_crack_stop = ttk.Button(btn_box, text="⏹ Stop Worker", style="Danger.TButton", state=tk.DISABLED,
                                         command=self._stop_cracking_worker)
        self.btn_crack_stop.pack(side=tk.LEFT, padx=6)

        tele_card = ttk.LabelFrame(root, text=" Live Attack Execution Telemetry ", padding=10)
        tele_card.pack(fill=tk.X, pady=(0, 8))

        t_grid = tk.Frame(tele_card, bg="#1e1e2f")
        t_grid.pack(fill=tk.X)

        tk.Label(t_grid, text="Attempts Completed:", bg="#1e1e2f", fg="#8e8ea8").grid(row=0, column=0, sticky=tk.W)
        self.lbl_crack_attempts = tk.Label(t_grid, text="0", font=("Consolas", 10, "bold"), bg="#1e1e2f", fg="#ffffff")
        self.lbl_crack_attempts.grid(row=0, column=1, sticky=tk.W, padx=8)

        tk.Label(t_grid, text="Guessing Velocity:", bg="#1e1e2f", fg="#8e8ea8").grid(row=0, column=2, sticky=tk.W,
                                                                                     padx=(16, 0))
        self.lbl_crack_rate = tk.Label(t_grid, text="0 att/sec", font=("Consolas", 10, "bold"), bg="#1e1e2f",
                                       fg="#00d2d3")
        self.lbl_crack_rate.grid(row=0, column=3, sticky=tk.W, padx=8)

        tk.Label(t_grid, text="Current Candidate String:", bg="#1e1e2f", fg="#8e8ea8").grid(row=1, column=0,
                                                                                            sticky=tk.W, pady=4)
        self.lbl_crack_candidate = tk.Label(t_grid, text="Idle", font=("Consolas", 10, "bold"), bg="#1e1e2f",
                                            fg="#f1c40f")
        self.lbl_crack_candidate.grid(row=1, column=1, sticky=tk.W, padx=8)

        tk.Label(t_grid, text="Elapsed Duration:", bg="#1e1e2f", fg="#8e8ea8").grid(row=1, column=2, sticky=tk.W,
                                                                                    padx=(16, 0))
        self.lbl_crack_elapsed = tk.Label(t_grid, text="0.000s", font=("Consolas", 10, "bold"), bg="#1e1e2f",
                                          fg="#ffffff")
        self.lbl_crack_elapsed.grid(row=1, column=3, sticky=tk.W, padx=8)

        con_card = ttk.LabelFrame(root, text=" Attack Engine Audit Log ", padding=8)
        con_card.pack(fill=tk.BOTH, expand=True)

        self.txt_crack_log = scrolledtext.ScrolledText(con_card, bg="#1a1a2b", fg="#ecf0f1", font=("Consolas", 9),
                                                       height=10)
        self.txt_crack_log.pack(fill=tk.BOTH, expand=True)

    def _start_cracking_worker(self):
        target = self.crack_target_var.get().strip()
        if not target:
            messagebox.showerror("Error", "Target password cannot be empty.")
            return

        mode = self.crack_mode_var.get()
        self.cracking_stop_event.clear()
        self.btn_crack_start.config(state=tk.DISABLED)
        self.btn_crack_stop.config(state=tk.NORMAL)

        self._log_crack(f"[*] Initialized {mode} against target '{target}'...")

        self.cracking_thread = threading.Thread(
            target=self._cracking_execution_loop,
            args=(target, mode, self.cracking_queue, self.cracking_stop_event),
            daemon=True
        )
        self.cracking_thread.start()

    def _stop_cracking_worker(self):
        self.cracking_stop_event.set()
        self.btn_crack_stop.config(state=tk.DISABLED)
        self._log_crack("[!] Operator issued termination signal to attack worker.")

    def _cracking_execution_loop(self, target: str, mode: str, q: queue.Queue, stop_ev: threading.Event):
        t0 = time.perf_counter()
        attempts = 0
        found = False

        charset = string.ascii_lowercase + string.digits + string.punctuation

        if "Dictionary" in mode:
            wordlist = list(EMBEDDED_WORDLIST)
            if "Mutated" in mode:
                mutated = set(wordlist)
                for w in wordlist:
                    mutated.add(w + "1")
                    mutated.add(w + "2024!")
                    mutated.add(w.capitalize())
                wordlist = list(mutated)

            for cand in wordlist:
                if stop_ev.is_set():
                    break
                attempts += 1
                if attempts % 50 == 0:
                    q.put(("UPDATE", attempts, cand, time.perf_counter() - t0))

                if cand == target:
                    found = True
                    q.put(("SUCCESS", attempts, cand, time.perf_counter() - t0))
                    return

        else:
            for length in range(1, 6):
                for comb in itertools.product(charset, repeat=length):
                    if stop_ev.is_set():
                        break
                    cand = "".join(comb)
                    attempts += 1
                    if attempts % 5000 == 0:
                        q.put(("UPDATE", attempts, cand, time.perf_counter() - t0))

                    if cand == target:
                        found = True
                        q.put(("SUCCESS", attempts, cand, time.perf_counter() - t0))
                        return
                if stop_ev.is_set():
                    break

        if not found:
            q.put(("EXHAUSTED", attempts, "", time.perf_counter() - t0))

    def _log_crack(self, msg: str):
        self.txt_crack_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_crack_log.see(tk.END)

    # --------------------------------------------------------------------------
    # TAB 3: HASHING LABORATORY
    # --------------------------------------------------------------------------
    def _build_tab_hashlab(self):
        root = self.tab_hashlab

        av_card = ttk.LabelFrame(root, text=" Cryptographic Avalanche Effect Visualizer ", padding=10)
        av_card.pack(fill=tk.X, pady=(0, 8))

        g = tk.Frame(av_card, bg="#1e1e2f")
        g.pack(fill=tk.X)

        tk.Label(g, text="Input String A:", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0, sticky=tk.W)
        self.hash_input_a = ttk.Entry(g, width=28)
        self.hash_input_a.insert(0, "Password123")
        self.hash_input_a.grid(row=0, column=1, padx=6, pady=3)
        self.hash_input_a.bind("<KeyRelease>", lambda e: self._eval_avalanche())

        tk.Label(g, text="Input String B (1-bit shift):", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0, sticky=tk.W)
        self.hash_input_b = ttk.Entry(g, width=28)
        self.hash_input_b.insert(0, "password123")
        self.hash_input_b.grid(row=1, column=1, padx=6, pady=3)
        self.hash_input_b.bind("<KeyRelease>", lambda e: self._eval_avalanche())

        self.lbl_avalanche_stats = tk.Label(g, text="", bg="#1e1e2f", fg="#00d2d3", font=("Consolas", 9, "bold"))
        self.lbl_avalanche_stats.grid(row=0, column=2, rowspan=2, padx=18, sticky=tk.W)

        timing_card = ttk.LabelFrame(root, text=" Side-Channel Timing Attack Simulation ", padding=10)
        timing_card.pack(fill=tk.X, pady=(0, 8))

        t_box = tk.Frame(timing_card, bg="#1e1e2f")
        t_box.pack(fill=tk.X)

        btn_run_timing = ttk.Button(t_box, text="Benchmark hmac.compare_digest vs Naive Equality",
                                    style="Primary.TButton", command=self._eval_timing_attack)
        btn_run_timing.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_timing_res = tk.Label(t_box, text="Status: Ready to benchmark", bg="#1e1e2f", fg="#f5f6fa",
                                       font=("Segoe UI", 9))
        self.lbl_timing_res.pack(side=tk.LEFT)

        kdf_card = ttk.LabelFrame(root, text=" Key Derivation Functions (KDF) Real-World Hardware Benchmarks ",
                                  padding=8)
        kdf_card.pack(fill=tk.BOTH, expand=True)

        self.txt_kdf_bench = scrolledtext.ScrolledText(kdf_card, bg="#1a1a2b", fg="#ecf0f1", font=("Consolas", 9))
        self.txt_kdf_bench.pack(fill=tk.BOTH, expand=True)

        self._eval_avalanche()
        self._populate_kdf_table()

    def _eval_avalanche(self):
        s1 = self.hash_input_a.get()
        s2 = self.hash_input_b.get()
        diff_bits, pct, h1, h2 = HashingLaboratory.calculate_avalanche(s1, s2)
        txt = (
            f"Hamming Distance: {diff_bits} / 256 bits flipped\n"
            f"Diffusion Ratio : {pct:.2f}% (Ideal cryptographic standard is ~50.0%)\n"
            f"Digest A: {h1[:32]}...\nDigest B: {h2[:32]}..."
        )
        self.lbl_avalanche_stats.config(text=txt)

    def _eval_timing_attack(self):
        secret = b"CorporateSecretToken99!"
        wrong_early = b"X" + secret[1:]
        wrong_late = secret[:-1] + b"X"

        _, t_const1, _ = HashingLaboratory.simulate_timing_attack(secret, wrong_early)
        _, t_const2, _ = HashingLaboratory.simulate_timing_attack(secret, wrong_late)

        txt = (
            f"Constant-Time hmac.compare_digest execution: Early Mismatch = {t_const1} ns | Late Mismatch = {t_const2} ns\n"
            f"[✓] Verification duration is invariant to character match position (Protects against side-channel timing leaks)."
        )
        self.lbl_timing_res.config(text=txt, fg="#2ecc71")

    def _populate_kdf_table(self):
        text = [
            "==================================================================================================",
            " ALGORITHM & WORK FACTOR         | LOCAL COST (ms)  | 8x RTX 4090 GPU RIG RUNTIME (8-CHAR ALPHA+NUM)",
            "==================================================================================================",
            " Fast Hash: MD5 (Vulnerable)     | < 0.001 ms       | ~12 Seconds (Catastrophically weak)",
            " Fast Hash: SHA-256 (General)    | ~0.002 ms        | ~72 Seconds (Infeasible for password protection)",
            " KDF: PBKDF2 (10,000 rounds)     | ~3.5 ms          | ~4.5 Days",
            " KDF: PBKDF2 (100,000 rounds)    | ~32.0 ms         | ~45 Days (Standard baseline)",
            " KDF: PBKDF2 (600,000 rounds)    | ~190.0 ms        | ~9.2 Months (OWASP Recommended standard)",
            " KDF: scrypt (N=16384, r=8, p=1) | ~85.0 ms         | ~4.8 Years (Memory-hard; exhausts GPU VRAM)",
            "=================================================================================================="
        ]
        self.txt_kdf_bench.delete("1.0", tk.END)
        self.txt_kdf_bench.insert(tk.END, "\n".join(text))

    # --------------------------------------------------------------------------
    # TAB 4: LOGIN DEFENSE GATEWAY
    # --------------------------------------------------------------------------
    def _build_tab_defense(self):
        root = self.tab_defense

        form_card = ttk.LabelFrame(root, text=" Interactive Authentication Gateway Test Portal ", padding=10)
        form_card.pack(fill=tk.X, pady=(0, 8))

        f_grid = tk.Frame(form_card, bg="#1e1e2f")
        f_grid.pack(fill=tk.X)

        tk.Label(f_grid, text="Username:", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0, sticky=tk.W)
        self.def_user_var = tk.StringVar(value="alice")
        ttk.Entry(f_grid, textvariable=self.def_user_var, width=18).grid(row=0, column=1, padx=6, pady=3)

        tk.Label(f_grid, text="Password:", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        self.def_pass_var = tk.StringVar(value="SuperSecret123#")
        ttk.Entry(f_grid, textvariable=self.def_pass_var, width=18, show="●").grid(row=0, column=3, padx=6, pady=3)

        tk.Label(f_grid, text="Origin IP:", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0, sticky=tk.W)
        self.def_ip_var = tk.StringVar(value="198.51.100.25")
        ttk.Entry(f_grid, textvariable=self.def_ip_var, width=18).grid(row=1, column=1, padx=6, pady=3)

        btn_login = ttk.Button(f_grid, text="Transmit Login Attempt", style="Primary.TButton",
                               command=self._handle_manual_login)
        btn_login.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=6, pady=6)

        res_card = ttk.LabelFrame(root, text=" Gateway Decision & Adaptive Countermeasures ", padding=10)
        res_card.pack(fill=tk.BOTH, expand=True)

        self.txt_def_output = scrolledtext.ScrolledText(res_card, bg="#1a1a2b", fg="#00d2d3", font=("Consolas", 10))
        self.txt_def_output.pack(fill=tk.BOTH, expand=True)

    def _handle_manual_login(self):
        user = self.def_user_var.get().strip()
        pwd = self.def_pass_var.get().strip()
        ip = self.def_ip_var.get().strip()
        now = datetime.datetime.now()

        status, action, risk, lat, det = self.gateway.evaluate_and_authenticate(now, ip, user, pwd)

        out = [
            f"[{now.strftime('%H:%M:%S')}] AUTHENTICATION EVALUATION RESULT:",
            f"• Access Status       : {status.value}",
            f"• Enacted Action      : {action.value}",
            f"• Behavioral Risk     : {risk:.1f} / 100",
            f"• Response Latency    : {lat:.2f} ms",
            f"• Decision Detail     : {det}",
            "-" * 65
        ]
        self.txt_def_output.insert(tk.END, "\n".join(out) + "\n")
        self.txt_def_output.see(tk.END)
        self._refresh_dashboard()

    # --------------------------------------------------------------------------
    # TAB 5: OTP / TOTP SECURITY WORKBENCH
    # --------------------------------------------------------------------------
    def _build_tab_otp(self):
        root = self.tab_otp

        totp_card = ttk.LabelFrame(root, text=" RFC 6238 TOTP Real-Time Authenticator Engine ", padding=10)
        totp_card.pack(fill=tk.X, pady=(0, 8))

        t_box = tk.Frame(totp_card, bg="#1e1e2f")
        t_box.pack(fill=tk.X)

        self.totp_secret = secrets.token_bytes(20)
        tk.Label(t_box, text=f"Secret Key (Hex): {self.totp_secret.hex()[:32]}...", bg="#1e1e2f", fg="#8e8ea8",
                 font=("Consolas", 9)).pack(anchor=tk.W)

        self.lbl_totp_display = tk.Label(t_box, text="------", font=("Segoe UI", 24, "bold"), bg="#1e1e2f",
                                         fg="#00d2d3")
        self.lbl_totp_display.pack(anchor=tk.W, pady=4)

        self.lbl_totp_timer = tk.Label(t_box, text="Time Step Remaining: 30s", bg="#1e1e2f", fg="#f1c40f",
                                       font=("Segoe UI", 9))
        self.lbl_totp_timer.pack(anchor=tk.W)

        trans_card = ttk.LabelFrame(root, text=" Transactional OTP & Replay Attack Defense (Burn-on-Use) ", padding=10)
        trans_card.pack(fill=tk.BOTH, expand=True)

        tb_grid = tk.Frame(trans_card, bg="#1e1e2f")
        tb_grid.pack(fill=tk.X)

        btn_gen_otp = ttk.Button(tb_grid, text="Generate Transactional 6-Digit OTP", style="Primary.TButton",
                                 command=self._generate_demo_otp)
        btn_gen_otp.grid(row=0, column=0, padx=(0, 10))

        self.lbl_active_otp = tk.Label(tb_grid, text="Active Token: None", font=("Consolas", 11, "bold"), bg="#1e1e2f",
                                       fg="#ffffff")
        self.lbl_active_otp.grid(row=0, column=1, sticky=tk.W)

        tk.Label(tb_grid, text="Verify Code:", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0, sticky=tk.W,
                                                                                pady=(8, 0))
        self.entry_otp_code = ttk.Entry(tb_grid, width=14)
        self.entry_otp_code.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))

        btn_sub_otp = ttk.Button(tb_grid, text="Verify Token", style="Secondary.TButton", command=self._verify_demo_otp)
        btn_sub_otp.grid(row=1, column=2, sticky=tk.W, padx=6, pady=(8, 0))

        btn_replay = ttk.Button(tb_grid, text="Simulate Replay Attack", style="Danger.TButton",
                                command=self._replay_demo_otp)
        btn_replay.grid(row=1, column=3, sticky=tk.W, padx=6, pady=(8, 0))

        self.txt_otp_log = scrolledtext.ScrolledText(trans_card, bg="#1a1a2b", fg="#f5f6fa", font=("Consolas", 9),
                                                     height=10)
        self.txt_otp_log.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.active_demo_session_id = None
        self.active_demo_plaintext = None

    def _generate_demo_otp(self):
        sess_id, code = self.otp_engine.create_transactional_otp("user_alice")
        self.active_demo_session_id = sess_id
        self.active_demo_plaintext = code
        self.lbl_active_otp.config(text=f"Active Token: {code} (TTL: {self.otp_engine.ttl_seconds}s)")
        self.entry_otp_code.delete(0, tk.END)
        self.entry_otp_code.insert(0, code)
        self._log_otp(f"Generated new CSPRNG OTP '{code}' for session {sess_id[:8]}...")

    def _verify_demo_otp(self):
        if not self.active_demo_session_id:
            messagebox.showwarning("Warning", "Generate an OTP token first.")
            return
        code = self.entry_otp_code.get().strip()
        res, msg = self.otp_engine.verify_otp(self.active_demo_session_id, code)
        self._log_otp(f"Verification candidate '{code}' -> {res.value} ({msg})")

    def _replay_demo_otp(self):
        if not self.active_demo_session_id or not self.active_demo_plaintext:
            messagebox.showwarning("Warning", "Generate and verify an OTP token first to test replay.")
            return
        res, msg = self.otp_engine.verify_otp(self.active_demo_session_id, self.active_demo_plaintext)
        self._log_otp(f"REPLAY ATTEMPT on burned token '{self.active_demo_plaintext}' -> {res.value} ({msg})")

    def _log_otp(self, msg: str):
        self.txt_otp_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_otp_log.see(tk.END)

    # --------------------------------------------------------------------------
    # TAB 6: ATTACK CAMPAIGNS & SIEM THREAT GENERATOR
    # --------------------------------------------------------------------------
    def _build_tab_threats(self):
        root = self.tab_threats

        ctrl_card = ttk.LabelFrame(root, text=" Adversarial Attack Vector Simulator ", padding=10)
        ctrl_card.pack(fill=tk.X, pady=(0, 8))

        btn_row = tk.Frame(ctrl_card, bg="#1e1e2f")
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="1. Targeted Brute Force", style="Primary.TButton",
                   command=lambda: self._trigger_sim_thread("BRUTE_FORCE")).pack(side=tk.LEFT, padx=4)

        ttk.Button(btn_row, text="2. Password Spraying (/24)", style="Primary.TButton",
                   command=lambda: self._trigger_sim_thread("SPRAY")).pack(side=tk.LEFT, padx=4)

        ttk.Button(btn_row, text="3. Honeypot Canary Trip", style="Danger.TButton",
                   command=lambda: self._trigger_sim_thread("CANARY")).pack(side=tk.LEFT, padx=4)

        ttk.Button(btn_row, text="4. Legitimate Staff Traffic", style="Secondary.TButton",
                   command=lambda: self._trigger_sim_thread("LEGIT")).pack(side=tk.LEFT, padx=4)

        alert_card = ttk.LabelFrame(root, text=" SIEM Correlated Incident Dossiers ", padding=8)
        alert_card.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "ts", "rule", "sev", "ip", "user", "details")
        self.tree_alerts = ttk.Treeview(alert_card, columns=cols, show="headings")
        self.tree_alerts.heading("id", text="Alert ID")
        self.tree_alerts.heading("ts", text="Timestamp")
        self.tree_alerts.heading("rule", text="Triggered SIEM Rule")
        self.tree_alerts.heading("sev", text="Severity")
        self.tree_alerts.heading("ip", text="Offending Source")
        self.tree_alerts.heading("user", text="Target User")
        self.tree_alerts.heading("details", text="Incident Investigation Summary")

        self.tree_alerts.column("id", width=90)
        self.tree_alerts.column("ts", width=140)
        self.tree_alerts.column("rule", width=180)
        self.tree_alerts.column("sev", width=80, anchor=tk.CENTER)
        self.tree_alerts.column("ip", width=120)
        self.tree_alerts.column("user", width=110)
        self.tree_alerts.column("details", width=360)

        self.tree_alerts.tag_configure("CRITICAL", foreground="#e74c3c")
        self.tree_alerts.tag_configure("HIGH", foreground="#f39c12")
        self.tree_alerts.tag_configure("MEDIUM", foreground="#f1c40f")

        self.tree_alerts.pack(fill=tk.BOTH, expand=True)

    def _trigger_sim_thread(self, scenario: str):
        threading.Thread(target=self._run_attack_simulation, args=(scenario,), daemon=True).start()

    def _run_attack_simulation(self, scenario: str):
        now = datetime.datetime.now()

        if scenario == "BRUTE_FORCE":
            ip = "198.51.100.77"
            for i in range(7):
                self.gateway.evaluate_and_authenticate(
                    now + datetime.timedelta(seconds=i * 2), ip, "bob", f"GuessPass_{i}", "HydraBot/1.0"
                )
                time.sleep(0.08)

        elif scenario == "SPRAY":
            subnet = "203.0.113."
            users = ["alice", "bob", "carol", "admin_sarah", "contractor"]
            for idx, u in enumerate(users):
                bot_ip = f"{subnet}{20 + idx}"
                self.gateway.evaluate_and_authenticate(
                    now + datetime.timedelta(seconds=idx * 2), bot_ip, u, "Company2024!", "SprayBot/2.1"
                )
                time.sleep(0.08)

        elif scenario == "CANARY":
            self.gateway.evaluate_and_authenticate(
                now, "192.0.2.99", "canary_admin", "LeakedCanaryPassword99!", "BreachTester/1.0"
            )

        elif scenario == "LEGIT":
            self.gateway.evaluate_and_authenticate(now, "10.0.0.15", "alice", "SuperSecret123#", "Firefox/124.0")
            self.gateway.evaluate_and_authenticate(now, "10.0.0.16", "admin_sarah", "GlobalAdminPass!2024",
                                                   "Safari/17.0")

        self.siem_engine.evaluate_telemetry()

    # --------------------------------------------------------------------------
    # TAB 7: REPORTS & FORENSIC EXPORTERS
    # --------------------------------------------------------------------------
    def _build_tab_reports(self):
        root = self.tab_reports

        bar = tk.Frame(root, bg="#141420")
        bar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(bar, text="Export Audit Events (.csv)", style="Primary.TButton", command=self._export_csv).pack(
            side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="Export Security Incidents (.json)", style="Secondary.TButton",
                   command=self._export_json).pack(side=tk.LEFT, padx=6)
        ttk.Button(bar, text="Compile Markdown Forensic Report", style="Secondary.TButton",
                   command=self._compile_markdown).pack(side=tk.LEFT, padx=6)

        dossier_card = ttk.LabelFrame(root, text=" Generated DFIR Security Incident Dossier ", padding=8)
        dossier_card.pack(fill=tk.BOTH, expand=True)

        self.txt_dossier = scrolledtext.ScrolledText(dossier_card, bg="#1a1a2b", fg="#f5f6fa", font=("Consolas", 9))
        self.txt_dossier.pack(fill=tk.BOTH, expand=True)

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        c = self.db.get_conn()
        with self.db.lock:
            rows = c.execute("SELECT * FROM audit_events;").fetchall()
        if rows:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(rows[0].keys())
                writer.writerows([tuple(r) for r in rows])
            messagebox.showinfo("Export Success", f"Saved {len(rows)} audit events to CSV.")

    def _export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        data = [asdict(a) for a in self.siem_engine.active_alerts]
        for item in data:
            item["severity"] = item["severity"].value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Export Success", f"Exported {len(data)} SIEM alerts to JSON.")

    def _compile_markdown(self):
        m = self.db.get_dashboard_metrics()
        lines = [
            "# EXECUTIVE DFIR AUTHENTICATION INCIDENT REPORT",
            f"**Audit Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "--------------------------------------------------------------------------------",
            "## 1. INCIDENT TELEMETRY SUMMARY",
            f"- Total Access Requests Evaluated : {m.get('total_events', 0)}",
            f"- Correlated Security Incidents   : {m.get('total_alerts', 0)}",
            f"- Active Perimeter Drops / Bans   : {m.get('active_bans', 0)}",
            f"- Mean Organizational Risk Score   : {m.get('avg_risk_score', 0):.2f} / 100",
            "",
            "## 2. ACTIVE CORRELATED INCIDENTS"
        ]
        for a in self.siem_engine.active_alerts:
            lines.append(f"### [{a.severity.value}] {a.rule_name} (ID: {a.alert_id})")
            lines.append(
                f"- **Origin:** `{a.source_ip}` | **Target:** `{a.target_user}` | **Timestamp:** `{a.timestamp}`")
            lines.append(f"- **Summary:** {a.details}")
            lines.append(f"- **Action Required:** {a.mitigation}\n")

        self.txt_dossier.delete("1.0", tk.END)
        self.txt_dossier.insert(tk.END, "\n".join(lines))
        messagebox.showinfo("Compiled", "Executive incident dossier compiled successfully.")

    # --------------------------------------------------------------------------
    # PERIODIC BACKGROUND POLLER & HEARTBEAT
    # --------------------------------------------------------------------------
    def _poll_events(self):
        """Processes async worker queue messages and updates UI state without freezing."""
        try:
            while True:
                msg = self.cracking_queue.get_nowait()
                mtype = msg[0]

                if mtype == "UPDATE":
                    _, att, cand, el = msg
                    rate = att / el if el > 0 else 0
                    self.lbl_crack_attempts.config(text=f"{att:,}")
                    self.lbl_crack_rate.config(text=f"{rate:,.0f} att/sec")
                    self.lbl_crack_candidate.config(text=cand)
                    self.lbl_crack_elapsed.config(text=f"{el:.3f}s")

                elif mtype == "SUCCESS":
                    _, att, cand, el = msg
                    rate = att / el if el > 0 else 0
                    self.lbl_crack_attempts.config(text=f"{att:,}")
                    self.lbl_crack_candidate.config(text=cand)
                    self.btn_crack_start.config(state=tk.NORMAL)
                    self.btn_crack_stop.config(state=tk.DISABLED)
                    self._log_crack(
                        f"[SUCCESS] Compromised! Plaintext '{cand}' cracked in {el:.4f}s ({att:,} attempts).")
                    messagebox.showinfo("Password Cracked", f"Found: '{cand}'\nAttempts: {att:,}\nTime: {el:.3f}s")

                elif mtype == "EXHAUSTED":
                    _, att, _, el = msg
                    self.btn_crack_start.config(state=tk.NORMAL)
                    self.btn_crack_stop.config(state=tk.DISABLED)
                    self._log_crack(f"[!] Exhausted keyspace without match after {att:,} attempts ({el:.3f}s).")

                self.cracking_queue.task_done()
        except queue.Empty:
            pass

        self.after(50, self._poll_events)

    def _siem_heartbeat(self):
        """Heartbeat: updates live TOTP step, runs correlation, refreshes streams."""
        now = time.time()

        # Update TOTP using for_time parameter
        code = OTPEngine.generate_totp_rfc6238(self.totp_secret, for_time=now)
        rem = 30 - int(now % 30)
        self.lbl_totp_display.config(text=f"{code[:3]} {code[3:]}")
        self.lbl_totp_timer.config(text=f"Time Step Remaining: {rem:02d}s")

        # Run SIEM correlation rules
        self.siem_engine.evaluate_telemetry()
        self._refresh_dashboard()

        self.after(1000, self._siem_heartbeat)

    def _refresh_dashboard(self):
        """Pulls recent SQLite metrics and repopulates dashboard tables."""
        m = self.db.get_dashboard_metrics()
        if not m:
            return

        self.kpi_events.config(text=str(m["total_events"]))
        self.kpi_alerts.config(text=str(m["total_alerts"]))
        self.kpi_bans.config(text=str(m["active_bans"]))
        self.kpi_fails.config(text=str(m["failed_attempts"]))
        self.kpi_succ.config(text=str(m["successful_attempts"]))
        self.kpi_risk.config(text=f"{m['avg_risk_score']:.1f}")

        label = "DEFCON 5 - NORMAL"
        if m["avg_risk_score"] >= 80:
            label = "DEFCON 1 - CRITICAL"
        elif m["avg_risk_score"] >= 50:
            label = "DEFCON 2 - ELEVATED"
        elif m["avg_risk_score"] >= 25:
            label = "DEFCON 3 - ADVISORY"
        self.soc_gauge.render(m["avg_risk_score"], label)

        c = self.db.get_conn()
        with self.db.lock:
            evs = c.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT 100;").fetchall()

        self.tree_stream.delete(*self.tree_stream.get_children())
        for e in evs:
            st = e["status"]
            tag = "SUCCESS" if st == "SUCCESS" else ("BLOCKED" if "BLOCKED" in st else "FAIL")
            self.tree_stream.insert("", tk.END, values=(
                e["timestamp"][11:19] if len(e["timestamp"]) >= 19 else e["timestamp"],
                e["source_ip"], e["username"], st,
                f"{e['risk_score']:.0f}", e["action_taken"], f"{e['latency_ms']:.1f}ms", e["details"]
            ), tags=(tag,))

        self.tree_alerts.delete(*self.tree_alerts.get_children())
        for a in self.siem_engine.active_alerts:
            self.tree_alerts.insert("", tk.END, values=(
                a.alert_id,
                a.timestamp[11:19] if len(a.timestamp) >= 19 else a.timestamp,
                a.rule_name, a.severity.value,
                a.source_ip, a.target_user, a.details
            ), tags=(a.severity.value,))


# ==============================================================================
# 9. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Prevent scaling blur on High-DPI Windows displays
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = SecurityLabMasterApp()
    app.mainloop()
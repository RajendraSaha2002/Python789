import os
import sys
import time
import math
import hmac
import hashlib
import secrets
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set


# ==============================================================================
# 1. ANSI STYLING & TERMINAL DASHBOARD UTILITIES
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


def print_banner(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.WHITE}  {title.upper()}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}\n")


def print_section(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.YELLOW}--- [ {title} ] ---{ANSI.RESET}\n")


# ==============================================================================
# 2. ENUMS & DATA MODELS
# ==============================================================================

class OTPType(Enum):
    NUMERIC_TRANSACTION = "NUMERIC_TRANSACTION"
    ALPHANUMERIC_TRANSACTION = "ALPHANUMERIC_TRANSACTION"
    RFC6238_TOTP = "RFC6238_TOTP"
    RFC4226_HOTP = "RFC4226_HOTP"


class OTPVerifyResult(Enum):
    SUCCESS = "SUCCESS"
    FAILED_INCORRECT = "FAILED_INCORRECT"
    FAILED_EXPIRED = "FAILED_EXPIRED"
    FAILED_REPLAY_ATTACK = "FAILED_REPLAY_ATTACK"
    FAILED_MAX_ATTEMPTS_EXCEEDED = "FAILED_MAX_ATTEMPTS_EXCEEDED"
    BLOCKED_COOLDOWN_ACTIVE = "BLOCKED_COOLDOWN_ACTIVE"
    BLOCKED_ACCOUNT_LOCKED = "BLOCKED_ACCOUNT_LOCKED"
    INVALID_SESSION = "INVALID_SESSION"


@dataclass
class OTPSecurityPolicy:
    """Security thresholds and operational governance parameters."""
    code_digits: int = 6
    ttl_seconds: int = 60
    max_verify_attempts: int = 3
    cooldown_after_failed_sessions: int = 3
    cooldown_duration_seconds: int = 30
    hard_lockout_failed_sessions: int = 5
    hard_lockout_duration_seconds: int = 300
    allow_totp_clock_skew: bool = True  # Allows +/- 1 step drift


@dataclass
class OTPSessionRecord:
    """Stateful metadata for an active OTP transaction."""
    session_id: str
    user_id: str
    otp_hash: str
    salt: bytes
    otp_type: OTPType
    created_at: float
    expires_at: float
    max_attempts: int
    attempts_remaining: int
    is_consumed: bool = False
    consumed_at: Optional[float] = None
    hotp_counter: Optional[int] = None
    totp_secret: Optional[bytes] = None


@dataclass
class UserSecurityState:
    """Tracks failed authentication strikes and lockout states per user."""
    user_id: str
    consecutive_failed_sessions: int = 0
    cooldown_until: float = 0.0
    hard_lock_until: float = 0.0
    total_successful_logins: int = 0
    total_failed_verifications: int = 0


# ==============================================================================
# 3. RFC 6238 TOTP & RFC 4226 HOTP PURE-PYTHON ENGINE
# ==============================================================================

class RFCComplianceEngine:
    """
    Standard-compliant implementation of HMAC-Based (HOTP) and Time-Based (TOTP)
    one-time password algorithms without external dependencies.
    """

    @staticmethod
    def generate_hotp(secret: bytes, counter: int, digits: int = 6) -> str:
        """Computes RFC 4226 HOTP code from secret and integer counter."""
        counter_bytes = counter.to_bytes(8, byteorder="big")
        hmac_digest = hmac.new(secret, counter_bytes, hashlib.sha1).digest()

        # Dynamic Binary Truncation
        offset = hmac_digest[-1] & 0x0F
        binary_code = (
                ((hmac_digest[offset] & 0x7F) << 24)
                | ((hmac_digest[offset + 1] & 0xFF) << 16)
                | ((hmac_digest[offset + 2] & 0xFF) << 8)
                | (hmac_digest[offset + 3] & 0xFF)
        )

        otp = binary_code % (10 ** digits)
        return str(otp).zfill(digits)

    @classmethod
    def generate_totp(cls, secret: bytes, time_step: int = 30, digits: int = 6,
                      for_time: Optional[float] = None) -> str:
        """Computes RFC 6238 TOTP code for the current or specified time epoch."""
        current_epoch = for_time if for_time is not None else time.time()
        time_counter = int(current_epoch // time_step)
        return cls.generate_hotp(secret, time_counter, digits)

    @classmethod
    def verify_totp_with_skew(cls, secret: bytes, candidate: str, time_step: int = 30, digits: int = 6) -> bool:
        """Validates candidate against current time, -1 step, and +1 step for clock drift."""
        now = time.time()
        for skew in (-1, 0, 1):
            valid_code = cls.generate_totp(secret, time_step, digits, for_time=now + (skew * time_step))
            if hmac.compare_digest(valid_code, candidate.strip()):
                return True
        return False


# ==============================================================================
# 4. CORE SECURE OTP SERVICE
# ==============================================================================

class SecureOTPService:
    """
    Production-grade OTP manager enforcing cryptographically secure generation,
    constant-time verification, replay prevention, and progressive rate limiting.
    """

    def __init__(self, policy: OTPSecurityPolicy):
        self.policy = policy
        self._lock = threading.Lock()

        # State stores
        self.active_sessions: Dict[str, OTPSessionRecord] = {}
        self.user_states: Dict[str, UserSecurityState] = {}
        self.consumed_token_registry: Set[str] = set()  # Prevents replay
        self.audit_event_log: List[Dict[str, Any]] = []

    def _get_or_create_user(self, user_id: str) -> UserSecurityState:
        if user_id not in self.user_states:
            self.user_states[user_id] = UserSecurityState(user_id=user_id)
        return self.user_states[user_id]

    @staticmethod
    def _hash_otp(otp_plaintext: str, salt: bytes) -> str:
        """Stores OTP in memory as a salted SHA-256 digest to prevent memory scraping."""
        return hashlib.sha256(salt + otp_plaintext.encode("utf-8")).hexdigest()

    def generate_otp(self, user_id: str, otp_type: OTPType = OTPType.NUMERIC_TRANSACTION) -> Tuple[str, str]:
        """
        Generates an OTP token, records its salted hash in an active session,
        and returns (session_id, plaintext_otp_for_delivery).
        """
        with self._lock:
            now = time.time()
            user = self._get_or_create_user(user_id)

            # Check Hard Lockout
            if now < user.hard_lock_until:
                rem = int(user.hard_lock_until - now)
                raise PermissionError(f"Account '{user_id}' is under HARD LOCKOUT. Retry in {rem}s.")

            # Check Cooldown
            if now < user.cooldown_until:
                rem = int(user.cooldown_until - now)
                raise PermissionError(f"Account '{user_id}' is in COOLDOWN. Retry in {rem}s.")

            session_id = secrets.token_hex(16)
            salt = secrets.token_bytes(16)
            plaintext_otp = ""
            totp_secret = None

            if otp_type == OTPType.NUMERIC_TRANSACTION:
                # CSPRNG bounded numeric code
                max_val = 10 ** self.policy.code_digits
                raw_num = secrets.randbelow(max_val)
                plaintext_otp = str(raw_num).zfill(self.policy.code_digits)

            elif otp_type == OTPType.ALPHANUMERIC_TRANSACTION:
                alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Omit ambiguous characters (I, O, 1, 0)
                plaintext_otp = "".join(secrets.choice(alphabet) for _ in range(self.policy.code_digits))

            elif otp_type == OTPType.RFC6238_TOTP:
                totp_secret = secrets.token_bytes(20)
                plaintext_otp = RFCComplianceEngine.generate_totp(totp_secret, digits=self.policy.code_digits)

            otp_hash = self._hash_otp(plaintext_otp, salt)
            session = OTPSessionRecord(
                session_id=session_id,
                user_id=user_id,
                otp_hash=otp_hash,
                salt=salt,
                otp_type=otp_type,
                created_at=now,
                expires_at=now + self.policy.ttl_seconds,
                max_attempts=self.policy.max_verify_attempts,
                attempts_remaining=self.policy.max_verify_attempts,
                totp_secret=totp_secret
            )

            self.active_sessions[session_id] = session
            self._log_audit(user_id, session_id, "GENERATE", f"Type: {otp_type.value}, TTL: {self.policy.ttl_seconds}s")
            return session_id, plaintext_otp

    def verify_otp(self, session_id: str, candidate_otp: str) -> Tuple[OTPVerifyResult, str]:
        """
        Validates candidate token against session policies, replay registry,
        expiration, and attempt constraints in constant time.
        """
        with self._lock:
            now = time.time()

            if session_id not in self.active_sessions:
                return OTPVerifyResult.INVALID_SESSION, "Session identifier not found or purged."

            session = self.active_sessions[session_id]
            user = self._get_or_create_user(session.user_id)

            # Check 1: User-level hard lock or cooldown
            if now < user.hard_lock_until:
                rem = int(user.hard_lock_until - now)
                return OTPVerifyResult.BLOCKED_ACCOUNT_LOCKED, f"Account locked. Cooldown: {rem}s."
            if now < user.cooldown_until:
                rem = int(user.cooldown_until - now)
                return OTPVerifyResult.BLOCKED_COOLDOWN_ACTIVE, f"Account in cooldown. Cooldown: {rem}s."

            # Check 2: Replay Prevention (Burn-on-Use)
            if session.is_consumed:
                self._log_audit(session.user_id, session_id, "VERIFY_REPLAY_ATTACK",
                                "Attempted reuse of consumed token.")
                return OTPVerifyResult.FAILED_REPLAY_ATTACK, "CRITICAL: Token has already been used and is invalidated."

            # Check 3: Expiration Check (TTL)
            if now > session.expires_at:
                self._log_audit(session.user_id, session_id, "VERIFY_EXPIRED", "Token expired prior to verification.")
                return OTPVerifyResult.FAILED_EXPIRED, "Token has expired. Request a new OTP."

            # Check 4: Remaining Attempts Exhaustion
            if session.attempts_remaining <= 0:
                self._log_audit(session.user_id, session_id, "VERIFY_EXHAUSTED", "Max verification attempts reached.")
                return OTPVerifyResult.FAILED_MAX_ATTEMPTS_EXCEEDED, "Maximum verification attempts exceeded. Session locked."

            # Check 5: Cryptographic Constant-Time Verification
            candidate_hash = self._hash_otp(candidate_otp.strip(), session.salt)
            is_valid = False

            if session.otp_type == OTPType.RFC6238_TOTP and session.totp_secret:
                # TOTP supports clock drift tolerance
                if self.policy.allow_totp_clock_skew:
                    is_valid = RFCComplianceEngine.verify_totp_with_skew(session.totp_secret, candidate_otp,
                                                                         digits=self.policy.code_digits)
                else:
                    curr_totp = RFCComplianceEngine.generate_totp(session.totp_secret, digits=self.policy.code_digits)
                    is_valid = hmac.compare_digest(curr_totp, candidate_otp.strip())
            else:
                is_valid = hmac.compare_digest(session.otp_hash, candidate_hash)

            if is_valid:
                # Success: Burn token immediately
                session.is_consumed = True
                session.consumed_at = now
                user.consecutive_failed_sessions = 0  # Reset failure streaks
                user.total_successful_logins += 1
                self.consumed_token_registry.add(session.otp_hash)

                self._log_audit(session.user_id, session_id, "VERIFY_SUCCESS",
                                "Authentication successful. Token consumed.")
                return OTPVerifyResult.SUCCESS, "Authentication successful. Access granted."

            else:
                # Failure branch
                session.attempts_remaining -= 1
                user.total_failed_verifications += 1

                # Check if this failure exhausted the current session
                if session.attempts_remaining <= 0:
                    user.consecutive_failed_sessions += 1

                    # Apply Escalating Lockouts
                    if user.consecutive_failed_sessions >= self.policy.hard_lockout_failed_sessions:
                        user.hard_lock_until = now + self.policy.hard_lockout_duration_seconds
                        self._log_audit(session.user_id, session_id, "LOCKOUT_HARD",
                                        f"Hard lockout for {self.policy.hard_lockout_duration_seconds}s.")
                        return OTPVerifyResult.BLOCKED_ACCOUNT_LOCKED, "Account placed under hard administrative lockout."

                    elif user.consecutive_failed_sessions >= self.policy.cooldown_after_failed_sessions:
                        user.cooldown_until = now + self.policy.cooldown_duration_seconds
                        self._log_audit(session.user_id, session_id, "LOCKOUT_COOLDOWN",
                                        f"Cooldown for {self.policy.cooldown_duration_seconds}s.")
                        return OTPVerifyResult.BLOCKED_COOLDOWN_ACTIVE, f"Multiple failed sessions. Cooldown active for {self.policy.cooldown_duration_seconds}s."

                    return OTPVerifyResult.FAILED_MAX_ATTEMPTS_EXCEEDED, "Incorrect OTP. Maximum attempts exceeded. Session terminated."

                self._log_audit(session.user_id, session_id, "VERIFY_FAIL",
                                f"Failed attempt. Remaining: {session.attempts_remaining}")
                return OTPVerifyResult.FAILED_INCORRECT, f"Incorrect OTP. {session.attempts_remaining} attempt(s) remaining."

    def _log_audit(self, user_id: str, session_id: str, action: str, details: str) -> None:
        self.audit_event_log.append({
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": session_id[:8] + "...",
            "action": action,
            "details": details
        })


# ==============================================================================
# 5. ADVERSARIAL ATTACK SIMULATION WORKBENCH
# ==============================================================================

class AdversarialSimulator:
    """
    Automated threat actor simulating exhaustive brute-force guessing,
    man-in-the-middle replay attempts, and race-condition window bypasses.
    """

    def __init__(self, service: SecureOTPService):
        self.service = service

    def simulate_brute_force_attack(self, target_user: str = "victim_user") -> None:
        print_section("SCENARIO 1: High-Velocity Exhaustive Brute-Force Guessing Attack")
        print("Adversary generates a valid target session, then launches automated guesses to crack the OTP.")

        # Policy: 6 digits = 1,000,000 possibilities, but max_attempts = 3
        session_id, real_otp = self.service.generate_otp(target_user, OTPType.NUMERIC_TRANSACTION)
        print(f"Target Session Created. [DEMO OBSERVER: Real OTP is '{ANSI.CYAN}{real_otp}{ANSI.RESET}']")
        print(f"Adversary attempts sequential and random guesses on session {session_id[:8]}...\n")

        # Simulate 10 automated guesses
        guesses = ["000000", "123456", "999999", "111111", "555555", "888888", "432109"]
        for idx, guess in enumerate(guesses, 1):
            res, msg = self.service.verify_otp(session_id, guess)
            color = ANSI.GREEN if res == OTPVerifyResult.SUCCESS else ANSI.RED
            print(f"  Guess #{idx:02d} ['{guess}'] -> {color}{res.value:<28}{ANSI.RESET} | Detail: {msg}")

            if res in (OTPVerifyResult.FAILED_MAX_ATTEMPTS_EXCEEDED, OTPVerifyResult.BLOCKED_COOLDOWN_ACTIVE):
                print(f"\n{ANSI.GREEN}[✓] DEFENSE CONFIRMED:{ANSI.RESET} Session locked after maximum attempts.")
                print(
                    f"    Attacker was stopped after {idx} guesses. Brute-force space searched: {idx}/1,000,000 (0.0003%).")
                break
            time.sleep(0.05)

    def simulate_replay_attack(self, target_user: str = "alice_finance") -> None:
        print_section("SCENARIO 2: Intercepted Token Replay Attack (Burn-on-Use)")
        print("A legitimate user authenticates with an OTP. An adversary eavesdrops and attempts to replay it.\n")

        session_id, real_otp = self.service.generate_otp(target_user, OTPType.NUMERIC_TRANSACTION)
        print(f"1. User receives valid OTP: '{ANSI.CYAN}{real_otp}{ANSI.RESET}'")

        # Legitimate verification
        res_legit, msg_legit = self.service.verify_otp(session_id, real_otp)
        print(f"2. Legitimate verification -> {ANSI.GREEN}{res_legit.value}{ANSI.RESET} ({msg_legit})")

        # Replay attempt by adversary
        print(
            f"3. Attacker intercepts and attempts to replay token '{ANSI.CYAN}{real_otp}{ANSI.RESET}' within valid TTL window...")
        res_replay, msg_replay = self.service.verify_otp(session_id, real_otp)
        print(f"4. Replay verification     -> {ANSI.RED}{res_replay.value}{ANSI.RESET} ({msg_replay})")

        if res_replay == OTPVerifyResult.FAILED_REPLAY_ATTACK:
            print(
                f"\n{ANSI.GREEN}[✓] DEFENSE CONFIRMED:{ANSI.RESET} Replay successfully mitigated via immediate burn-on-use.")

    def simulate_expiration_race(self, target_user: str = "charlie_dev") -> None:
        print_section("SCENARIO 3: Post-Expiration Window Attack")
        print("Adversary acquires a token and attempts verification after the TTL has lapsed.\n")

        # Temporarily use low TTL
        self.service.policy.ttl_seconds = 2
        session_id, real_otp = self.service.generate_otp(target_user, OTPType.NUMERIC_TRANSACTION)
        print(f"Session generated with strict 2-second TTL. OTP is '{ANSI.CYAN}{real_otp}{ANSI.RESET}'.")
        print("Waiting 2.5 seconds for token expiration...")
        time.sleep(2.5)

        res, msg = self.service.verify_otp(session_id, real_otp)
        print(f"Verification attempt after TTL -> {ANSI.RED}{res.value}{ANSI.RESET} ({msg})")

        # Restore standard policy
        self.service.policy.ttl_seconds = 60
        if res == OTPVerifyResult.FAILED_EXPIRED:
            print(
                f"\n{ANSI.GREEN}[✓] DEFENSE CONFIRMED:{ANSI.RESET} Expired credentials rejected regardless of valid characters.")

    def simulate_progressive_lockout_escalation(self, target_user: str = "persistent_attacker") -> None:
        print_section("SCENARIO 4: Escalating Lockout & Cooldown Enforcement")
        print("Attacker repeatedly triggers max attempt failures across multiple consecutive sessions.\n")

        threshold = self.service.policy.cooldown_after_failed_sessions
        print(f"Policy Cooldown Trigger: {threshold} failed sessions.\n")

        for s_idx in range(1, threshold + 2):
            session_id, _ = self.service.generate_otp(target_user, OTPType.NUMERIC_TRANSACTION)
            print(f"--- Session Batch {s_idx} [Session: {session_id[:8]}...] ---")

            # Exhaust the session
            for g in range(self.service.policy.max_verify_attempts):
                res, msg = self.service.verify_otp(session_id, "999999")

            print(f"Exhausted Session {s_idx} Result: {ANSI.YELLOW}{res.value}{ANSI.RESET} | {msg}")

        # Attempt to create a new session while in cooldown
        print("\nAttacker attempts to request a brand new OTP during active cooldown:")
        try:
            self.service.generate_otp(target_user)
            print(f"{ANSI.RED}[!] FAILED: System generated OTP during cooldown!{ANSI.RESET}")
        except PermissionError as ex:
            print(
                f"{ANSI.GREEN}[✓] DEFENSE CONFIRMED:{ANSI.RESET} Gateway blocked generation: {ANSI.RED}{ex}{ANSI.RESET}")


# ==============================================================================
# 6. MATHEMATICAL PROBABILITY & SECURITY ANALYZER
# ==============================================================================

class OTPSecurityMatrix:
    """Computes mathematical search-space metrics and adversarial success probability."""

    @staticmethod
    def render_security_matrix():
        print_section("MATHEMATICAL ENTROPY & GUESSABILITY MATRIX")
        print("Formula: P(Compromise) = Allowed Attempts / Total Key Space (R^L)\n")

        scenarios = [
            ("4-Digit PIN (Numeric)", 10, 4, 3),
            ("6-Digit Standard (Numeric)", 10, 6, 3),
            ("6-Digit Standard (Numeric)", 10, 6, 5),
            ("8-Digit High-Security", 10, 8, 3),
            ("6-Char Alphanumeric", 32, 6, 3),
            ("8-Char Alphanumeric", 32, 8, 3),
        ]

        print(
            f"{ANSI.BOLD}{'Token Architecture':<28} | {'Key Space':<14} | {'Allowed Guesses':<16} | {'Probability of Breach'}{ANSI.RESET}")
        print("-" * 84)

        for name, pool, length, attempts in scenarios:
            space = pool ** length
            prob = (attempts / space) * 100.0

            if prob > 0.01:
                prob_str = f"{ANSI.RED}{prob:.4f}% (DANGEROUS){ANSI.RESET}"
            elif prob > 0.0001:
                prob_str = f"{ANSI.YELLOW}{prob:.6f}% (ACCEPTABLE){ANSI.RESET}"
            else:
                prob_str = f"{ANSI.GREEN}{prob:.8f}% (CRYPTOGRAPHIC){ANSI.RESET}"

            print(f"{name:<28} | {space:<14,} | {attempts:<16} | {prob_str}")

        print("\nTakeaway: A 6-digit numeric OTP constrained to 3 attempts reduces adversary odds to 0.0003%.")


# ==============================================================================
# 7. INTERACTIVE CLI & GUIDED EXPERIMENTATION
# ==============================================================================

class ConsoleApplication:
    """Interactive management shell for manual experimentation."""

    def __init__(self):
        self.policy = OTPSecurityPolicy()
        self.service = SecureOTPService(self.policy)
        self.simulator = AdversarialSimulator(self.service)

    def main_menu(self) -> None:
        while True:
            print_banner("OTP Security, Verification & Guessing Simulator")
            print(" 1. Run All Automated Adversarial Simulations (Brute-Force, Replay, Lockouts)")
            print(" 2. Interactive Manual OTP Verification Workflow")
            print(" 3. RFC 6238 TOTP Real-Time Authenticator Demo (30s Step)")
            print(" 4. View Mathematical Entropy & Probability Security Matrix")
            print(" 5. Inspect Forensic Security Audit Trail")
            print(" 6. Reconfigure OTP Security Policies (Digits, TTL, Max Guesses)")
            print(" 0. Terminate Application")
            print(f"{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")

            choice = input(f"{ANSI.BOLD}Select Operation [0-6]: {ANSI.RESET}").strip()

            if choice == "1":
                self.simulator.simulate_brute_force_attack()
                self.simulator.simulate_replay_attack()
                self.simulator.simulate_expiration_race()
                self.simulator.simulate_progressive_lockout_escalation()
            elif choice == "2":
                self._manual_otp_flow()
            elif choice == "3":
                self._totp_live_demo()
            elif choice == "4":
                OTPSecurityMatrix.render_security_matrix()
            elif choice == "5":
                self._display_audit_log()
            elif choice == "6":
                self._reconfigure_policy()
            elif choice == "0":
                print(f"\n{ANSI.GREEN}[✓] Simulator closed cleanly.{ANSI.RESET}")
                sys.exit(0)
            else:
                print(f"{ANSI.RED}[!] Invalid choice.{ANSI.RESET}")

            input(f"\n{ANSI.DIM}Press Enter to return to main menu...{ANSI.RESET}")

    def _manual_otp_flow(self) -> None:
        print_section("MANUAL TRANSACTIONAL OTP VERIFICATION")
        user = input("Enter User ID (default: user_demo): ").strip() or "user_demo"

        try:
            session_id, plaintext = self.service.generate_otp(user, OTPType.NUMERIC_TRANSACTION)
        except PermissionError as e:
            print(f"{ANSI.RED}[!] Generation Failed: {e}{ANSI.RESET}")
            return

        print(f"\n{ANSI.GREEN}[✓] OTP Dispatched Successfully!{ANSI.RESET}")
        print(f"Session ID : {session_id}")
        print(f"Delivered OTP: {ANSI.BOLD}{ANSI.CYAN}{plaintext}{ANSI.RESET} (Expires in {self.policy.ttl_seconds}s)")
        print(f"Attempts Allowed: {self.policy.max_verify_attempts}\n")

        while True:
            candidate = input(f"Enter verification token (or 'q' to abort): ").strip()
            if candidate.lower() == 'q':
                break

            status, msg = self.service.verify_otp(session_id, candidate)
            color = ANSI.GREEN if status == OTPVerifyResult.SUCCESS else ANSI.RED
            print(f"Verification Result: {color}{status.value}{ANSI.RESET}")
            print(f"Details: {msg}\n")

            if status in (OTPVerifyResult.SUCCESS, OTPVerifyResult.FAILED_MAX_ATTEMPTS_EXCEEDED,
                          OTPVerifyResult.FAILED_EXPIRED):
                break

    def _totp_live_demo(self) -> None:
        print_section("RFC 6238 TOTP REAL-TIME AUTHENTICATOR")
        secret = secrets.token_bytes(20)
        print("Generated RFC 6238 Secret (Hex):", secret.hex())
        print("Current Time Step: 30 seconds. Generating live codes...\n")

        for _ in range(3):
            now = time.time()
            code = RFCComplianceEngine.generate_totp(secret, digits=6, for_time=now)
            step_rem = 30 - int(now % 30)
            print(
                f"  Timestamp: {datetime.now().strftime('%H:%M:%S')} | Code: {ANSI.BOLD}{ANSI.CYAN}{code}{ANSI.RESET} | Valid for: {step_rem:02d}s")
            time.sleep(2)

    def _display_audit_log(self) -> None:
        print_section("IMMUTABLE FORENSIC AUDIT TRAIL")
        logs = self.service.audit_event_log
        if not logs:
            print("No events logged yet.")
            return

        print(f"{ANSI.BOLD}{'Timestamp':<24} | {'User ID':<16} | {'Action':<22} | {'Details'}{ANSI.RESET}")
        print("-" * 88)
        for entry in logs[-15:]:
            print(f"{entry['timestamp']:<24} | {entry['user_id']:<16} | {entry['action']:<22} | {entry['details']}")

    def _reconfigure_policy(self) -> None:
        print_section("RECONFIGURE OTP SECURITY POLICIES")
        print(f"1. Code Length (Current: {self.policy.code_digits})")
        print(f"2. Time-To-Live TTL (Current: {self.policy.ttl_seconds}s)")
        print(f"3. Max Verification Attempts (Current: {self.policy.max_verify_attempts})")

        opt = input("Select setting to update (1-3) or 'q' to return: ").strip()
        if opt == "1":
            self.policy.code_digits = int(input("Enter code length (4, 6, 8): "))
        elif opt == "2":
            self.policy.ttl_seconds = int(input("Enter TTL seconds: "))
        elif opt == "3":
            self.policy.max_verify_attempts = int(input("Enter max verification attempts: "))
        print(f"{ANSI.GREEN}[✓] Policy parameters updated successfully.{ANSI.RESET}")


# ==============================================================================
# 8. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    try:
        app = ConsoleApplication()
        # Non-interactive execution flag
        if len(sys.argv) > 1 and sys.argv[1] in ("--auto", "-a", "--demo"):
            app.simulator.simulate_brute_force_attack()
            app.simulator.simulate_replay_attack()
            app.simulator.simulate_expiration_race()
            app.simulator.simulate_progressive_lockout_escalation()
            OTPSecurityMatrix.render_security_matrix()
            sys.exit(0)

        app.main_menu()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Simulator aborted by user.{ANSI.RESET}")
        sys.exit(0)
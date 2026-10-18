import os
import sys
import time
import timeit
import hmac
import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any


# ==============================================================================
# 1. ANSI STYLING & TERMINAL FORMATTING
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
    BG_BLUE = "\033[44m"


def print_header(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.WHITE}  {title.upper()}{ANSI.RESET}")
    print(f"{ANSI.BOLD}{ANSI.CYAN}{'=' * 80}{ANSI.RESET}\n")


def print_section(title: str) -> None:
    print(f"\n{ANSI.BOLD}{ANSI.YELLOW}--- [ {title} ] ---{ANSI.RESET}\n")


# ==============================================================================
# 2. CORE CRYPTOGRAPHIC ENGINES & PHC FORMAT SERIALIZER
# ==============================================================================

@dataclass
class PHCHashRecord:
    """
    Standard Password Hashing Competition (PHC) format container.
    Format: $<id>[$v=<version>][$<param>=<val>,...][$<salt>[$<hash>]]
    """
    algorithm: str
    params: Dict[str, Any]
    salt_hex: str
    hash_hex: str

    def serialize(self) -> str:
        param_str = ",".join(f"{k}={v}" for k, v in self.params.items())
        if param_str:
            return f"${self.algorithm}${param_str}${self.salt_hex}${self.hash_hex}"
        return f"${self.algorithm}${self.salt_hex}${self.hash_hex}"

    @classmethod
    def deserialize(cls, phc_string: str) -> "PHCHashRecord":
        parts = phc_string.strip().split("$")
        if len(parts) < 4:
            raise ValueError("Malformed PHC string.")
        algo = parts[1]
        if len(parts) == 5:
            raw_params = parts[2].split(",")
            params = {}
            for p in raw_params:
                if "=" in p:
                    k, v = p.split("=")
                    params[k] = int(v) if v.isdigit() else v
            salt_hex = parts[3]
            hash_hex = parts[4]
        else:
            params = {}
            salt_hex = parts[2]
            hash_hex = parts[3]
        return cls(algorithm=algo, params=params, salt_hex=salt_hex, hash_hex=hash_hex)


class CryptoEngine:
    """Cryptographic primitive implementations for testing and production."""

    @staticmethod
    def raw_sha256(password: str) -> str:
        """Fast, unsalted SHA-256 (VULNERABLE for passwords)."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def salted_sha256(password: str, salt: bytes) -> str:
        """Salted single-round SHA-256 (VULNERABLE: easily brute-forced on GPUs)."""
        return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    @staticmethod
    def pbkdf2_sha256(password: str, salt: bytes, iterations: int = 100_000) -> PHCHashRecord:
        """Standard PBKDF2-HMAC-SHA256 Key Derivation Function."""
        dk = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt,
            iterations=iterations,
            dklen=32
        )
        return PHCHashRecord(
            algorithm="pbkdf2-sha256",
            params={"i": iterations},
            salt_hex=salt.hex(),
            hash_hex=dk.hex()
        )

    @staticmethod
    def scrypt_hash(password: str, salt: bytes, n: int = 16384, r: int = 8, p: int = 1) -> PHCHashRecord:
        """Modern memory-hard scrypt KDF (High resistance to GPU/ASIC clusters)."""
        if not hasattr(hashlib, "scrypt"):
            raise NotImplementedError("scrypt is not supported on this OpenSSL build.")
        dk = hashlib.scrypt(
            password=password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=0,
            dklen=32
        )
        return PHCHashRecord(
            algorithm="scrypt",
            params={"n": n, "r": r, "p": p},
            salt_hex=salt.hex(),
            hash_hex=dk.hex()
        )


# ==============================================================================
# 3. EXPERIMENT 1: VULNERABILITIES OF RAW FAST HASHES & AVALANCHE EFFECT
# ==============================================================================

class ExperimentRawHashes:
    """Demonstrates identical hash collisions and bitwise diffusion."""

    @staticmethod
    def run_identical_password_leak_demo():
        print_section("VULNERABILITY: The Identical Password Leak in Unsalted Hashes")
        print("When raw or unsalted hashes are used, identical passwords produce identical digests.")
        print("This allows attackers to detect password reuse across accounts and use pre-computed tables.\n")

        users = [
            ("Alice (Finance)", "SuperSecret123"),
            ("Bob (Engineering)", "Winter2024!"),
            ("Charlie (HR)", "SuperSecret123"),  # Same as Alice
            ("David (Admin)", "Summer2024!")
        ]

        print(
            f"{ANSI.BOLD}{'User Account':<22} | {'Plaintext Password':<18} | {'Raw SHA-256 Stored Digest'}{ANSI.RESET}")
        print("-" * 90)

        hashes = []
        for user, pwd in users:
            h = CryptoEngine.raw_sha256(pwd)
            hashes.append(h)
            # Highlight identical hashes in red
            color = ANSI.RED if hashes.count(h) > 1 or [u[1] for u in users].count(pwd) > 1 else ANSI.GREEN
            print(f"{user:<22} | {pwd:<18} | {color}{h}{ANSI.RESET}")

        print(f"\n{ANSI.RED}{ANSI.BOLD}[!] CRITICAL OBSERVATION:{ANSI.RESET}")
        print("Notice that Alice and Charlie have the EXACT same hash signature:")
        print(f"    {ANSI.RED}{hashes[0]}{ANSI.RESET}")
        print("An attacker breaching this database instantly knows Alice and Charlie share credentials,")
        print("even without cracking the original plaintext.")

    @staticmethod
    def run_avalanche_effect_visualizer():
        print_section("CRYPTOGRAPHIC PROPERTY: The Avalanche Effect (Diffusion)")
        print("A secure hash function must exhibit high diffusion: flipping a single bit in the input")
        print("must flip approximately 50% of the bits in the resulting digest.\n")

        p1 = "Password123"
        p2 = "password123"  # Single letter case change ('P' -> 'p')

        h1 = CryptoEngine.raw_sha256(p1)
        h2 = CryptoEngine.raw_sha256(p2)

        # Convert hexadecimal digests to binary bitstrings
        bin1 = bin(int(h1, 16))[2:].zfill(256)
        bin2 = bin(int(h2, 16))[2:].zfill(256)

        # Compute bitwise Hamming Distance
        diff_bits = sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
        percentage = (diff_bits / 256.0) * 100.0

        print(f"Input 1: '{ANSI.CYAN}{p1}{ANSI.RESET}' -> SHA-256: {h1}")
        print(f"Input 2: '{ANSI.CYAN}{p2}{ANSI.RESET}' -> SHA-256: {h2}\n")

        print("Binary Bitstring Comparison (First 64 bits):")
        formatted_bits = []
        for b1, b2 in zip(bin1[:64], bin2[:64]):
            if b1 != b2:
                formatted_bits.append(f"{ANSI.RED}{b2}{ANSI.RESET}")
            else:
                formatted_bits.append(f"{ANSI.DIM}{b2}{ANSI.RESET}")

        print(f"  P1 Bits : {bin1[:64]}")
        print(f"  P2 Bits : {''.join(formatted_bits)}")
        print(f"\n{ANSI.BOLD}Hamming Distance:{ANSI.RESET} {diff_bits} out of 256 bits flipped.")
        print(
            f"{ANSI.BOLD}Avalanche Diffusion Rate:{ANSI.RESET} {ANSI.GREEN if 45 <= percentage <= 55 else ANSI.YELLOW}{percentage:.2f}%{ANSI.RESET} (Ideal is ~50.0%)")


# ==============================================================================
# 4. EXPERIMENT 2: CRYPTOGRAPHIC SALTING & RAINBOW TABLE DEFENSE
# ==============================================================================

class ExperimentSalting:
    """Demonstrates how CSPRNG salts neutralize rainbow tables and identical hashes."""

    @staticmethod
    def run_salt_defense_demonstration():
        print_section("DEFENSE: Unique CSPRNG Cryptographic Salting")
        print("A salt is a cryptographically random, unique sequence appended to passwords before hashing.")
        print("Salts do NOT need to be secret, but MUST be globally unique per user account.\n")

        password = "UniversalPassword99#"
        print(
            f"Simulating 4 different users who all choose the exact same password: '{ANSI.CYAN}{password}{ANSI.RESET}'\n")

        print(
            f"{ANSI.BOLD}{'User':<10} | {'Random Salt (16-Bytes Hex)':<34} | {'Stored Salted SHA-256 Digest'}{ANSI.RESET}")
        print("-" * 115)

        for u in ["User_A", "User_B", "User_C", "User_D"]:
            salt = secrets.token_bytes(16)
            digest = CryptoEngine.salted_sha256(password, salt)
            print(f"{u:<10} | {salt.hex():<34} | {ANSI.GREEN}{digest}{ANSI.RESET}")

        print(f"\n{ANSI.GREEN}{ANSI.BOLD}[✓] SECURITY RESULT:{ANSI.RESET}")
        print("Despite having identical passwords, every stored hash is completely unique.")
        print("1. Pre-computed Rainbow Tables are rendered mathematically useless.")
        print("2. Attackers cannot crack passwords in parallel; each account requires separate computation.")


# ==============================================================================
# 5. EXPERIMENT 3: TIMING ATTACKS & CONSTANT-TIME VERIFICATION
# ==============================================================================

class ExperimentTimingAttacks:
    """Demonstrates side-channel vulnerabilities in naive string comparisons."""

    @staticmethod
    def vulnerable_compare(known: bytes, candidate: bytes) -> bool:
        """
        Vulnerable short-circuit comparison.
        Returns False as soon as the first mismatched byte is encountered.
        """
        if len(known) != len(candidate):
            return False
        for i in range(len(known)):
            if known[i] != candidate[i]:
                return False  # Early exit leaks timing information!
        return True

    @classmethod
    def run_timing_attack_analysis(cls):
        print_section("SIDE-CHANNEL DEFENSE: Timing Leakage vs. hmac.compare_digest")
        print("Standard string comparison ('==') terminates immediately on the first mismatched byte.")
        print("Attackers measuring remote nanosecond response deltas can deduce secret characters one by one.\n")

        secret = b"a" * 64
        # Candidate 1: Fails on index 0
        candidate_bad_start = b"z" + (b"a" * 63)
        # Candidate 2: Matches 63 bytes, fails on last index
        candidate_bad_end = (b"a" * 63) + b"z"
        # Candidate 3: Matches perfectly
        candidate_exact = b"a" * 64

        iterations = 200_000

        # Benchmark vulnerable comparison
        t_early = timeit.timeit(lambda: cls.vulnerable_compare(secret, candidate_bad_start), number=iterations)
        t_late = timeit.timeit(lambda: cls.vulnerable_compare(secret, candidate_bad_end), number=iterations)

        # Benchmark constant-time comparison
        t_hmac_early = timeit.timeit(lambda: hmac.compare_digest(secret, candidate_bad_start), number=iterations)
        t_hmac_late = timeit.timeit(lambda: hmac.compare_digest(secret, candidate_bad_end), number=iterations)

        print(
            f"{ANSI.BOLD}{'Comparison Method':<30} | {'Mismatched Position':<20} | {'Execution Time (200k runs)'}{ANSI.RESET}")
        print("-" * 80)
        print(f"{'Vulnerable Naive Loop':<30} | {'Index 0 (Early Exit)':<20} | {t_early:.6f} seconds")
        print(
            f"{'Vulnerable Naive Loop':<30} | {'Index 63 (Late Exit)':<20} | {ANSI.YELLOW}{t_late:.6f} seconds (LEAKS TIMING){ANSI.RESET}")
        print(f"{'hmac.compare_digest':<30} | {'Index 0 (Early Exit)':<20} | {t_hmac_early:.6f} seconds")
        print(
            f"{'hmac.compare_digest':<30} | {'Index 63 (Late Exit)':<20} | {ANSI.GREEN}{t_hmac_late:.6f} seconds (CONSTANT-TIME){ANSI.RESET}")

        print(f"\n{ANSI.BOLD}Analysis:{ANSI.RESET}")
        print(f"The vulnerable loop was {((t_late - t_early) / t_early) * 100:.1f}% slower when matching more bytes.")
        print(f"{ANSI.GREEN}[✓] Always use `hmac.compare_digest()` for cryptographic comparisons.{ANSI.RESET}")


# ==============================================================================
# 6. EXPERIMENT 4: FAST HASHES VS. KEY-STRETCHING KDFs & ATTACK ESTIMATION
# ==============================================================================

class ExperimentKDFBenchmark:
    """Benchmarks CPU work factors and computes attacker hardware cracking times."""

    @staticmethod
    def run_kdf_benchmark_arena():
        print_section("PERFORMANCE BATTLE: Fast Hashes vs. Password-Specific KDFs")
        print("General-purpose hashes (MD5, SHA-256) are optimized for file verification and are dangerously fast.")
        print("Password KDFs intentionally introduce computational work and memory-hardness to slow attackers.\n")

        test_pwd = "Correct-Horse-Battery-Staple-2024"
        salt = secrets.token_bytes(16)

        benchmarks = [
            ("Fast Hash: MD5 (Obsolete)", lambda: hashlib.md5(test_pwd.encode()).hexdigest(), 50_000, 100_000_000_000),
            ("Fast Hash: SHA-256 (General)", lambda: hashlib.sha256(test_pwd.encode()).hexdigest(), 50_000,
             30_000_000_000),
            ("KDF: PBKDF2 (1,000 rounds)", lambda: CryptoEngine.pbkdf2_sha256(test_pwd, salt, 1_000), 500, 20_000_000),
            ("KDF: PBKDF2 (100,000 rounds)", lambda: CryptoEngine.pbkdf2_sha256(test_pwd, salt, 100_000), 20, 250_000),
            ("KDF: PBKDF2 (600,000 rounds - OWASP)", lambda: CryptoEngine.pbkdf2_sha256(test_pwd, salt, 600_000), 5,
             45_000),
        ]

        if hasattr(hashlib, "scrypt"):
            benchmarks.append(
                ("KDF: scrypt (N=16384, r=8, p=1)", lambda: CryptoEngine.scrypt_hash(test_pwd, salt), 10, 15_000)
            )

        print(
            f"{ANSI.BOLD}{'Hashing Algorithm / Work Factor':<42} | {'Local Cost (ms)':<16} | {'8x RTX 4090 GPU Crack Speed'}{ANSI.RESET}")
        print("-" * 92)

        for name, fn, runs, attacker_gpu_rate in benchmarks:
            # Measure local duration
            start = time.perf_counter()
            for _ in range(runs):
                fn()
            total_elapsed = time.perf_counter() - start
            avg_ms = (total_elapsed / runs) * 1000.0

            rate_fmt = f"{attacker_gpu_rate:,.0f} guesses/sec"
            color = ANSI.RED if attacker_gpu_rate > 1_000_000_000 else (
                ANSI.YELLOW if attacker_gpu_rate > 500_000 else ANSI.GREEN)

            print(f"{name:<42} | {avg_ms:10.3f} ms     | {color}{rate_fmt}{ANSI.RESET}")

        print(
            f"\n{ANSI.BOLD}Theoretical Crack Time for an 8-Character Password (Alpha+Num = 2.18 Trillion combos):{ANSI.RESET}")
        print(f"  • {ANSI.RED}SHA-256 (Raw){ANSI.RESET}      : ~72 seconds on modern GPU cluster!")
        print(f"  • {ANSI.YELLOW}PBKDF2 (100k){ANSI.RESET}      : ~101 days")
        print(f"  • {ANSI.GREEN}scrypt / Argon2id{ANSI.RESET}  : ~4.6 years (Plus massive GPU VRAM exhaustion)")


# ==============================================================================
# 7. PRODUCTION USER CREDENTIAL STORE & SEAMLESS MIGRATION ENGINE
# ==============================================================================

@dataclass
class UserAccount:
    username: str
    phc_hash: str
    algorithm_family: str
    last_updated: str


class CredentialManager:
    """
    Manages user registration, constant-time verification, password changes,
    and automatic in-place hash algorithm upgrades.
    """

    def __init__(self):
        self.user_database: Dict[str, UserAccount] = {}
        self.active_policy_algo = "pbkdf2-sha256"
        self.active_pbkdf2_rounds = 100_000

    def register_user(self, username: str, password: str) -> None:
        """Provisions a new user using the current active security policy."""
        salt = secrets.token_bytes(16)
        record = CryptoEngine.pbkdf2_sha256(password, salt, self.active_pbkdf2_rounds)

        self.user_database[username.lower()] = UserAccount(
            username=username.lower(),
            phc_hash=record.serialize(),
            algorithm_family="pbkdf2-sha256",
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    def register_legacy_user(self, username: str, password: str, legacy_type: str = "raw_sha256") -> None:
        """Injects obsolete hashes to demonstrate auto-upgrade migration."""
        if legacy_type == "raw_sha256":
            phc_str = f"$sha256$$none${CryptoEngine.raw_sha256(password)}"
        elif legacy_type == "low_pbkdf2":
            salt = secrets.token_bytes(16)
            rec = CryptoEngine.pbkdf2_sha256(password, salt, iterations=1_000)
            phc_str = rec.serialize()
        else:
            raise ValueError("Unknown legacy type.")

        self.user_database[username.lower()] = UserAccount(
            username=username.lower(),
            phc_hash=phc_str,
            algorithm_family=legacy_type,
            last_updated="2018-01-01 00:00:00"
        )

    def verify_and_upgrade(self, username: str, candidate_password: str) -> Tuple[bool, str]:
        """
        Verifies login credentials and automatically upgrades outdated hashes
        in-place without disrupting the user experience.
        """
        uname = username.lower()
        if uname not in self.user_database:
            return False, "User does not exist."

        user = self.user_database[uname]
        record = PHCHashRecord.deserialize(user.phc_hash)
        authenticated = False

        # Verify depending on stored algorithm
        if record.algorithm == "sha256":
            # Legacy raw SHA-256 check
            cand_hash = CryptoEngine.raw_sha256(candidate_password)
            authenticated = hmac.compare_digest(cand_hash, record.hash_hex)

        elif record.algorithm == "pbkdf2-sha256":
            salt = bytes.fromhex(record.salt_hex)
            iterations = record.params.get("i", 100_000)
            check_rec = CryptoEngine.pbkdf2_sha256(candidate_password, salt, iterations)
            authenticated = hmac.compare_digest(check_rec.hash_hex, record.hash_hex)

        elif record.algorithm == "scrypt":
            salt = bytes.fromhex(record.salt_hex)
            check_rec = CryptoEngine.scrypt_hash(candidate_password, salt, record.params["n"], record.params["r"],
                                                 record.params["p"])
            authenticated = hmac.compare_digest(check_rec.hash_hex, record.hash_hex)

        if not authenticated:
            return False, "Invalid password."

        # Check if algorithm or work factor requires auto-upgrade
        needs_upgrade = False
        upgrade_reason = ""

        if record.algorithm == "sha256":
            needs_upgrade = True
            upgrade_reason = "Migrated from insecure unsalted SHA-256 to PBKDF2-HMAC-SHA256"
        elif record.algorithm == "pbkdf2-sha256" and record.params.get("i", 0) < self.active_pbkdf2_rounds:
            needs_upgrade = True
            upgrade_reason = f"Upgraded work factor from {record.params.get('i')} to {self.active_pbkdf2_rounds} iterations"

        if needs_upgrade:
            new_salt = secrets.token_bytes(16)
            new_record = CryptoEngine.pbkdf2_sha256(candidate_password, new_salt, self.active_pbkdf2_rounds)
            user.phc_hash = new_record.serialize()
            user.algorithm_family = "pbkdf2-sha256"
            user.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
            return True, f"Authentication Successful! [AUTOMATIC SECURITY UPGRADE: {upgrade_reason}]"

        return True, "Authentication Successful! (Hash conforms to current security policy)"

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Validates current credentials and generates a new salt and hash."""
        success, msg = self.verify_and_upgrade(username, old_password)
        if not success:
            return False, f"Password change rejected: {msg}"

        if old_password == new_password:
            return False, "New password cannot be identical to current password."

        new_salt = secrets.token_bytes(16)
        new_record = CryptoEngine.pbkdf2_sha256(new_password, new_salt, self.active_pbkdf2_rounds)

        user = self.user_database[username.lower()]
        user.phc_hash = new_record.serialize()
        user.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        return True, "Password successfully updated with fresh salt and updated work factor."


# ==============================================================================
# 8. INTERACTIVE CLI & GUIDED LABORATORY TOUR
# ==============================================================================

class LaboratoryHarness:
    """Console interface and interactive scenario runner."""

    def __init__(self):
        self.mgr = CredentialManager()
        self._seed_sample_identities()

    def _seed_sample_identities(self):
        # 1. Modern user with strong PBKDF2
        self.mgr.register_user("alice_modern", "CorporateShield2024!")
        # 2. Legacy user created in 2018 with raw SHA-256
        self.mgr.register_legacy_user("bob_legacy_sha256", "Summer2018!", "raw_sha256")
        # 3. Legacy user with low-iteration PBKDF2 (1,000 rounds)
        self.mgr.register_legacy_user("charlie_legacy_kdf", "Pass12345", "low_pbkdf2")

    def run_guided_tour(self):
        print_header("Guided Full Laboratory Tour")
        print("This comprehensive walk-through covers foundational vulnerabilities, defenses, and modern KDFs.")

        input(f"\n{ANSI.CYAN}Press Enter to start Experiment 1: The Identical Password Leak...{ANSI.RESET}")
        ExperimentRawHashes.run_identical_password_leak_demo()

        input(f"\n{ANSI.CYAN}Press Enter to start Experiment 2: The Avalanche Effect Visualizer...{ANSI.RESET}")
        ExperimentRawHashes.run_avalanche_effect_visualizer()

        input(f"\n{ANSI.CYAN}Press Enter to start Experiment 3: Cryptographic Salting Defense...{ANSI.RESET}")
        ExperimentSalting.run_salt_defense_demonstration()

        input(
            f"\n{ANSI.CYAN}Press Enter to start Experiment 4: Timing Attacks & Constant-Time Comparison...{ANSI.RESET}")
        ExperimentTimingAttacks.run_timing_attack_analysis()

        input(f"\n{ANSI.CYAN}Press Enter to start Experiment 5: Fast Hashes vs. KDF Benchmark Arena...{ANSI.RESET}")
        ExperimentKDFBenchmark.run_kdf_benchmark_arena()

        input(
            f"\n{ANSI.CYAN}Press Enter to start Experiment 6: In-Place Hash Upgrades & Account Management...{ANSI.RESET}")
        self.demo_auto_upgrade()

    def demo_auto_upgrade(self):
        print_section("SEAMLESS CREDENTIAL MIGRATION DEMO")
        print("Legacy systems often hold outdated hashes. When a user authenticates,")
        print("we can verify against the legacy hash and immediately upgrade to modern PBKDF2/scrypt in-place.\n")

        print("Current Database State:")
        self.print_user_table()

        print(
            f"\n[*] Authenticating legacy user '{ANSI.YELLOW}bob_legacy_sha256{ANSI.RESET}' with correct password 'Summer2018!'...")
        ok, msg = self.mgr.verify_and_upgrade("bob_legacy_sha256", "Summer2018!")
        print(f"Result: {ANSI.GREEN if ok else ANSI.RED}{msg}{ANSI.RESET}\n")

        print("Updated Database State (Notice Bob's hash format and algorithm updated):")
        self.print_user_table()

    def print_user_table(self):
        print(f"{ANSI.BOLD}{'Username':<22} | {'Algorithm Family':<18} | {'PHC Stored Hash Record'}{ANSI.RESET}")
        print("-" * 105)
        for u in self.mgr.user_database.values():
            trunc_hash = u.phc_hash[:55] + "..." if len(u.phc_hash) > 55 else u.phc_hash
            print(f"{u.username:<22} | {u.algorithm_family:<18} | {ANSI.CYAN}{trunc_hash}{ANSI.RESET}")

    def main_menu(self):
        while True:
            print_header("Password Hashing Laboratory Menu")
            print(" 1. Run Complete Guided Tour (All Experiments)")
            print(" 2. Experiment 1: The Identical Password Leak & Avalanche Effect")
            print(" 3. Experiment 2: Cryptographic Salting & Rainbow Table Defense")
            print(" 4. Experiment 3: Timing Attacks & Constant-Time (hmac.compare_digest)")
            print(" 5. Experiment 4: KDF Benchmark Arena (Fast vs. Slow Key-Stretching)")
            print(" 6. Experiment 5: Credential Lifecycle & Automatic Hash Migration")
            print(" 7. User Sandbox: Register Account / Authenticate / Change Password")
            print(" 0. Exit Laboratory")
            print(f"{ANSI.CYAN}{'=' * 80}{ANSI.RESET}")

            choice = input(f"{ANSI.BOLD}Select an Option [0-7]: {ANSI.RESET}").strip()

            if choice == "1":
                self.run_guided_tour()
            elif choice == "2":
                ExperimentRawHashes.run_identical_password_leak_demo()
                ExperimentRawHashes.run_avalanche_effect_visualizer()
            elif choice == "3":
                ExperimentSalting.run_salt_defense_demonstration()
            elif choice == "4":
                ExperimentTimingAttacks.run_timing_attack_analysis()
            elif choice == "5":
                ExperimentKDFBenchmark.run_kdf_benchmark_arena()
            elif choice == "6":
                self.demo_auto_upgrade()
            elif choice == "7":
                self.interactive_sandbox()
            elif choice == "0":
                print(f"\n{ANSI.GREEN}[✓] Laboratory session closed.{ANSI.RESET}")
                sys.exit(0)
            else:
                print(f"{ANSI.RED}[!] Invalid choice.{ANSI.RESET}")

            input(f"\n{ANSI.DIM}Press Enter to return to main menu...{ANSI.RESET}")

    def interactive_sandbox(self):
        print_section("INTERACTIVE CREDENTIAL SANDBOX")
        print("1. Register New User")
        print("2. Authenticate User")
        print("3. Change Password")
        print("4. Inspect Raw PHC String")

        opt = input("Select sub-action [1-4]: ").strip()
        if opt == "1":
            u = input("Username: ").strip()
            p = input("Password: ").strip()
            self.mgr.register_user(u, p)
            print(
                f"{ANSI.GREEN}[✓] Registered '{u}' with PBKDF2-HMAC-SHA256 (100k rounds) and CSPRNG salt.{ANSI.RESET}")
        elif opt == "2":
            u = input("Username: ").strip()
            p = input("Password: ").strip()
            ok, msg = self.mgr.verify_and_upgrade(u, p)
            color = ANSI.GREEN if ok else ANSI.RED
            print(f"{color}{msg}{ANSI.RESET}")
        elif opt == "3":
            u = input("Username: ").strip()
            old_p = input("Current Password: ").strip()
            new_p = input("New Password: ").strip()
            ok, msg = self.mgr.change_password(u, old_p, new_p)
            color = ANSI.GREEN if ok else ANSI.RED
            print(f"{color}{msg}{ANSI.RESET}")
        elif opt == "4":
            u = input("Username to inspect: ").strip().lower()
            if u in self.mgr.user_database:
                rec = self.mgr.user_database[u]
                print(f"\nRaw Serialized PHC String for {u}:")
                print(f"{ANSI.YELLOW}{rec.phc_hash}{ANSI.RESET}")
                parsed = PHCHashRecord.deserialize(rec.phc_hash)
                print(f"Algorithm : {parsed.algorithm}")
                print(f"Parameters: {parsed.params}")
                print(f"Salt (Hex): {parsed.salt_hex}")
                print(f"Hash (Hex): {parsed.hash_hex}")
            else:
                print(f"{ANSI.RED}User not found.{ANSI.RESET}")


# ==============================================================================
# 9. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    try:
        lab = LaboratoryHarness()
        # If run with --auto, execute full guided tour and exit
        if len(sys.argv) > 1 and sys.argv[1] in ("--auto", "-a", "--tour"):
            ExperimentRawHashes.run_identical_password_leak_demo()
            ExperimentRawHashes.run_avalanche_effect_visualizer()
            ExperimentSalting.run_salt_defense_demonstration()
            ExperimentTimingAttacks.run_timing_attack_analysis()
            ExperimentKDFBenchmark.run_kdf_benchmark_arena()
            lab.demo_auto_upgrade()
            sys.exit(0)

        lab.main_menu()
    except KeyboardInterrupt:
        print(f"\n{ANSI.YELLOW}[!] Laboratory session aborted.{ANSI.RESET}")
        sys.exit(0)
import os
import sys
import csv
import re
import math
import time
import json
import hashlib
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font as tkFont


# ==============================================================================
# 1. ENUMS, DATA MODELS & DEFAULT POLICIES
# ==============================================================================

class ComplianceStatus(Enum):
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    NON_COMPLIANT = "NON_COMPLIANT"
    CRITICAL = "CRITICAL"


@dataclass
class PolicyConfiguration:
    """Configurable organizational password governance policy."""
    min_length: int = 12
    max_length: int = 128
    require_lowercase: bool = True
    require_uppercase: bool = True
    require_digits: bool = True
    require_symbols: bool = True
    disallow_username: bool = True
    disallow_company_tokens: bool = True
    company_tokens: List[str] = field(default_factory=lambda: ["acme", "corp", "enterprise", "global", "2024", "2023"])
    max_repeated_chars: int = 3
    max_sequential_chars: int = 3
    passphrase_length_waiver: int = 18  # Length threshold where symbol/digit requirements are waived
    disallow_dictionary_words: bool = True


@dataclass
class UserCredential:
    """User directory record model."""
    username: str
    password: str
    department: str
    role: str
    email: str = ""


@dataclass
class AuditResult:
    """Comprehensive compliance evaluation record for an account."""
    user: UserCredential
    compliance_score: float
    status: ComplianceStatus
    violations: List[str]
    warnings: List[str]
    is_duplicate: bool
    duplicate_cluster_size: int
    shared_with_accounts: List[str]
    is_privileged_cross_reuse: bool
    entropy_bits: float
    remediation_advice: List[str]


# Top common passwords embedded directly to eliminate external dependencies
EMBEDDED_PASSWORD_BLACKLIST = {
    "password", "123456", "123456789", "guest", "qwerty", "12345678", "111111",
    "12345", "123123", "dragon", "welcome", "ninja", "master", "monkey",
    "shadow", "football", "baseball", "superman", "jordan", "killer", "trustno1",
    "hunter2", "princess", "sunshine", "iloveyou", "admin", "admin123", "pass123",
    "secret", "secret123", "root", "toor", "system", "oracle", "login",
    "default", "access", "test", "testing", "letmein", "changeme", "computer",
    "internet", "qwertyuiop", "asdfghjkl", "zxcvbnm", "charlie", "merlin",
    "ranger", "wizard", "starwars", "pokemon", "welcome1", "welcome123",
    "password123", "p@ssword", "p@ssw0rd", "admin@123", "root123", "P@sswOrd123!"
}


# ==============================================================================
# 2. PATTERN DETECTION & COMPLIANCE EVALUATION ENGINE
# ==============================================================================

class PatternDetectionEngine:
    """Identifies structural weaknesses, dictionary matches, and keyboard walks."""

    KEYBOARD_SEQUENCES = [
        "1234567890", "0987654321",
        "qwertyuiop", "poiuytrewq",
        "asdfghjkl", "lkjhgfdsa",
        "zxcvbnm", "mnbvcxz",
        "abcdefghijklmnopqrstuvwxyz", "zyxwvutsrqponmlkjihgfedcba"
    ]

    @classmethod
    def check_keyboard_walk(cls, pwd: str, max_seq: int) -> Optional[str]:
        """Detects sequential key runs exceeding the threshold."""
        pwd_lower = pwd.lower()
        if len(pwd_lower) < max_seq:
            return None

        for seq in cls.KEYBOARD_SEQUENCES:
            for i in range(len(seq) - max_seq + 1):
                sub = seq[i:i + max_seq]
                if sub in pwd_lower:
                    return sub
        return None

    @classmethod
    def check_repeated_characters(cls, pwd: str, max_rep: int) -> Optional[str]:
        """Detects repetitive identical character runs."""
        pattern = re.compile(r"(.)\1{" + str(max_rep - 1) + r",}")
        match = pattern.search(pwd)
        if match:
            return match.group(0)
        return None

    @classmethod
    def check_token_presence(cls, pwd: str, token: str) -> bool:
        """Case-insensitive presence check for tokens or usernames."""
        if not token or len(token) < 3:
            return False
        return token.lower() in pwd.lower()

    @staticmethod
    def calculate_entropy(pwd: str) -> float:
        """Calculates theoretical Shannon entropy in bits."""
        if not pwd:
            return 0.0
        pool = 0
        if any(c.islower() for c in pwd): pool += 26
        if any(c.isupper() for c in pwd): pool += 26
        if any(c.isdigit() for c in pwd): pool += 10
        if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/`~" for c in pwd): pool += 32
        pool = max(pool, 1)
        return len(pwd) * math.log2(pool)


class AuditEvaluator:
    """Evaluates user datasets against configured policy and clusters duplicates."""

    def __init__(self, policy: PolicyConfiguration):
        self.policy = policy

    def evaluate_directory(self, users: List[UserCredential]) -> List[AuditResult]:
        """Runs batch evaluation, duplicate hash clustering, and scoring."""
        # 1. Cluster duplicate passwords using cryptographic hashes
        hash_to_accounts: Dict[str, List[UserCredential]] = defaultdict(list)
        for u in users:
            p_hash = hashlib.sha256(u.password.encode("utf-8")).hexdigest()
            hash_to_accounts[p_hash].append(u)

        results: List[AuditResult] = []

        # 2. Evaluate individual credential compliance
        for u in users:
            pwd = u.password
            p_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
            shared_accounts = hash_to_accounts[p_hash]
            is_dup = len(shared_accounts) > 1
            other_shared = [other.username for other in shared_accounts if other.username != u.username]

            # Detect privileged cross-role reuse
            is_cross_role = False
            if is_dup:
                roles = {acct.role.lower() for acct in shared_accounts}
                if any("admin" in r or "exec" in r for r in roles) and len(roles) > 1:
                    is_cross_role = True

            violations: List[str] = []
            warnings: List[str] = []
            remediations: List[str] = []
            score = 100.0

            # Rule: Length constraints
            if len(pwd) < self.policy.min_length:
                violations.append(f"Insufficient length: {len(pwd)} chars (Minimum required: {self.policy.min_length})")
                remediations.append(f"Increase password length to at least {self.policy.min_length} characters.")
                score -= 30.0
            elif len(pwd) > self.policy.max_length:
                violations.append(f"Excessive length: {len(pwd)} chars (Maximum allowed: {self.policy.max_length})")
                score -= 10.0

            # Rule: Passphrase length exemption waiver
            is_passphrase = len(pwd) >= self.policy.passphrase_length_waiver

            # Rule: Character Diversity
            if not is_passphrase:
                if self.policy.require_lowercase and not any(c.islower() for c in pwd):
                    violations.append("Missing required lowercase letter [a-z]")
                    remediations.append("Include at least one lowercase character.")
                    score -= 10.0
                if self.policy.require_uppercase and not any(c.isupper() for c in pwd):
                    violations.append("Missing required uppercase letter [A-Z]")
                    remediations.append("Include at least one uppercase character.")
                    score -= 10.0
                if self.policy.require_digits and not any(c.isdigit() for c in pwd):
                    violations.append("Missing required numeric digit [0-9]")
                    remediations.append("Include at least one numerical digit.")
                    score -= 10.0
                if self.policy.require_symbols and not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/`~" for c in pwd):
                    violations.append("Missing required special symbol (!@#$...)")
                    remediations.append("Include at least one special symbol.")
                    score -= 10.0
            else:
                warnings.append("Passphrase length waiver active (character complexity classes relaxed)")

            # Rule: Contains Username or Email handle
            if self.policy.disallow_username:
                if PatternDetectionEngine.check_token_presence(pwd, u.username):
                    violations.append(f"Contains account username string '{u.username}'")
                    remediations.append("Remove personal identifier / username from password.")
                    score -= 20.0
                if u.email and PatternDetectionEngine.check_token_presence(pwd, u.email.split("@")[0]):
                    violations.append("Contains email local-part prefix")
                    remediations.append("Remove email prefix from password.")
                    score -= 15.0

            # Rule: Company Brand / Organization Tokens
            if self.policy.disallow_company_tokens:
                for tok in self.policy.company_tokens:
                    if PatternDetectionEngine.check_token_presence(pwd, tok):
                        violations.append(f"Contains predictable enterprise token '{tok}'")
                        remediations.append(f"Remove corporate keyword '{tok}'.")
                        score -= 15.0
                        break

            # Rule: Sequential Keyboard Walks
            walk = PatternDetectionEngine.check_keyboard_walk(pwd, self.policy.max_sequential_chars)
            if walk:
                violations.append(f"Sequential keyboard/character walk detected '{walk}'")
                remediations.append(f"Eliminate predictable sequence '{walk}'.")
                score -= 15.0

            # Rule: Repetitive Character Runs
            rep = PatternDetectionEngine.check_repeated_characters(pwd, self.policy.max_repeated_chars)
            if rep:
                violations.append(f"Repetitive character cluster detected '{rep}'")
                remediations.append(f"Avoid repetitive characters like '{rep}'.")
                score -= 10.0

            # Rule: Embedded Dictionary Blacklist
            if self.policy.disallow_dictionary_words and pwd.lower() in EMBEDDED_PASSWORD_BLACKLIST:
                violations.append("Exact match against common breached password blacklist")
                remediations.append("Select a completely unique credential not present in breach dictionaries.")
                score -= 40.0

            # Rule: Duplicate Password Reuse
            if is_dup:
                violations.append(f"Password reused across {len(shared_accounts)} organizational accounts")
                remediations.append("Rotate credential to a globally unique password.")
                score -= 25.0
                if is_cross_role:
                    violations.append("CRITICAL: Privileged account sharing password with standard/contractor user!")
                    remediations.append("Immediately revoke and isolate privileged credentials.")
                    score -= 30.0

            score = max(0.0, min(100.0, score))
            entropy = PatternDetectionEngine.calculate_entropy(pwd)

            # Determine Compliance Status
            if score >= 85 and not violations:
                status = ComplianceStatus.COMPLIANT
            elif score >= 65:
                status = ComplianceStatus.WARNING
            elif score >= 40:
                status = ComplianceStatus.NON_COMPLIANT
            else:
                status = ComplianceStatus.CRITICAL

            results.append(AuditResult(
                user=u,
                compliance_score=score,
                status=status,
                violations=violations,
                warnings=warnings,
                is_duplicate=is_dup,
                duplicate_cluster_size=len(shared_accounts),
                shared_with_accounts=other_shared,
                is_privileged_cross_reuse=is_cross_role,
                entropy_bits=entropy,
                remediation_advice=remediations
            ))

        return results


# ==============================================================================
# 3. SYNTHETIC ENTERPRISE DATASET GENERATOR
# ==============================================================================

class SyntheticDatasetGenerator:
    """Seeds rich corporate test directories with intentional realistic flaws."""

    @classmethod
    def generate_benchmark_directory(cls) -> List[UserCredential]:
        users = [
            # High-Privilege Accounts
            UserCredential("admin_sarah", "AcmeAdmin2024!", "IT & Security", "IT Administrator",
                           "sarah.admin@acme.corp"),
            UserCredential("admin_carlos", "P@ssword123", "IT & Security", "Systems Architect",
                           "carlos.admin@acme.corp"),  # Blacklist match
            UserCredential("cfo_richard", "Spring2024!", "Executive", "Chief Financial Officer",
                           "richard.cfo@acme.corp"),  # Token violation
            UserCredential("ceo_elena", "correct-horse-battery-staple-99#", "Executive", "Chief Executive Officer",
                           "elena.ceo@acme.corp"),  # Compliant Passphrase

            # Cross-Privilege Duplicate Cluster (Admin & Contractor share same password)
            UserCredential("devops_dave", "EnterpriseSharedSecret#1", "Engineering", "Lead DevOps",
                           "dave.dev@acme.corp"),
            UserCredential("contractor_mike", "EnterpriseSharedSecret#1", "External Vendors", "Contractor",
                           "mike.vendor@acme.corp"),

            # Common Staff Accounts
            UserCredential("jordan_sales", "qwerty123456", "Sales & Marketing", "Account Executive",
                           "jordan@acme.corp"),  # Keyboard walk
            UserCredential("alice_hr", "hr_alice_2024", "Human Resources", "HR Generalist", "alice.hr@acme.corp"),
            # Username in password
            UserCredential("bob_eng", "bob_eng", "Engineering", "Frontend Engineer", "bob@acme.corp"),  # Exact username
            UserCredential("carol_eng", "K9#mQ2$vL9!zP8*", "Engineering", "Backend Engineer", "carol@acme.corp"),
            # Fully Compliant
            UserCredential("david_fin", "111111111111", "Finance & Accounting", "Staff Accountant",
                           "david.fin@acme.corp"),  # Repetitive
            UserCredential("emma_legal", "Password123", "Legal & Compliance", "General Counsel",
                           "emma.legal@acme.corp"),  # Blacklist match
            UserCredential("frank_ops", "AcmeGlobal2024", "Operations", "Logistics Coordinator", "frank@acme.corp"),
            # Brand tokens
            UserCredential("grace_qa", "qa_testing_pw!", "Engineering", "QA Engineer", "grace@acme.corp"),
            UserCredential("henry_support", "Short1!", "Customer Support", "Tier 1 Specialist", "henry@acme.corp"),
            # Too short
            UserCredential("isabel_sales", "EnterpriseSharedSecret#1", "Sales & Marketing", "Sales Representative",
                           "isabel@acme.corp")  # Part of reuse cluster
        ]
        return users


# ==============================================================================
# 4. CUSTOM CANVAS VISUALIZATIONS (RADIAL GAUGE & BAR CHART)
# ==============================================================================

class RadialComplianceGauge(tk.Canvas):
    """Vector canvas rendering overall enterprise compliance percentage and grade."""

    def __init__(self, master, width=220, height=180, bg="#1e1e2f", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.render(0.0, "N/A", "F")

    def render(self, percentage: float, compliant_ratio: str, grade: str):
        self.delete("all")
        cx = self.width / 2
        cy = self.height * 0.72
        radius = self.width * 0.38
        stroke = 14

        # Track background
        self.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                        start=0, extent=180, style=tk.ARC, outline="#2c2c44", width=stroke)

        fraction = min(max(percentage / 100.0, 0.0), 1.0)
        extent = -180.0 * fraction

        color = "#e74c3c"
        if percentage >= 85:
            color = "#2ecc71"
        elif percentage >= 65:
            color = "#f1c40f"
        elif percentage >= 50:
            color = "#e67e22"

        if fraction > 0.005:
            self.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                            start=180, extent=extent, style=tk.ARC, outline=color, width=stroke)

        self.create_text(cx, cy - 24, text=f"{percentage:.1f}%", font=("Segoe UI", 22, "bold"), fill="#ffffff")
        self.create_text(cx, cy - 2, text=f"GRADE: {grade}", font=("Segoe UI", 10, "bold"), fill=color)
        self.create_text(cx, cy + 18, text=compliant_ratio, font=("Segoe UI", 8), fill="#8e8ea8")


class DepartmentBarChart(tk.Canvas):
    """Vector horizontal bar chart depicting department-level compliance rates."""

    def __init__(self, master, width=320, height=180, bg="#1e1e2f", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height

    def render(self, dept_scores: Dict[str, float]):
        self.delete("all")
        if not dept_scores:
            self.create_text(self.width / 2, self.height / 2, text="No Departmental Data", fill="#8e8ea8")
            return

        items = list(dept_scores.items())[:5]
        bar_h = 16
        gap = 14
        start_y = 15

        for idx, (dept, score) in enumerate(items):
            y = start_y + idx * (bar_h + gap)
            # Label
            self.create_text(10, y + 8, text=dept[:18], anchor=tk.W, font=("Segoe UI", 8, "bold"), fill="#f5f6fa")

            # Bar track
            track_x1 = 140
            track_x2 = self.width - 45
            track_w = track_x2 - track_x1
            self.create_rectangle(track_x1, y, track_x2, y + bar_h, fill="#2c2c44", outline="")

            # Fill bar
            color = "#2ecc71" if score >= 80 else ("#f1c40f" if score >= 60 else "#e74c3c")
            fill_w = track_w * (score / 100.0)
            self.create_rectangle(track_x1, y, track_x1 + fill_w, y + bar_h, fill=color, outline="")

            # Percentage text
            self.create_text(self.width - 38, y + 8, text=f"{score:.0f}%", anchor=tk.W, font=("Segoe UI", 8),
                             fill="#ffffff")


# ==============================================================================
# 5. ENTERPRISE APPLICATION GUI & INTERACTIVE CONTROLS
# ==============================================================================

class PolicyAuditorApp(tk.Tk):
    """Master Application Window containing all auditing views."""

    def __init__(self):
        super().__init__()
        self.title("Enterprise Password Policy Auditor & Credential Compliance Suite")
        self.geometry("1180x820")
        self.minsize(1020, 720)
        self.configure(bg="#141420")

        self.policy = PolicyConfiguration()
        self.evaluator = AuditEvaluator(self.policy)
        self.active_dataset: List[UserCredential] = []
        self.audit_results: List[AuditResult] = []

        self._setup_styles()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Seed initial synthetic dataset and run audit
        self.load_synthetic_dataset()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(".", background="#141420", foreground="#f5f6fa", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#141420")
        self.style.configure("TNotebook", background="#141420", tabmargins=[10, 10, 2, 0], borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#1e1e2f", foreground="#a4a4c1", padding=[16, 8],
                             font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#00d2d3"), ("active", "#282842")],
                       foreground=[("selected", "#0f172a"), ("active", "#ffffff")]
                       )

        self.style.configure("TLabelframe", background="#1e1e2f", borderwidth=1, relief="solid")
        self.style.configure("TLabelframe.Label", background="#1e1e2f", foreground="#00d2d3",
                             font=("Segoe UI", 10, "bold"))

        self.style.configure("Treeview",
                             background="#1a1a2b",
                             foreground="#f5f6fa",
                             fieldbackground="#1a1a2b",
                             rowheight=26,
                             font=("Segoe UI", 9)
                             )
        self.style.configure("Treeview.Heading",
                             background="#27273f",
                             foreground="#00d2d3",
                             relief="flat",
                             font=("Segoe UI", 9, "bold")
                             )

        self.style.configure("Primary.TButton", background="#00d2d3", foreground="#0f172a",
                             font=("Segoe UI", 9, "bold"), padding=6)
        self.style.map("Primary.TButton", background=[("active", "#01a3a4")])
        self.style.configure("Secondary.TButton", background="#2c2c44", foreground="#ffffff", font=("Segoe UI", 9),
                             padding=6)
        self.style.map("Secondary.TButton", background=[("active", "#3d3d5c")])

    def _build_header(self):
        hdr = tk.Frame(self, bg="#1e1e2f", height=60)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        title = tk.Label(hdr, text="ENTERPRISE PASSWORD POLICY AUDITOR", font=("Segoe UI", 13, "bold"), bg="#1e1e2f",
                         fg="#ffffff")
        title.pack(side=tk.LEFT, padx=20, pady=8)

        lbl = tk.Label(hdr, text="ACTIVE GOVERNANCE: NIST SP 800-63B ALIGNED", font=("Consolas", 9, "bold"),
                       bg="#1e1e2f", fg="#00d2d3")
        lbl.pack(side=tk.RIGHT, padx=20, pady=12)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

        # Tabs
        self.tab_dashboard = ttk.Frame(self.notebook, padding=12)
        self.tab_audit_grid = ttk.Frame(self.notebook, padding=12)
        self.tab_duplicates = ttk.Frame(self.notebook, padding=12)
        self.tab_policy_cfg = ttk.Frame(self.notebook, padding=12)
        self.tab_remediation = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_dashboard, text=" Executive Dashboard ")
        self.notebook.add(self.tab_audit_grid, text=" Account Audit Grid ")
        self.notebook.add(self.tab_duplicates, text=" Credential Reuse Matrix ")
        self.notebook.add(self.tab_policy_cfg, text=" Policy Configuration ")
        self.notebook.add(self.tab_remediation, text=" Remediation & Dossier ")

        self._build_tab_dashboard()
        self._build_tab_audit_grid()
        self._build_tab_duplicates()
        self._build_tab_policy_cfg()
        self._build_tab_remediation()

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self, bg="#1a1a2b", height=24)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.statusbar.pack_propagate(False)

        self.status_lbl = tk.Label(self.statusbar, text="Auditor Engine Ready.", font=("Segoe UI", 8), bg="#1a1a2b",
                                   fg="#8e8ea8")
        self.status_lbl.pack(side=tk.LEFT, padx=15)

    # --------------------------------------------------------------------------
    # TAB 1: EXECUTIVE DASHBOARD
    # --------------------------------------------------------------------------
    def _build_tab_dashboard(self):
        root = self.tab_dashboard

        # Action Bar Top
        action_bar = tk.Frame(root, bg="#141420")
        action_bar.pack(fill=tk.X, pady=(0, 10))

        btn_load_synth = ttk.Button(action_bar, text="Load Synthetic Dataset", style="Primary.TButton",
                                    command=self.load_synthetic_dataset)
        btn_load_synth.pack(side=tk.LEFT, padx=(0, 8))

        btn_load_csv = ttk.Button(action_bar, text="Import Custom CSV File...", style="Secondary.TButton",
                                  command=self.import_custom_csv)
        btn_load_csv.pack(side=tk.LEFT, padx=8)

        btn_export = ttk.Button(action_bar, text="Export Audit Dossier (CSV/JSON/TXT)...", style="Secondary.TButton",
                                command=self.export_reports_dialog)
        btn_export.pack(side=tk.RIGHT)

        # Upper Cards: Visual Gauge + Department Chart
        chart_row = tk.Frame(root, bg="#141420")
        chart_row.pack(fill=tk.X, pady=(0, 10))

        gauge_card = ttk.LabelFrame(chart_row, text=" Overall Organizational Compliance ", padding=10)
        gauge_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.gauge = RadialComplianceGauge(gauge_card, width=240, height=160, bg="#1e1e2f")
        self.gauge.pack(anchor=tk.CENTER)

        dept_card = ttk.LabelFrame(chart_row, text=" Departmental Compliance Breakdown ", padding=10)
        dept_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.dept_chart = DepartmentBarChart(dept_card, width=380, height=160, bg="#1e1e2f")
        self.dept_chart.pack(anchor=tk.CENTER)

        # Lower Metrics Cards
        kpi_card = ttk.LabelFrame(root, text=" Executive Threat & Policy KPI Metrics ", padding=12)
        kpi_card.pack(fill=tk.BOTH, expand=True)

        kpi_grid = tk.Frame(kpi_card, bg="#1e1e2f")
        kpi_grid.pack(fill=tk.BOTH, expand=True)

        self.kpi_total = self._create_kpi_cell(kpi_grid, "Total Accounts Audited", "0", 0, 0)
        self.kpi_compliant = self._create_kpi_cell(kpi_grid, "Compliant Accounts", "0", 0, 1, color="#2ecc71")
        self.kpi_non_compliant = self._create_kpi_cell(kpi_grid, "Violating Accounts", "0", 0, 2, color="#e74c3c")
        self.kpi_reused = self._create_kpi_cell(kpi_grid, "Reused / Shared Passwords", "0", 1, 0, color="#f1c40f")
        self.kpi_cross_priv = self._create_kpi_cell(kpi_grid, "Privileged Cross-Role Reuses", "0", 1, 1,
                                                    color="#e74c3c")
        self.kpi_avg_entropy = self._create_kpi_cell(kpi_grid, "Mean Key-Space Entropy", "0.0 bits", 1, 2)

    def _create_kpi_cell(self, parent, title: str, init_val: str, row: int, col: int,
                         color: str = "#ffffff") -> tk.Label:
        f = tk.Frame(parent, bg="#27273f", padx=14, pady=12, relief="flat")
        f.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)

        tk.Label(f, text=title, font=("Segoe UI", 9), bg="#27273f", fg="#8e8ea8").pack(anchor=tk.W)
        val_lbl = tk.Label(f, text=init_val, font=("Segoe UI", 16, "bold"), bg="#27273f", fg=color)
        val_lbl.pack(anchor=tk.W, pady=(4, 0))
        return val_lbl

    # --------------------------------------------------------------------------
    # TAB 2: AUDIT GRID (TREEVIEW)
    # --------------------------------------------------------------------------
    def _build_tab_audit_grid(self):
        root = self.tab_audit_grid

        # Filter bar
        filter_bar = tk.Frame(root, bg="#141420")
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(filter_bar, text="Filter Status:", bg="#141420", fg="#f5f6fa").pack(side=tk.LEFT, padx=(0, 6))
        self.combo_status_filter = ttk.Combobox(filter_bar,
                                                values=["ALL", "COMPLIANT", "WARNING", "NON_COMPLIANT", "CRITICAL"],
                                                state="readonly", width=14)
        self.combo_status_filter.set("ALL")
        self.combo_status_filter.pack(side=tk.LEFT, padx=6)
        self.combo_status_filter.bind("<<ComboboxSelected>>", lambda e: self._populate_treeview())

        tk.Label(filter_bar, text="Search User:", bg="#141420", fg="#f5f6fa").pack(side=tk.LEFT, padx=(12, 6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_bar, textvariable=self.search_var, width=18)
        self.search_entry.pack(side=tk.LEFT, padx=6)
        self.search_var.trace_add("write", lambda *a: self._populate_treeview())

        # Table
        cols = ("user", "dept", "role", "score", "status", "entropy", "violations")
        self.tree_audit = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
        self.tree_audit.heading("user", text="Account Username")
        self.tree_audit.heading("dept", text="Department")
        self.tree_audit.heading("role", text="Role Title")
        self.tree_audit.heading("score", text="Score (0-100)")
        self.tree_audit.heading("status", text="Policy Status")
        self.tree_audit.heading("entropy", text="Entropy (Bits)")
        self.tree_audit.heading("violations", text="Primary Violations Detected")

        self.tree_audit.column("user", width=130)
        self.tree_audit.column("dept", width=140)
        self.tree_audit.column("role", width=140)
        self.tree_audit.column("score", width=80, anchor=tk.CENTER)
        self.tree_audit.column("status", width=110, anchor=tk.CENTER)
        self.tree_audit.column("entropy", width=90, anchor=tk.E)
        self.tree_audit.column("violations", width=340)

        # Tags color styling
        self.tree_audit.tag_configure("COMPLIANT", foreground="#2ecc71")
        self.tree_audit.tag_configure("WARNING", foreground="#f1c40f")
        self.tree_audit.tag_configure("NON_COMPLIANT", foreground="#e67e22")
        self.tree_audit.tag_configure("CRITICAL", foreground="#e74c3c")

        self.tree_audit.pack(fill=tk.BOTH, expand=True)
        self.tree_audit.bind("<<TreeviewSelect>>", self._on_tree_select_user)

    # --------------------------------------------------------------------------
    # TAB 3: CREDENTIAL REUSE MATRIX
    # --------------------------------------------------------------------------
    def _build_tab_duplicates(self):
        root = self.tab_duplicates

        banner = ttk.LabelFrame(root, text=" Cross-Account Credential Reuse & Privilege Escalation Risks ", padding=10)
        banner.pack(fill=tk.X, pady=(0, 8))

        expl = (
            "DANGER: When standard users and administrators share identical passwords, compromising a low-tier account\n"
            "grants full domain administrative control. Passwords below are hashed via SHA-256 for cluster identification."
        )
        tk.Label(banner, text=expl, bg="#1e1e2f", fg="#f1c40f", justify=tk.LEFT, font=("Segoe UI", 9)).pack(anchor=tk.W)

        cols = ("hash", "cluster_size", "cross_priv", "accounts")
        self.tree_dups = ttk.Treeview(root, columns=cols, show="headings")
        self.tree_dups.heading("hash", text="Password Fingerprint (SHA-256)")
        self.tree_dups.heading("cluster_size", text="Reuse Count")
        self.tree_dups.heading("cross_priv", text="Privilege Escalation Risk")
        self.tree_dups.heading("accounts", text="Identified Reusing Accounts")

        self.tree_dups.column("hash", width=220)
        self.tree_dups.column("cluster_size", width=90, anchor=tk.CENTER)
        self.tree_dups.column("cross_priv", width=160, anchor=tk.CENTER)
        self.tree_dups.column("accounts", width=420)

        self.tree_dups.tag_configure("HIGH_RISK", foreground="#e74c3c")
        self.tree_dups.tag_configure("STANDARD_RISK", foreground="#f1c40f")

        self.tree_dups.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # TAB 4: POLICY CONFIGURATION
    # --------------------------------------------------------------------------
    def _build_tab_policy_cfg(self):
        root = self.tab_policy_cfg

        frame = ttk.LabelFrame(root, text=" Governance Parameters (NIST SP 800-63B / CIS Benchmark) ", padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        grid = tk.Frame(frame, bg="#1e1e2f")
        grid.pack(fill=tk.BOTH, expand=True)

        # Min / Max length
        tk.Label(grid, text="Minimum Length (Characters):", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0,
                                                                                             sticky=tk.W, pady=6)
        self.spin_min_len = ttk.Spinbox(grid, from_=6, to=64, width=6)
        self.spin_min_len.set(self.policy.min_length)
        self.spin_min_len.grid(row=0, column=1, sticky=tk.W, padx=10)

        # Passphrase waiver threshold
        tk.Label(grid, text="Passphrase Length Waiver (Waives character classes if length >=):", bg="#1e1e2f",
                 fg="#f5f6fa").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.spin_waiver = ttk.Spinbox(grid, from_=14, to=64, width=6)
        self.spin_waiver.set(self.policy.passphrase_length_waiver)
        self.spin_waiver.grid(row=1, column=1, sticky=tk.W, padx=10)

        # Checkboxes for complexity
        self.var_lower = tk.BooleanVar(value=self.policy.require_lowercase)
        self.var_upper = tk.BooleanVar(value=self.policy.require_uppercase)
        self.var_digits = tk.BooleanVar(value=self.policy.require_digits)
        self.var_symbols = tk.BooleanVar(value=self.policy.require_symbols)

        tk.Checkbutton(grid, text="Require Lowercase [a-z]", variable=self.var_lower, bg="#1e1e2f", fg="#f5f6fa",
                       selectcolor="#2c2c44").grid(row=2, column=0, sticky=tk.W, pady=4)
        tk.Checkbutton(grid, text="Require Uppercase [A-Z]", variable=self.var_upper, bg="#1e1e2f", fg="#f5f6fa",
                       selectcolor="#2c2c44").grid(row=3, column=0, sticky=tk.W, pady=4)
        tk.Checkbutton(grid, text="Require Numerical Digits [0-9]", variable=self.var_digits, bg="#1e1e2f",
                       fg="#f5f6fa", selectcolor="#2c2c44").grid(row=4, column=0, sticky=tk.W, pady=4)
        tk.Checkbutton(grid, text="Require Special Symbols (!@#$)", variable=self.var_symbols, bg="#1e1e2f",
                       fg="#f5f6fa", selectcolor="#2c2c44").grid(row=5, column=0, sticky=tk.W, pady=4)

        # Context-aware tokens
        self.var_disallow_user = tk.BooleanVar(value=self.policy.disallow_username)
        tk.Checkbutton(grid, text="Disallow Account Username in Password", variable=self.var_disallow_user,
                       bg="#1e1e2f", fg="#f5f6fa", selectcolor="#2c2c44").grid(row=6, column=0, sticky=tk.W, pady=4)

        self.var_disallow_corp = tk.BooleanVar(value=self.policy.disallow_company_tokens)
        tk.Checkbutton(grid, text="Disallow Company Keywords / Year Suffixes", variable=self.var_disallow_corp,
                       bg="#1e1e2f", fg="#f5f6fa", selectcolor="#2c2c44").grid(row=7, column=0, sticky=tk.W, pady=4)

        tk.Label(grid, text="Restricted Company Keywords (Comma-separated):", bg="#1e1e2f", fg="#f5f6fa").grid(row=8,
                                                                                                               column=0,
                                                                                                               sticky=tk.W,
                                                                                                               pady=6)
        self.entry_tokens = ttk.Entry(grid, width=40)
        self.entry_tokens.insert(0, ", ".join(self.policy.company_tokens))
        self.entry_tokens.grid(row=8, column=1, sticky=tk.W, padx=10)

        # Save Button
        btn_apply = ttk.Button(grid, text="Apply Policy & Re-Audit Entire Directory", style="Primary.TButton",
                               command=self._apply_policy_and_reaudit)
        btn_apply.grid(row=9, column=0, columnspan=2, pady=16, sticky=tk.W)

    def _apply_policy_and_reaudit(self):
        try:
            self.policy.min_length = int(self.spin_min_len.get())
            self.policy.passphrase_length_waiver = int(self.spin_waiver.get())
            self.policy.require_lowercase = self.var_lower.get()
            self.policy.require_uppercase = self.var_upper.get()
            self.policy.require_digits = self.var_digits.get()
            self.policy.require_symbols = self.var_symbols.get()
            self.policy.disallow_username = self.var_disallow_user.get()
            self.policy.disallow_company_tokens = self.var_disallow_corp.get()

            raw_tokens = self.entry_tokens.get().split(",")
            self.policy.company_tokens = [t.strip().lower() for t in raw_tokens if t.strip()]

            self.run_audit()
            messagebox.showinfo("Policy Updated", "Updated security policy applied. Directory re-audited successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please ensure numeric values are valid integers.")

    # --------------------------------------------------------------------------
    # TAB 5: REMEDIATION & USER DOSSIER
    # --------------------------------------------------------------------------
    def _build_tab_remediation(self):
        root = self.tab_remediation

        top_info = tk.Frame(root, bg="#141420")
        top_info.pack(fill=tk.X, pady=(0, 10))

        tk.Label(top_info,
                 text="Select an account from the Audit Grid to view individual compliance remediation dossiers.",
                 bg="#141420", fg="#8e8ea8").pack(side=tk.LEFT)

        # Dossier Text
        self.txt_dossier = scrolledtext.ScrolledText(root, bg="#1a1a2b", fg="#f5f6fa", font=("Consolas", 10),
                                                     relief="flat")
        self.txt_dossier.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # EVENT HANDLERS & CORE DATA PIPELINE
    # --------------------------------------------------------------------------
    def load_synthetic_dataset(self):
        """Loads the pre-seeded benchmark dataset."""
        self.active_dataset = SyntheticDatasetGenerator.generate_benchmark_directory()
        self.run_audit()
        self.status_lbl.config(text=f"Loaded Synthetic Benchmark Directory ({len(self.active_dataset)} accounts).")

    def import_custom_csv(self):
        """Allows importing external CSV file with arbitrary user credentials."""
        path = filedialog.askopenfilename(
            title="Import User Credential CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not path:
            return

        try:
            imported: List[UserCredential] = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Flexible column matching
                    uname = row.get("username") or row.get("user") or row.get("email") or "unknown"
                    pwd = row.get("password") or row.get("pass") or ""
                    dept = row.get("department") or row.get("dept") or "General"
                    role = row.get("role") or row.get("title") or "User"
                    email = row.get("email") or ""
                    if uname and pwd:
                        imported.append(
                            UserCredential(username=uname, password=pwd, department=dept, role=role, email=email))

            if not imported:
                messagebox.showwarning("Empty File",
                                       "No valid user credentials found in CSV. Expected headers: username, password, department, role")
                return

            self.active_dataset = imported
            self.run_audit()
            messagebox.showinfo("Import Success",
                                f"Successfully loaded {len(imported)} accounts from '{os.path.basename(path)}'.")
        except Exception as ex:
            messagebox.showerror("Import Error", f"Failed to parse CSV file: {ex}")

    def run_audit(self):
        """Executes full audit evaluation on the active dataset."""
        self.audit_results = self.evaluator.evaluate_directory(self.active_dataset)
        self._refresh_dashboard_metrics()
        self._populate_treeview()
        self._populate_duplicates_matrix()

    def _refresh_dashboard_metrics(self):
        total = len(self.audit_results)
        if total == 0:
            return

        compliant = sum(1 for r in self.audit_results if r.status == ComplianceStatus.COMPLIANT)
        non_compliant = total - compliant
        reused = sum(1 for r in self.audit_results if r.is_duplicate)
        cross_priv = sum(1 for r in self.audit_results if r.is_privileged_cross_reuse)
        avg_entropy = sum(r.entropy_bits for r in self.audit_results) / total
        compliance_pct = (compliant / total) * 100.0

        grade = "F"
        if compliance_pct >= 90:
            grade = "A"
        elif compliance_pct >= 80:
            grade = "B"
        elif compliance_pct >= 70:
            grade = "C"
        elif compliance_pct >= 55:
            grade = "D"

        self.kpi_total.config(text=str(total))
        self.kpi_compliant.config(text=f"{compliant} ({compliance_pct:.1f}%)")
        self.kpi_non_compliant.config(text=str(non_compliant))
        self.kpi_reused.config(text=str(reused))
        self.kpi_cross_priv.config(text=str(cross_priv))
        self.kpi_avg_entropy.config(text=f"{avg_entropy:.1f} bits")

        # Update Visual Gauges
        self.gauge.render(compliance_pct, f"{compliant} / {total} Compliant", grade)

        # Departmental breakdown
        dept_totals = defaultdict(int)
        dept_compliant = defaultdict(int)
        for r in self.audit_results:
            dept = r.user.department
            dept_totals[dept] += 1
            if r.status == ComplianceStatus.COMPLIANT:
                dept_compliant[dept] += 1

        dept_percentages = {}
        for d, tot in dept_totals.items():
            dept_percentages[d] = (dept_compliant[d] / tot) * 100.0

        self.dept_chart.render(dept_percentages)

    def _populate_treeview(self):
        self.tree_audit.delete(*self.tree_audit.get_children())
        filter_status = self.combo_status_filter.get()
        search_query = self.search_var.get().strip().lower()

        for r in self.audit_results:
            if filter_status != "ALL" and r.status.value != filter_status:
                continue
            if search_query and (
                    search_query not in r.user.username.lower() and search_query not in r.user.department.lower()):
                continue

            violation_summary = "; ".join(r.violations) if r.violations else "None (Conforms to all policy rules)"
            self.tree_audit.insert("", tk.END, values=(
                r.user.username,
                r.user.department,
                r.user.role,
                f"{r.compliance_score:.0f}",
                r.status.value,
                f"{r.entropy_bits:.1f}",
                violation_summary
            ), tags=(r.status.value,))

    def _populate_duplicates_matrix(self):
        self.tree_dups.delete(*self.tree_dups.get_children())
        # Group by hash
        seen_hashes = set()
        for r in self.audit_results:
            if r.is_duplicate:
                p_hash = hashlib.sha256(r.user.password.encode("utf-8")).hexdigest()
                if p_hash not in seen_hashes:
                    seen_hashes.add(p_hash)
                    accounts_str = f"{r.user.username}, {', '.join(r.shared_with_accounts)}"
                    risk_str = "CRITICAL: PRIVILEGED CROSS-REUSE" if r.is_privileged_cross_reuse else "Standard Account Sharing"
                    tag = "HIGH_RISK" if r.is_privileged_cross_reuse else "STANDARD_RISK"
                    self.tree_dups.insert("", tk.END, values=(
                        p_hash[:28] + "...",
                        r.duplicate_cluster_size,
                        risk_str,
                        accounts_str
                    ), tags=(tag,))

    def _on_tree_select_user(self, event):
        sel = self.tree_audit.selection()
        if not sel:
            return
        item = self.tree_audit.item(sel[0])
        username = item["values"][0]

        record = next((r for r in self.audit_results if r.user.username == username), None)
        if not record:
            return

        self._render_user_dossier(record)

    def _render_user_dossier(self, r: AuditResult):
        self.txt_dossier.delete("1.0", tk.END)
        lines = [
            "================================================================================",
            f"          ENTERPRISE CREDENTIAL AUDIT & REMEDIATION DOSSIER                     ",
            "================================================================================",
            f"Target Account      : {r.user.username}",
            f"Department / Unit   : {r.user.department}",
            f"Organizational Role : {r.user.role}",
            f"Corporate Email     : {r.user.email or 'N/A'}",
            f"Compliance Score    : {r.compliance_score:.1f} / 100 ({r.status.value})",
            f"Key-Space Entropy   : {r.entropy_bits:.2f} bits",
            "--------------------------------------------------------------------------------",
            "1. IDENTIFIED POLICY VIOLATIONS & SECURITY DEFECTS:",
            "--------------------------------------------------------------------------------"
        ]

        if r.violations:
            for v in r.violations:
                lines.append(f"  [X] {v}")
        else:
            lines.append("  [✓] Zero policy violations detected. Account conforms to all rules.")

        if r.warnings:
            lines.append("\n  WARNINGS / ADVISORIES:")
            for w in r.warnings:
                lines.append(f"  [!] {w}")

        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            "2. ACTIONABLE REMEDIATION GUIDANCE:",
            "--------------------------------------------------------------------------------"
        ])

        if r.remediation_advice:
            for idx, rem in enumerate(r.remediation_advice, 1):
                lines.append(f"  Step {idx}: {rem}")
        else:
            lines.append("  No remediation necessary.")

        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            "3. AUTOMATED EMPLOYEE NOTIFICATION DRAFT:",
            "--------------------------------------------------------------------------------",
            f"To: {r.user.email or r.user.username + '@acme.corp'}",
            "Subject: ACTION REQUIRED: Update Non-Compliant Enterprise Credentials",
            "",
            f"Dear {r.user.username},",
            "",
            "An automated security audit of the enterprise directory detected that your current",
            "account password does not comply with the corporate security standard.",
            "",
            f"Current Policy Status: {r.status.value}",
            "Required Actions:",
        ])

        for rem in (r.remediation_advice or ["Maintain current strong password habits."]):
            lines.append(f"  - {rem}")

        lines.extend([
            "",
            "Please navigate to https://identity.acme.corp/self-service to rotate your credential.",
            "Failure to update non-compliant credentials within 48 hours may lead to account lockout.",
            "",
            "Enterprise Security Operations Team (SecOps)",
            "================================================================================"
        ])

        self.txt_dossier.insert(tk.END, "\n".join(lines))
        # Switch to remediation tab automatically on selection
        self.notebook.select(self.tab_remediation)

    # --------------------------------------------------------------------------
    # REPORT EXPORT DIALOGS
    # --------------------------------------------------------------------------
    def export_reports_dialog(self):
        if not self.audit_results:
            messagebox.showwarning("No Data", "No audit results available to export.")
            return

        choice = messagebox.askyesnocancel(
            "Export Audit Reports",
            "Choose export format:\n\nClick 'Yes' for structured CSV & JSON.\nClick 'No' for Executive Summary Text.\nClick 'Cancel' to abort."
        )

        if choice is True:
            # Export CSV and JSON
            dir_path = filedialog.askdirectory(title="Select Folder to Save Reports")
            if not dir_path:
                return

            csv_file = os.path.join(dir_path, "enterprise_password_audit.csv")
            json_file = os.path.join(dir_path, "enterprise_password_audit.json")

            # Write CSV
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Username", "Department", "Role", "Score", "Status", "EntropyBits", "Violations", "Remediation"])
                for r in self.audit_results:
                    writer.writerow([
                        r.user.username,
                        r.user.department,
                        r.user.role,
                        f"{r.compliance_score:.1f}",
                        r.status.value,
                        f"{r.entropy_bits:.1f}",
                        "; ".join(r.violations),
                        "; ".join(r.remediation_advice)
                    ])

            # Write JSON
            data = []
            for r in self.audit_results:
                d = {
                    "username": r.user.username,
                    "department": r.user.department,
                    "role": r.user.role,
                    "score": r.compliance_score,
                    "status": r.status.value,
                    "entropy_bits": r.entropy_bits,
                    "is_duplicate": r.is_duplicate,
                    "duplicate_accounts": r.shared_with_accounts,
                    "is_privileged_cross_reuse": r.is_privileged_cross_reuse,
                    "violations": r.violations,
                    "remediation": r.remediation_advice
                }
                data.append(d)

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            messagebox.showinfo("Export Successful", f"Saved audit dossiers:\n- {csv_file}\n- {json_file}")

        elif choice is False:
            # Export Executive Summary Text
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Documents", "*.txt")],
                title="Save Executive Audit Summary"
            )
            if not file_path:
                return

            total = len(self.audit_results)
            compliant = sum(1 for r in self.audit_results if r.status == ComplianceStatus.COMPLIANT)
            pct = (compliant / total) * 100.0

            lines = [
                "================================================================================",
                "          EXECUTIVE ENTERPRISE PASSWORD AUDIT DOSSIER                           ",
                "================================================================================",
                f"Audit Generated On : {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Accounts Evaluated : {total}",
                f"Compliant Accounts : {compliant} ({pct:.1f}%)",
                f"Non-Compliant      : {total - compliant}",
                f"Reused Passwords   : {sum(1 for r in self.audit_results if r.is_duplicate)}",
                f"Privilege Escalation Risk Count: {sum(1 for r in self.audit_results if r.is_privileged_cross_reuse)}",
                "--------------------------------------------------------------------------------",
                "TOP VIOLATION TYPES DETECTED ACROSS ENTERPRISE:",
            ]
            all_viols = []
            for r in self.audit_results:
                all_viols.extend(r.violations)
            counts = Counter(all_viols)
            for v, cnt in counts.most_common(8):
                lines.append(f"  • {v:<60} : {cnt} accounts")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            messagebox.showinfo("Report Exported", f"Executive summary saved to:\n{file_path}")


# ==============================================================================
# 6. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Prevent scaling blur on High-DPI Windows displays
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PolicyAuditorApp()
    app.mainloop()
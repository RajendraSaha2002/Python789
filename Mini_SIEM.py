import sys
import os
import re
import ast
import csv
import ssl
import json
import time
import socket
import hashlib
import sqlite3
import platform
import datetime
import threading
import queue
import urllib.parse
import urllib.request
import urllib.error
import http.cookies
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
#                               THEME & PALETTE
# ==============================================================================
THEME = {
    "bg_root": "#0e131f",
    "bg_card": "#141c2b",
    "bg_card_inner": "#0d131f",
    "border": "#212d42",
    "border_highlight": "#344565",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#525f73",
    "neon_green": "#00ff88",
    "neon_cyan": "#00e5ff",
    "neon_orange": "#ff9800",
    "neon_red": "#ff4d4d",
    "neon_yellow": "#ffd600",
    "meter_track": "#1e293b",
    "font_main": ("Segoe UI", 9) if sys.platform.startswith("win") else ("Helvetica", 9),
    "font_bold": ("Segoe UI", 9, "bold") if sys.platform.startswith("win") else ("Helvetica", 9, "bold"),
    "font_title": ("Segoe UI", 12, "bold") if sys.platform.startswith("win") else ("Helvetica", 12, "bold"),
    "font_large": ("Segoe UI", 20, "bold") if sys.platform.startswith("win") else ("Helvetica", 20, "bold"),
    "font_mono": ("Consolas", 8) if sys.platform.startswith("win") else ("Menlo", 8),
    "font_mono_bold": ("Consolas", 8, "bold") if sys.platform.startswith("win") else ("Menlo", 8, "bold"),
}

DB_FILE = "siem_vault.db"

# ==============================================================================
#                         SQLITE DATABASE PERSISTENCE
# ==============================================================================
class DatabaseManager:
    """Manages SQLite storage for assets, findings, scans, and FIM baselines."""

    @classmethod
    def get_connection(cls):
        return sqlite3.connect(DB_FILE)

    @classmethod
    def initialize_db(cls):
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Assets Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    asset_type TEXT,
                    target TEXT,
                    created_at TEXT
                )
            """)
            # 2. Scans Record
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER,
                    scan_type TEXT,
                    risk_score INTEGER,
                    timestamp TEXT,
                    FOREIGN KEY(asset_id) REFERENCES assets(id)
                )
            """)
            # 3. Findings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    vuln_family TEXT,
                    cve_id TEXT,
                    title TEXT,
                    description TEXT,
                    cvss REAL,
                    trs INTEGER,
                    status TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(scan_id) REFERENCES scans(id)
                )
            """)
            # 4. File Integrity Monitoring Baselines
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fim_baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    sha256 TEXT,
                    size INTEGER,
                    last_updated TEXT
                )
            """)
            # 5. Historical Score Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    score INTEGER,
                    open_findings INTEGER
                )
            """)
            conn.commit()

        # Seed sample benchmark entries if empty
        cls._seed_sample_data()

    @classmethod
    def _seed_sample_data(cls):
        with cls.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM findings")
            if c.fetchone()[0] == 0:
                # Add default assets
                c.execute("INSERT OR IGNORE INTO assets (name, asset_type, target, created_at) VALUES ('PCI-BUNKER-CORE', 'Web Application', 'https://cisa.gov', datetime('now'))")
                c.execute("INSERT OR IGNORE INTO assets (name, asset_type, target, created_at) VALUES ('DMZ-GATEWAY', 'TLS Endpoint', 'cisa.gov', datetime('now'))")
                c.execute("INSERT OR IGNORE INTO assets (name, asset_type, target, created_at) VALUES ('PROD-API-SERVER', 'Local Host', '127.0.0.1', datetime('now'))")

                c.execute("INSERT INTO scans (asset_id, scan_type, risk_score, timestamp) VALUES (1, 'FULL_ASSESSMENT', 773, datetime('now'))")
                scan_id = c.lastrowid

                sample_findings = [
                    ("Common Vulnerability (Browser)", "CVE-2015-6152", "Memory Corruption in Document Engine", "Allows remote attackers to execute arbitrary code or cause memory corruption.", 9.0, 964, "Open"),
                    ("Common Vulnerability (Java Runtime)", "CVE-2015-4843", "Unspecified Vulnerability in Java SE", "Allows remote attackers to affect confidentiality, integrity, and availability.", 9.1, 693, "Open"),
                    ("Common Vulnerability (Network Protocol)", "CVE-2015-4881", "Insecure RPC Deserialization Vector", "Subversion of object input streams leads to remote payload execution.", 9.1, 693, "Open"),
                    ("Common Vulnerability (Java Sandbox)", "CVE-2015-4844", "Java SE Sandbox Escape via Reflection", "Allows unprivileged applets or servlets to bypass execution sandboxes.", 9.1, 693, "Closed"),
                    ("Common Vulnerability (Directory Traversal)", "CVE-2014-4227", "Arbitrary File Disclosure in Server", "Relative path traversal permits retrieval of host configuration files.", 9.1, 693, "Open"),
                    ("Insecure Web Header", "CWE-693", "Missing Strict-Transport-Security (HSTS)", "Enables potential SSL stripping and man-in-the-middle attacks.", 6.5, 420, "Open"),
                    ("Insecure Web Header", "CWE-1021", "Missing Content-Security-Policy (CSP)", "Increases probability of Cross-Site Scripting (XSS) exploitation.", 7.2, 510, "Open"),
                ]

                for fam, cve, title, desc, cvss, trs, st in sample_findings:
                    c.execute("""
                        INSERT INTO findings (scan_id, vuln_family, cve_id, title, description, cvss, trs, status, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (scan_id, fam, cve, title, desc, cvss, trs, st))

                # Populate history curve
                sample_history = [(720, 14), (745, 18), (760, 20), (750, 19), (773, 22)]
                for idx, (sc, op) in enumerate(sample_history):
                    past_date = (datetime.datetime.now() - datetime.timedelta(days=(len(sample_history) - idx) * 3)).strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO risk_history (timestamp, score, open_findings) VALUES (?, ?, ?)", (past_date, sc, op))

                conn.commit()


# ==============================================================================
#                           CORE AUDIT MODULES
# ==============================================================================
class WebHeaderAuditor:
    """Module 1: Audits website HTTP headers and cookie security flags."""

    @staticmethod
    def audit(target_url: str) -> list:
        findings = []
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "https://" + target_url

        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mini-SIEM-Auditor/1.0"})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                headers = {k.lower(): v for k, v in resp.getheaders()}

                if "strict-transport-security" not in headers:
                    findings.append(("Insecure Web Header", "CWE-693", "Missing HSTS Header", "Strict-Transport-Security header is missing.", 6.8, 480))
                if "content-security-policy" not in headers:
                    findings.append(("Insecure Web Header", "CWE-1021", "Missing CSP Header", "Content-Security-Policy is not configured.", 7.1, 520))
                if "x-frame-options" not in headers:
                    findings.append(("Clickjacking Exposure", "CWE-1021", "Missing X-Frame-Options", "Allows website to be framed inside hostile iframes.", 5.3, 310))
                if "x-content-type-options" not in headers:
                    findings.append(("MIME Sniffing Vulnerability", "CWE-79", "Missing X-Content-Type-Options", "Browser may sniff response content away from declared MIME type.", 4.5, 260))

                server = headers.get("server")
                if server:
                    findings.append(("Information Disclosure", "CWE-200", "Server Banner Leak", f"Server disclosed software signature: {server}", 3.8, 180))

        except Exception as e:
            findings.append(("Network Unreachable", "CWE-398", "Web Inspection Timeout", f"Could not complete HTTP scan: {str(e)}", 2.0, 100))

        return findings


class TLSAndDNSAuditor:
    """Module 2: Audits SSL/TLS certificates and mail DNS records."""

    @staticmethod
    def audit(domain: str) -> list:
        findings = []
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]

        # TLS Expiration Check
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=4) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    expire_str = cert.get("notAfter")
                    expire_dt = datetime.datetime.strptime(expire_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc)
                    days_left = (expire_dt - datetime.datetime.now(datetime.timezone.utc)).days

                    if days_left < 0:
                        findings.append(("Cryptographic Flaw", "CWE-295", "Expired TLS Certificate", f"Certificate expired {abs(days_left)} days ago!", 9.2, 750))
                    elif days_left < 15:
                        findings.append(("Expiring Certificate", "CWE-295", "TLS Certificate Expiring Imminently", f"Certificate expires in {days_left} days.", 7.0, 480))
        except Exception as e:
            findings.append(("TLS Handshake Failure", "CWE-295", "Invalid SSL/TLS Configuration", str(e), 8.0, 620))

        return findings


class StaticCodeASTAuditor:
    """Module 3: Audits Python source code using Abstract Syntax Trees (AST)."""

    class SecurityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.issues = []

        def visit_Call(self, node):
            # Check for eval() or exec()
            if isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    self.issues.append(("Code Injection", "CWE-95", f"Arbitrary Code Execution via {node.func.id}()", f"Usage of {node.func.id}() at line {node.lineno} permits arbitrary code execution.", 9.5, 880))
            # Check for subprocess shell=True
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("Popen", "call", "run", "check_output"):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            self.issues.append(("Command Injection", "CWE-78", "subprocess with shell=True", f"Command executed with shell=True at line {node.lineno}.", 8.8, 720))
            self.generic_visit(node)

        def visit_Assign(self, node):
            # Check for hardcoded API keys or passwords
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name_lower = target.id.lower()
                    if any(secret in name_lower for secret in ("password", "api_key", "secret_key", "auth_token")):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            if len(node.value.value) > 6:
                                self.issues.append(("Hardcoded Credential", "CWE-798", f"Hardcoded Secret in Variable '{target.id}'", f"Found high-entropy token literal assigned at line {node.lineno}.", 7.5, 590))
            self.generic_visit(node)

    @classmethod
    def audit_file(cls, filepath: str) -> list:
        visitor = cls.SecurityVisitor()
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                code_ast = ast.parse(f.read(), filename=filepath)
            visitor.visit(code_ast)
        except Exception as e:
            visitor.issues.append(("Static Analysis Error", "CWE-20", "AST Parser Error", str(e), 2.0, 50))
        return visitor.issues


class LocalNetworkAuditor:
    """Module 4: Audits local host listening ports and identifies 0.0.0.0 exposure."""

    @staticmethod
    def audit() -> list:
        findings = []
        os_type = platform.system().lower()
        try:
            if "windows" in os_type:
                output = os.popen("netstat -ano -p tcp").read()
            else:
                output = os.popen("netstat -tuln").read()

            for line in output.splitlines():
                if "LISTEN" in line:
                    if "0.0.0.0" in line or "[::]" in line or "*:*" in line:
                        parts = line.split()
                        addr = parts[1] if len(parts) > 1 else "Unknown"
                        findings.append(("Network Exposure", "CWE-1327", "Port Bound to 0.0.0.0 (Public)", f"Service listening globally on {addr} without loopback constraint.", 6.2, 410))
        except Exception as e:
            findings.append(("Inventory Failure", "CWE-398", "Netstat Query Failed", str(e), 2.0, 50))
        return findings


class FileIntegrityMonitor:
    """Module 5: SHA-256 baseline hashing and change detection."""

    @classmethod
    def compute_sha256(cls, filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def check_file(cls, filepath: str) -> list:
        findings = []
        if not os.path.exists(filepath):
            return [("FIM Violation", "CWE-345", "Monitored File Missing", f"Target file '{filepath}' was deleted!", 8.0, 680)]

        new_hash = cls.compute_sha256(filepath)
        size = os.path.getsize(filepath)

        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT sha256 FROM fim_baselines WHERE file_path = ?", (filepath,))
            row = c.fetchone()
            if row is None:
                # Create Baseline
                c.execute("INSERT INTO fim_baselines (file_path, sha256, size, last_updated) VALUES (?, ?, ?, datetime('now'))", (filepath, new_hash, size))
                conn.commit()
            else:
                old_hash = row[0]
                if old_hash != new_hash:
                    findings.append(("FIM Tamper Detected", "CWE-345", "Critical File Integrity Alteration", f"File '{filepath}' hash mutated from {old_hash[:10]}... to {new_hash[:10]}...", 9.4, 820))
                    c.execute("UPDATE fim_baselines SET sha256 = ?, size = ?, last_updated = datetime('now') WHERE file_path = ?", (new_hash, size, filepath))
                    conn.commit()

        return findings


# ==============================================================================
#                        CANVAS METRICS & CHARTS
# ==============================================================================
class DonutGauge(tk.Canvas):
    """Custom circular gauge chart matching the circular metrics in the screenshot."""

    def __init__(self, parent, size: int = 110, track_color: str = "#1e293b", fill_color: str = "#ff9800", **kwargs):
        super().__init__(parent, width=size, height=size, bg=THEME["bg_card"], highlightthickness=0, **kwargs)
        self.size = size
        self.track_color = track_color
        self.fill_color = fill_color
        self.draw(0, "0", "Total")

    def draw(self, percent: float, center_val: str, subtitle: str):
        self.delete("all")
        pad = 8
        extent = -(percent / 100.0) * 359.9

        # Background track
        self.create_arc(pad, pad, self.size - pad, self.size - pad, start=90, extent=359.9, outline=self.track_color, width=8, style="arc")
        # Active progress arc
        if percent > 0:
            self.create_arc(pad, pad, self.size - pad, self.size - pad, start=90, extent=extent, outline=self.fill_color, width=8, style="arc")

        # Center typography
        self.create_text(self.size // 2, self.size // 2 - 8, text=center_val, fill=THEME["text_primary"], font=THEME["font_title"])
        self.create_text(self.size // 2, self.size // 2 + 10, text=subtitle, fill=THEME["text_secondary"], font=THEME["font_mono"])


class ScoreTimelineCanvas(tk.Canvas):
    """Draws the 'TRUE RISK SCORE EVOLUTION' historical graph."""

    def __init__(self, parent, height: int = 100, **kwargs):
        super().__init__(parent, height=height, bg=THEME["bg_card"], highlightthickness=0, **kwargs)

    def render_history(self, points: list):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        if w <= 10 or h <= 10 or not points:
            return

        pad_x = 35
        pad_y = 15
        max_score = 1000
        min_score = 0

        # Draw grid horizontal guidelines
        for grid_val in [0, 500, 1000]:
            y = h - pad_y - ((grid_val - min_score) / (max_score - min_score)) * (h - 2 * pad_y)
            self.create_line(pad_x, y, w - 10, y, fill=THEME["border"], width=1, dash=(2, 4))
            self.create_text(pad_x - 14, y, text=str(grid_val), fill=THEME["text_muted"], font=THEME["font_mono"])

        # Plot data points
        step_x = (w - pad_x - 20) / max(1, (len(points) - 1))
        coords = []
        for i, pt in enumerate(points):
            val = pt.get("score", 0)
            x = pad_x + i * step_x
            y = h - pad_y - ((val - min_score) / (max_score - min_score)) * (h - 2 * pad_y)
            coords.extend([x, y])

        if len(coords) >= 4:
            self.create_line(coords, fill=THEME["neon_orange"], width=2)

        for i in range(0, len(coords), 2):
            cx, cy = coords[i], coords[i + 1]
            self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=THEME["neon_green"], outline=THEME["bg_card"], width=1)


# ==============================================================================
#                       MAIN SIEM APPLICATION WINDOW
# ==============================================================================
class MiniSIEMApp(tk.Tk):
    """Main Application Controller."""

    def __init__(self):
        super().__init__()
        self.title("PCI Bunker — Vulnerability Assessment Center & Mini-SIEM")
        self.geometry("1380x900")
        self.minsize(1150, 750)
        self.configure(bg=THEME["bg_root"])

        DatabaseManager.initialize_db()
        self.task_queue = queue.Queue()

        self._configure_styles()
        self._build_top_brand_bar()
        self._build_executive_summary_dashboard()
        self._build_filter_controls()
        self._build_main_findings_table()

        # Canvas resize hook
        self.bind("<Configure>", lambda e: self.after_idle(self._redraw_timeline))
        self.after(200, self.refresh_dashboard)
        self.after(100, self._process_task_queue)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=THEME["bg_root"], foreground=THEME["text_primary"])
        style.configure("TScrollbar", background=THEME["bg_card"], troughcolor=THEME["bg_root"], bordercolor=THEME["border"])

    def _build_top_brand_bar(self):
        """Top brand bar matching the 'Perin | PCI BUNKER' layout."""
        bar = tk.Frame(self, bg=THEME["bg_card"], padx=18, pady=10, highlightbackground=THEME["border"], highlightthickness=1)
        bar.pack(fill=tk.X, padx=16, pady=(12, 6))

        tk.Label(bar, text="🛡️ PCI BUNKER", font=THEME["font_title"], fg=THEME["neon_green"], bg=THEME["bg_card"]).pack(side=tk.LEFT, padx=(0, 16))

        today_str = datetime.datetime.now().strftime("%B %dTH %Y").upper()
        tk.Label(bar, text=f"ASSESSMENT CYCLE: {today_str}", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(side=tk.LEFT)

        # Action Buttons
        btn_scan = tk.Button(bar, text="⚡ RUN SCAN LAUNCHER", font=THEME["font_bold"], bg=THEME["neon_orange"], fg="#0d131f", activebackground=THEME["neon_green"], relief=tk.FLAT, padx=12, pady=3, cursor="hand2", command=self.open_scan_launcher)
        btn_scan.pack(side=tk.RIGHT, padx=4)

        btn_export = tk.Button(bar, text="📥 EXPORT CSV", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self.export_csv_report)
        btn_export.pack(side=tk.RIGHT, padx=4)

        btn_json = tk.Button(bar, text="📄 EXPORT JSON", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self.export_json_report)
        btn_json.pack(side=tk.RIGHT, padx=4)

    def _build_executive_summary_dashboard(self):
        """Top row matching: True Risk Score, Findings Status, Donut Gauges, and TRS Evolution."""
        dash = tk.Frame(self, bg=THEME["bg_card"], padx=16, pady=12, highlightbackground=THEME["border"], highlightthickness=1)
        dash.pack(fill=tk.X, padx=16, pady=4)

        # 1. True Risk Score Panel
        p1 = tk.Frame(dash, bg=THEME["bg_card"], width=180)
        p1.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))

        tk.Label(p1, text="TRUE RISK SCORE ⇄", font=THEME["font_mono_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(anchor="w")
        self.lbl_trs_score = tk.Label(p1, text="773", font=THEME["font_large"], fg=THEME["text_primary"], bg=THEME["bg_card"])
        self.lbl_trs_score.pack(anchor="w", pady=(2, 2))

        # Horizontal progress meter 0 to 1000
        self.meter_frame = tk.Frame(p1, bg=THEME["meter_track"], height=6, width=150)
        self.meter_frame.pack(anchor="w", pady=(2, 0))
        self.meter_frame.pack_propagate(False)
        self.meter_fill = tk.Frame(self.meter_frame, bg=THEME["neon_orange"], height=6)
        self.meter_fill.place(x=0, y=0, relwidth=0.773, relheight=1.0)

        # 2. Findings Status Breakdown
        p2 = tk.Frame(dash, bg=THEME["bg_card"], width=180)
        p2.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Label(p2, text="FINDINGS STATUS", font=THEME["font_mono_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(anchor="w")
        row_status = tk.Frame(p2, bg=THEME["bg_card"])
        row_status.pack(anchor="w", pady=4)

        self.lbl_open = tk.Label(row_status, text="⊗ Open: 0", font=THEME["font_bold"], fg=THEME["neon_red"], bg=THEME["bg_card"])
        self.lbl_open.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_closed = tk.Label(row_status, text="✔ Closed: 0", font=THEME["font_bold"], fg=THEME["neon_green"], bg=THEME["bg_card"])
        self.lbl_closed.pack(side=tk.LEFT)

        # 3. Circular Donut Gauges
        p3 = tk.Frame(dash, bg=THEME["bg_card"])
        p3.pack(side=tk.LEFT, padx=16)

        self.gauge_findings = DonutGauge(p3, size=90, fill_color=THEME["neon_yellow"])
        self.gauge_findings.pack(side=tk.LEFT, padx=6)

        self.gauge_assets = DonutGauge(p3, size=90, fill_color=THEME["neon_orange"])
        self.gauge_assets.pack(side=tk.LEFT, padx=6)

        # 4. Timeline Graph: True Risk Score Evolution
        p4 = tk.Frame(dash, bg=THEME["bg_card"])
        p4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        tk.Label(p4, text="TRUE RISK SCORE EVOLUTION (HISTORICAL TIMELINE)", font=THEME["font_mono_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(anchor="w")
        self.timeline_canvas = ScoreTimelineCanvas(p4, height=75)
        self.timeline_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    def _build_filter_controls(self):
        """Filter bar matching the 'VULNERABILITIES LISTING' search and attribute filters."""
        bar = tk.Frame(self, bg=THEME["bg_root"], padx=16, pady=8)
        bar.pack(fill=tk.X)

        self.lbl_table_title = tk.Label(bar, text="VULNERABILITIES LISTING (0)", font=THEME["font_bold"], fg=THEME["text_primary"], bg=THEME["bg_root"])
        self.lbl_table_title.pack(side=tk.LEFT, padx=(0, 14))

        # Severity / Type Dropdown
        self.filter_type_var = tk.StringVar(value="All Families")
        type_cb = ttk.Combobox(bar, textvariable=self.filter_type_var, values=["All Families", "Common Vulnerability", "Insecure Web Header", "Cryptographic Flaw", "Code Injection", "Network Exposure"], state="readonly", width=18)
        type_cb.pack(side=tk.LEFT, padx=4)
        type_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())

        # Status Filter
        self.filter_status_var = tk.StringVar(value="All Statuses")
        st_cb = ttk.Combobox(bar, textvariable=self.filter_status_var, values=["All Statuses", "Open", "Closed"], state="readonly", width=14)
        st_cb.pack(side=tk.LEFT, padx=4)
        st_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())

        # Search Query
        self.search_entry = tk.Entry(bar, width=24, font=THEME["font_main"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], insertbackground=THEME["neon_cyan"], relief=tk.FLAT, highlightbackground=THEME["border"], highlightthickness=1)
        self.search_entry.pack(side=tk.RIGHT, padx=4, ipady=3)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_dashboard())
        tk.Label(bar, text="🔍 Search:", font=THEME["font_main"], fg=THEME["text_secondary"], bg=THEME["bg_root"]).pack(side=tk.RIGHT, padx=4)

    def _build_main_findings_table(self):
        """Findings table matching the screenshot columns: TICKETS | VULN FAMILY | ATTRIBUTES | DESCRIPTION | FINDINGS | MAX CVSS | MAX TRS."""
        container = tk.Frame(self, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        canvas = tk.Canvas(container, bg=THEME["bg_card"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.table_inner = tk.Frame(canvas, bg=THEME["bg_card"])

        self.table_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self.table_inner, anchor="nw")

        def _resize(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _resize)
        canvas.configure(yscrollcommand=v_scroll.set)

        # Mousewheel scroll support
        def _scroll_table(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)) if sys.platform.startswith("win") else int(-1 * event.delta), "units")

        canvas.bind_all("<MouseWheel>", _scroll_table)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._render_table_headers()

    def _render_table_headers(self):
        h_frame = tk.Frame(self.table_inner, bg=THEME["bg_card_inner"], padx=10, pady=8)
        h_frame.pack(fill=tk.X, side=tk.TOP)

        cols = [
            ("STATUS", 8, "center"),
            ("VULN FAMILY", 24, "w"),
            ("ATTRIBUTES", 18, "w"),
            ("DESCRIPTION", 46, "w"),
            ("MAX CVSS", 10, "center"),
            ("MAX TRS", 10, "center"),
        ]

        for title, width, anchor in cols:
            tk.Label(h_frame, text=title, font=THEME["font_mono_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card_inner"], width=width, anchor=anchor).pack(side=tk.LEFT, padx=4)

    # ==========================================================================
    #                     DATA REFRESH & CHARTS
    # ==========================================================================
    def refresh_dashboard(self):
        """Pulls findings from SQLite and re-renders table and metrics."""
        for child in list(self.table_inner.winfo_children())[1:]:
            child.destroy()

        query_filter = self.search_entry.get().strip().lower()
        fam_filter = self.filter_type_var.get()
        st_filter = self.filter_status_var.get()

        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()

            # Stats aggregation
            c.execute("SELECT COUNT(*) FROM findings WHERE status = 'Open'")
            open_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM findings WHERE status = 'Closed'")
            closed_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM assets")
            asset_count = c.fetchone()[0]

            # Fetch Findings with filters
            c.execute("SELECT id, vuln_family, cve_id, title, description, cvss, trs, status FROM findings ORDER BY cvss DESC")
            all_rows = c.fetchall()

            # Historical score records
            c.execute("SELECT score, timestamp FROM risk_history ORDER BY id ASC")
            hist_rows = [{"score": r[0], "ts": r[1]} for r in c.fetchall()]

        # Filter in memory
        filtered_rows = []
        for r in all_rows:
            f_id, fam, cve, title, desc, cvss, trs, status = r
            if fam_filter != "All Families" and fam_filter not in fam:
                continue
            if st_filter != "All Statuses" and status != st_filter:
                continue
            if query_filter and (query_filter not in fam.lower() and query_filter not in cve.lower() and query_filter not in title.lower()):
                continue
            filtered_rows.append(r)

        # Update Metrics
        total_findings = open_count + closed_count
        self.lbl_open.config(text=f"⊗ Open: {open_count}")
        self.lbl_closed.config(text=f"✔ Closed: {closed_count}")

        # Compute dynamic True Risk Score (TRS)
        trs_val = min(1000, int((open_count * 55) + 320)) if open_count > 0 else 0
        self.lbl_trs_score.config(text=str(trs_val))
        self.meter_fill.place_configure(relwidth=trs_val / 1000.0)

        # Update Gauges
        self.gauge_findings.draw(min(100, open_count * 5), str(open_count), "Open")
        self.gauge_assets.draw(min(100, asset_count * 20), str(asset_count), "Total Assets")

        self.lbl_table_title.config(text=f"VULNERABILITIES LISTING ({len(filtered_rows)})")

        # Redraw timeline
        self._history_points = hist_rows
        self._redraw_timeline()

        # Render Rows
        for idx, row in enumerate(filtered_rows):
            self._render_finding_row(idx, row)

    def _redraw_timeline(self):
        if hasattr(self, "_history_points"):
            self.timeline_canvas.render_history(self._history_points)

    def _render_finding_row(self, idx: int, data: tuple):
        f_id, fam, cve, title, desc, cvss, trs, status = data
        bg_color = THEME["bg_card"] if idx % 2 == 0 else THEME["bg_card_inner"]

        row = tk.Frame(self.table_inner, bg=bg_color, padx=10, pady=7)
        row.pack(fill=tk.X, side=tk.TOP)

        # 1. Status Badge
        is_open = status == "Open"
        st_frame = tk.Frame(row, bg=bg_color, width=64)
        st_frame.pack(side=tk.LEFT, padx=4)
        st_frame.pack_propagate(False)

        badge = tk.Label(st_frame, text="OPEN" if is_open else "CLOSED", font=THEME["font_mono_bold"], fg=THEME["neon_red"] if is_open else THEME["neon_green"], bg=THEME["border"], padx=4, pady=1)
        badge.pack(anchor="center")

        # 2. Family
        tk.Label(row, text=fam, font=THEME["font_bold"], fg=THEME["text_primary"], bg=bg_color, width=24, anchor="w").pack(side=tk.LEFT, padx=4)

        # 3. Attributes (CVE Badge)
        attr_frame = tk.Frame(row, bg=bg_color, width=130)
        attr_frame.pack(side=tk.LEFT, padx=4)
        attr_frame.pack_propagate(False)
        tk.Label(attr_frame, text=cve, font=THEME["font_mono_bold"], fg=THEME["neon_cyan"], bg=THEME["border"], padx=4, pady=1).pack(anchor="w")

        # 4. Description
        desc_preview = f"{title}: {desc}"
        if len(desc_preview) > 60:
            desc_preview = desc_preview[:57] + "..."
        tk.Label(row, text=desc_preview, font=THEME["font_main"], fg=THEME["text_secondary"], bg=bg_color, width=46, anchor="w").pack(side=tk.LEFT, padx=4)

        # 5. Max CVSS
        cvss_col = THEME["neon_red"] if cvss >= 8.5 else (THEME["neon_orange"] if cvss >= 6.0 else THEME["neon_green"])
        tk.Label(row, text=f"{cvss:.1f} 🛡️", font=THEME["font_mono_bold"], fg=cvss_col, bg=bg_color, width=10, anchor="center").pack(side=tk.LEFT, padx=4)

        # 6. Max TRS
        tk.Label(row, text=f"{trs} ⚡", font=THEME["font_mono_bold"], fg=THEME["neon_orange"], bg=bg_color, width=10, anchor="center").pack(side=tk.LEFT, padx=4)

    # ==========================================================================
    #                     SCAN LAUNCHER & SCHEDULING
    # ==========================================================================
    def open_scan_launcher(self):
        """Modal launcher for Web, TLS, Code AST, Network, and FIM assessments."""
        win = tk.Toplevel(self)
        win.title("Unified Assessment Launcher")
        win.geometry("580x420")
        win.configure(bg=THEME["bg_root"])

        tk.Label(win, text="Launch Local / Authorized Security Audit", font=THEME["font_title"], fg=THEME["neon_green"], bg=THEME["bg_root"]).pack(anchor="w", padx=16, pady=12)

        # Target Type
        tk.Label(win, text="Assessment Type:", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_root"]).pack(anchor="w", padx=16)
        mod_var = tk.StringVar(value="Web Configuration (HTTP/CSP)")
        cb = ttk.Combobox(win, textvariable=mod_var, values=["Web Configuration (HTTP/CSP)", "TLS/SSL Certificate Audit", "Python Source AST Scanner", "Local Network Sockets Exposure", "File Integrity Monitor (FIM)"], state="readonly")
        cb.pack(fill=tk.X, padx=16, pady=4)

        # Target string
        tk.Label(win, text="Target (Domain, IP, or File Path):", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_root"]).pack(anchor="w", padx=16, pady=(10, 0))
        target_entry = tk.Entry(win, font=THEME["font_mono_bold"], bg=THEME["bg_card"], fg=THEME["text_primary"], insertbackground=THEME["neon_cyan"], relief=tk.FLAT, highlightbackground=THEME["border"], highlightthickness=1)
        target_entry.pack(fill=tk.X, padx=16, pady=4, ipady=4)
        target_entry.insert(0, "https://cisa.gov")

        # Auto-update placeholder on combo change
        def _on_mod_change(e):
            m = mod_var.get()
            target_entry.delete(0, tk.END)
            if "Web" in m:
                target_entry.insert(0, "https://cisa.gov")
            elif "TLS" in m:
                target_entry.insert(0, "cisa.gov")
            elif "Python" in m:
                target_entry.insert(0, os.path.abspath(__file__))
            elif "Network" in m:
                target_entry.insert(0, "127.0.0.1")
            elif "FIM" in m:
                target_entry.insert(0, os.path.abspath(__file__))

        cb.bind("<<ComboboxSelected>>", _on_mod_change)

        lbl_status = tk.Label(win, text="Ready", font=THEME["font_mono"], fg=THEME["text_muted"], bg=THEME["bg_root"])
        lbl_status.pack(anchor="w", padx=16, pady=8)

        def _execute_scan():
            mod = mod_var.get()
            target = target_entry.get().strip()
            if not target:
                messagebox.showwarning("Missing Target", "Please input a target.")
                return

            lbl_status.config(text="Auditing target in background thread...", fg=THEME["neon_cyan"])
            threading.Thread(target=self._run_audit_thread, args=(mod, target, win), daemon=True).start()

        btn_run = tk.Button(win, text="START ASSESSMENT", font=THEME["font_bold"], bg=THEME["neon_green"], fg="#0d131f", relief=tk.FLAT, padx=14, pady=6, cursor="hand2", command=_execute_scan)
        btn_run.pack(anchor="e", padx=16, pady=16)

    def _run_audit_thread(self, mod_name: str, target: str, window: tk.Toplevel):
        new_findings = []

        if "Web" in mod_name:
            new_findings = WebHeaderAuditor.audit(target)
        elif "TLS" in mod_name:
            new_findings = TLSAndDNSAuditor.audit(target)
        elif "Python" in mod_name:
            new_findings = StaticCodeASTAuditor.audit_file(target)
        elif "Network" in mod_name:
            new_findings = LocalNetworkAuditor.audit()
        elif "FIM" in mod_name:
            new_findings = FileIntegrityMonitor.check_file(target)

        # Store in SQLite
        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO scans (asset_id, scan_type, risk_score, timestamp) VALUES (1, ?, 750, datetime('now'))", (mod_name,))
            scan_id = c.lastrowid
            for fam, cve, title, desc, cvss, trs in new_findings:
                c.execute("""
                    INSERT INTO findings (scan_id, vuln_family, cve_id, title, description, cvss, trs, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', datetime('now'))
                """, (scan_id, fam, cve, title, desc, cvss, trs))

            # Record history point
            c.execute("INSERT INTO risk_history (timestamp, score, open_findings) VALUES (datetime('now'), ?, ?)", (780, len(new_findings)))
            conn.commit()

        self.task_queue.put({"__FINISHED__": True, "count": len(new_findings)})
        window.destroy()

    def _process_task_queue(self):
        try:
            while not self.task_queue.empty():
                item = self.task_queue.get_nowait()
                if "__FINISHED__" in item:
                    messagebox.showinfo("Scan Completed", f"Audit complete! Discovered and logged {item['count']} security findings.")
                    self.refresh_dashboard()
        finally:
            self.after(100, self._process_task_queue)

    # ==========================================================================
    #                          COMPLIANCE EXPORTS
    # ==========================================================================
    def export_csv_report(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile=f"siem_findings_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if not filepath:
            return

        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, vuln_family, cve_id, title, description, cvss, trs, status, timestamp FROM findings")
            rows = c.fetchall()

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Vulnerability Family", "CVE / CWE", "Title", "Description", "CVSS", "TRS Score", "Status", "Timestamp"])
            writer.writerows(rows)

        messagebox.showinfo("Export Successful", f"Saved findings report:\n{filepath}")

    def export_json_report(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile=f"siem_findings_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if not filepath:
            return

        with DatabaseManager.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, vuln_family, cve_id, title, description, cvss, trs, status, timestamp FROM findings")
            rows = c.fetchall()

        payload = [
            {"id": r[0], "family": r[1], "cve": r[2], "title": r[3], "description": r[4], "cvss": r[5], "trs": r[6], "status": r[7], "timestamp": r[8]}
            for r in rows
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

        messagebox.showinfo("Export Successful", f"Saved JSON report:\n{filepath}")


# ==============================================================================
#                                ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = MiniSIEMApp()
    app.mainloop()
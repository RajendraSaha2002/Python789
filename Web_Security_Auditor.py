import sys
import os
import re
import ssl
import socket
import json
import csv
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
import threading

# Conditional import for headless environments
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


# ============================================================================
# AUDIT ENGINE CORE
# ============================================================================

class Severity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Finding:
    def __init__(self, category: str, severity: str, title: str, description: str, remediation: str):
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.remediation = remediation

    def to_dict(self):
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "remediation": self.remediation
        }


class SecurityAuditor:
    """Non-intrusive web security configuration auditor."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WebSecurityAuditor/1.0"
    DEFAULT_TIMEOUT = 8

    def __init__(self, target_url: str):
        self.raw_target = target_url.strip()
        self.url = self._normalize_url(self.raw_target)
        self.parsed = urllib.parse.urlparse(self.url)
        self.findings = []
        self.metadata = {
            "target": self.url,
            "hostname": self.parsed.hostname,
            "port": self.parsed.port or (443 if self.parsed.scheme == "https" else 80),
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "status_code": None,
            "tls_info": {}
        }

    def _normalize_url(self, url: str) -> str:
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return "https://" + url
        return url

    def run_all_checks(self, status_callback=None):
        """Runs the complete suite of passive configuration audits."""
        if status_callback: status_callback("Inspecting TLS/SSL configuration...")
        self.check_tls_configuration()

        if status_callback: status_callback("Auditing HTTP security headers...")
        self.check_http_headers()

        if status_callback: status_callback("Checking public administrative files...")
        self.check_public_files()

        if status_callback: status_callback("Audit complete.")
        return self.findings

    # ------------------------------------------------------------------------
    # 1. TLS/SSL Configuration Check
    # ------------------------------------------------------------------------
    def check_tls_configuration(self):
        if self.parsed.scheme != "https":
            self.findings.append(Finding(
                category="Transport Layer Security",
                severity=Severity.HIGH,
                title="Unencrypted Transport Protocol (Plain HTTP)",
                description="The target does not use HTTPS by default. Data sent in transit is vulnerable to interception and tampering.",
                remediation="Configure a valid TLS certificate and enforce strict redirection from HTTP to HTTPS."
            ))
            return

        hostname = self.parsed.hostname
        port = self.parsed.port or 443

        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.DEFAULT_TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    proto_version = ssock.version()

                    self.metadata["tls_info"] = {
                        "protocol_version": proto_version,
                        "cipher_suite": cipher[0] if cipher else "Unknown",
                        "cipher_bits": cipher[2] if cipher else "Unknown"
                    }

                    # Certificate expiration audit
                    not_after_str = cert.get("notAfter")
                    if not_after_str:
                        # SSL date format: 'May 20 12:00:00 2026 GMT'
                        exp_date = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        days_left = (exp_date - datetime.now(timezone.utc)).days
                        self.metadata["tls_info"]["days_to_expiry"] = days_left

                        if days_left < 0:
                            self.findings.append(Finding(
                                category="Transport Layer Security",
                                severity=Severity.HIGH,
                                title="TLS Certificate Has Expired",
                                description=f"The SSL/TLS certificate expired on {exp_date.strftime('%Y-%m-%d')}.",
                                remediation="Renew and replace the expired certificate immediately."
                            ))
                        elif days_left < 15:
                            self.findings.append(Finding(
                                category="Transport Layer Security",
                                severity=Severity.MEDIUM,
                                title="TLS Certificate Expiring Soon",
                                description=f"The SSL/TLS certificate expires in {days_left} days ({exp_date.strftime('%Y-%m-%d')}).",
                                remediation="Schedule certificate renewal before service disruption occurs."
                            ))
                        else:
                            self.findings.append(Finding(
                                category="Transport Layer Security",
                                severity=Severity.INFO,
                                title="TLS Certificate Validity Healthy",
                                description=f"Certificate is valid for another {days_left} days (Expires: {exp_date.strftime('%Y-%m-%d')}).",
                                remediation="Continue tracking certificate expiration dates."
                            ))

                    # Deprecated Protocol Detection
                    if proto_version in ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]:
                        self.findings.append(Finding(
                            category="Transport Layer Security",
                            severity=Severity.HIGH,
                            title="Legacy/Insecure TLS Protocol Supported",
                            description=f"Server negotiated connection using legacy protocol: {proto_version}.",
                            remediation="Disable SSLv2, SSLv3, TLS 1.0, and TLS 1.1. Enforce TLS 1.2 or TLS 1.3 only."
                        ))

        except ssl.SSLCertVerificationError as e:
            self.findings.append(Finding(
                category="Transport Layer Security",
                severity=Severity.HIGH,
                title="TLS Certificate Validation Failed",
                description=f"Untrusted or invalid certificate: {e.verify_message}",
                remediation="Ensure certificate is issued by a recognized Certificate Authority and domain matches."
            ))
        except Exception as e:
            self.findings.append(Finding(
                category="Transport Layer Security",
                severity=Severity.MEDIUM,
                title="TLS Inspection Failed",
                description=f"Could not complete TLS handshake: {str(e)}",
                remediation="Ensure the server is reachable and listening on port 443 with a valid TLS configuration."
            ))

    # ------------------------------------------------------------------------
    # 2. HTTP Security Headers & Disclosures
    # ------------------------------------------------------------------------
    def check_http_headers(self):
        req = urllib.request.Request(self.url, headers={"User-Agent": self.USER_AGENT})
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT, context=ctx) as response:
                headers = {k.lower(): v for k, v in response.headers.items()}
                self.metadata["status_code"] = response.status

                # Strict-Transport-Security (HSTS)
                if "strict-transport-security" in headers:
                    hsts_val = headers["strict-transport-security"]
                    if "max-age" in hsts_val:
                        match = re.search(r"max-age=(\d+)", hsts_val)
                        if match and int(match.group(1)) < 15552000: # 180 days
                            self.findings.append(Finding(
                                category="Security Headers",
                                severity=Severity.LOW,
                                title="HSTS Max-Age Insufficient",
                                description=f"HSTS header present, but max-age is below recommended 180 days ({hsts_val}).",
                                remediation="Increase 'max-age' to at least 31536000 (1 year) and includeSubDomains."
                            ))
                        else:
                            self.findings.append(Finding(
                                category="Security Headers",
                                severity=Severity.INFO,
                                title="HSTS Enforced Appropriately",
                                description=f"HSTS configured: {hsts_val}",
                                remediation="Maintain current configuration."
                            ))
                elif self.parsed.scheme == "https":
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.MEDIUM,
                        title="Missing Strict-Transport-Security (HSTS)",
                        description="HSTS ensures modern browsers connect exclusively via HTTPS, defending against protocol downgrade attacks.",
                        remediation="Add header: 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload'."
                    ))

                # Content-Security-Policy (CSP)
                if "content-security-policy" in headers:
                    csp = headers["content-security-policy"]
                    if "'unsafe-inline'" in csp or "'unsafe-eval'" in csp:
                        self.findings.append(Finding(
                            category="Security Headers",
                            severity=Severity.LOW,
                            title="Weak Directives in Content-Security-Policy",
                            description="CSP contains 'unsafe-inline' or 'unsafe-eval', degrading Cross-Site Scripting (XSS) protections.",
                            remediation="Refactor inline scripts and style attributes into hashed or nonce-validated external assets."
                        ))
                    else:
                        self.findings.append(Finding(
                            category="Security Headers",
                            severity=Severity.INFO,
                            title="Content-Security-Policy Implemented",
                            description="A Content-Security-Policy header was detected on the primary endpoint.",
                            remediation="Maintain and regularly audit CSP rules for minimal privileges."
                        ))
                else:
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.MEDIUM,
                        title="Missing Content-Security-Policy (CSP)",
                        description="CSP mitigates Cross-Site Scripting (XSS) and data injection vulnerabilities.",
                        remediation="Configure a robust Content-Security-Policy tailored to application asset origins."
                    ))

                # X-Frame-Options
                if "x-frame-options" not in headers:
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.MEDIUM,
                        title="Missing X-Frame-Options Header",
                        description="Application may be vulnerable to UI redressing (Clickjacking) when rendered inside iframes.",
                        remediation="Set 'X-Frame-Options: DENY' or 'X-Frame-Options: SAMEORIGIN'."
                    ))

                # X-Content-Type-Options
                if headers.get("x-content-type-options", "").lower() != "nosniff":
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.LOW,
                        title="Missing or Invalid X-Content-Type-Options",
                        description="Allows MIME-type sniffing, which can lead to unexpected script execution of uploaded files.",
                        remediation="Set 'X-Content-Type-Options: nosniff'."
                    ))

                # Referrer-Policy
                if "referrer-policy" not in headers:
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.LOW,
                        title="Missing Referrer-Policy Header",
                        description="Referrer URLs containing sensitive path tokens or parameters may leak to external domains.",
                        remediation="Set 'Referrer-Policy: strict-origin-when-cross-origin' or 'no-referrer'."
                    ))

                # Permissions-Policy
                if "permissions-policy" not in headers:
                    self.findings.append(Finding(
                        category="Security Headers",
                        severity=Severity.LOW,
                        title="Missing Permissions-Policy Header",
                        description="Allows default browser access to hardware APIs like microphone, camera, geolocation.",
                        remediation="Define a Permissions-Policy restricting sensitive browser features."
                    ))

                # Technology Disclosure Checks
                for disc_header in ["server", "x-powered-by", "x-aspnet-version", "x-runtime", "x-generator"]:
                    if disc_header in headers:
                        val = headers[disc_header]
                        self.findings.append(Finding(
                            category="Information Disclosure",
                            severity=Severity.LOW,
                            title=f"Technology Disclosure in '{disc_header}' Header",
                            description=f"Server broadcasts tech stack details: '{val}'. Helps attackers tailor targeting profiles.",
                            remediation=f"Mask or remove the '{disc_header}' header in the web server / reverse proxy config."
                        ))

        except urllib.error.HTTPError as e:
            self.metadata["status_code"] = e.code
            self.findings.append(Finding(
                category="HTTP Accessibility",
                severity=Severity.INFO,
                title=f"Root URL Returned HTTP {e.code}",
                description=f"Primary endpoint returned non-200 status: {e.reason}",
                remediation="Verify server configuration and endpoint availability."
            ))
        except Exception as e:
            self.findings.append(Finding(
                category="HTTP Accessibility",
                severity=Severity.MEDIUM,
                title="HTTP Connection Failed",
                description=f"Could not establish HTTP communication: {str(e)}",
                remediation="Ensure host is reachable and DNS resolves correctly."
            ))

    # ------------------------------------------------------------------------
    # 3. Public Administrative Files Checks
    # ------------------------------------------------------------------------
    def check_public_files(self):
        base = f"{self.parsed.scheme}://{self.parsed.netloc}"
        files_to_check = [
            ("/robots.txt", "Robots Exclusion Protocol File", True),
            ("/.well-known/security.txt", "Security Contact Descriptor (RFC 9116)", False),
            ("/sitemap.xml", "XML Sitemap", True)
        ]

        ctx = ssl.create_default_context()
        for path, label, is_standard in files_to_check:
            target_file_url = urllib.parse.urljoin(base, path)
            req = urllib.request.Request(target_file_url, headers={"User-Agent": self.USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT, context=ctx) as resp:
                    if resp.status == 200:
                        content_sample = resp.read(250).decode("utf-8", errors="ignore").replace("\n", " ")
                        self.findings.append(Finding(
                            category="Public Files",
                            severity=Severity.INFO,
                            title=f"Accessible {label}",
                            description=f"Endpoint is publicly available at {path}. Sample: '{content_sample[:80]}...'",
                            remediation="Audit file contents to ensure internal endpoints or staging paths are not exposed."
                        ))
            except urllib.error.HTTPError as e:
                if path == "/.well-known/security.txt" and e.code == 404:
                    self.findings.append(Finding(
                        category="Public Files",
                        severity=Severity.INFO,
                        title="Missing security.txt Descriptor",
                        description="RFC 9116 encourages publishing security vulnerability reporting instructions at /.well-known/security.txt.",
                        remediation="Deploy a security.txt file specifying security researcher contact channels and policy."
                    ))
            except Exception:
                pass


# ============================================================================
# REPORT GENERATORS
# ============================================================================

class ReportGenerator:
    @staticmethod
    def to_json(auditor: SecurityAuditor, filepath: str):
        payload = {
            "metadata": auditor.metadata,
            "findings_count": len(auditor.findings),
            "findings": [f.to_dict() for f in auditor.findings]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

    @staticmethod
    def to_csv(auditor: SecurityAuditor, filepath: str):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Severity", "Title", "Description", "Remediation"])
            for f in auditor.findings:
                writer.writerow([f.category, f.severity, f.title, f.description, f.remediation])

    @staticmethod
    def to_html(auditor: SecurityAuditor, filepath: str):
        severities = [f.severity for f in auditor.findings]
        counts = {
            "HIGH": severities.count(Severity.HIGH),
            "MEDIUM": severities.count(Severity.MEDIUM),
            "LOW": severities.count(Severity.LOW),
            "INFO": severities.count(Severity.INFO)
        }

        badge_colors = {
            "HIGH": "#dc3545",
            "MEDIUM": "#fd7e14",
            "LOW": "#ffc107",
            "INFO": "#0dcaf0"
        }

        findings_html = ""
        for item in auditor.findings:
            color = badge_colors.get(item.severity, "#6c757d")
            text_color = "#000" if item.severity in ["LOW", "INFO"] else "#fff"
            findings_html += f"""
            <div class="finding-card">
                <div class="finding-header">
                    <span class="badge" style="background-color: {color}; color: {text_color};">{item.severity}</span>
                    <strong style="font-size: 1.05rem;">{item.title}</strong>
                    <span class="category-tag">{item.category}</span>
                </div>
                <div class="finding-body">
                    <p><strong>Description:</strong> {item.description}</p>
                    <p class="remediation"><strong>Remediation:</strong> {item.remediation}</p>
                </div>
            </div>
            """

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Security Configuration Audit - {auditor.metadata['hostname']}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2.5rem;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        h1 {{ margin: 0 0 0.5rem 0; font-weight: 700; }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            background: var(--surface-color);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            border: 1px solid var(--border-color);
        }}
        .meta-item label {{
            display: block;
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}
        .meta-item span {{
            font-weight: 600;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--surface-color);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border-color);
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }}
        .finding-card {{
            background: var(--surface-color);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            margin-bottom: 1rem;
            overflow: hidden;
        }}
        .finding-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.85rem 1.25rem;
            background: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid var(--border-color);
        }}
        .finding-body {{
            padding: 1.25rem;
        }}
        .badge {{
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .category-tag {{
            margin-left: auto;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }}
        .remediation {{
            background: rgba(16, 185, 129, 0.08);
            border-left: 3px solid #10b981;
            padding: 0.75rem;
            border-radius: 0 4px 4px 0;
            margin-top: 0.75rem;
        }}
        p {{ margin: 0.25rem 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Web Security Configuration Audit</h1>
            <p style="color: var(--text-secondary); margin: 0;">Automated Non-Intrusive Security Hygiene Assessment</p>
        </div>

        <div class="meta-grid">
            <div class="meta-item"><label>Target URL</label><span>{auditor.metadata['target']}</span></div>
            <div class="meta-item"><label>Scan Timestamp (UTC)</label><span>{auditor.metadata['scan_timestamp']}</span></div>
            <div class="meta-item"><label>TLS Version</label><span>{auditor.metadata['tls_info'].get('protocol_version', 'N/A')}</span></div>
            <div class="meta-item"><label>HTTP Status</label><span>{auditor.metadata.get('status_code', 'N/A')}</span></div>
        </div>

        <div class="stats-grid">
            <div class="stat-card" style="border-top: 4px solid #dc3545;"><label>HIGH</label><div class="stat-value">{counts['HIGH']}</div></div>
            <div class="stat-card" style="border-top: 4px solid #fd7e14;"><label>MEDIUM</label><div class="stat-value">{counts['MEDIUM']}</div></div>
            <div class="stat-card" style="border-top: 4px solid #ffc107;"><label>LOW</label><div class="stat-value">{counts['LOW']}</div></div>
            <div class="stat-card" style="border-top: 4px solid #0dcaf0;"><label>INFO</label><div class="stat-value">{counts['INFO']}</div></div>
        </div>

        <h2 style="margin-bottom: 1rem;">Findings & Compliance Overview</h2>
        {findings_html}
    </div>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_doc)


# ============================================================================
# GUI PRESENTATION LAYER (TKINTER)
# ============================================================================

if TKINTER_AVAILABLE:
    class AuditorGUI(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Web Security Configuration Auditor")
            self.geometry("980x700")
            self.minsize(800, 550)
            self.auditor = None

            self._configure_styles()
            self._build_ui()

        def _configure_styles(self):
            style = ttk.Style(self)
            style.theme_use("clam")
            # Palette
            style.configure(".", background="#f5f6f8", foreground="#212529", font=("Segoe UI", 9))
            style.configure("Treeview", rowheight=26, background="#ffffff", fieldbackground="#ffffff")
            style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
            style.map("Treeview", background=[("selected", "#0d6efd")], foreground=[("selected", "#ffffff")])

        def _build_ui(self):
            # Top Bar: URL Input
            top_frame = ttk.Frame(self, padding="15 15 15 10")
            top_frame.pack(fill=tk.X)

            ttk.Label(top_frame, text="Target Domain/URL:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
            self.url_entry = ttk.Entry(top_frame, font=("Segoe UI", 10))
            self.url_entry.insert(0, "https://example.com")
            self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

            self.scan_btn = ttk.Button(top_frame, text="Start Audit", command=self._start_audit_thread)
            self.scan_btn.pack(side=tk.RIGHT)

            # Status Banner
            status_frame = ttk.Frame(self, padding="15 0 15 5")
            status_frame.pack(fill=tk.X)
            self.status_label = ttk.Label(status_frame, text="Ready. Enter a target and click Start Audit.", foreground="#6c757d")
            self.status_label.pack(side=tk.LEFT)

            # Central Display Area (Treeview Split)
            mid_frame = ttk.Frame(self, padding="15 5 15 10")
            mid_frame.pack(fill=tk.BOTH, expand=True)

            columns = ("severity", "category", "title")
            self.tree = ttk.Treeview(mid_frame, columns=columns, show="headings", selectmode="browse")
            self.tree.heading("severity", text="Severity")
            self.tree.heading("category", text="Category")
            self.tree.heading("title", text="Finding Title")

            self.tree.column("severity", width=100, stretch=False, anchor=tk.CENTER)
            self.tree.column("category", width=180, stretch=False)
            self.tree.column("title", width=450, stretch=True)

            tree_scroll = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
            self.tree.configure(yscrollcommand=tree_scroll.set)
            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            self.tree.bind("<<TreeviewSelect>>", self._on_item_select)

            # Details Pane
            bottom_frame = ttk.LabelFrame(self, text="Finding Details & Remediation", padding="10")
            bottom_frame.pack(fill=tk.BOTH, expand=False, padx=15, pady=(0, 10))
            bottom_frame.configure(height=160)

            self.detail_text = tk.Text(bottom_frame, height=6, wrap=tk.WORD, font=("Consolas", 9), relief=tk.FLAT)
            self.detail_text.pack(fill=tk.BOTH, expand=True)
            self.detail_text.config(state=tk.DISABLED)

            # Bottom Controls & Exporting
            footer_frame = ttk.Frame(self, padding="15 0 15 15")
            footer_frame.pack(fill=tk.X)

            self.export_json_btn = ttk.Button(footer_frame, text="Export JSON", state=tk.DISABLED, command=self._export_json)
            self.export_json_btn.pack(side=tk.RIGHT, padx=(5, 0))

            self.export_csv_btn = ttk.Button(footer_frame, text="Export CSV", state=tk.DISABLED, command=self._export_csv)
            self.export_csv_btn.pack(side=tk.RIGHT, padx=(5, 0))

            self.export_html_btn = ttk.Button(footer_frame, text="Export HTML Report", state=tk.DISABLED, command=self._export_html)
            self.export_html_btn.pack(side=tk.RIGHT, padx=(5, 0))

        def _set_status(self, text: str):
            self.status_label.config(text=text)

        def _start_audit_thread(self):
            target = self.url_entry.get().strip()
            if not target:
                messagebox.showerror("Error", "Please specify a target domain or URL.")
                return

            self.scan_btn.config(state=tk.DISABLED)
            self.export_json_btn.config(state=tk.DISABLED)
            self.export_csv_btn.config(state=tk.DISABLED)
            self.export_html_btn.config(state=tk.DISABLED)

            self.tree.delete(*self.tree.get_children())
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete("1.0", tk.END)
            self.detail_text.config(state=tk.DISABLED)

            threading.Thread(target=self._run_audit, args=(target,), daemon=True).start()

        def _run_audit(self, target: str):
            self.auditor = SecurityAuditor(target)
            self.auditor.run_all_checks(status_callback=lambda msg: self.after(0, self._set_status, msg))
            self.after(0, self._render_results)

        def _render_results(self):
            self.scan_btn.config(state=tk.NORMAL)
            self.export_json_btn.config(state=tk.NORMAL)
            self.export_csv_btn.config(state=tk.NORMAL)
            self.export_html_btn.config(state=tk.NORMAL)

            # Sort findings by severity priority
            priority = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
            sorted_findings = sorted(self.auditor.findings, key=lambda f: priority.get(f.severity, 9))

            for idx, item in enumerate(sorted_findings):
                self.tree.insert("", tk.END, iid=str(idx), values=(item.severity, item.category, item.title))

            total = len(self.auditor.findings)
            self._set_status(f"Completed. {total} findings identified across inspected layers.")

        def _on_item_select(self, event):
            selection = self.tree.selection()
            if not selection:
                return

            idx = int(selection[0])
            priority = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
            sorted_findings = sorted(self.auditor.findings, key=lambda f: priority.get(f.severity, 9))
            finding = sorted_findings[idx]

            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete("1.0", tk.END)
            content = (
                f"CATEGORY:    {finding.category}\n"
                f"SEVERITY:    {finding.severity}\n"
                f"TITLE:       {finding.title}\n\n"
                f"DESCRIPTION:\n{finding.description}\n\n"
                f"RECOMMENDED REMEDIATION:\n{finding.remediation}\n"
            )
            self.detail_text.insert(tk.END, content)
            self.detail_text.config(state=tk.DISABLED)

        def _export_json(self):
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
            if path:
                ReportGenerator.to_json(self.auditor, path)
                messagebox.showinfo("Export Successful", f"Saved JSON report to:\n{path}")

        def _export_csv(self):
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if path:
                ReportGenerator.to_csv(self.auditor, path)
                messagebox.showinfo("Export Successful", f"Saved CSV report to:\n{path}")

        def _export_html(self):
            path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML Files", "*.html")])
            if path:
                ReportGenerator.to_html(self.auditor, path)
                messagebox.showinfo("Export Successful", f"Saved HTML report to:\n{path}")


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================

def run_cli_audit(target: str, export_format: str = None, export_file: str = None):
    print(f"[*] Initializing configuration audit for target: {target}")
    auditor = SecurityAuditor(target)
    auditor.run_all_checks(status_callback=lambda msg: print(f"    - {msg}"))

    print("\n" + "=" * 80)
    print(f"{'SEVERITY':<10} | {'CATEGORY':<25} | {'TITLE'}")
    print("=" * 80)

    priority = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
    sorted_findings = sorted(auditor.findings, key=lambda f: priority.get(f.severity, 9))

    for f in sorted_findings:
        print(f"{f.severity:<10} | {f.category:<25} | {f.title}")

    print("=" * 80)
    print(f"Total findings: {len(auditor.findings)}")

    if export_format and export_file:
        if export_format.lower() == "json":
            ReportGenerator.to_json(auditor, export_file)
        elif export_format.lower() == "csv":
            ReportGenerator.to_csv(auditor, export_file)
        elif export_format.lower() == "html":
            ReportGenerator.to_html(auditor, export_file)
        print(f"[+] Successfully exported report to: {export_file}")


def main():
    if len(sys.argv) > 1:
        # CLI execution mode
        target = sys.argv[1]
        export_fmt = None
        export_out = None

        if len(sys.argv) >= 4 and sys.argv[2] in ["--json", "--csv", "--html"]:
            export_fmt = sys.argv[2].replace("--", "")
            export_out = sys.argv[3]

        run_cli_audit(target, export_fmt, export_out)
    else:
        # GUI mode
        if TKINTER_AVAILABLE:
            app = AuditorGUI()
            app.mainloop()
        else:
            print("[-] Tkinter is not available in this environment.")
            print("    Usage: python web_security_auditor.py <target_url> [--json|--csv|--html output_file]")


if __name__ == "__main__":
    main()
import sys
import os
import re
import ssl
import socket
import json
import time
from datetime import datetime, timezone
import threading

# Conditional import for headless/CLI environments
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


# ============================================================================
# AUDIT CONSTANTS & DATA MODELS
# ============================================================================

class AlertLevel:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    HEALTHY = "HEALTHY"


class SecurityFinding:
    def __init__(self, level: str, title: str, details: str, recommendation: str):
        self.level = level
        self.title = title
        self.details = details
        self.recommendation = recommendation

    def to_dict(self):
        return {
            "level": self.level,
            "title": self.title,
            "details": self.details,
            "recommendation": self.recommendation
        }


# ============================================================================
# CORE TLS AUDITING ENGINE
# ============================================================================

class CertificateAnalyzer:
    """Performs passive cryptographic and architectural analysis of TLS certificates."""

    DEFAULT_TIMEOUT = 6.0

    def __init__(self, host: str, port: int = 443, sni_hostname: str = None):
        self.raw_host = host.strip()
        self.host = self._sanitize_hostname(self.raw_host)
        self.port = int(port)
        self.sni = sni_hostname.strip() if sni_hostname else self.host
        self.findings = []
        self.data = {
            "target": {"host": self.host, "port": self.port, "sni": self.sni},
            "network": {},
            "tls": {},
            "certificate": {},
            "validation": {"chain_valid": False, "error": None},
            "findings": []
        }

    @staticmethod
    def _sanitize_hostname(host: str) -> str:
        # Strip scheme if present
        host = re.sub(r"^https?://", "", host, flags=re.IGNORECASE)
        # Strip path / query
        host = host.split("/")[0].split("?")[0]
        # Strip port if present in string
        if ":" in host and not host.startswith("["):
            host = host.split(":")[0]
        return host.strip()

    @staticmethod
    def _parse_dn(dn_tuple) -> dict:
        """Converts X.509 Distinguished Name tuples to a flat dictionary."""
        dn = {}
        if not dn_tuple:
            return dn
        for rdn in dn_tuple:
            for key, val in rdn:
                dn[key] = val
        return dn

    @staticmethod
    def _matches_hostname(hostname: str, pattern: str) -> bool:
        """Evaluates single-level RFC 6125 wildcard matching."""
        hostname = hostname.lower()
        pattern = pattern.lower()
        if pattern.startswith("*."):
            suffix = pattern[1:]  # e.g., '.example.com'
            if hostname.endswith(suffix):
                prefix = hostname[:-len(suffix)]
                if "." not in prefix and len(prefix) > 0:
                    return True
            return False
        return hostname == pattern

    def execute_audit(self) -> dict:
        """Conducts network resolution, handshake negotiation, and cert parsing."""
        t_start = time.perf_counter()

        # 1. DNS Resolution
        try:
            resolved_ip = socket.gethostbyname(self.host)
            self.data["network"]["resolved_ip"] = resolved_ip
        except socket.gaierror as e:
            self.data["validation"]["error"] = f"DNS Resolution Failed: {str(e)}"
            self.findings.append(SecurityFinding(
                AlertLevel.CRITICAL,
                "Domain Name Unresolvable",
                f"Could not resolve IP address for {self.host}.",
                "Check DNS configuration, registrar settings, and domain availability."
            ))
            self._finalize_data(time.perf_counter() - t_start)
            return self.data

        # 2. Connection and TLS Handshake
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

        try:
            with socket.create_connection((self.host, self.port), timeout=self.DEFAULT_TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.sni) as ssock:
                    latency = (time.perf_counter() - t_start) * 1000
                    self.data["network"]["handshake_latency_ms"] = round(latency, 2)
                    self.data["validation"]["chain_valid"] = True

                    # Protocol and Cipher inspection
                    proto = ssock.version()
                    cipher = ssock.cipher()
                    self._audit_tls_connection(proto, cipher)

                    # Peer Certificate Analysis
                    cert = ssock.getpeercert()
                    self._audit_certificate_details(cert)

        except ssl.SSLCertVerificationError as e:
            self.data["validation"]["chain_valid"] = False
            self.data["validation"]["error"] = f"{e.verify_message} (Code: {e.verify_code})"
            self.findings.append(SecurityFinding(
                AlertLevel.CRITICAL,
                "Certificate Chain Validation Failed",
                f"Validation error: {e.verify_message}. The client cannot establish trust.",
                "Ensure intermediate certificates are installed on the server and the root CA is public."
            ))
        except ssl.SSLError as e:
            self.data["validation"]["chain_valid"] = False
            self.data["validation"]["error"] = str(e)
            self.findings.append(SecurityFinding(
                AlertLevel.HIGH,
                "TLS Handshake Failure",
                f"Handshake failed: {str(e)}",
                "Verify compatible protocols, cipher suites, and server SNI routing."
            ))
        except (socket.timeout, socket.error) as e:
            self.data["validation"]["chain_valid"] = False
            self.data["validation"]["error"] = f"Socket connection failed: {str(e)}"
            self.findings.append(SecurityFinding(
                AlertLevel.HIGH,
                "Endpoint Unreachable",
                f"Could not establish TCP connection to {self.host}:{self.port} ({str(e)}).",
                "Ensure firewall policies permit inbound connections on port 443."
            ))

        self._finalize_data(time.perf_counter() - t_start)
        return self.data

    def _audit_tls_connection(self, protocol: str, cipher: tuple):
        cipher_name = cipher[0] if cipher else "Unknown"
        cipher_proto = cipher[1] if cipher else "Unknown"
        cipher_bits = cipher[2] if cipher else 0

        self.data["tls"] = {
            "protocol_version": protocol,
            "cipher_name": cipher_name,
            "cipher_protocol": cipher_proto,
            "cipher_bits": cipher_bits
        }

        # Protocol posture
        if protocol in ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]:
            self.findings.append(SecurityFinding(
                AlertLevel.CRITICAL,
                f"Obsolete Protocol Negotiated ({protocol})",
                f"The server allows connection via {protocol}, which is deprecated and insecure.",
                "Enforce TLS 1.2 or TLS 1.3 exclusively across all endpoints."
            ))
        elif protocol == "TLSv1.2":
            self.findings.append(SecurityFinding(
                AlertLevel.INFO,
                "TLS 1.2 Negotiated",
                "Connection secured with TLS 1.2. Compatible with older clients.",
                "Plan to deploy TLS 1.3 to leverage zero round-trip and modern key exchange."
            ))
        elif protocol == "TLSv1.3":
            self.findings.append(SecurityFinding(
                AlertLevel.HEALTHY,
                "Modern TLS 1.3 Negotiated",
                "Connection negotiated using current industry-standard TLS 1.3.",
                "Maintain this configuration."
            ))

        # Cipher posture
        if cipher_bits < 128:
            self.findings.append(SecurityFinding(
                AlertLevel.CRITICAL,
                f"Weak Encryption Key Length ({cipher_bits} bits)",
                f"Cipher suite '{cipher_name}' uses inadequate cryptographic key lengths.",
                "Disable all cipher suites operating below 128-bit encryption."
            ))
        elif "RC4" in cipher_name or "3DES" in cipher_name or "CBC" in cipher_name:
            self.findings.append(SecurityFinding(
                AlertLevel.MEDIUM,
                f"Legacy Cipher Architecture ({cipher_name})",
                "Cipher contains CBC-mode or deprecated symmetric primitives vulnerable to side-channels.",
                "Prioritize AEAD suites such as AES-GCM or CHACHA20-POLY1305."
            ))

    def _audit_certificate_details(self, cert: dict):
        subject = self._parse_dn(cert.get("subject", ()))
        issuer = self._parse_dn(cert.get("issuer", ()))
        serial = cert.get("serialNumber", "N/A")
        version = cert.get("version", "N/A")

        # Subject Alternative Names (SAN)
        raw_sans = cert.get("subjectAltName", ())
        dns_sans = [val for typ, val in raw_sans if typ == "DNS"]
        ip_sans = [val for typ, val in raw_sans if typ == "IP Address"]
        all_sans = dns_sans + ip_sans

        # Validity Dates
        not_before_raw = cert.get("notBefore")
        not_after_raw = cert.get("notAfter")

        not_before_dt = None
        not_after_dt = None
        days_left = None

        if not_before_raw:
            ts_before = ssl.cert_time_to_seconds(not_before_raw)
            not_before_dt = datetime.fromtimestamp(ts_before, tz=timezone.utc)

        if not_after_raw:
            ts_after = ssl.cert_time_to_seconds(not_after_raw)
            not_after_dt = datetime.fromtimestamp(ts_after, tz=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            days_left = (not_after_dt - now_utc).days

        self.data["certificate"] = {
            "subject": subject,
            "issuer": issuer,
            "serial_number": serial,
            "version": version,
            "sans": all_sans,
            "valid_from": not_before_dt.isoformat() if not_before_dt else None,
            "valid_until": not_after_dt.isoformat() if not_after_dt else None,
            "days_remaining": days_left
        }

        # Expiration Checks
        if days_left is not None:
            if days_left < 0:
                self.findings.append(SecurityFinding(
                    AlertLevel.CRITICAL,
                    "Certificate Has Expired",
                    f"Certificate expired {abs(days_left)} days ago on {not_after_dt.strftime('%Y-%m-%d')}.",
                    "Replace the expired certificate immediately to restore user trust and traffic."
                ))
            elif days_left <= 7:
                self.findings.append(SecurityFinding(
                    AlertLevel.CRITICAL,
                    "Critical: Certificate Expires in Under 7 Days",
                    f"Certificate validity ends on {not_after_dt.strftime('%Y-%m-%d')} ({days_left} days remaining).",
                    "Renew and deploy the new certificate immediately to prevent outages."
                ))
            elif days_left <= 30:
                self.findings.append(SecurityFinding(
                    AlertLevel.MEDIUM,
                    "Warning: Certificate Expiring Soon",
                    f"Certificate validity ends in {days_left} days ({not_after_dt.strftime('%Y-%m-%d')}).",
                    "Verify automated renewal (e.g. ACME) or initiate manual certificate rotation."
                ))
            else:
                self.findings.append(SecurityFinding(
                    AlertLevel.HEALTHY,
                    "Certificate Validity Window Healthy",
                    f"Certificate is valid for {days_left} more days (Expires: {not_after_dt.strftime('%Y-%m-%d')}).",
                    "Maintain standard renewal monitoring."
                ))

        # Hostname Matching Audit (SAN and CN)
        cn = subject.get("commonName", "")
        matched = False
        candidates = all_sans if all_sans else ([cn] if cn else [])

        for candidate in candidates:
            if self._matches_hostname(self.host, candidate):
                matched = True
                break

        self.data["validation"]["hostname_match"] = matched
        self.data["validation"]["evaluated_name"] = self.host

        if not matched:
            self.findings.append(SecurityFinding(
                AlertLevel.CRITICAL,
                "Hostname Mismatch Identified",
                f"Requested host '{self.host}' does not match CN ('{cn}') or any SAN entries ({', '.join(candidates[:5])}).",
                "Reissue the certificate including all required public domain names in the SAN extension."
            ))
        else:
            self.findings.append(SecurityFinding(
                AlertLevel.HEALTHY,
                "Hostname Validated Successfully",
                f"Hostname '{self.host}' matches certificate identities.",
                "Ensure future service subdomains are covered under the current SAN or wildcard scope."
            ))

        # Self-Signed Heuristic
        if subject == issuer and subject:
            self.findings.append(SecurityFinding(
                AlertLevel.HIGH,
                "Self-Signed Certificate In Use",
                f"Subject and Issuer are identical ('{cn}'). Not trusted by public clients.",
                "Deploy certificates issued by a publicly trusted WebPKI Certificate Authority for public services."
            ))

    def _finalize_data(self, elapsed_sec: float):
        self.data["audit_duration_sec"] = round(elapsed_sec, 3)
        self.data["findings"] = [f.to_dict() for f in self.findings]


# ============================================================================
# REPORT GENERATORS
# ============================================================================

class ReportExporter:
    @staticmethod
    def export_json(data: dict, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def export_text(data: dict, filepath: str):
        target = data.get("target", {})
        net = data.get("network", {})
        tls = data.get("tls", {})
        cert = data.get("certificate", {})
        val = data.get("validation", {})
        findings = data.get("findings", [])

        lines = [
            "=" * 78,
            "TLS/SSL CERTIFICATE & HTTPS SECURITY AUDIT REPORT",
            "=" * 78,
            f"Target Host       : {target.get('host')}:{target.get('port')}",
            f"SNI Parameter     : {target.get('sni')}",
            f"Resolved IP       : {net.get('resolved_ip', 'N/A')}",
            f"Latency           : {net.get('handshake_latency_ms', 'N/A')} ms",
            f"Validation Result : {'VALID & TRUSTED' if val.get('chain_valid') else 'FAILED'}",
            f"Hostname Match    : {'MATCHED' if val.get('hostname_match') else 'MISMATCH'}",
            "-" * 78,
            "CONNECTION & CRYPTO",
            "-" * 78,
            f"Protocol Version  : {tls.get('protocol_version', 'N/A')}",
            f"Cipher Suite      : {tls.get('cipher_name', 'N/A')}",
            f"Key Strength      : {tls.get('cipher_bits', 'N/A')} bits",
            "-" * 78,
            "CERTIFICATE IDENTITIES",
            "-" * 78,
            f"Subject CN        : {cert.get('subject', {}).get('commonName', 'N/A')}",
            f"Organization (O)  : {cert.get('subject', {}).get('organizationName', 'N/A')}",
            f"Issuer CN         : {cert.get('issuer', {}).get('commonName', 'N/A')}",
            f"Issuer Org        : {cert.get('issuer', {}).get('organizationName', 'N/A')}",
            f"Valid From        : {cert.get('valid_from', 'N/A')}",
            f"Valid Until       : {cert.get('valid_until', 'N/A')}",
            f"Days Remaining    : {cert.get('days_remaining', 'N/A')} days",
            f"SAN Count         : {len(cert.get('sans', []))}",
            "-" * 78,
            "FINDINGS & SECURITY AUDIT SUMMARY",
            "-" * 78,
        ]

        for idx, f in enumerate(findings, 1):
            lines.extend([
                f"[{f['level']}] #{idx}: {f['title']}",
                f"Details        : {f['details']}",
                f"Recommendation : {f['recommendation']}",
                ""
            ])

        lines.append("=" * 78)
        with open(filepath, "w", encoding="utf-8") as file_out:
            file_out.write("\n".join(lines))


# ============================================================================
# GUI PRESENTATION INTERFACE (TKINTER)
# ============================================================================

if TKINTER_AVAILABLE:
    class TLSAnalyzerApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("TLS/SSL Certificate Security Analyzer")
            self.geometry("1024x720")
            self.minsize(850, 580)
            self.result_data = None

            self._apply_style()
            self._build_widgets()

        def _apply_style(self):
            style = ttk.Style(self)
            style.theme_use("clam")
            # Base UI colors
            style.configure(".", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 9))
            style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), background="#f8fafc")
            style.configure("Badge.TLabel", font=("Segoe UI", 10, "bold"), padding=4)
            style.configure("Treeview", rowheight=24, background="#ffffff", fieldbackground="#ffffff")
            style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
            style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        def _build_widgets(self):
            # 1. Top Input Banner
            input_box = ttk.LabelFrame(self, text="Target Configuration", padding="12")
            input_box.pack(fill=tk.X, padx=15, pady=(12, 6))

            grid = ttk.Frame(input_box)
            grid.pack(fill=tk.X)

            ttk.Label(grid, text="Hostname / Domain:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
            self.entry_host = ttk.Entry(grid, width=32, font=("Segoe UI", 10))
            self.entry_host.insert(0, "example.com")
            self.entry_host.grid(row=0, column=1, sticky=tk.W, padx=(0, 16))

            ttk.Label(grid, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 6))
            self.entry_port = ttk.Entry(grid, width=7, font=("Segoe UI", 10))
            self.entry_port.insert(0, "443")
            self.entry_port.grid(row=0, column=3, sticky=tk.W, padx=(0, 16))

            ttk.Label(grid, text="SNI (Optional):").grid(row=0, column=4, sticky=tk.W, padx=(0, 6))
            self.entry_sni = ttk.Entry(grid, width=24, font=("Segoe UI", 10))
            self.entry_sni.grid(row=0, column=5, sticky=tk.W, padx=(0, 16))

            self.btn_scan = ttk.Button(grid, text="Inspect Certificate", command=self._start_audit_thread)
            self.btn_scan.grid(row=0, column=6, sticky=tk.E)

            # 2. Status Badge Strip
            self.badge_frame = ttk.Frame(self, padding="15 6 15 6")
            self.badge_frame.pack(fill=tk.X)

            self.badge_trust = self._create_card(self.badge_frame, "TRUST STATUS", "Not Inspected", "#64748b")
            self.badge_days = self._create_card(self.badge_frame, "EXPIRATION", "-- Days", "#64748b")
            self.badge_proto = self._create_card(self.badge_frame, "PROTOCOL", "N/A", "#64748b")
            self.badge_cipher = self._create_card(self.badge_frame, "KEY LENGTH", "0-bit", "#64748b")

            # 3. Notebook / Tabs
            self.notebook = ttk.Notebook(self)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=6)

            # Tab 1: Findings & Health
            self.tab_findings = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.tab_findings, text="Security Audit Findings")
            self._init_findings_tab(self.tab_findings)

            # Tab 2: Certificate Identity
            self.tab_identity = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.tab_identity, text="Certificate Identity & SANs")
            self._init_identity_tab(self.tab_identity)

            # Tab 3: Raw Inspection Tree
            self.tab_raw = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(self.tab_raw, text="Technical Details & Cryptography")
            self._init_tech_tab(self.tab_raw)

            # 4. Footer & Action Bar
            footer = ttk.Frame(self, padding="15 6 15 12")
            footer.pack(fill=tk.X)

            self.status_label = ttk.Label(footer, text="Ready. Enter a domain and start inspection.", foreground="#64748b")
            self.status_label.pack(side=tk.LEFT)

            self.btn_export_txt = ttk.Button(footer, text="Export Text", state=tk.DISABLED, command=self._export_text)
            self.btn_export_txt.pack(side=tk.RIGHT, padx=(4, 0))

            self.btn_export_json = ttk.Button(footer, text="Export JSON", state=tk.DISABLED, command=self._export_json)
            self.btn_export_json.pack(side=tk.RIGHT, padx=(4, 0))

        def _create_card(self, parent, label_text: str, default_val: str, color: str):
            f = tk.Frame(parent, bg="#ffffff", bd=1, relief=tk.SOLID)
            f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            lbl_title = tk.Label(f, text=label_text, font=("Segoe UI", 7, "bold"), fg="#64748b", bg="#ffffff")
            lbl_title.pack(anchor=tk.W, padx=8, pady=(4, 0))
            lbl_val = tk.Label(f, text=default_val, font=("Segoe UI", 11, "bold"), fg=color, bg="#ffffff")
            lbl_val.pack(anchor=tk.W, padx=8, pady=(0, 4))
            return {"frame": f, "title": lbl_title, "value": lbl_val}

        def _init_findings_tab(self, parent):
            cols = ("level", "title", "recommendation")
            self.tree_findings = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
            self.tree_findings.heading("level", text="Severity")
            self.tree_findings.heading("title", text="Observed Condition")
            self.tree_findings.heading("recommendation", text="Remediation Strategy")

            self.tree_findings.column("level", width=110, stretch=False, anchor=tk.CENTER)
            self.tree_findings.column("title", width=340, stretch=False)
            self.tree_findings.column("recommendation", width=420, stretch=True)

            scroller = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree_findings.yview)
            self.tree_findings.configure(yscrollcommand=scroller.set)
            self.tree_findings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroller.pack(side=tk.RIGHT, fill=tk.Y)

        def _init_identity_tab(self, parent):
            left_frame = ttk.LabelFrame(parent, text="Subject / Issuer DN", padding=8)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

            self.txt_identity = tk.Text(left_frame, wrap=tk.WORD, font=("Consolas", 9), relief=tk.FLAT)
            self.txt_identity.pack(fill=tk.BOTH, expand=True)
            self.txt_identity.config(state=tk.DISABLED)

            right_frame = ttk.LabelFrame(parent, text="Subject Alternative Names (SAN)", padding=8)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

            self.list_sans = tk.Listbox(right_frame, font=("Segoe UI", 9), selectmode=tk.BROWSE, relief=tk.FLAT)
            san_scroller = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.list_sans.yview)
            self.list_sans.configure(yscrollcommand=san_scroller.set)
            self.list_sans.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            san_scroller.pack(side=tk.RIGHT, fill=tk.Y)

        def _init_tech_tab(self, parent):
            self.txt_tech = tk.Text(parent, wrap=tk.WORD, font=("Consolas", 9), relief=tk.FLAT)
            scroller = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_tech.yview)
            self.txt_tech.configure(yscrollcommand=scroller.set)
            self.txt_tech.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroller.pack(side=tk.RIGHT, fill=tk.Y)
            self.txt_tech.config(state=tk.DISABLED)

        def _start_audit_thread(self):
            host = self.entry_host.get().strip()
            port_s = self.entry_port.get().strip()
            sni = self.entry_sni.get().strip()

            if not host:
                messagebox.showerror("Error", "Hostname must be populated.")
                return

            try:
                port = int(port_s)
            except ValueError:
                messagebox.showerror("Error", "Port must be an integer (e.g. 443).")
                return

            self.btn_scan.config(state=tk.DISABLED)
            self.status_label.config(text=f"Connecting and verifying TLS on {host}:{port}...")

            threading.Thread(target=self._run_audit_worker, args=(host, port, sni), daemon=True).start()

        def _run_audit_worker(self, host: str, port: int, sni: str):
            analyzer = CertificateAnalyzer(host, port, sni)
            data = analyzer.execute_audit()
            self.after(0, self._render_results, data)

        def _render_results(self, data: dict):
            self.result_data = data
            self.btn_scan.config(state=tk.NORMAL)
            self.btn_export_json.config(state=tk.NORMAL)
            self.btn_export_txt.config(state=tk.NORMAL)

            val = data.get("validation", {})
            cert = data.get("certificate", {})
            tls = data.get("tls", {})
            findings = data.get("findings", [])

            # Update Badges
            if val.get("chain_valid"):
                self.badge_trust["value"].config(text="TRUSTED", fg="#16a34a")
            else:
                self.badge_trust["value"].config(text="UNTRUSTED", fg="#dc2626")

            days = cert.get("days_remaining")
            if days is None:
                self.badge_days["value"].config(text="N/A", fg="#64748b")
            elif days < 0:
                self.badge_days["value"].config(text="EXPIRED", fg="#dc2626")
            elif days <= 7:
                self.badge_days["value"].config(text=f"{days}d (CRITICAL)", fg="#dc2626")
            elif days <= 30:
                self.badge_days["value"].config(text=f"{days}d (WARN)", fg="#d97706")
            else:
                self.badge_days["value"].config(text=f"{days} Days", fg="#16a34a")

            self.badge_proto["value"].config(text=tls.get("protocol_version", "Failed"), fg="#0284c7")
            self.badge_cipher["value"].config(text=f"{tls.get('cipher_bits', 0)}-bit", fg="#0284c7")

            # Findings Tree
            self.tree_findings.delete(*self.tree_findings.get_children())
            for idx, item in enumerate(findings):
                self.tree_findings.insert("", tk.END, iid=str(idx), values=(item["level"], item["title"], item["recommendation"]))

            # Identity Tab
            self.txt_identity.config(state=tk.NORMAL)
            self.txt_identity.delete("1.0", tk.END)

            subj = cert.get("subject", {})
            iss = cert.get("issuer", {})
            ident_text = (
                f"--- SUBJECT DISTINGUISHED NAME ---\n"
                f"Common Name (CN)      : {subj.get('commonName', 'N/A')}\n"
                f"Organization (O)      : {subj.get('organizationName', 'N/A')}\n"
                f"Organizational Unit   : {subj.get('organizationalUnitName', 'N/A')}\n"
                f"Country (C)           : {subj.get('countryName', 'N/A')}\n"
                f"State / Locality      : {subj.get('stateOrProvinceName', 'N/A')}, {subj.get('localityName', 'N/A')}\n\n"
                f"--- ISSUER DISTINGUISHED NAME ---\n"
                f"Issuer CN             : {iss.get('commonName', 'N/A')}\n"
                f"Issuer Organization   : {iss.get('organizationName', 'N/A')}\n"
                f"Issuer Country        : {iss.get('countryName', 'N/A')}\n\n"
                f"--- DATES & SERIAL ---\n"
                f"Serial Number         : {cert.get('serial_number', 'N/A')}\n"
                f"X.509 Version         : v{cert.get('version', 'N/A')}\n"
                f"Valid From            : {cert.get('valid_from', 'N/A')}\n"
                f"Valid Until           : {cert.get('valid_until', 'N/A')}\n"
            )
            self.txt_identity.insert(tk.END, ident_text)
            self.txt_identity.config(state=tk.DISABLED)

            # SANs List
            self.list_sans.delete(0, tk.END)
            for san in cert.get("sans", []):
                self.list_sans.insert(tk.END, f"• {san}")

            # Tech Details Tab
            self.txt_tech.config(state=tk.NORMAL)
            self.txt_tech.delete("1.0", tk.END)
            self.txt_tech.insert(tk.END, json.dumps(data, indent=4))
            self.txt_tech.config(state=tk.DISABLED)

            # Status Bar
            dur = data.get("audit_duration_sec", 0)
            err = val.get("error")
            if err:
                self.status_label.config(text=f"Completed with warnings in {dur}s: {err}")
            else:
                self.status_label.config(text=f"Audit completed successfully in {dur} seconds.")

        def _export_json(self):
            if not self.result_data:
                return
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
            if path:
                ReportExporter.export_json(self.result_data, path)
                messagebox.showinfo("Export Successful", f"Saved JSON report:\n{path}")

        def _export_text(self):
            if not self.result_data:
                return
            path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Log", "*.txt")])
            if path:
                ReportExporter.export_text(self.result_data, path)
                messagebox.showinfo("Export Successful", f"Saved Text report:\n{path}")


# ============================================================================
# CLI RUNNER INTERFACE
# ============================================================================

def run_cli_audit(host: str, port: int = 443, sni: str = None, json_out: str = None, text_out: str = None):
    print(f"[*] Commencing TLS/SSL inspection on {host}:{port} (SNI: {sni or host})...")
    analyzer = CertificateAnalyzer(host, port, sni)
    data = analyzer.execute_audit()

    val = data.get("validation", {})
    tls = data.get("tls", {})
    cert = data.get("certificate", {})

    print("\n" + "=" * 80)
    print("TLS/SSL CERTIFICATE INSPECTION SUMMARY")
    print("=" * 80)
    print(f"Target Endpoint   : {host}:{port}")
    print(f"Chain Trust       : {'TRUSTED' if val.get('chain_valid') else 'UNTRUSTED / VERIFICATION FAILED'}")
    if val.get("error"):
        print(f"Error Diagnostic  : {val.get('error')}")
    print(f"Hostname Match    : {'PASSED' if val.get('hostname_match') else 'FAILED'}")
    print(f"Protocol & Cipher : {tls.get('protocol_version', 'N/A')} | {tls.get('cipher_name', 'N/A')} ({tls.get('cipher_bits', 0)} bits)")
    print(f"Subject Identity  : {cert.get('subject', {}).get('commonName', 'N/A')}")
    print(f"Issuer Authority  : {cert.get('issuer', {}).get('commonName', 'N/A')}")
    print(f"Validity Remaining: {cert.get('days_remaining', 'N/A')} days")
    print("-" * 80)
    print(f"{'SEVERITY':<12} | {'TITLE'}")
    print("-" * 80)

    for item in data.get("findings", []):
        print(f"{item['level']:<12} | {item['title']}")

    print("=" * 80)

    if json_out:
        ReportExporter.export_json(data, json_out)
        print(f"[+] JSON report saved to: {json_out}")

    if text_out:
        ReportExporter.export_text(data, text_out)
        print(f"[+] Text report saved to: {text_out}")


def main():
    if len(sys.argv) > 1:
        # CLI Mode
        target_host = sys.argv[1]
        target_port = 443
        json_file = None
        txt_file = None

        idx = 2
        while idx < len(sys.argv):
            arg = sys.argv[idx]
            if arg == "--port" and idx + 1 < len(sys.argv):
                target_port = int(sys.argv[idx + 1])
                idx += 2
            elif arg == "--json" and idx + 1 < len(sys.argv):
                json_file = sys.argv[idx + 1]
                idx += 2
            elif arg == "--text" and idx + 1 < len(sys.argv):
                txt_file = sys.argv[idx + 1]
                idx += 2
            else:
                idx += 1

        run_cli_audit(target_host, target_port, None, json_file, txt_file)
    else:
        # Interactive GUI Mode
        if TKINTER_AVAILABLE:
            app = TLSAnalyzerApp()
            app.mainloop()
        else:
            print("[-] Tkinter graphical interface is unavailable in this environment.")
            print("    CLI Usage: python tls_certificate_analyzer.py <hostname> [--port 443] [--json out.json] [--text out.txt]")


if __name__ == "__main__":
    main()
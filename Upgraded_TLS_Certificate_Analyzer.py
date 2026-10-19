import sys
import os
import re
import ssl
import socket
import json
import urllib.parse
import http.client
import datetime
import calendar
import threading
import queue
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
#                               THEME & PALETTE
# ==============================================================================
THEME = {
    "bg_dark": "#0a0e17",
    "bg_card": "#131b29",
    "bg_card_inner": "#0d1420",
    "border": "#212e45",
    "border_highlight": "#304263",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#586069",
    "accent_cyan": "#00e5ff",
    "accent_green": "#00ff88",
    "accent_amber": "#ffb86c",
    "accent_red": "#ff5555",
    "accent_blue": "#58a6ff",
    "badge_bg": "#1e293b",
    "font_main": ("Segoe UI", 10) if sys.platform.startswith("win") else ("Helvetica", 10),
    "font_bold": ("Segoe UI", 10, "bold") if sys.platform.startswith("win") else ("Helvetica", 10, "bold"),
    "font_title": ("Segoe UI", 14, "bold") if sys.platform.startswith("win") else ("Helvetica", 14, "bold"),
    "font_mono": ("Consolas", 9) if sys.platform.startswith("win") else ("Menlo", 9),
    "font_mono_bold": ("Consolas", 9, "bold") if sys.platform.startswith("win") else ("Menlo", 9, "bold"),
}

# ==============================================================================
#                          CORE SCANNER ENGINE
# ==============================================================================
class SSLSecurityScanner:
    """Core network and TLS analysis engine using standard socket and ssl."""

    def __init__(self, target: str, port: int = 443, timeout: float = 6.0):
        self.raw_target = target.strip()
        self.port = int(port)
        self.timeout = timeout
        self.domain = self._clean_target(self.raw_target)

    @staticmethod
    def _clean_target(target: str) -> str:
        """Strips URL prefixes, paths, and extraneous characters."""
        if "://" in target:
            target = urllib.parse.urlsplit(target).hostname or target
        else:
            target = target.split("/")[0]
        if ":" in target:
            target = target.split(":")[0]
        return target.strip().lower()

    def scan(self) -> dict:
        """Executes full diagnostic suite and returns a structured audit payload."""
        result = {
            "target": self.domain,
            "port": self.port,
            "scan_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "dns": {},
            "handshake": {},
            "certificate": {},
            "trust": {},
            "security_headers": {},
            "audit_flags": [],
            "status": "UNKNOWN",
            "error": None,
        }

        # 1. DNS Resolution
        try:
            addr_info = socket.getaddrinfo(self.domain, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            resolved_ips = list(set([item[4][0] for item in addr_info]))
            result["dns"]["resolved_ips"] = resolved_ips
            result["dns"]["primary_ip"] = resolved_ips[0] if resolved_ips else "Unknown"
        except socket.gaierror as e:
            result["status"] = "ERROR"
            result["error"] = f"DNS resolution failed: {e}"
            result["audit_flags"].append({"level": "CRITICAL", "msg": f"Domain could not be resolved: {e}"})
            return result

        # 2. TLS Connection & Chain Validation Pass (Strict Mode)
        verified_cert = None
        verification_error = None
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        try:
            with socket.create_connection((self.domain, self.port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    verified_cert = ssock.getpeercert()
                    result["handshake"]["protocol_version"] = ssock.version()
                    result["handshake"]["cipher_suite"] = ssock.cipher()
                    result["handshake"]["alpn_protocol"] = ssock.selected_alpn_protocol()
                    result["trust"]["trusted"] = True
                    result["trust"]["message"] = "Certificate chain and hostname successfully verified by system trust store."
        except ssl.SSLCertVerificationError as e:
            verification_error = str(e)
            result["trust"]["trusted"] = False
            result["trust"]["message"] = f"Verification Failure: {e.verify_message if hasattr(e, 'verify_message') else str(e)}"
            result["audit_flags"].append({"level": "CRITICAL", "msg": f"Trust validation failed: {result['trust']['message']}"})
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            result["status"] = "ERROR"
            result["error"] = f"Network connection failed: {e}"
            result["audit_flags"].append({"level": "CRITICAL", "msg": f"TCP connection error on port {self.port}: {e}"})
            return result

        # 3. Fallback Pass (Retrieve Raw Data if Strict Mode Failed)
        raw_cert = verified_cert
        raw_pem = ""
        try:
            raw_pem = ssl.get_server_certificate((self.domain, self.port), timeout=self.timeout)
            result["certificate"]["raw_pem"] = raw_pem
        except Exception as e:
            result["certificate"]["raw_pem"] = f"Unable to fetch raw PEM: {e}"

        if not raw_cert:
            # Fallback to unverified handshake to inspect metadata
            unverified_ctx = ssl._create_unverified_context()
            unverified_ctx.check_hostname = False
            unverified_ctx.verify_mode = ssl.CERT_NONE
            try:
                with socket.create_connection((self.domain, self.port), timeout=self.timeout) as sock:
                    with unverified_ctx.wrap_socket(sock, server_hostname=self.domain) as ssock:
                        result["handshake"]["protocol_version"] = ssock.version()
                        result["handshake"]["cipher_suite"] = ssock.cipher()
                        result["handshake"]["alpn_protocol"] = ssock.selected_alpn_protocol()
            except Exception as e:
                result["audit_flags"].append({"level": "WARNING", "msg": f"Unverified handshake fallback also failed: {e}"})

        # 4. Parse Peer Certificate Fields
        if verified_cert:
            self._parse_standard_certificate(verified_cert, result)
        else:
            self._parse_fallback_certificate(result, verification_error)

        # 5. Security Header Audit (HSTS, CSP, etc.)
        self._audit_http_headers(result)

        # 6. Overall Security Audit Synthesis
        self._evaluate_audit_rules(result)

        return result

    def _parse_standard_certificate(self, cert: dict, result: dict):
        """Extracts structured values from Python's standard cert dictionary."""
        c_data = result["certificate"]

        # Subject & Issuer decomposition
        subject_dict = {}
        for rdn in cert.get("subject", ()):
            for key, val in rdn:
                subject_dict[key] = val
        c_data["subject"] = subject_dict
        c_data["common_name"] = subject_dict.get("commonName", "N/A")
        c_data["organization"] = subject_dict.get("organizationName", "N/A")
        c_data["country"] = subject_dict.get("countryName", "N/A")

        issuer_dict = {}
        for rdn in cert.get("issuer", ()):
            for key, val in rdn:
                issuer_dict[key] = val
        c_data["issuer"] = issuer_dict
        c_data["issuer_common_name"] = issuer_dict.get("commonName", "N/A")
        c_data["issuer_organization"] = issuer_dict.get("organizationName", "N/A")

        # Serial Number & Version
        c_data["serial_number"] = cert.get("serialNumber", "N/A")
        c_data["version"] = cert.get("version", "N/A")

        # Validity Dates
        not_before_str = cert.get("notBefore")
        not_after_str = cert.get("notAfter")
        c_data["not_before_raw"] = not_before_str
        c_data["not_after_raw"] = not_after_str

        # Parse ASN1 dates (Format typically: 'Jul 24 00:00:00 2024 GMT')
        date_fmt = "%b %d %H:%M:%S %Y %Z"
        try:
            nb_dt = datetime.datetime.strptime(not_before_str, date_fmt).replace(tzinfo=datetime.timezone.utc)
            na_dt = datetime.datetime.strptime(not_after_str, date_fmt).replace(tzinfo=datetime.timezone.utc)
            now_dt = datetime.datetime.now(datetime.timezone.utc)

            c_data["valid_from_iso"] = nb_dt.isoformat()
            c_data["valid_to_iso"] = na_dt.isoformat()

            days_remaining = (na_dt - now_dt).days
            total_duration = (na_dt - nb_dt).days
            elapsed_days = (now_dt - nb_dt).days

            c_data["days_remaining"] = days_remaining
            c_data["total_validity_days"] = total_duration
            c_data["is_expired"] = now_dt > na_dt
            c_data["is_not_yet_valid"] = now_dt < nb_dt

            # Progress calculation
            if total_duration > 0:
                pct = max(0, min(100, int((elapsed_days / total_duration) * 100)))
            else:
                pct = 100
            c_data["validity_percentage_used"] = pct

        except Exception as e:
            c_data["date_parse_error"] = str(e)
            c_data["days_remaining"] = None
            c_data["is_expired"] = False

        # Subject Alternative Names (SANs)
        san_entries = []
        for san_type, san_val in cert.get("subjectAltName", ()):
            san_entries.append({"type": san_type, "value": san_val})
        c_data["sans"] = san_entries

        # Hostname Match Check
        dns_names = [e["value"] for e in san_entries if e["type"] == "DNS"]
        if not dns_names and c_data["common_name"] != "N/A":
            dns_names = [c_data["common_name"]]

        c_data["hostname_matched"] = self._matches_hostname(self.domain, dns_names)

    @staticmethod
    def _matches_hostname(hostname: str, patterns: list) -> bool:
        """Tests hostname against list of SAN DNS names including wildcards."""
        hostname = hostname.lower()
        for pattern in patterns:
            pattern = pattern.lower()
            if pattern.startswith("*."):
                suffix = pattern[2:]
                host_parts = hostname.split(".", 1)
                if len(host_parts) == 2 and host_parts[1] == suffix:
                    return True
            elif hostname == pattern:
                return True
        return False

    def _parse_fallback_certificate(self, result: dict, error_msg: str):
        """Populates baseline info when standard verified decoding cannot finish."""
        c_data = result["certificate"]
        c_data["subject"] = {"commonName": "Inspection restricted (Untrusted chain)"}
        c_data["common_name"] = "Untrusted / Unverified"
        c_data["issuer_common_name"] = "Unknown"
        c_data["organization"] = "N/A"
        c_data["issuer_organization"] = "N/A"
        c_data["days_remaining"] = 0
        c_data["is_expired"] = "expired" in (error_msg or "").lower()
        c_data["hostname_matched"] = False
        c_data["sans"] = []

    def _audit_http_headers(self, result: dict):
        """Examines security-relevant HTTP response headers over TLS."""
        h_data = result["security_headers"]
        try:
            conn = http.client.HTTPSConnection(self.domain, self.port, timeout=self.timeout)
            conn.request("HEAD", "/", headers={"User-Agent": "Mozilla/5.0 (Security-Analyzer/1.0)"})
            resp = conn.getresponse()
            headers = {k.lower(): v for k, v in resp.getheaders()}
            conn.close()

            # Strict Transport Security (HSTS)
            hsts = headers.get("strict-transport-security")
            h_data["hsts_present"] = hsts is not None
            h_data["hsts_raw"] = hsts or "Not Present"
            h_data["hsts_preload"] = "preload" in (hsts or "").lower()
            h_data["hsts_subdomains"] = "includesubdomains" in (hsts or "").lower()

            # CSP, X-Frame-Options, X-Content-Type-Options
            h_data["csp_present"] = "content-security-policy" in headers
            h_data["csp_raw"] = headers.get("content-security-policy", "Not Present")
            h_data["x_frame_options"] = headers.get("x-frame-options", "Not Present")
            h_data["x_content_type_options"] = headers.get("x-content-type-options", "Not Present")
            h_data["server_banner"] = headers.get("server", "Hidden / Not Disclosed")

        except Exception as e:
            h_data["error"] = f"Header inspection bypassed: {e}"
            h_data["hsts_present"] = False
            h_data["csp_present"] = False
            h_data["x_frame_options"] = "Unknown"
            h_data["x_content_type_options"] = "Unknown"
            h_data["server_banner"] = "Unknown"

    def _evaluate_audit_rules(self, result: dict):
        """Runs security heuristics and calculates status ratings."""
        flags = result["audit_flags"]
        c_data = result["certificate"]
        h_data = result["security_headers"]
        hs_data = result["handshake"]

        # Check Expiration
        if c_data.get("is_expired"):
            flags.append({"level": "CRITICAL", "msg": "The certificate is EXPIRED."})
        elif c_data.get("days_remaining") is not None:
            days = c_data["days_remaining"]
            if days <= 0:
                flags.append({"level": "CRITICAL", "msg": "The certificate has reached its end of life."})
            elif days <= 14:
                flags.append({"level": "CRITICAL", "msg": f"Certificate expires imminently in {days} days!"})
            elif days <= 30:
                flags.append({"level": "WARNING", "msg": f"Certificate expiration warning: only {days} days left."})

        # Check Hostname
        if not c_data.get("hostname_matched", True):
            flags.append({"level": "CRITICAL", "msg": f"Hostname mismatch! Host '{self.domain}' not found in Certificate Subject/SAN."})

        # Check Protocol
        proto = hs_data.get("protocol_version", "")
        if proto in ("TLSv1", "TLSv1.1", "SSLv2", "SSLv3"):
            flags.append({"level": "CRITICAL", "msg": f"Obsolete and vulnerable protocol negotiated: {proto}"})
        elif proto == "TLSv1.2":
            flags.append({"level": "INFO", "msg": "TLSv1.2 in use. Functional, but TLSv1.3 is recommended."})

        # Check HSTS
        if not h_data.get("hsts_present"):
            flags.append({"level": "WARNING", "msg": "HTTP Strict Transport Security (HSTS) header is missing."})
        elif not h_data.get("hsts_preload"):
            flags.append({"level": "INFO", "msg": "HSTS header is active but missing 'preload' directive."})

        # Check CSP & Clickjacking
        if not h_data.get("csp_present"):
            flags.append({"level": "INFO", "msg": "Content-Security-Policy header is absent."})
        if h_data.get("x_frame_options") == "Not Present":
            flags.append({"level": "INFO", "msg": "X-Frame-Options not set; site might be vulnerable to Clickjacking."})

        # Final Status determination
        has_critical = any(f["level"] == "CRITICAL" for f in flags)
        has_warning = any(f["level"] == "WARNING" for f in flags)

        if has_critical:
            result["status"] = "CRITICAL"
        elif has_warning:
            result["status"] = "WARNING"
        else:
            result["status"] = "SECURE"


# ==============================================================================
#                        DASHBOARD GUI COMPONENTS
# ==============================================================================
class MetricCard(tk.Frame):
    """Card container that mimics the modern Web Check modular UI."""

    def __init__(self, parent, title: str, icon: str = "•", **kwargs):
        super().__init__(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightcolor=THEME["border_highlight"],
            highlightthickness=1,
            padx=12,
            pady=10,
            **kwargs,
        )
        self.grid_propagate(True)

        # Header bar
        self.header_frame = tk.Frame(self, bg=THEME["bg_card"])
        self.header_frame.pack(fill=tk.X, pady=(0, 8))

        self.icon_lbl = tk.Label(
            self.header_frame,
            text=f"{icon} ",
            font=THEME["font_mono_bold"],
            fg=THEME["accent_cyan"],
            bg=THEME["bg_card"],
        )
        self.icon_lbl.pack(side=tk.LEFT)

        self.title_lbl = tk.Label(
            self.header_frame,
            text=title.upper(),
            font=THEME["font_bold"],
            fg=THEME["accent_cyan"],
            bg=THEME["bg_card"],
        )
        self.title_lbl.pack(side=tk.LEFT)

        # Body container
        self.body = tk.Frame(self, bg=THEME["bg_card"])
        self.body.pack(fill=tk.BOTH, expand=True)

    def add_row(self, label: str, value: str, val_color: str = None, mono: bool = False):
        """Appends an aligned key-value pair to the card."""
        row_frame = tk.Frame(self.body, bg=THEME["bg_card"])
        row_frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(
            row_frame,
            text=label,
            font=THEME["font_main"],
            fg=THEME["text_secondary"],
            bg=THEME["bg_card"],
            anchor="w",
            width=18,
        )
        lbl.pack(side=tk.LEFT)

        font = THEME["font_mono"] if mono else THEME["font_main"]
        color = val_color or THEME["text_primary"]

        val = tk.Label(
            row_frame,
            text=value,
            font=font,
            fg=color,
            bg=THEME["bg_card"],
            anchor="w",
            wraplength=320,
            justify=tk.LEFT,
        )
        val.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return val


class ValidityProgressBar(tk.Frame):
    """Custom progress meter visualizing certificate lifetime spent."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME["bg_card_inner"], height=16, **kwargs)
        self.pack_propagate(False)
        self.fill_bar = tk.Frame(self, bg=THEME["accent_green"], height=16)
        self.fill_bar.place(x=0, y=0, relheight=1.0, width=0)

    def update_progress(self, percent: int, is_expired: bool = False):
        if is_expired:
            self.fill_bar.config(bg=THEME["accent_red"])
            self.fill_bar.place_configure(relwidth=1.0)
        else:
            color = THEME["accent_green"]
            if percent > 85:
                color = THEME["accent_red"]
            elif percent > 70:
                color = THEME["accent_amber"]

            self.fill_bar.config(bg=color)
            self.fill_bar.place_configure(relwidth=max(0.01, min(1.0, percent / 100.0)))


# ==============================================================================
#                       MAIN APPLICATION WINDOW
# ==============================================================================
class TLSAnalyzerApp(tk.Tk):
    """Master application controller."""

    def __init__(self):
        super().__init__()
        self.title("TLS/SSL Certificate Security Analyzer")
        self.geometry("1260x860")
        self.minsize(1050, 700)
        self.configure(bg=THEME["bg_dark"])

        self.scan_queue = queue.Queue()
        self.current_payload = None

        self._configure_styles()
        self._build_top_controls()
        self._build_status_banner()
        self._build_dashboard_grid()
        self._build_footer()

        # Check periodic worker queue
        self.after(100, self._process_worker_queue)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=THEME["bg_dark"], foreground=THEME["text_primary"])
        style.configure("TScrollbar", background=THEME["bg_card"], troughcolor=THEME["bg_dark"], bordercolor=THEME["border"])

    def _build_top_controls(self):
        """Search and command bar."""
        top_frame = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=14, highlightbackground=THEME["border"], highlightthickness=1)
        top_frame.pack(fill=tk.X, padx=16, pady=(16, 8))

        # Title / Brand
        brand_lbl = tk.Label(
            top_frame,
            text="⚡ SSL/TLS ANALYZER",
            font=THEME["font_title"],
            fg=THEME["accent_green"],
            bg=THEME["bg_card"],
        )
        brand_lbl.pack(side=tk.LEFT, padx=(0, 24))

        # Input Frame
        in_frame = tk.Frame(top_frame, bg=THEME["bg_card"])
        in_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(in_frame, text="Hostname / Target:", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(side=tk.LEFT, padx=(0, 6))

        self.target_entry = tk.Entry(
            in_frame,
            font=THEME["font_mono_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["accent_cyan"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent_cyan"],
            highlightthickness=1,
        )
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)
        self.target_entry.insert(0, "cisa.gov")
        self.target_entry.bind("<Return>", lambda e: self.start_analysis())

        tk.Label(in_frame, text="Port:", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(side=tk.LEFT, padx=(4, 6))
        self.port_entry = tk.Entry(
            in_frame,
            width=6,
            font=THEME["font_mono_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["accent_cyan"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent_cyan"],
            highlightthickness=1,
        )
        self.port_entry.pack(side=tk.LEFT, padx=(0, 15), ipady=5)
        self.port_entry.insert(0, "443")

        # Action Buttons
        self.scan_btn = tk.Button(
            top_frame,
            text="RUN AUDIT",
            font=THEME["font_bold"],
            bg=THEME["accent_cyan"],
            fg="#050a12",
            activebackground=THEME["accent_green"],
            activeforeground="#050a12",
            relief=tk.FLAT,
            padx=16,
            pady=5,
            cursor="hand2",
            command=self.start_analysis,
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = tk.Button(
            top_frame,
            text="EXPORT JSON",
            font=THEME["font_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            activebackground=THEME["border_highlight"],
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.export_json_report,
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)

    def _build_status_banner(self):
        """Top high-level diagnostic summary indicator."""
        self.banner = tk.Frame(self, bg=THEME["badge_bg"], padx=20, pady=8, highlightbackground=THEME["border"], highlightthickness=1)
        self.banner.pack(fill=tk.X, padx=16, pady=(0, 8))

        self.banner_status_lbl = tk.Label(
            self.banner,
            text="SYSTEM READY",
            font=THEME["font_bold"],
            fg=THEME["accent_cyan"],
            bg=THEME["badge_bg"],
        )
        self.banner_status_lbl.pack(side=tk.LEFT)

        self.banner_detail_lbl = tk.Label(
            self.banner,
            text="Enter any fully qualified domain name or IP address and click 'RUN AUDIT'.",
            font=THEME["font_main"],
            fg=THEME["text_secondary"],
            bg=THEME["badge_bg"],
        )
        self.banner_detail_lbl.pack(side=tk.LEFT, padx=20)

    def _build_dashboard_grid(self):
        """Scrollable responsive grid containing diagnostic metric cards."""
        container = tk.Frame(self, bg=THEME["bg_dark"])
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=0)

        canvas = tk.Canvas(container, bg=THEME["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scroll_content = tk.Frame(canvas, bg=THEME["bg_dark"])

        self.scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        # Allow Mousewheel scrolling
        def _on_mousewheel(event):
            if sys.platform.startswith("win"):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * event.delta), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Grid system for Cards (2 Columns)
        self.scroll_content.columnconfigure(0, weight=1)
        self.scroll_content.columnconfigure(1, weight=1)

        # Cards instantiation
        self.card_cert = MetricCard(self.scroll_content, "Certificate Subject & Issuer", icon="📋")
        self.card_cert.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.card_validity = MetricCard(self.scroll_content, "Validity Period & Expiration", icon="⏳")
        self.card_validity.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.card_trust = MetricCard(self.scroll_content, "Chain Validation & Host Matching", icon="🛡️")
        self.card_trust.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.card_proto = MetricCard(self.scroll_content, "Negotiation & Protocol Information", icon="🔒")
        self.card_proto.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        self.card_headers = MetricCard(self.scroll_content, "HTTP Security & HSTS Checklist", icon="🌐")
        self.card_headers.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)

        self.card_audit = MetricCard(self.scroll_content, "Security Warnings & Risk Findings", icon="⚠️")
        self.card_audit.grid(row=2, column=1, sticky="nsew", padx=6, pady=6)

        # Initialize Cards with placeholder content
        self._populate_blank_cards()

    def _build_footer(self):
        """Bottom info bar."""
        footer = tk.Frame(self, bg=THEME["bg_card"], padx=16, pady=6, highlightbackground=THEME["border"], highlightthickness=1)
        footer.pack(fill=tk.X, padx=16, pady=(6, 12))

        lbl = tk.Label(
            footer,
            text="Standard Library Engine (ssl, socket, http.client) | Cryptographic Verification Active",
            font=THEME["font_mono"],
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        lbl.pack(side=tk.LEFT)

        self.lbl_clock = tk.Label(
            footer,
            text=f"UTC: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            font=THEME["font_mono"],
            fg=THEME["text_muted"],
            bg=THEME["bg_card"],
        )
        self.lbl_clock.pack(side=tk.RIGHT)
        self._tick_clock()

    def _tick_clock(self):
        self.lbl_clock.config(text=f"UTC: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        self.after(1000, self._tick_clock)

    def _populate_blank_cards(self):
        """Initial placeholders."""
        self.card_cert.add_row("Common Name (CN):", "Ready")
        self.card_cert.add_row("Organization (O):", "Ready")
        self.card_cert.add_row("Issuer (CA):", "Ready")
        self.card_cert.add_row("Serial Number:", "Ready", mono=True)

        self.card_validity.add_row("Valid From:", "Ready")
        self.card_validity.add_row("Valid Until:", "Ready")
        self.card_validity.add_row("Days Remaining:", "Ready")

        self.card_trust.add_row("Chain Verified:", "Ready")
        self.card_trust.add_row("SAN Host Match:", "Ready")
        self.card_trust.add_row("SAN Count:", "Ready")

        self.card_proto.add_row("TLS Protocol:", "Ready")
        self.card_proto.add_row("Cipher Suite:", "Ready", mono=True)
        self.card_proto.add_row("ALPN Protocol:", "Ready")
        self.card_proto.add_row("Primary IP:", "Ready", mono=True)

        self.card_headers.add_row("HSTS Active:", "Ready")
        self.card_headers.add_row("HSTS Preloaded:", "Ready")
        self.card_headers.add_row("CSP Policy:", "Ready")
        self.card_headers.add_row("X-Frame-Options:", "Ready")

        self.card_audit.add_row("Status Summary:", "Ready for target scan")

    # ==========================================================================
    #                     SCAN MANAGEMENT & THREADING
    # ==========================================================================
    def start_analysis(self):
        """Initiates threaded scan to keep GUI fully responsive."""
        target = self.target_entry.get().strip()
        port_raw = self.port_entry.get().strip()

        if not target:
            messagebox.showwarning("Input Missing", "Please enter a valid hostname or domain name.")
            return

        try:
            port = int(port_raw)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Port", "Port number must be an integer between 1 and 65535.")
            return

        # UI state during scan
        self.scan_btn.config(state=tk.DISABLED, text="AUDITING...")
        self.banner_status_lbl.config(text="SCANNING IN PROGRESS", fg=THEME["accent_cyan"])
        self.banner_detail_lbl.config(text=f"Establishing cryptographic TLS socket handshake with {target}:{port}...")

        # Worker thread
        worker = threading.Thread(target=self._run_scan_thread, args=(target, port), daemon=True)
        worker.start()

    def _run_scan_thread(self, target: str, port: int):
        scanner = SSLSecurityScanner(target, port)
        payload = scanner.scan()
        self.scan_queue.put(payload)

    def _process_worker_queue(self):
        """Processes payload from worker thread."""
        try:
            while not self.scan_queue.empty():
                payload = self.scan_queue.get_nowait()
                self._render_scan_results(payload)
                self.scan_btn.config(state=tk.NORMAL, text="RUN AUDIT")
        finally:
            self.after(100, self._process_worker_queue)

    # ==========================================================================
    #                       DASHBOARD RENDER ENGINE
    # ==========================================================================
    def _clear_card(self, card: MetricCard):
        for widget in card.body.winfo_children():
            widget.destroy()

    def _render_scan_results(self, data: dict):
        self.current_payload = data

        # Status Banner Updates
        status = data.get("status", "UNKNOWN")
        if status == "SECURE":
            self.banner_status_lbl.config(text="● SECURE & TRUSTED", fg=THEME["accent_green"])
            self.banner_detail_lbl.config(text="Valid certificate chain, trusted root, correct hostname, and active security measures.")
        elif status == "WARNING":
            self.banner_status_lbl.config(text="▲ SECURITY WARNING", fg=THEME["accent_amber"])
            self.banner_detail_lbl.config(text="Certificate functional, but potential vulnerabilities or expiration warnings detected.")
        else:
            self.banner_status_lbl.config(text="✖ CRITICAL / UNTRUSTED", fg=THEME["accent_red"])
            self.banner_detail_lbl.config(text=data.get("error") or "Security validation failed. High risk detected.")

        # 1. Subject & Issuer Card
        self._clear_card(self.card_cert)
        cert = data.get("certificate", {})
        self.card_cert.add_row("Common Name (CN):", cert.get("common_name", "N/A"), val_color=THEME["accent_cyan"])
        self.card_cert.add_row("Organization (O):", cert.get("organization", "N/A"))
        self.card_cert.add_row("Country (C):", cert.get("country", "N/A"))
        self.card_cert.add_row("Issuer (CA):", cert.get("issuer_common_name", "N/A"), val_color=THEME["accent_blue"])
        self.card_cert.add_row("Issuer Org:", cert.get("issuer_organization", "N/A"))
        self.card_cert.add_row("Serial Number:", str(cert.get("serial_number", "N/A"))[:32] + "...", mono=True)

        # 2. Validity & Expiration Card
        self._clear_card(self.card_validity)
        days = cert.get("days_remaining")
        is_expired = cert.get("is_expired", False)

        self.card_validity.add_row("Valid From:", str(cert.get("valid_from_iso", cert.get("not_before_raw", "N/A"))))
        self.card_validity.add_row("Valid Until:", str(cert.get("valid_to_iso", cert.get("not_after_raw", "N/A"))))

        if is_expired:
            self.card_validity.add_row("Expiration Status:", "EXPIRED", val_color=THEME["accent_red"], mono=True)
        elif days is not None:
            day_color = THEME["accent_green"] if days > 30 else (THEME["accent_amber"] if days > 14 else THEME["accent_red"])
            self.card_validity.add_row("Days Remaining:", f"{days} Days", val_color=day_color, mono=True)
            self.card_validity.add_row("Total Lifespan:", f"{cert.get('total_validity_days', 'N/A')} Days")

            # Lifetime Meter
            pct = cert.get("validity_percentage_used", 0)
            meter_frame = tk.Frame(self.card_validity.body, bg=THEME["bg_card"])
            meter_frame.pack(fill=tk.X, pady=(6, 2))
            tk.Label(meter_frame, text=f"Life Used ({pct}%):", font=THEME["font_main"], fg=THEME["text_secondary"], bg=THEME["bg_card"], width=18, anchor="w").pack(side=tk.LEFT)
            bar = ValidityProgressBar(meter_frame)
            bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
            bar.update_progress(pct, is_expired)
        else:
            self.card_validity.add_row("Days Remaining:", "Unknown / Parse Error", val_color=THEME["accent_amber"])

        # 3. Chain & Trust Card
        self._clear_card(self.card_trust)
        trust = data.get("trust", {})
        is_trusted = trust.get("trusted", False)
        t_color = THEME["accent_green"] if is_trusted else THEME["accent_red"]
        self.card_trust.add_row("Root CA Trust:", "VERIFIED" if is_trusted else "FAILED / UNTRUSTED", val_color=t_color, mono=True)

        matched = cert.get("hostname_matched", False)
        m_color = THEME["accent_green"] if matched else THEME["accent_red"]
        self.card_trust.add_row("Hostname Match:", "PASS" if matched else "MISMATCH", val_color=m_color, mono=True)

        sans = cert.get("sans", [])
        self.card_trust.add_row("SAN Count:", f"{len(sans)} Alternative Names")
        if sans:
            san_preview = ", ".join([s["value"] for s in sans[:4]])
            if len(sans) > 4:
                san_preview += f" ... (+{len(sans)-4} more)"
            self.card_trust.add_row("SAN List:", san_preview, mono=True)

        # 4. Protocol Card
        self._clear_card(self.card_proto)
        hs = data.get("handshake", {})
        proto_ver = hs.get("protocol_version", "N/A")
        p_color = THEME["accent_green"] if proto_ver in ("TLSv1.3", "TLSv1.2") else THEME["accent_red"]
        self.card_proto.add_row("Negotiated TLS:", proto_ver, val_color=p_color, mono=True)

        cipher = hs.get("cipher_suite")
        if cipher and isinstance(cipher, tuple):
            self.card_proto.add_row("Cipher Name:", cipher[0], val_color=THEME["accent_cyan"], mono=True)
            self.card_proto.add_row("Cipher Bits:", f"{cipher[2]} bits", mono=True)
        else:
            self.card_proto.add_row("Cipher Name:", "N/A", mono=True)

        self.card_proto.add_row("ALPN Protocol:", str(hs.get("alpn_protocol") or "None"))
        dns = data.get("dns", {})
        self.card_proto.add_row("Primary Target IP:", dns.get("primary_ip", "Unknown"), mono=True)

        # 5. HTTP Security Headers Card
        self._clear_card(self.card_headers)
        h = data.get("security_headers", {})
        hsts_ok = h.get("hsts_present", False)
        self.card_headers.add_row("HSTS Active:", "YES" if hsts_ok else "NO", val_color=THEME["accent_green"] if hsts_ok else THEME["accent_amber"], mono=True)
        self.card_headers.add_row("HSTS Preloaded:", "YES" if h.get("hsts_preload") else "NO", mono=True)
        self.card_headers.add_row("CSP Active:", "YES" if h.get("csp_present") else "NO", mono=True)
        self.card_headers.add_row("X-Frame-Options:", str(h.get("x_frame_options", "N/A")), mono=True)
        self.card_headers.add_row("Server Header:", str(h.get("server_banner", "N/A")), mono=True)

        # 6. Audit & Warnings Card
        self._clear_card(self.card_audit)
        flags = data.get("audit_flags", [])
        if not flags:
            self.card_audit.add_row("Audit Finding:", "Clean Scan - Zero critical vulnerabilities detected.", val_color=THEME["accent_green"])
        else:
            for flag in flags:
                lvl = flag["level"]
                col = THEME["accent_red"] if lvl == "CRITICAL" else (THEME["accent_amber"] if lvl == "WARNING" else THEME["accent_cyan"])
                self.card_audit.add_row(f"[{lvl}]:", flag["msg"], val_color=col)

    # ==========================================================================
    #                           REPORT EXPORTER
    # ==========================================================================
    def export_json_report(self):
        """Exports the active diagnostic scan results into a formatted JSON file."""
        if not self.current_payload:
            messagebox.showinfo("Export Empty", "Run a target audit first before exporting.")
            return

        domain = self.current_payload.get("target", "domain")
        default_filename = f"ssl_audit_{domain}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile=default_filename,
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.current_payload, f, indent=4)
                messagebox.showinfo("Export Successful", f"Full audit payload saved:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Unable to write file: {e}")


# ==============================================================================
#                              MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    # Enable high DPI awareness on Windows if possible
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = TLSAnalyzerApp()
    app.mainloop()
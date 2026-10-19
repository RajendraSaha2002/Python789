import sys
import os
import re
import socket
import struct
import random
import json
import datetime
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
#                               THEME CONSTANTS
# ==============================================================================
THEME = {
    "bg_dark": "#0b101b",
    "bg_card": "#131b2a",
    "bg_card_inner": "#0d1421",
    "border": "#1e2a3f",
    "border_bright": "#2c3e5e",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#4d5b6e",
    "neon_green": "#5af78e",
    "neon_cyan": "#00e5ff",
    "neon_amber": "#ffb86c",
    "neon_red": "#ff5555",
    "badge_pass_bg": "#122a22",
    "badge_fail_bg": "#2b1418",
    "font_main": ("Segoe UI", 10) if sys.platform.startswith("win") else ("Helvetica", 10),
    "font_bold": ("Segoe UI", 10, "bold") if sys.platform.startswith("win") else ("Helvetica", 10, "bold"),
    "font_title": ("Segoe UI", 14, "bold") if sys.platform.startswith("win") else ("Helvetica", 14, "bold"),
    "font_mono": ("Consolas", 9) if sys.platform.startswith("win") else ("Menlo", 9),
    "font_mono_bold": ("Consolas", 9, "bold") if sys.platform.startswith("win") else ("Menlo", 9, "bold"),
}

# Known Email Providers Fingerprints
PROVIDER_SIGNATURES = {
    "Google Workspace": [r"_spf\.google\.com", r"googlemail\.com", r"aspmx\.l\.google\.com", r"google-site-verification"],
    "Microsoft 365": [r"spf\.protection\.outlook\.com", r"mail\.protection\.outlook\.com", r"ms\d+", r"microsoft"],
    "ProtonMail": [r"_spf\.protonmail\.ch", r"protonmail\.ch", r"protonmail-verification"],
    "Mimecast": [r"_netblocks\.mimecast\.com", r"mimecast\.com"],
    "Proofpoint": [r"_spf\.pphosted\.com", r"pphosted\.com"],
    "Amazon SES": [r"amazonses\.com", r"feedback-smtp\..*\.amazonses\.com"],
    "SendGrid": [r"sendgrid\.net", r"sendgrid\.com"],
    "Mailgun": [r"mailgun\.org", r"mailgun\.net"],
    "Zoho Mail": [r"zoho\.com", r"transmail\.net", r"zoho-verification"],
    "Fastmail": [r"fastmail\.com", r"messagingengine\.com"],
    "Apple iCloud": [r"icloud\.com", r"apple-domain-verification"],
}

# ==============================================================================
#                 PURE PYTHON RFC 1035 DNS PROTOCOL CLIENT
# ==============================================================================
class DNSQueryEngine:
    """Low-level UDP DNS client constructing RFC 1035 wire packets without 3rd party libs."""

    QTYPE_A = 1
    QTYPE_NS = 2
    QTYPE_CNAME = 5
    QTYPE_SOA = 6
    QTYPE_MX = 15
    QTYPE_TXT = 16
    QTYPE_AAAA = 28

    DNS_SERVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]

    @classmethod
    def _encode_domain(cls, domain: str) -> bytes:
        parts = domain.strip(".").split(".")
        encoded = b""
        for part in parts:
            part_b = part.encode("ascii", errors="ignore")
            encoded += bytes([len(part_b)]) + part_b
        return encoded + b"\x00"

    @classmethod
    def _decode_name(cls, buffer: bytes, offset: int):
        labels = []
        jumped = False
        start_offset = offset

        while True:
            if offset >= len(buffer):
                break
            length = buffer[offset]
            if (length & 0xC0) == 0xC0:
                pointer = struct.unpack("!H", buffer[offset:offset + 2])[0] & 0x3FFF
                if not jumped:
                    start_offset = offset + 2
                    jumped = True
                offset = pointer
                continue
            offset += 1
            if length == 0:
                break
            labels.append(buffer[offset:offset + length].decode("ascii", errors="ignore"))
            offset += length

        if not jumped:
            start_offset = offset
        return ".".join(labels), start_offset

    @classmethod
    def query_raw(cls, domain: str, qtype: int, server: str = "1.1.1.1", timeout: float = 3.5) -> list:
        """Sends raw DNS UDP datagram and parses answers."""
        query_id = random.randint(1000, 65535)
        # Header: ID, Flags(RD=1), QDCOUNT=1, ANCOUNT=0, NSCOUNT=0, ARCOUNT=0
        header = struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
        question = cls._encode_domain(domain) + struct.pack("!HH", qtype, 1)
        packet = header + question

        answers = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        try:
            sock.sendto(packet, (server, 53))
            data, _ = sock.recvfrom(4096)
        except Exception:
            return answers
        finally:
            sock.close()

        if len(data) < 12:
            return answers

        resp_id, flags, qdcount, ancount, _, _ = struct.unpack("!HHHHHH", data[:12])
        if resp_id != query_id or ancount == 0:
            return answers

        # Skip question section
        offset = 12
        for _ in range(qdcount):
            _, offset = cls._decode_name(data, offset)
            offset += 4  # Skip QTYPE and QCLASS

        # Parse answers
        for _ in range(ancount):
            if offset >= len(data):
                break
            _, offset = cls._decode_name(data, offset)
            rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
            offset += 10
            rdata_end = offset + rdlength

            if rtype == cls.QTYPE_MX:
                prio = struct.unpack("!H", data[offset:offset + 2])[0]
                exchange, _ = cls._decode_name(data, offset + 2)
                answers.append({"priority": prio, "host": exchange})
            elif rtype == cls.QTYPE_TXT:
                txt_chunks = []
                cur = offset
                while cur < rdata_end:
                    txt_len = data[cur]
                    cur += 1
                    txt_chunks.append(data[cur:cur + txt_len].decode("utf-8", errors="ignore"))
                    cur += txt_len
                answers.append("".join(txt_chunks))
            elif rtype == cls.QTYPE_A:
                ip = socket.inet_ntoa(data[offset:offset + 4])
                answers.append(ip)
            elif rtype == cls.QTYPE_AAAA:
                ip = socket.inet_ntop(socket.AF_INET6, data[offset:offset + 16])
                answers.append(ip)
            elif rtype in (cls.QTYPE_CNAME, cls.QTYPE_NS):
                name, _ = cls._decode_name(data, offset)
                answers.append(name)

            offset = rdata_end

        return answers

    @classmethod
    def query(cls, domain: str, qtype_str: str) -> list:
        """Executes pure UDP query with fallback to OS nslookup."""
        type_map = {
            "MX": cls.QTYPE_MX,
            "TXT": cls.QTYPE_TXT,
            "A": cls.QTYPE_A,
            "AAAA": cls.QTYPE_AAAA,
            "NS": cls.QTYPE_NS,
            "CNAME": cls.QTYPE_CNAME,
        }
        qtype = type_map.get(qtype_str.upper(), cls.QTYPE_TXT)

        # 1. Try Pure Python DNS UDP client first across public DNS
        for srv in cls.DNS_SERVERS:
            res = cls.query_raw(domain, qtype, server=srv)
            if res:
                return res

        # 2. Resilient Fallback to system nslookup subprocess
        return cls._nslookup_fallback(domain, qtype_str)

    @staticmethod
    def _nslookup_fallback(domain: str, qtype: str) -> list:
        records = []
        try:
            cmd = ["nslookup", f"-type={qtype}", domain]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            output = proc.stdout

            if qtype.upper() == "MX":
                matches = re.findall(r"mail exchanger = (.*?)$", output, re.MULTILINE)
                for m in matches:
                    parts = m.strip().split()
                    if len(parts) >= 2:
                        try:
                            records.append({"priority": int(parts[0]), "host": parts[1].rstrip(".")})
                        except ValueError:
                            records.append({"priority": 10, "host": parts[-1].rstrip(".")})
            elif qtype.upper() == "TXT":
                matches = re.findall(r'text\s*=\s*"(.*?)"', output, re.IGNORECASE)
                if not matches:
                    matches = re.findall(r'"([^"]*)"', output)
                records.extend(matches)
        except Exception:
            pass
        return records


# ==============================================================================
#                      EMAIL SECURITY AUDITOR CORE
# ==============================================================================
class EmailDomainAuditor:
    """Evaluates MX records, SPF, DMARC, DKIM, BIMI, and External Mail Services."""

    COMMON_DKIM_SELECTORS = [
        "default", "google", "k1", "mail", "s1", "s2", "s2048",
        "protonmail", "selector1", "selector2", "smtp", "dkim"
    ]

    def __init__(self, target: str):
        self.domain = self._clean_target(target)

    @staticmethod
    def _clean_target(target: str) -> str:
        target = target.strip().lower()
        if "://" in target:
            target = target.split("://")[1]
        target = target.split("/")[0].split(":")[0]
        return target

    def audit(self) -> dict:
        results = {
            "domain": self.domain,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checklist": {"SPF": False, "DKIM": False, "DMARC": False, "BIMI": False},
            "mx_records": [],
            "external_services": {},
            "mail_txt_records": [],
            "spf_details": {},
            "dmarc_details": {},
            "dkim_details": {},
            "bimi_details": {},
            "warnings": [],
            "score": 0,
        }

        # 1. Audit MX Records
        mx_raw = DNSQueryEngine.query(self.domain, "MX")
        mx_records = []
        if mx_raw and isinstance(mx_raw[0], dict):
            mx_records = sorted(mx_raw, key=lambda x: x.get("priority", 999))
        results["mx_records"] = mx_records

        if not mx_records:
            results["warnings"].append("No MX records configured; domain cannot directly receive inbound email.")

        # 2. Audit All TXT Records & SPF
        txt_records = DNSQueryEngine.query(self.domain, "TXT")
        spf_records = [r for r in txt_records if r.lower().startswith("v=spf1")]
        results["mail_txt_records"] = spf_records

        if len(spf_records) == 1:
            results["checklist"]["SPF"] = True
            spf_val = spf_records[0]
            results["spf_details"]["raw"] = spf_val

            # Policy strictness test
            if "-all" in spf_val:
                results["spf_details"]["policy"] = "Hardfail (-all) [Optimal]"
            elif "~all" in spf_val:
                results["spf_details"]["policy"] = "Softfail (~all) [Acceptable]"
                results["warnings"].append("SPF uses '~all' (Softfail). Consider upgrading to '-all' (Hardfail) with DMARC.")
            elif "?all" in spf_val:
                results["spf_details"]["policy"] = "Neutral (?all) [Weak]"
                results["warnings"].append("SPF policy '?all' does not block forged mail.")
            elif "+all" in spf_val:
                results["spf_details"]["policy"] = "Pass (+all) [CRITICAL VULNERABILITY]"
                results["warnings"].append("CRITICAL: SPF '+all' allows ANY IP address in the world to spoof this domain!")
            else:
                results["spf_details"]["policy"] = "Missing explicit all mechanism"

        elif len(spf_records) > 1:
            results["checklist"]["SPF"] = False
            results["warnings"].append("CRITICAL: Multiple SPF records detected! RFC 7208 specifies this causes PERMERROR.")

        # 3. Audit DMARC
        dmarc_txt = DNSQueryEngine.query(f"_dmarc.{self.domain}", "TXT")
        dmarc_candidates = [t for t in dmarc_txt if "v=dmarc1" in t.lower()]

        if dmarc_candidates:
            d_val = dmarc_candidates[0]
            results["checklist"]["DMARC"] = True
            results["dmarc_details"]["raw"] = d_val

            policy_match = re.search(r"\bp=([a-zA-Z]+)", d_val, re.IGNORECASE)
            p_val = policy_match.group(1).lower() if policy_match else "none"
            results["dmarc_details"]["policy"] = p_val

            if p_val == "reject":
                results["dmarc_details"]["enforcement"] = "Maximum Protection (reject)"
            elif p_val == "quarantine":
                results["dmarc_details"]["enforcement"] = "Quarantine Protection (quarantine)"
            else:
                results["dmarc_details"]["enforcement"] = "Monitoring Only (none)"
                results["warnings"].append("DMARC policy is set to 'p=none'; spoofed emails will not be blocked.")

            # Reports check
            has_rua = "rua=" in d_val.lower()
            results["dmarc_details"]["reports_configured"] = has_rua
            if not has_rua:
                results["warnings"].append("DMARC record lacks 'rua=' tag; aggregate telemetry is disabled.")
        else:
            results["checklist"]["DMARC"] = False
            results["warnings"].append("DMARC record is missing! Domain is susceptible to direct email impersonation.")

        # 4. Audit DKIM (Scan standard popular selectors)
        found_dkim = False
        for selector in self.COMMON_DKIM_SELECTORS:
            dkim_res = DNSQueryEngine.query(f"{selector}._domainkey.{self.domain}", "TXT")
            for entry in dkim_res:
                if "v=dkim1" in entry.lower() or "k=rsa" in entry.lower() or "p=" in entry.lower():
                    found_dkim = True
                    results["checklist"]["DKIM"] = True
                    results["dkim_details"]["selector"] = selector
                    results["dkim_details"]["raw"] = entry[:60] + "..."
                    break
            if found_dkim:
                break

        # 5. Audit BIMI (Brand Indicators for Message Identification)
        bimi_txt = DNSQueryEngine.query(f"default._bimi.{self.domain}", "TXT")
        bimi_entries = [b for b in bimi_txt if "v=bimi1" in b.lower()]
        if bimi_entries:
            results["checklist"]["BIMI"] = True
            results["bimi_details"]["raw"] = bimi_entries[0]
        else:
            results["checklist"]["BIMI"] = False

        # 6. Detect External Mail Services
        detected_services = {}
        corpus = " ".join([m.get("host", "") for m in mx_records] + txt_records)

        for provider, patterns in PROVIDER_SIGNATURES.items():
            for pat in patterns:
                match = re.search(pat, corpus, re.IGNORECASE)
                if match:
                    # Extract fingerprint token
                    token = match.group(0)
                    for t in txt_records:
                        if pat.replace(r"\.", ".") in t:
                            token = t[:36] + ("..." if len(t) > 36 else "")
                            break
                    detected_services[provider] = token
                    break

        results["external_services"] = detected_services

        # 7. Compute Security Checklist Score
        score = 0
        if results["checklist"]["SPF"]:
            score += 30
        if results["checklist"]["DMARC"]:
            score += 35
        if results["checklist"]["DKIM"]:
            score += 25
        if results["checklist"]["BIMI"]:
            score += 10
        results["score"] = score

        return results


# ==============================================================================
#                       CARD COMPONENT (SCREENSHOT UI)
# ==============================================================================
class EmailConfigCard(tk.Frame):
    """Card container replicating the exact layout from the provided screenshot."""

    def __init__(self, parent, on_refresh_callback=None, **kwargs):
        super().__init__(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightcolor=THEME["border_bright"],
            highlightthickness=1,
            padx=18,
            pady=16,
            **kwargs,
        )
        self.on_refresh_callback = on_refresh_callback
        self._build_card_header()
        self._build_sections()

    def _build_card_header(self):
        head = tk.Frame(self, bg=THEME["bg_card"])
        head.pack(fill=tk.X, pady=(0, 10))

        title = tk.Label(
            head,
            text="Email Configuration",
            font=THEME["font_title"],
            fg=THEME["neon_green"],
            bg=THEME["bg_card"],
        )
        title.pack(side=tk.LEFT)

        # Refresh / Info icon controls
        btn_box = tk.Frame(head, bg=THEME["bg_card"])
        btn_box.pack(side=tk.RIGHT)

        lbl_info = tk.Label(btn_box, text="ⓘ", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"], cursor="hand2")
        lbl_info.pack(side=tk.LEFT, padx=(0, 8))
        lbl_info.bind("<Button-1>", lambda e: messagebox.showinfo(
            "About Email Configuration",
            "Audits critical email validation standards:\n\n"
            "• SPF: Prevents unauthorized sender IPs\n"
            "• DKIM: Cryptographically signs messages\n"
            "• DMARC: Enforces alignment & reporting policies\n"
            "• BIMI: Visual brand logo verification\n"
            "• MX: Inbound routing & priority verification"
        ))

        lbl_refresh = tk.Label(btn_box, text="↺", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"], cursor="hand2")
        lbl_refresh.pack(side=tk.LEFT)
        if self.on_refresh_callback:
            lbl_refresh.bind("<Button-1>", lambda e: self.on_refresh_callback())

    def _build_sections(self):
        # Section 1: Mail Security Checklist
        self._create_section_label("Mail Security Checklist")
        self.checklist_frame = tk.Frame(self, bg=THEME["bg_card"])
        self.checklist_frame.pack(fill=tk.X, pady=(2, 10))

        self.check_labels = {}
        for check in ["SPF", "DKIM", "DMARC", "BIMI"]:
            row = tk.Frame(self.checklist_frame, bg=THEME["bg_card"])
            row.pack(fill=tk.X, pady=2)

            name = tk.Label(row, text=check, font=THEME["font_bold"], fg=THEME["text_primary"], bg=THEME["bg_card"])
            name.pack(side=tk.LEFT)

            # Divider line
            sep = tk.Frame(row, bg=THEME["border"], height=1)
            sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=4)

            badge = tk.Label(row, text=" - ", font=THEME["font_mono_bold"], fg=THEME["text_muted"], bg=THEME["bg_card"])
            badge.pack(side=tk.RIGHT)
            self.check_labels[check] = badge

        # Section 2: MX Records
        self._create_section_label("MX Records")
        self.mx_container = tk.Frame(self, bg=THEME["bg_card"])
        self.mx_container.pack(fill=tk.X, pady=(2, 10))

        # Section 3: External Mail Services
        self._create_section_label("External Mail Services")
        self.services_container = tk.Frame(self, bg=THEME["bg_card"])
        self.services_container.pack(fill=tk.X, pady=(2, 10))

        # Section 4: Mail-related TXT Records
        self._create_section_label("Mail-related TXT Records")
        self.txt_container = tk.Frame(self, bg=THEME["bg_card"])
        self.txt_container.pack(fill=tk.X, pady=(2, 4))

    def _create_section_label(self, text: str):
        lbl = tk.Label(
            self,
            text=text,
            font=THEME["font_bold"],
            fg=THEME["neon_green"],
            bg=THEME["bg_card"],
            anchor="w",
        )
        lbl.pack(fill=tk.X, pady=(6, 2))

    def update_data(self, data: dict):
        """Populates the card matching the exact visual style."""
        # 1. Update Checklist Badges
        checklist = data.get("checklist", {})
        for item, badge in self.check_labels.items():
            passed = checklist.get(item, False)
            if passed:
                badge.config(text="  ✔  ", fg=THEME["neon_green"], bg=THEME["badge_pass_bg"])
            else:
                badge.config(text="  ✖  ", fg=THEME["neon_red"], bg=THEME["badge_fail_bg"])

        # 2. Update MX Records
        for child in self.mx_container.winfo_children():
            child.destroy()

        mx_records = data.get("mx_records", [])
        if not mx_records:
            lbl = tk.Label(self.mx_container, text="No MX records discovered", font=THEME["font_mono"], fg=THEME["text_muted"], bg=THEME["bg_card"])
            lbl.pack(anchor="w")
        else:
            for mx in mx_records:
                row = tk.Frame(self.mx_container, bg=THEME["bg_card"])
                row.pack(fill=tk.X, pady=2)

                host_lbl = tk.Label(row, text=mx.get("host", ""), font=THEME["font_mono"], fg=THEME["text_primary"], bg=THEME["bg_card"])
                host_lbl.pack(side=tk.LEFT)

                prio_lbl = tk.Label(row, text=f"Priority: {mx.get('priority', 0)}", font=THEME["font_mono"], fg=THEME["text_secondary"], bg=THEME["bg_card"])
                prio_lbl.pack(side=tk.RIGHT)

                sep = tk.Frame(self.mx_container, bg=THEME["border"], height=1)
                sep.pack(fill=tk.X, pady=2)

        # 3. Update External Mail Services
        for child in self.services_container.winfo_children():
            child.destroy()

        services = data.get("external_services", {})
        if not services:
            lbl = tk.Label(self.services_container, text="No recognized external mail signatures detected", font=THEME["font_mono"], fg=THEME["text_muted"], bg=THEME["bg_card"])
            lbl.pack(anchor="w")
        else:
            for s_name, s_token in services.items():
                row = tk.Frame(self.services_container, bg=THEME["bg_card"])
                row.pack(fill=tk.X, pady=3)

                name_lbl = tk.Label(row, text=s_name, font=THEME["font_bold"], fg=THEME["text_primary"], bg=THEME["bg_card"], width=18, anchor="w")
                name_lbl.pack(side=tk.LEFT)

                tok_lbl = tk.Label(row, text=s_token, font=THEME["font_mono"], fg=THEME["text_secondary"], bg=THEME["bg_card"], anchor="e")
                tok_lbl.pack(side=tk.RIGHT, fill=tk.X, expand=True)

                sep = tk.Frame(self.services_container, bg=THEME["border"], height=1)
                sep.pack(fill=tk.X, pady=2)

        # 4. Update Mail TXT Records
        for child in self.txt_container.winfo_children():
            child.destroy()

        txt_list = data.get("mail_txt_records", [])
        if not txt_list:
            lbl = tk.Label(self.txt_container, text="No SPF/mail TXT records found", font=THEME["font_mono"], fg=THEME["text_muted"], bg=THEME["bg_card"])
            lbl.pack(anchor="w")
        else:
            for txt_val in txt_list:
                row = tk.Frame(self.txt_container, bg=THEME["bg_card_inner"], padx=8, pady=6, highlightbackground=THEME["border"], highlightthickness=1)
                row.pack(fill=tk.X, pady=3)

                lbl = tk.Label(row, text=txt_val, font=THEME["font_mono"], fg=THEME["neon_cyan"], bg=THEME["bg_card_inner"], wraplength=480, justify=tk.LEFT)
                lbl.pack(anchor="w")


# ==============================================================================
#                             MAIN GUI APPLICATION
# ==============================================================================
class EmailSecurityApp(tk.Tk):
    """Main Application Controller."""

    def __init__(self):
        super().__init__()
        self.title("DNS & Email Security Auditor")
        self.geometry("1180x840")
        self.minsize(980, 720)
        self.configure(bg=THEME["bg_dark"])

        self.scan_queue = queue.Queue()
        self.current_payload = None

        self._configure_styles()
        self._build_top_bar()
        self._build_content_area()

        # Start background worker queue polling
        self.after(100, self._process_scan_queue)

        # Initial benchmark run (proton.me or protonmail.ch matching the screenshot)
        self.target_entry.insert(0, "proton.me")
        self.start_audit()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=THEME["bg_dark"], foreground=THEME["text_primary"])
        style.configure("TScrollbar", background=THEME["bg_card"], troughcolor=THEME["bg_dark"], bordercolor=THEME["border"])

    def _build_top_bar(self):
        bar = tk.Frame(self, bg=THEME["bg_card"], padx=18, pady=12, highlightbackground=THEME["border"], highlightthickness=1)
        bar.pack(fill=tk.X, padx=16, pady=(16, 10))

        brand = tk.Label(bar, text="🛡️ MAIL SEC AUDITOR", font=THEME["font_title"], fg=THEME["neon_green"], bg=THEME["bg_card"])
        brand.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(bar, text="Domain:", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(side=tk.LEFT, padx=(0, 6))

        self.target_entry = tk.Entry(
            bar,
            font=THEME["font_mono_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["neon_cyan"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["neon_green"],
            highlightthickness=1,
            width=32,
        )
        self.target_entry.pack(side=tk.LEFT, padx=(0, 12), ipady=4)
        self.target_entry.bind("<Return>", lambda e: self.start_audit())

        self.btn_scan = tk.Button(
            bar,
            text="AUDIT DOMAIN",
            font=THEME["font_bold"],
            bg=THEME["neon_green"],
            fg="#050a12",
            activebackground=THEME["neon_cyan"],
            relief=tk.FLAT,
            padx=16,
            pady=4,
            cursor="hand2",
            command=self.start_audit,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=4)

        self.btn_export = tk.Button(
            bar,
            text="EXPORT REPORT",
            font=THEME["font_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            activebackground=THEME["border_bright"],
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.export_report,
        )
        self.btn_export.pack(side=tk.LEFT, padx=4)

        self.lbl_status = tk.Label(bar, text="Ready", font=THEME["font_mono"], fg=THEME["text_muted"], bg=THEME["bg_card"])
        self.lbl_status.pack(side=tk.RIGHT, padx=6)

    def _build_content_area(self):
        container = tk.Frame(self, bg=THEME["bg_dark"])
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        # Left Column: Exact Email Configuration Card (from screenshot)
        left_pane = tk.Frame(container, bg=THEME["bg_dark"], width=520)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_pane.pack_propagate(False)

        self.email_card = EmailConfigCard(left_pane, on_refresh_callback=self.start_audit)
        self.email_card.pack(fill=tk.BOTH, expand=True)

        # Right Column: Deep Inspection Details & Warnings
        right_pane = tk.Frame(container, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1, padx=16, pady=14)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right_pane, text="Domain Security Diagnostics & Advisory", font=THEME["font_title"], fg=THEME["neon_cyan"], bg=THEME["bg_card"]).pack(anchor="w")

        self.txt_advisory = tk.Text(
            right_pane,
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            font=THEME["font_mono"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=12,
            pady=12,
        )
        self.txt_advisory.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def start_audit(self):
        target = self.target_entry.get().strip()
        if not target:
            messagebox.showwarning("Input Missing", "Please enter a valid domain name.")
            return

        self.btn_scan.config(state=tk.DISABLED, text="AUDITING...")
        self.lbl_status.config(text="Resolving DNS records...", fg=THEME["neon_cyan"])

        # Run non-blocking worker thread
        t = threading.Thread(target=self._worker_audit, args=(target,), daemon=True)
        t.start()

    def _worker_audit(self, target: str):
        auditor = EmailDomainAuditor(target)
        result = auditor.audit()
        self.scan_queue.put(result)

    def _process_scan_queue(self):
        try:
            while not self.scan_queue.empty():
                payload = self.scan_queue.get_nowait()
                self._render_audit(payload)
                self.btn_scan.config(state=tk.NORMAL, text="AUDIT DOMAIN")
                self.lbl_status.config(text=f"Scan complete ({payload.get('score', 0)}/100)", fg=THEME["neon_green"])
        finally:
            self.after(100, self._process_scan_queue)

    def _render_audit(self, data: dict):
        self.current_payload = data

        # 1. Update left screenshot card
        self.email_card.update_data(data)

        # 2. Update right diagnostic console
        self.txt_advisory.config(state=tk.NORMAL)
        self.txt_advisory.delete("1.0", tk.END)

        dom = data.get("domain", "")
        score = data.get("score", 0)

        self.txt_advisory.insert(tk.END, f"=================================================================\n")
        self.txt_advisory.insert(tk.END, f" TARGET SECURITY POSTURE: {dom.upper()}  [SCORE: {score}/100]\n")
        self.txt_advisory.insert(tk.END, f" Timestamp: {data.get('timestamp')}\n")
        self.txt_advisory.insert(tk.END, f"=================================================================\n\n")

        # Checklist overview
        self.txt_advisory.insert(tk.END, "[*] PROTOCOL STATUS OVERVIEW:\n")
        for k, v in data.get("checklist", {}).items():
            status_symbol = "[ PASS ]" if v else "[ FAIL ]"
            self.txt_advisory.insert(tk.END, f"  {k:<8}: {status_symbol}\n")

        # Detailed SPF Breakdown
        self.txt_advisory.insert(tk.END, "\n[*] SPF (SENDER POLICY FRAMEWORK) ANALYSIS:\n")
        spf = data.get("spf_details", {})
        if spf:
            self.txt_advisory.insert(tk.END, f"  • Policy Directive: {spf.get('policy', 'None')}\n")
            self.txt_advisory.insert(tk.END, f"  • Raw Value: {spf.get('raw', '')}\n")
        else:
            self.txt_advisory.insert(tk.END, "  • No SPF records discovered.\n")

        # Detailed DMARC Breakdown
        self.txt_advisory.insert(tk.END, "\n[*] DMARC (DOMAIN-BASED MESSAGE AUTHENTICATION) ANALYSIS:\n")
        dmarc = data.get("dmarc_details", {})
        if dmarc:
            self.txt_advisory.insert(tk.END, f"  • Enforced Policy: {dmarc.get('enforcement', 'None')}\n")
            self.txt_advisory.insert(tk.END, f"  • Aggregate Reports (rua): {'Configured' if dmarc.get('reports_configured') else 'Missing'}\n")
            self.txt_advisory.insert(tk.END, f"  • Raw Value: {dmarc.get('raw', '')}\n")
        else:
            self.txt_advisory.insert(tk.END, "  • No DMARC record found at _dmarc." + dom + "\n")

        # Detailed DKIM & BIMI
        self.txt_advisory.insert(tk.END, "\n[*] DKIM & BIMI RECORD TRACES:\n")
        dkim = data.get("dkim_details", {})
        if dkim:
            self.txt_advisory.insert(tk.END, f"  • Active DKIM Selector: '{dkim.get('selector')}'\n")
            self.txt_advisory.insert(tk.END, f"  • Signature String: {dkim.get('raw')}\n")
        else:
            self.txt_advisory.insert(tk.END, "  • No standard DKIM selector discovered during automatic scan.\n")

        bimi = data.get("bimi_details", {})
        if bimi:
            self.txt_advisory.insert(tk.END, f"  • BIMI Visual Indicator Record: {bimi.get('raw')}\n")
        else:
            self.txt_advisory.insert(tk.END, "  • BIMI record is not configured.\n")

        # Warnings and Security Hardening Recommendations
        self.txt_advisory.insert(tk.END, "\n[!] DEFENSIVE SECURITY ADVISORY & WARNINGS:\n")
        warnings = data.get("warnings", [])
        if not warnings:
            self.txt_advisory.insert(tk.END, "  ✔ Excellent posture! Zero mail configuration vulnerabilities flagged.\n")
        else:
            for w in warnings:
                self.txt_advisory.insert(tk.END, f"  ⚠️ {w}\n")

        self.txt_advisory.config(state=tk.DISABLED)

    def export_report(self):
        """Saves active security scan as formatted JSON and Text reports."""
        if not self.current_payload:
            messagebox.showinfo("Export Empty", "Run an audit first before exporting.")
            return

        dom = self.current_payload.get("domain", "domain")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Audit", "*.json"), ("Text Report", "*.txt")],
            initialfile=f"email_security_{dom}_{ts}.json",
        )

        if filepath:
            try:
                if filepath.endswith(".json"):
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(self.current_payload, f, indent=4)
                else:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(self.txt_advisory.get("1.0", tk.END))
                messagebox.showinfo("Report Exported", f"Audit report successfully saved:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Unable to save report:\n{e}")


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

    app = EmailSecurityApp()
    app.mainloop()
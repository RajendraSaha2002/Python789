import os
import sys
import re
import csv
import ssl
import json
import queue
import datetime
import threading
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
    "bg_root": "#0a0e17",
    "bg_card": "#121927",
    "bg_card_inner": "#0a0f1a",
    "border": "#1e2a3f",
    "border_highlight": "#2d3e5c",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#525b68",
    "grade_a": "#00ff88",
    "grade_b": "#00d2ff",
    "grade_c": "#ffb86c",
    "grade_d": "#ff9100",
    "grade_f": "#ff5252",
    "stat_box_bg": "#101622",
    "row_odd": "#101624",
    "row_even": "#121927",
    "font_main": ("Segoe UI", 9) if sys.platform.startswith("win") else ("Helvetica", 9),
    "font_bold": ("Segoe UI", 9, "bold") if sys.platform.startswith("win") else ("Helvetica", 9, "bold"),
    "font_title": ("Segoe UI", 13, "bold") if sys.platform.startswith("win") else ("Helvetica", 13, "bold"),
    "font_metric": ("Segoe UI", 22, "bold") if sys.platform.startswith("win") else ("Helvetica", 22, "bold"),
    "font_mono": ("Consolas", 9) if sys.platform.startswith("win") else ("Menlo", 9),
    "font_mono_bold": ("Consolas", 9, "bold") if sys.platform.startswith("win") else ("Menlo", 9, "bold"),
}

# ==============================================================================
#                          SECURITY AUDIT ENGINE
# ==============================================================================
SECURITY_HEADER_STANDARDS = {
    "Strict-Transport-Security": {
        "name": "Strict-Transport-Security (HSTS)",
        "weight": 25,
        "category": "Transport Security",
        "desc": "Forces modern web browsers to communicate exclusively via HTTPS.",
        "remediation": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload' in web server config.",
    },
    "Content-Security-Policy": {
        "name": "Content-Security-Policy (CSP)",
        "weight": 25,
        "category": "XSS & Injection",
        "desc": "Mitigates cross-site scripting (XSS), data injections, and content tampering.",
        "remediation": "Define a robust policy: 'default-src \\'self\\'; script-src \\'self\\'; object-src \\'none\\''.",
    },
    "X-Frame-Options": {
        "name": "X-Frame-Options",
        "weight": 15,
        "category": "Clickjacking",
        "desc": "Prevents clickjacking attacks by forbidding framing of this page.",
        "remediation": "Set 'X-Frame-Options: DENY' or 'X-Frame-Options: SAMEORIGIN'.",
    },
    "X-Content-Type-Options": {
        "name": "X-Content-Type-Options",
        "weight": 15,
        "category": "MIME Sniffing",
        "desc": "Stops browsers from MIME-sniffing a response away from the declared Content-Type.",
        "remediation": "Set 'X-Content-Type-Options: nosniff' across all responses.",
    },
    "Referrer-Policy": {
        "name": "Referrer-Policy",
        "weight": 10,
        "category": "Information Leak",
        "desc": "Controls what data is sent inside the Referer header during navigations.",
        "remediation": "Set 'Referrer-Policy: strict-origin-when-cross-origin' or 'no-referrer'.",
    },
    "Permissions-Policy": {
        "name": "Permissions-Policy",
        "weight": 10,
        "category": "Browser Capabilities",
        "desc": "Restricts browser API access (geolocation, camera, microphone, payment).",
        "remediation": "Set 'Permissions-Policy: camera=(), microphone=(), geolocation=()'.",
    },
}

INFO_LEAK_HEADERS = ["Server", "X-Powered-By", "X-AspNet-Version", "X-Runtime"]


class DomainAuditor:
    """Audits headers, cookies, and TLS policies for a target domain."""

    def __init__(self, target: str, timeout: float = 6.0):
        self.raw_target = target.strip()
        self.timeout = timeout
        self.url = self._format_url(self.raw_target)
        self.domain = urllib.parse.urlsplit(self.url).hostname or self.raw_target

    @staticmethod
    def _format_url(target: str) -> str:
        target = target.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            return f"https://{target}"
        return target

    def audit(self) -> dict:
        result = {
            "target": self.raw_target,
            "domain": self.domain,
            "final_url": self.url,
            "status_code": 0,
            "score": 0,
            "grade": "F",
            "present_headers": {},
            "missing_headers": [],
            "info_leaks": {},
            "cookies": [],
            "cookie_risks": [],
            "hsts_details": {},
            "csp_details": {},
            "remediations": [],
            "error": None,
        }

        # Setup standard-compliant SSL context
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Security-Header-Auditor/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        resp_headers = {}
        cookie_raw_headers = []

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as resp:
                result["status_code"] = resp.status
                result["final_url"] = resp.geturl()

                # Collect headers into lowercase key mapping
                for k, v in resp.getheaders():
                    lower_k = k.lower()
                    if lower_k == "set-cookie":
                        cookie_raw_headers.append(v)
                    else:
                        resp_headers[lower_k] = v

        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            for k, v in e.headers.items():
                lower_k = k.lower()
                if lower_k == "set-cookie":
                    cookie_raw_headers.append(v)
                else:
                    resp_headers[lower_k] = v
        except Exception as e:
            result["error"] = str(e)
            result["score"] = 0
            result["grade"] = "F"
            result["missing_headers"] = list(SECURITY_HEADER_STANDARDS.keys())
            return result

        # 1. Evaluate Core Headers
        score = 0
        for header, spec in SECURITY_HEADER_STANDARDS.items():
            val = resp_headers.get(header.lower())
            if val:
                result["present_headers"][header] = val
                score += spec["weight"]
            else:
                result["missing_headers"].append(header)
                result["remediations"].append({
                    "priority": "HIGH" if spec["weight"] >= 20 else "MEDIUM",
                    "title": f"Missing {header}",
                    "remediation": spec["remediation"],
                })

        # 2. Evaluate HSTS Details
        hsts_val = resp_headers.get("strict-transport-security")
        if hsts_val:
            hsts_val_lower = hsts_val.lower()
            max_age_match = re.search(r"max-age=(\d+)", hsts_val_lower)
            max_age = int(max_age_match.group(1)) if max_age_match else 0
            has_subdomains = "includesubdomains" in hsts_val_lower
            is_preload = "preload" in hsts_val_lower

            result["hsts_details"] = {
                "raw": hsts_val,
                "max_age": max_age,
                "include_subdomains": has_subdomains,
                "preload": is_preload,
            }

            if max_age < 10368000:  # < 120 days
                score = max(0, score - 8)
                result["remediations"].append({
                    "priority": "MEDIUM",
                    "title": "HSTS max-age too short",
                    "remediation": "Increase HSTS max-age to at least 31536000 seconds (1 year).",
                })
            if not has_subdomains:
                result["remediations"].append({
                    "priority": "LOW",
                    "title": "HSTS without subdomains",
                    "remediation": "Add 'includeSubDomains' to your HSTS directive to protect all subdomains.",
                })

        # 3. Evaluate CSP Details
        csp_val = resp_headers.get("content-security-policy")
        if csp_val:
            has_unsafe_inline = "'unsafe-inline'" in csp_val.lower()
            has_unsafe_eval = "'unsafe-eval'" in csp_val.lower()
            has_default_src = "default-src" in csp_val.lower()

            result["csp_details"] = {
                "raw": csp_val,
                "unsafe_inline": has_unsafe_inline,
                "unsafe_eval": has_unsafe_eval,
                "default_src_present": has_default_src,
            }

            if has_unsafe_inline:
                score = max(0, score - 5)
                result["remediations"].append({
                    "priority": "MEDIUM",
                    "title": "CSP includes 'unsafe-inline'",
                    "remediation": "Eliminate 'unsafe-inline' by using cryptographically random nonces or hashes.",
                })
            if has_unsafe_eval:
                score = max(0, score - 5)
                result["remediations"].append({
                    "priority": "MEDIUM",
                    "title": "CSP includes 'unsafe-eval'",
                    "remediation": "Refactor JavaScript code to remove eval() and avoid using 'unsafe-eval'.",
                })

        # 4. Check Information Leak Headers
        for leak in INFO_LEAK_HEADERS:
            val = resp_headers.get(leak.lower())
            if val:
                result["info_leaks"][leak] = val
                score = max(0, score - 3)
                result["remediations"].append({
                    "priority": "LOW",
                    "title": f"Information disclosure via {leak}",
                    "remediation": f"Suppress or obfuscate the '{leak}' header to avoid exposing server versions.",
                })

        # 5. Evaluate Cookie Security Attributes
        for raw_c in cookie_raw_headers:
            try:
                c = http.cookies.SimpleCookie()
                c.load(raw_c)
                for cookie_name, morsel in c.items():
                    flags = {
                        "name": cookie_name,
                        "secure": morsel["secure"] is True or "secure" in morsel.output().lower(),
                        "httponly": morsel["httponly"] is True or "httponly" in morsel.output().lower(),
                        "samesite": morsel["samesite"] if "samesite" in morsel else "None",
                    }
                    result["cookies"].append(flags)

                    # Deduct points for insecure cookies
                    if not flags["secure"]:
                        result["cookie_risks"].append(f"Cookie '{cookie_name}' lacks 'Secure' flag.")
                        score = max(0, score - 4)
                    if not flags["httponly"]:
                        result["cookie_risks"].append(f"Cookie '{cookie_name}' lacks 'HttpOnly' flag.")
                        score = max(0, score - 3)
                    if flags["samesite"] in ("None", "", None):
                        result["cookie_risks"].append(f"Cookie '{cookie_name}' lacks explicit 'SameSite' attribute.")
                        score = max(0, score - 2)
            except Exception:
                pass

        # 6. Final Score & Grade Assignment
        result["score"] = max(0, min(100, score))
        if result["score"] >= 90:
            result["grade"] = "A"
        elif result["score"] >= 75:
            result["grade"] = "B"
        elif result["score"] >= 60:
            result["grade"] = "C"
        elif result["score"] >= 40:
            result["grade"] = "D"
        else:
            result["grade"] = "F"

        return result


# ==============================================================================
#                        CUSTOM UI WIDGETS
# ==============================================================================
class StatCard(tk.Frame):
    """Executive metric summary card matching the top stat boxes in the screenshot."""

    def __init__(self, parent, value: str, label: str, val_color: str, **kwargs):
        super().__init__(
            parent,
            bg=THEME["stat_box_bg"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=12,
            **kwargs,
        )
        self.val_lbl = tk.Label(self, text=value, font=THEME["font_metric"], fg=val_color, bg=THEME["stat_box_bg"])
        self.val_lbl.pack(anchor="w")

        self.label_lbl = tk.Label(self, text=label.upper(), font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["stat_box_bg"])
        self.label_lbl.pack(anchor="w", pady=(2, 0))

    def update_value(self, val: str):
        self.val_lbl.config(text=val)


class MiniScoreBar(tk.Frame):
    """Custom progress meter visualizing the 0-100 score."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME["bg_card_inner"], height=7, width=70, **kwargs)
        self.pack_propagate(False)
        self.fill_bar = tk.Frame(self, bg=THEME["grade_a"], height=7)
        self.fill_bar.place(x=0, y=0, relheight=1.0, width=0)

    def set_score(self, score: int, grade: str):
        color_map = {
            "A": THEME["grade_a"],
            "B": THEME["grade_b"],
            "C": THEME["grade_c"],
            "D": THEME["grade_d"],
            "F": THEME["grade_f"],
        }
        color = color_map.get(grade, THEME["grade_f"])
        self.fill_bar.config(bg=color)
        pct = max(0.02, min(1.0, score / 100.0))
        self.fill_bar.place_configure(relwidth=pct)


# ==============================================================================
#                        MAIN APPLICATION WINDOW
# ==============================================================================
class HeaderAuditorApp(tk.Tk):
    """Main Application GUI."""

    def __init__(self):
        super().__init__()
        self.title("HTTP Security Headers & Cookie Auditor")
        self.geometry("1280x880")
        self.minsize(1080, 720)
        self.configure(bg=THEME["bg_root"])

        self.task_queue = queue.Queue()
        self.audit_results = []
        self.selected_audit = None

        self._configure_styles()
        self._build_top_brand_bar()
        self._build_stat_cards()
        self._build_controls()
        self._build_main_split_view()

        # Preload standard benchmark domains as seen in audit suites
        default_benchmarks = [
            "bbc.co.uk", "gov.uk", "autotrader.co.uk", "reed.co.uk",
            "github.com", "amazon.co.uk", "barclays.co.uk", "linkedin.com",
            "nhs.uk", "stackoverflow.com", "tesco.com", "rightmove.co.uk"
        ]
        self.domain_input_entry.insert(0, ", ".join(default_benchmarks))

        # Start periodic queue processor
        self.after(100, self._process_task_queue)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=THEME["bg_root"], foreground=THEME["text_primary"])
        style.configure("TScrollbar", background=THEME["bg_card"], troughcolor=THEME["bg_root"], bordercolor=THEME["border"])

    def _build_top_brand_bar(self):
        """Header matching the screenshot title layout."""
        brand_frame = tk.Frame(self, bg=THEME["bg_root"], padx=20, pady=12)
        brand_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            brand_frame,
            text="🛡️ HTTP Security Headers Auditor",
            font=THEME["font_title"],
            fg=THEME["text_primary"],
            bg=THEME["bg_root"],
        )
        title_lbl.pack(anchor="w")

        now_str = datetime.datetime.now().strftime("%d %b %Y %H:%M")
        self.sub_title_lbl = tk.Label(
            brand_frame,
            text=f"OWASP recommended headers • Ready for execution • {now_str}",
            font=THEME["font_main"],
            fg=THEME["text_secondary"],
            bg=THEME["bg_root"],
        )
        self.sub_title_lbl.pack(anchor="w", pady=(2, 0))

    def _build_stat_cards(self):
        """Top stat boxes matching: AVG SCORE, GRADE A, GRADE F, AUDITED."""
        stats_frame = tk.Frame(self, bg=THEME["bg_root"], padx=20, pady=6)
        stats_frame.pack(fill=tk.X)

        self.card_avg = StatCard(stats_frame, "--", "Avg Score", THEME["grade_b"])
        self.card_avg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.card_a = StatCard(stats_frame, "0", "Grade A", THEME["grade_a"])
        self.card_a.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.card_f = StatCard(stats_frame, "0", "Grade F", THEME["grade_f"])
        self.card_f.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.card_total = StatCard(stats_frame, "0", "Audited", THEME["text_primary"])
        self.card_total.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

    def _build_controls(self):
        """Input and control bar for running scans and exporting data."""
        bar = tk.Frame(self, bg=THEME["bg_card"], padx=16, pady=10, highlightbackground=THEME["border"], highlightthickness=1)
        bar.pack(fill=tk.X, padx=20, pady=(10, 8))

        tk.Label(bar, text="Target Domains (comma-separated):", font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"]).pack(side=tk.LEFT, padx=(0, 10))

        self.domain_input_entry = tk.Entry(
            bar,
            font=THEME["font_mono"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["grade_b"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["grade_b"],
            highlightthickness=1,
        )
        self.domain_input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)

        self.scan_btn = tk.Button(
            bar,
            text="AUDIT DOMAINS",
            font=THEME["font_bold"],
            bg=THEME["grade_b"],
            fg="#050a12",
            activebackground=THEME["grade_a"],
            activeforeground="#050a12",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.start_batch_audit,
        )
        self.scan_btn.pack(side=tk.LEFT, padx=4)

        self.export_csv_btn = tk.Button(
            bar,
            text="EXPORT CSV",
            font=THEME["font_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            activebackground=THEME["border_highlight"],
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.export_csv,
        )
        self.export_csv_btn.pack(side=tk.LEFT, padx=4)

    def _build_main_split_view(self):
        """Split view: Table on top/left, deep inspection card on bottom/right."""
        main_paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 14))

        # 1. Top Section: Table List
        table_frame = tk.Frame(main_paned, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        main_paned.add(table_frame, weight=3)

        # Scrollable table container
        canvas = tk.Canvas(table_frame, bg=THEME["bg_card"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        self.table_inner = tk.Frame(canvas, bg=THEME["bg_card"])

        self.table_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self.table_inner, anchor="nw")

        def _resize_canvas(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _resize_canvas)
        canvas.configure(yscrollcommand=v_scroll.set)

        # Mousewheel scroll support
        def _scroll_table(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)) if sys.platform.startswith("win") else int(-1 * event.delta), "units")

        canvas.bind_all("<MouseWheel>", _scroll_table)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._render_table_headers()

        # 2. Bottom Section: Drill-down Inspector
        self.inspector_frame = tk.Frame(main_paned, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1, padx=16, pady=12)
        main_paned.add(self.inspector_frame, weight=2)

        # Tabs in inspector: Headers, Cookies, Remediation
        self.notebook = ttk.Notebook(self.inspector_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_headers = tk.Frame(self.notebook, bg=THEME["bg_card"])
        self.tab_cookies = tk.Frame(self.notebook, bg=THEME["bg_card"])
        self.tab_remediation = tk.Frame(self.notebook, bg=THEME["bg_card"])

        self.notebook.add(self.tab_headers, text="Active & Missing Headers")
        self.notebook.add(self.tab_cookies, text="Cookie Security Flags")
        self.notebook.add(self.tab_remediation, text="Remediation Advisory")

        # Initial inspector empty message
        self.empty_lbl = tk.Label(self.tab_headers, text="Select any domain from the list above to view deep diagnostic inspection.", font=THEME["font_main"], fg=THEME["text_muted"], bg=THEME["bg_card"])
        self.empty_lbl.pack(pady=40)

    def _render_table_headers(self):
        """Header row matching screenshot columns: # | DOMAIN | GRADE | SCORE | HEADERS | MISSING."""
        h_frame = tk.Frame(self.table_inner, bg=THEME["bg_card_inner"], padx=12, pady=8)
        h_frame.pack(fill=tk.X, side=tk.TOP)

        cols = [
            ("#", 4, "w"),
            ("DOMAIN", 22, "w"),
            ("GRADE", 8, "center"),
            ("SCORE", 16, "w"),
            ("HEADERS", 10, "center"),
            ("MISSING", 45, "w"),
        ]

        for title, width, anchor in cols:
            tk.Label(
                h_frame,
                text=title,
                font=THEME["font_mono_bold"],
                fg=THEME["text_secondary"],
                bg=THEME["bg_card_inner"],
                width=width,
                anchor=anchor,
            ).pack(side=tk.LEFT, padx=4)

    # ==========================================================================
    #                     SCAN MANAGEMENT & WORKERS
    # ==========================================================================
    def start_batch_audit(self):
        raw_text = self.domain_input_entry.get().strip()
        if not raw_text:
            messagebox.showwarning("Input Missing", "Please enter at least one target domain.")
            return

        domains = [d.strip() for d in raw_text.split(",") if d.strip()]
        if not domains:
            return

        self.scan_btn.config(state=tk.DISABLED, text="AUDITING...")
        self.audit_results.clear()

        # Clear existing table rows
        for child in list(self.table_inner.winfo_children())[1:]:
            child.destroy()

        self.sub_title_lbl.config(text=f"Auditing {len(domains)} target domains in parallel...")

        # Worker thread
        t = threading.Thread(target=self._worker_scan_domains, args=(domains,), daemon=True)
        t.start()

    def _worker_scan_domains(self, domains: list):
        for idx, dom in enumerate(domains, 1):
            auditor = DomainAuditor(dom)
            res = auditor.audit()
            res["index"] = idx
            self.task_queue.put(res)

        self.task_queue.put({"__FINISHED__": True, "total": len(domains)})

    def _process_task_queue(self):
        try:
            while not self.task_queue.empty():
                item = self.task_queue.get_nowait()
                if "__FINISHED__" in item:
                    self.scan_btn.config(state=tk.NORMAL, text="AUDIT DOMAINS")
                    self.sub_title_lbl.config(
                        text=f"OWASP recommended headers • {item['total']} domains scanned • {datetime.datetime.now().strftime('%d %b %Y %H:%M')}"
                    )
                    self._update_aggregate_stats()
                else:
                    self.audit_results.append(item)
                    self._append_table_row(item)
                    self._update_aggregate_stats()
        finally:
            self.after(100, self._process_task_queue)

    def _append_table_row(self, data: dict):
        """Constructs an aligned table row matching the provided screenshot design."""
        idx = data.get("index", 1)
        row_bg = THEME["row_odd"] if idx % 2 != 0 else THEME["row_even"]

        row = tk.Frame(self.table_inner, bg=row_bg, padx=12, pady=7, highlightbackground=THEME["border"], highlightthickness=0)
        row.pack(fill=tk.X, side=tk.TOP)

        # Hover and click to inspect
        def _on_enter(e):
            row.config(bg=THEME["border"])
            for child in row.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=THEME["border"])

        def _on_leave(e):
            row.config(bg=row_bg)
            for child in row.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=row_bg)

        def _on_click(e):
            self.display_drilldown(data)

        row.bind("<Enter>", _on_enter)
        row.bind("<Leave>", _on_leave)
        row.bind("<Button-1>", _on_click)

        # 1. Index
        lbl_idx = tk.Label(row, text=str(idx), font=THEME["font_mono"], fg=THEME["text_muted"], bg=row_bg, width=4, anchor="w")
        lbl_idx.pack(side=tk.LEFT, padx=4)
        lbl_idx.bind("<Button-1>", _on_click)

        # 2. Domain
        lbl_dom = tk.Label(row, text=data["domain"], font=THEME["font_bold"], fg=THEME["text_primary"], bg=row_bg, width=22, anchor="w")
        lbl_dom.pack(side=tk.LEFT, padx=4)
        lbl_dom.bind("<Button-1>", _on_click)

        # 3. Grade Badge
        grade = data["grade"]
        color_map = {
            "A": THEME["grade_a"],
            "B": THEME["grade_b"],
            "C": THEME["grade_c"],
            "D": THEME["grade_d"],
            "F": THEME["grade_f"],
        }
        badge_color = color_map.get(grade, THEME["grade_f"])

        grade_frame = tk.Frame(row, bg=row_bg, width=64)
        grade_frame.pack(side=tk.LEFT, padx=4)
        grade_frame.pack_propagate(False)

        lbl_grade = tk.Label(
            grade_frame,
            text=f" {grade} ",
            font=THEME["font_mono_bold"],
            fg=badge_color,
            bg=THEME["stat_box_bg"],
            highlightbackground=badge_color,
            highlightthickness=1,
            padx=6,
            pady=1,
        )
        lbl_grade.pack(anchor="center")
        lbl_grade.bind("<Button-1>", _on_click)

        # 4. Score + Mini Progress Bar
        score_frame = tk.Frame(row, bg=row_bg, width=120)
        score_frame.pack(side=tk.LEFT, padx=4)
        score_frame.pack_propagate(False)

        lbl_score = tk.Label(score_frame, text=f"{data['score']}/100", font=THEME["font_mono_bold"], fg=badge_color, bg=row_bg)
        lbl_score.pack(anchor="w")
        lbl_score.bind("<Button-1>", _on_click)

        bar = MiniScoreBar(score_frame)
        bar.pack(anchor="w", pady=(2, 0))
        bar.set_score(data["score"], grade)

        # 5. Headers count (e.g., 6/7)
        present_count = len(data["present_headers"])
        total_std = len(SECURITY_HEADER_STANDARDS)
        lbl_count = tk.Label(row, text=f"{present_count}/{total_std}", font=THEME["font_mono"], fg=THEME["text_primary"], bg=row_bg, width=10, anchor="center")
        lbl_count.pack(side=tk.LEFT, padx=4)
        lbl_count.bind("<Button-1>", _on_click)

        # 6. Missing headers summary list
        missing_list = data["missing_headers"]
        missing_str = ", ".join([h.replace("X-", "").replace("Strict-Transport-Security", "HSTS").replace("Content-Security-Policy", "CSP").replace("-Options", "") for h in missing_list]) if missing_list else "None"
        if len(missing_str) > 48:
            missing_str = missing_str[:45] + "..."

        lbl_missing = tk.Label(row, text=missing_str, font=THEME["font_main"], fg=THEME["text_muted"] if missing_str == "None" else THEME["grade_c"], bg=row_bg, width=45, anchor="w")
        lbl_missing.pack(side=tk.LEFT, padx=4)
        lbl_missing.bind("<Button-1>", _on_click)

        # Auto select the first domain if not selected yet
        if len(self.audit_results) == 1:
            self.display_drilldown(data)

    def _update_aggregate_stats(self):
        """Recalculates the top 4 executive metric cards."""
        if not self.audit_results:
            return

        total = len(self.audit_results)
        avg_score = int(sum(r["score"] for r in self.audit_results) / total)
        count_a = sum(1 for r in self.audit_results if r["grade"] == "A")
        count_f = sum(1 for r in self.audit_results if r["grade"] == "F")

        self.card_avg.update_value(str(avg_score))
        self.card_a.update_value(str(count_a))
        self.card_f.update_value(str(count_f))
        self.card_total.update_value(str(total))

    # ==========================================================================
    #                      DRILL-DOWN DETAIL INSPECTOR
    # ==========================================================================
    def display_drilldown(self, data: dict):
        """Populates the bottom tabbed notebook with deep analytical data."""
        self.selected_audit = data

        # Clear existing tabs
        for tab in (self.tab_headers, self.tab_cookies, self.tab_remediation):
            for child in tab.winfo_children():
                child.destroy()

        # 1. Headers Tab
        h_box = tk.Text(self.tab_headers, bg=THEME["bg_card_inner"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=10, pady=10)
        h_box.pack(fill=tk.BOTH, expand=True)

        h_box.insert(tk.END, f"=== SECURITY HEADER AUDIT: {data['domain']} (Score: {data['score']}/100 - Grade {data['grade']}) ===\n\n")

        h_box.insert(tk.END, "[+] ACTIVE / PRESENT HEADERS:\n")
        if data["present_headers"]:
            for k, v in data["present_headers"].items():
                h_box.insert(tk.END, f"  • {k}: {v}\n")
        else:
            h_box.insert(tk.END, "  (None detected)\n")

        h_box.insert(tk.END, "\n[-] MISSING SECURITY HEADERS:\n")
        if data["missing_headers"]:
            for m in data["missing_headers"]:
                spec = SECURITY_HEADER_STANDARDS.get(m, {})
                h_box.insert(tk.END, f"  ✖ {m} (Weight: {spec.get('weight', 0)} pts) - {spec.get('desc', '')}\n")
        else:
            h_box.insert(tk.END, "  ✔ Excellent! All standard OWASP security headers are present.\n")

        if data["info_leaks"]:
            h_box.insert(tk.END, "\n[!] INFORMATION DISCLOSURE HEADERS:\n")
            for k, v in data["info_leaks"].items():
                h_box.insert(tk.END, f"  ⚠️ {k}: {v}\n")

        h_box.config(state=tk.DISABLED)

        # 2. Cookies Tab
        c_box = tk.Text(self.tab_cookies, bg=THEME["bg_card_inner"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=10, pady=10)
        c_box.pack(fill=tk.BOTH, expand=True)

        c_box.insert(tk.END, f"=== COOKIE ATTRIBUTE AUDIT: {data['domain']} ===\n\n")
        if not data["cookies"]:
            c_box.insert(tk.END, "No Set-Cookie directives were observed during the HTTP response.\n")
        else:
            for c in data["cookies"]:
                c_box.insert(tk.END, f"Cookie Name: {c['name']}\n")
                c_box.insert(tk.END, f"  - Secure:   {'✔ True' if c['secure'] else '✖ MISSING (High Risk over HTTPS)'}\n")
                c_box.insert(tk.END, f"  - HttpOnly: {'✔ True' if c['httponly'] else '✖ MISSING (Exposed to JavaScript XSS)'}\n")
                c_box.insert(tk.END, f"  - SameSite: {c['samesite']}\n\n")

        if data["cookie_risks"]:
            c_box.insert(tk.END, "[!] IDENTIFIED COOKIE RISKS:\n")
            for risk in data["cookie_risks"]:
                c_box.insert(tk.END, f"  • {risk}\n")

        c_box.config(state=tk.DISABLED)

        # 3. Remediation Tab
        r_box = tk.Text(self.tab_remediation, bg=THEME["bg_card_inner"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=10, pady=10)
        r_box.pack(fill=tk.BOTH, expand=True)

        r_box.insert(tk.END, f"=== REMEDIATION & HARDENING ROADMAP: {data['domain']} ===\n\n")
        if not data["remediations"]:
            r_box.insert(tk.END, "✔ No remediation required. The domain satisfies OWASP baseline security header directives.\n")
        else:
            for idx, r in enumerate(data["remediations"], 1):
                r_box.insert(tk.END, f"{idx}. [{r['priority']}] {r['title']}\n")
                r_box.insert(tk.END, f"   ACTION: {r['remediation']}\n\n")

        r_box.config(state=tk.DISABLED)

    # ==========================================================================
    #                          CSV REPORT EXPORT
    # ==========================================================================
    def export_csv(self):
        """Exports the audited dataset into an enterprise CSV format."""
        if not self.audit_results:
            messagebox.showinfo("Export Empty", "No audited data available to export.")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile=f"security_headers_audit_{now_str}.csv",
        )

        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Index", "Domain", "Status Code", "Score", "Grade",
                    "Present Headers Count", "Missing Headers", "Cookies Count",
                    "Cookie Risks Count", "HSTS Max-Age", "HSTS Preload",
                    "CSP Present", "Server Banner"
                ])

                for item in self.audit_results:
                    writer.writerow([
                        item.get("index"),
                        item.get("domain"),
                        item.get("status_code"),
                        item.get("score"),
                        item.get("grade"),
                        len(item.get("present_headers", {})),
                        "; ".join(item.get("missing_headers", [])),
                        len(item.get("cookies", [])),
                        len(item.get("cookie_risks", [])),
                        item.get("hsts_details", {}).get("max_age", 0),
                        item.get("hsts_details", {}).get("preload", False),
                        "Yes" if "Content-Security-Policy" in item.get("present_headers", {}) else "No",
                        item.get("info_leaks", {}).get("Server", "Hidden"),
                    ])

            messagebox.showinfo("Export Complete", f"Successfully exported audit report:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not write CSV file:\n{e}")


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

    app = HeaderAuditorApp()
    app.mainloop()
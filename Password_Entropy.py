import math
import string
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext


# ==============================================================================
# 1. MATHEMATICAL & THEORETICAL ANALYSIS ENGINE
# ==============================================================================

class ThreatModel:
    """Represents a specific offline or online cracking hardware configuration."""

    def __init__(self, name, rate_per_sec, description, category):
        self.name = name
        self.rate_per_sec = rate_per_sec  # Guesses per second
        self.description = description
        self.category = category


# Benchmark Threat Models based on modern offensive hardware standards
STANDARD_THREAT_MODELS = [
    ThreatModel(
        "Online Rate-Limited Web API",
        100 / 3600,  # ~100 attempts / hour
        "Throttled authentication portal with IP lockouts and captchas.",
        "Online"
    ),
    ThreatModel(
        "Online High-Throughput API",
        1_000,
        "Distributed botnet attacking unthrottled OAuth/LDAP endpoints.",
        "Online"
    ),
    ThreatModel(
        "Offline Slow KDF (Argon2id / bcrypt)",
        10_000,
        "Modern dedicated 8x RTX 4090 rig targeting hardened password hashes.",
        "Offline Slow"
    ),
    ThreatModel(
        "Offline PBKDF2-HMAC-SHA256",
        5_000_000,
        "Custom GPU rig targeting standard key derivation functions.",
        "Offline Medium"
    ),
    ThreatModel(
        "Offline Fast Hash (MD5 / NTLM / SHA1)",
        100_000_000_000,
        "Standard multi-GPU hashcat cluster (100 Giga-hashes/sec).",
        "Offline Fast"
    ),
    ThreatModel(
        "Nation-State Distributed Cluster",
        100_000_000_000_000,
        "Dedicated supercomputing ASIC array / botnet (100 Tera-hashes/sec).",
        "Supercomputing"
    ),
]


class EntropyEngine:
    """Core mathematical engine for search space, entropy, and crack time."""

    # Curated common patterns for heuristic penalty analysis
    COMMON_SEQUENCES = (
        "1234567890", "0987654321",
        "qwertyuiop", "asdfghjkl", "zxcvbnm",
        "abcdefghijklmnopqrstuvwxyz"
    )

    COMMON_DICTIONARY_ROOTS = (
        "password", "admin", "welcome", "login", "master", "monkey", "dragon",
        "letmein", "trustno1", "shadow", "sunshine", "football", "baseball",
        "superman", "freedom", "default", "charlie", "jordan", "access"
    )

    @classmethod
    def analyze_composition(cls, pwd: str) -> dict:
        """Inspects character set distribution and pool size."""
        has_lower = any(c in string.ascii_lowercase for c in pwd)
        has_upper = any(c in string.ascii_uppercase for c in pwd)
        has_digits = any(c in string.digits for c in pwd)
        has_symbols = any(c in string.punctuation for c in pwd)
        has_space = any(c == ' ' for c in pwd)
        has_extended = any(ord(c) > 127 for c in pwd)

        pool_size = 0
        pool_desc = []
        if has_lower:
            pool_size += 26
            pool_desc.append("Lowercase [a-z] (26)")
        if has_upper:
            pool_size += 26
            pool_desc.append("Uppercase [A-Z] (26)")
        if has_digits:
            pool_size += 10
            pool_desc.append("Digits [0-9] (10)")
        if has_symbols:
            pool_size += len(string.punctuation)
            pool_desc.append(f"Symbols [{len(string.punctuation)}]")
        if has_space:
            pool_size += 1
            pool_desc.append("Space (1)")
        if has_extended:
            pool_size += 128
            pool_desc.append("Extended ASCII/Unicode (128)")

        return {
            "length": len(pwd),
            "pool_size": pool_size,
            "pool_desc": ", ".join(pool_desc) if pool_desc else "None",
            "has_lower": has_lower,
            "has_upper": has_upper,
            "has_digits": has_digits,
            "has_symbols": has_symbols,
            "has_space": has_space,
            "has_extended": has_extended
        }

    @classmethod
    def calculate_hartley_entropy(cls, length: int, pool_size: int) -> float:
        """Standard Hartley / Combinatorial Entropy: H = L * log2(R)."""
        if length <= 0 or pool_size <= 0:
            return 0.0
        return float(length * math.log2(pool_size))

    @classmethod
    def calculate_shannon_entropy(cls, pwd: str) -> float:
        """Information-theoretic Shannon entropy based on symbol frequency."""
        if not pwd:
            return 0.0
        length = len(pwd)
        freq = {}
        for char in pwd:
            freq[char] = freq.get(char, 0) + 1

        entropy = 0.0
        for count in freq.values():
            p_x = count / length
            entropy -= p_x * math.log2(p_x)

        # Total Shannon Entropy over the sequence
        return float(entropy * length)

    @classmethod
    def calculate_heuristic_entropy(cls, pwd: str) -> tuple[float, list[str]]:
        """
        NIST-inspired heuristic entropy model accounting for pattern penalties,
        repetitions, casing stereotypes, and common dictionary roots.
        """
        comp = cls.analyze_composition(pwd)
        raw_entropy = cls.calculate_hartley_entropy(comp["length"], comp["pool_size"])
        penalties = []
        effective_entropy = raw_entropy

        if not pwd:
            return 0.0, ["Empty password"]

        lower_pwd = pwd.lower()

        # 1. Dictionary root match penalty
        for root in cls.COMMON_DICTIONARY_ROOTS:
            if root in lower_pwd:
                deduction = len(root) * 3.5
                effective_entropy -= deduction
                penalties.append(f"Contains dictionary root '{root}' (-{deduction:.1f} bits)")
                break

        # 2. Sequential keyboard/alphabet penalty
        for seq in cls.COMMON_SEQUENCES:
            for i in range(len(seq) - 2):
                triplet = seq[i:i + 3]
                if triplet in lower_pwd:
                    effective_entropy -= 5.0
                    penalties.append(f"Sequential run detected '{triplet}' (-5.0 bits)")
                    break

        # 3. Predictable casing stereotype (First char uppercase, last char digit/symbol)
        if len(pwd) > 2:
            if pwd[0].isupper() and pwd[1:].islower():
                effective_entropy -= 4.0
                penalties.append("Predictable single-leading capital (-4.0 bits)")
            if pwd[-1].isdigit():
                effective_entropy -= 3.0
                penalties.append("Predictable trailing digit (-3.0 bits)")
            elif pwd[-1] in string.punctuation:
                effective_entropy -= 3.0
                penalties.append("Predictable trailing symbol (-3.0 bits)")

        # 4. Repeated character clusters
        repeats = 0
        for i in range(len(pwd) - 1):
            if pwd[i] == pwd[i + 1]:
                repeats += 1
        if repeats > 0:
            deduction = repeats * 3.0
            effective_entropy -= deduction
            penalties.append(f"Repeated adjacent characters x{repeats} (-{deduction:.1f} bits)")

        effective_entropy = max(0.0, effective_entropy)
        return effective_entropy, penalties

    @classmethod
    def get_search_space_digits(cls, length: int, pool_size: int) -> tuple[int, float]:
        """
        Calculates search space S = R^L without overflow.
        Returns: (exact_int or -1 if too large, log10_value)
        """
        if length <= 0 or pool_size <= 0:
            return 0, 0.0

        log10_s = length * math.log10(pool_size)
        if log10_s < 300:  # Within safe Python integer conversion limit
            exact_s = pool_size ** length
        else:
            exact_s = -1  # Indicates too massive for practical base-10 string
        return exact_s, log10_s

    @classmethod
    def compute_crack_time(cls, log10_search_space: float, rate_per_sec: float) -> dict:
        """
        Computes the time to crack using log-scale arithmetic to prevent overflow.
        Average attempts to break = S / 2.
        log10(T_sec) = log10(S) - log10(2) - log10(rate).
        """
        if log10_search_space <= 0 or rate_per_sec <= 0:
            return {"seconds": 0.0, "formatted": "Instantaneous", "is_astronomical": False}

        log10_rate = math.log10(rate_per_sec)
        log10_time_sec = log10_search_space - math.log10(2.0) - log10_rate

        # Conversion constants in log10
        LOG10_MINUTE = math.log10(60.0)
        LOG10_HOUR = math.log10(3600.0)
        LOG10_DAY = math.log10(86400.0)
        LOG10_YEAR = math.log10(31_557_600.0)  # Julian year (365.25 days)
        LOG10_UNIVERSE = LOG10_YEAR + math.log10(13.8e9)  # 13.8 billion years

        if log10_time_sec < -3:
            return {"seconds": 10 ** log10_time_sec, "formatted": "< 1 Millisecond", "is_astronomical": False}
        elif log10_time_sec < 0:
            val = 10 ** log10_time_sec * 1000.0
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.1f} Milliseconds", "is_astronomical": False}
        elif log10_time_sec < LOG10_MINUTE:
            val = 10 ** log10_time_sec
            return {"seconds": val, "formatted": f"{val:.2f} Seconds", "is_astronomical": False}
        elif log10_time_sec < LOG10_HOUR:
            val = 10 ** (log10_time_sec - LOG10_MINUTE)
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Minutes", "is_astronomical": False}
        elif log10_time_sec < LOG10_DAY:
            val = 10 ** (log10_time_sec - LOG10_HOUR)
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Hours", "is_astronomical": False}
        elif log10_time_sec < LOG10_YEAR:
            val = 10 ** (log10_time_sec - LOG10_DAY)
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Days", "is_astronomical": False}
        elif log10_time_sec < LOG10_YEAR + 3:
            val = 10 ** (log10_time_sec - LOG10_YEAR)
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Years", "is_astronomical": False}
        elif log10_time_sec < LOG10_YEAR + 6:
            val = 10 ** (log10_time_sec - (LOG10_YEAR + 3))
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Thousand Years", "is_astronomical": False}
        elif log10_time_sec < LOG10_YEAR + 9:
            val = 10 ** (log10_time_sec - (LOG10_YEAR + 6))
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Million Years", "is_astronomical": False}
        elif log10_time_sec < LOG10_UNIVERSE:
            val = 10 ** (log10_time_sec - (LOG10_YEAR + 9))
            return {"seconds": 10 ** log10_time_sec, "formatted": f"{val:.2f} Billion Years", "is_astronomical": False}
        else:
            universes = 10 ** (log10_time_sec - LOG10_UNIVERSE)
            if universes < 1e6:
                return {
                    "seconds": float('inf'),
                    "formatted": f"{universes:.2f} × Age of Universe",
                    "is_astronomical": True
                }
            else:
                exponent = log10_time_sec - LOG10_YEAR
                return {
                    "seconds": float('inf'),
                    "formatted": f"10^{exponent:.1f} Years (Infeasible)",
                    "is_astronomical": True
                }


# ==============================================================================
# 2. CUSTOM TKINTER VECTOR GAUGES & CHARTS
# ==============================================================================

class CircularEntropyGauge(tk.Canvas):
    """A vector-drawn radial gauge displaying entropy bits (0 to 128+)."""

    def __init__(self, master, width=220, height=180, bg="#1e1e2f", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.bg_color = bg
        self.current_entropy = 0.0
        self.draw_gauge(0.0, "Empty")

    def draw_gauge(self, entropy: float, classification: str):
        self.delete("all")
        self.current_entropy = entropy

        cx = self.width / 2
        cy = self.height * 0.72
        radius = self.width * 0.38
        stroke = 14

        # Background track arc (180 degrees: from 180 to 0)
        self.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=0, extent=180, style=tk.ARC, outline="#2c2c44", width=stroke
        )

        # Fraction of max gauge scale (Max scale = 128 bits)
        fraction = min(max(entropy / 128.0, 0.0), 1.0)
        extent = -180.0 * fraction

        # Determine color grade
        if entropy < 30:
            gauge_color = "#e74c3c"  # Red
        elif entropy < 55:
            gauge_color = "#e67e22"  # Orange
        elif entropy < 80:
            gauge_color = "#f1c40f"  # Yellow
        elif entropy < 110:
            gauge_color = "#2ecc71"  # Emerald
        else:
            gauge_color = "#00d2d3"  # Cyan / Impenetrable

        if fraction > 0.005:
            self.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=180, extent=extent, style=tk.ARC, outline=gauge_color, width=stroke
            )

        # Center numerical readout
        self.create_text(
            cx, cy - 25,
            text=f"{entropy:.1f}",
            font=("Segoe UI", 24, "bold"),
            fill="#ffffff"
        )
        self.create_text(
            cx, cy - 2,
            text="BITS OF ENTROPY",
            font=("Segoe UI", 8, "bold"),
            fill="#8e8ea8"
        )
        self.create_text(
            cx, cy + 22,
            text=classification.upper(),
            font=("Segoe UI", 11, "bold"),
            fill=gauge_color
        )

        # Threshold tick labels
        self.create_text(cx - radius - 5, cy + 12, text="0", font=("Segoe UI", 8), fill="#8e8ea8")
        self.create_text(cx, cy - radius - 10, text="64", font=("Segoe UI", 8), fill="#8e8ea8")
        self.create_text(cx + radius + 10, cy + 12, text="128+", font=("Segoe UI", 8), fill="#8e8ea8")


class SegmentedStrengthBar(tk.Canvas):
    """Multi-segment visual pill meter."""

    def __init__(self, master, width=320, height=22, bg="#1e1e2f", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.render(0.0)

    def render(self, entropy: float):
        self.delete("all")
        segments = 5
        gap = 4
        total_gaps = gap * (segments - 1)
        seg_w = (self.width - total_gaps) / segments
        seg_h = self.height

        # Thresholds: 25, 45, 65, 85, 105+
        thresholds = [25, 45, 65, 85, 105]
        active_color = "#e74c3c"
        if entropy >= 105:
            active_color = "#00d2d3"
        elif entropy >= 85:
            active_color = "#2ecc71"
        elif entropy >= 65:
            active_color = "#f1c40f"
        elif entropy >= 45:
            active_color = "#e67e22"

        for i in range(segments):
            x1 = i * (seg_w + gap)
            x2 = x1 + seg_w
            fill_col = active_color if entropy >= thresholds[i] else "#2c2c44"
            self.create_rectangle(x1, 2, x2, seg_h - 2, fill=fill_col, outline="", width=0)


# ==============================================================================
# 3. MAIN GUI APPLICATION WINDOW & NOTEBOOK TABS
# ==============================================================================

class PasswordEntropyApp(tk.Tk):
    """Master Application Window containing all analyzer views."""

    def __init__(self):
        super().__init__()
        self.title("Password Entropy & Guessability Analyzer — Theoretical Security Suite")
        self.geometry("1120x820")
        self.minsize(980, 720)
        self.configure(bg="#141420")

        self._setup_styles()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Initial calculation trigger
        self.after(100, self._on_password_input_change)

    def _setup_styles(self):
        """Configures modern slate / cyber aesthetic styles for standard TTK widgets."""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Global base styling
        self.style.configure(".", background="#141420", foreground="#f5f6fa", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#141420")
        self.style.configure("Card.TFrame", background="#1e1e2f", relief="flat")

        # Notebook Tabs Styling
        self.style.configure("TNotebook", background="#141420", tabmargins=[10, 10, 2, 0], borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#1e1e2f", foreground="#a4a4c1", padding=[18, 9],
                             font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#00d2d3"), ("active", "#282842")],
                       foreground=[("selected", "#0f172a"), ("active", "#ffffff")]
                       )

        # LabelFrame Styling
        self.style.configure("TLabelframe", background="#1e1e2f", borderwidth=1, relief="solid")
        self.style.configure("TLabelframe.Label", background="#1e1e2f", foreground="#00d2d3",
                             font=("Segoe UI", 10, "bold"))

        # Treeview Styling
        self.style.configure("Treeview",
                             background="#1a1a2b",
                             foreground="#f5f6fa",
                             fieldbackground="#1a1a2b",
                             rowheight=28,
                             font=("Consolas", 9)
                             )
        self.style.configure("Treeview.Heading",
                             background="#27273f",
                             foreground="#00d2d3",
                             relief="flat",
                             font=("Segoe UI", 9, "bold")
                             )
        self.style.map("Treeview", background=[("selected", "#34495e")])

        # Buttons
        self.style.configure("Primary.TButton", background="#00d2d3", foreground="#0f172a",
                             font=("Segoe UI", 10, "bold"), padding=6)
        self.style.map("Primary.TButton", background=[("active", "#01a3a4")])
        self.style.configure("Secondary.TButton", background="#2c2c44", foreground="#ffffff", font=("Segoe UI", 9),
                             padding=6)
        self.style.map("Secondary.TButton", background=[("active", "#3d3d5c")])

    def _build_header(self):
        """Top banner brand display."""
        header_frame = tk.Frame(self, bg="#1e1e2f", height=65)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="ENTROPY & THEORETICAL KEY-SPACE ANALYZER",
            font=("Segoe UI", 14, "bold"),
            bg="#1e1e2f",
            fg="#ffffff"
        )
        title_lbl.pack(side=tk.LEFT, padx=20, pady=8)

        sub_lbl = tk.Label(
            header_frame,
            text="OFFLINE BRUTE-FORCE COMPLEXITY MODELING",
            font=("Consolas", 9, "bold"),
            bg="#1e1e2f",
            fg="#00d2d3"
        )
        sub_lbl.pack(side=tk.RIGHT, padx=20, pady=12)

    def _build_notebook(self):
        """Constructs tabs for modular exploration."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

        # Tab 1: Live Interactive Analyzer
        self.tab_analyzer = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_analyzer, text=" Live Interactive Analyzer ")

        # Tab 2: Search-Space Matrix & Comparison
        self.tab_matrix = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_matrix, text=" Search-Space Matrix ")

        # Tab 3: Short vs. Long Password Deep Dive
        self.tab_comparison = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_comparison, text=" Short vs Long Comparison ")

        # Tab 4: Custom Threat & Cost Simulator
        self.tab_simulator = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_simulator, text=" Threat & Financial Cost Simulator ")

        # Tab 5: Security Report Exporter
        self.tab_report = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_report, text=" Audit Report Exporter ")

        # Build individual tabs
        self._build_tab_analyzer_view()
        self._build_tab_matrix_view()
        self._build_tab_comparison_view()
        self._build_tab_simulator_view()
        self._build_tab_report_view()

    def _build_statusbar(self):
        """Bottom operational state bar."""
        self.statusbar = tk.Frame(self, bg="#1a1a2b", height=26)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.statusbar.pack_propagate(False)

        self.status_lbl = tk.Label(
            self.statusbar,
            text="Theoretical engine operational. Calculations run in logarithmic space.",
            font=("Segoe UI", 8),
            bg="#1a1a2b",
            fg="#8e8ea8"
        )
        self.status_lbl.pack(side=tk.LEFT, padx=15)

    # --------------------------------------------------------------------------
    # TAB 1: LIVE INTERACTIVE ANALYZER VIEW
    # --------------------------------------------------------------------------
    def _build_tab_analyzer_view(self):
        root = self.tab_analyzer

        # Top interactive input bar
        input_card = ttk.LabelFrame(root, text=" Target Password String ", padding=14)
        input_card.pack(fill=tk.X, pady=(0, 10))

        input_row = tk.Frame(input_card, bg="#1e1e2f")
        input_row.pack(fill=tk.X)

        tk.Label(input_row, text="Target Input:", font=("Segoe UI", 10, "bold"), bg="#1e1e2f", fg="#f5f6fa").pack(
            side=tk.LEFT, padx=(0, 10))

        self.pwd_var = tk.StringVar(value="Correct-Horse-99#")
        self.pwd_entry = tk.Entry(
            input_row,
            textvariable=self.pwd_var,
            font=("Consolas", 12),
            bg="#2c2c44",
            fg="#ffffff",
            insertbackground="#00d2d3",
            relief="flat",
            bd=5
        )
        self.pwd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.pwd_var.trace_add("write", lambda *args: self._on_password_input_change())

        self.show_mask_var = tk.BooleanVar(value=True)
        self.chk_mask = tk.Checkbutton(
            input_row,
            text="Show Plaintext",
            variable=self.show_mask_var,
            command=self._toggle_pwd_visibility,
            bg="#1e1e2f",
            fg="#f5f6fa",
            selectcolor="#2c2c44",
            activebackground="#1e1e2f",
            activeforeground="#00d2d3"
        )
        self.chk_mask.pack(side=tk.LEFT, padx=10)

        # Middle Splitted Area: Left Metrics & Gauge | Right Threat Table
        mid_pane = tk.Frame(root, bg="#141420")
        mid_pane.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(mid_pane, bg="#141420", width=360)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        # Vector Radial Gauge Frame
        gauge_card = ttk.LabelFrame(left_col, text=" Information Theory Entropy ", padding=10)
        gauge_card.pack(fill=tk.X, pady=(0, 10))

        self.gauge = CircularEntropyGauge(gauge_card, width=280, height=160, bg="#1e1e2f")
        self.gauge.pack(anchor=tk.CENTER)

        self.strength_bar = SegmentedStrengthBar(gauge_card, width=280, height=14, bg="#1e1e2f")
        self.strength_bar.pack(anchor=tk.CENTER, pady=(5, 5))

        # Compositional Diagnostics Card
        comp_card = ttk.LabelFrame(left_col, text=" Key Space Composition ", padding=10)
        comp_card.pack(fill=tk.BOTH, expand=True)

        self.lbl_comp_len = tk.Label(comp_card, text="Length (L): 0", bg="#1e1e2f", fg="#f5f6fa", anchor=tk.W)
        self.lbl_comp_len.pack(fill=tk.X, pady=2)

        self.lbl_comp_pool = tk.Label(comp_card, text="Character Pool (R): 0", bg="#1e1e2f", fg="#f5f6fa", anchor=tk.W)
        self.lbl_comp_pool.pack(fill=tk.X, pady=2)

        self.lbl_comp_shannon = tk.Label(comp_card, text="Shannon Entropy: 0.00 bits", bg="#1e1e2f", fg="#f5f6fa",
                                         anchor=tk.W)
        self.lbl_comp_shannon.pack(fill=tk.X, pady=2)

        self.lbl_comp_heuristic = tk.Label(comp_card, text="Heuristic Score: 0.00 bits", bg="#1e1e2f", fg="#f5f6fa",
                                           anchor=tk.W)
        self.lbl_comp_heuristic.pack(fill=tk.X, pady=2)

        self.lbl_comp_space = tk.Label(comp_card, text="Search Space: 10^0", bg="#1e1e2f", fg="#00d2d3",
                                       font=("Consolas", 10, "bold"), anchor=tk.W)
        self.lbl_comp_space.pack(fill=tk.X, pady=(6, 2))

        # Right Column: Attack Scenarios Table & Penalties
        right_col = tk.Frame(mid_pane, bg="#141420")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        threat_card = ttk.LabelFrame(right_col, text=" Threat-Model Crack Time Matrix (Average 50% Key-Space Search) ",
                                     padding=8)
        threat_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("model", "rate", "time", "category")
        self.tree_threats = ttk.Treeview(threat_card, columns=columns, show="headings", height=6)
        self.tree_threats.heading("model", text="Attack Threat Profile")
        self.tree_threats.heading("rate", text="Guess Rate")
        self.tree_threats.heading("time", text="Estimated Time to Crack")
        self.tree_threats.heading("category", text="Environment")

        self.tree_threats.column("model", width=220)
        self.tree_threats.column("rate", width=120, anchor=tk.E)
        self.tree_threats.column("time", width=190, anchor=tk.W)
        self.tree_threats.column("category", width=100, anchor=tk.CENTER)

        self.tree_threats.pack(fill=tk.BOTH, expand=True)

        # Pattern Deductions Panel
        penalty_card = ttk.LabelFrame(right_col, text=" Heuristic Vulnerability & Pattern Audit ", padding=8)
        penalty_card.pack(fill=tk.X)

        self.txt_penalties = tk.Text(penalty_card, height=4, bg="#1a1a2b", fg="#f5f6fa", font=("Segoe UI", 9),
                                     relief="flat")
        self.txt_penalties.pack(fill=tk.X)

    def _toggle_pwd_visibility(self):
        if self.show_mask_var.get():
            self.pwd_entry.config(show="")
        else:
            self.pwd_entry.config(show="●")

    def _on_password_input_change(self):
        pwd = self.pwd_var.get()
        comp = EntropyEngine.analyze_composition(pwd)
        hartley = EntropyEngine.calculate_hartley_entropy(comp["length"], comp["pool_size"])
        shannon = EntropyEngine.calculate_shannon_entropy(pwd)
        heuristic, penalties = EntropyEngine.calculate_heuristic_entropy(pwd)

        # Classification
        if comp["length"] == 0:
            classification = "Empty"
        elif heuristic < 28:
            classification = "Very Weak"
        elif heuristic < 48:
            classification = "Weak"
        elif heuristic < 68:
            classification = "Moderate"
        elif heuristic < 88:
            classification = "Strong"
        elif heuristic < 128:
            classification = "Very Strong"
        else:
            classification = "Quantum-Safe"

        # Update Gauges
        self.gauge.draw_gauge(heuristic, classification)
        self.strength_bar.render(heuristic)

        # Update text diagnostics
        self.lbl_comp_len.config(text=f"Length (L): {comp['length']} characters")
        self.lbl_comp_pool.config(text=f"Character Pool (R): {comp['pool_size']} ({comp['pool_desc']})")
        self.lbl_comp_shannon.config(text=f"Shannon Entropy: {shannon:.2f} bits (Uniform Max: {hartley:.2f})")
        self.lbl_comp_heuristic.config(text=f"NIST Heuristic Score: {heuristic:.2f} effective bits")

        exact_s, log10_s = EntropyEngine.get_search_space_digits(comp["length"], comp["pool_size"])
        if exact_s != -1 and exact_s < 1_000_000_000_000:
            self.lbl_comp_space.config(text=f"Search Space: {exact_s:,} (10^{log10_s:.2f})")
        else:
            self.lbl_comp_space.config(text=f"Search Space: 10^{log10_s:.2f} combinations")

        # Update Threat Model Table
        self.tree_threats.delete(*self.tree_threats.get_children())
        for model in STANDARD_THREAT_MODELS:
            res = EntropyEngine.compute_crack_time(log10_s, model.rate_per_sec)
            rate_fmt = f"{model.rate_per_sec:,.0f} /s" if model.rate_per_sec >= 1 else f"{model.rate_per_sec * 3600:.0f} /hr"
            self.tree_threats.insert("", tk.END, values=(
                model.name,
                rate_fmt,
                res["formatted"],
                model.category
            ))

        # Update Penalties Audit
        self.txt_penalties.delete("1.0", tk.END)
        if not penalties:
            self.txt_penalties.insert(tk.END,
                                      "✓ No obvious dictionary roots, sequences, or casing penalties detected.\nHigh resilience against heuristic rule-based mutation dictionaries.")
        else:
            for p in penalties:
                self.txt_penalties.insert(tk.END, f"⚠ {p}\n")

    # --------------------------------------------------------------------------
    # TAB 2: SEARCH-SPACE MATRIX & COMPARATIVE CALCULATOR
    # --------------------------------------------------------------------------
    def _build_tab_matrix_view(self):
        root = self.tab_matrix

        ctrl_frame = ttk.LabelFrame(root, text=" Matrix Generation Parameters ", padding=10)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        row = tk.Frame(ctrl_frame, bg="#1e1e2f")
        row.pack(fill=tk.X)

        tk.Label(row, text="Select Target Hardware Threat:", bg="#1e1e2f", fg="#f5f6fa").pack(side=tk.LEFT,
                                                                                              padx=(0, 10))
        self.matrix_threat_var = tk.StringVar(value="Offline Fast Hash (MD5 / NTLM / SHA1)")
        threat_names = [m.name for m in STANDARD_THREAT_MODELS]
        self.combo_matrix_threat = ttk.Combobox(row, textvariable=self.matrix_threat_var, values=threat_names,
                                                state="readonly", width=40)
        self.combo_matrix_threat.pack(side=tk.LEFT, padx=5)
        self.combo_matrix_threat.bind("<<ComboboxSelected>>", lambda e: self._generate_search_space_matrix())

        btn_refresh = ttk.Button(row, text="Regenerate Matrix", style="Primary.TButton",
                                 command=self._generate_search_space_matrix)
        btn_refresh.pack(side=tk.LEFT, padx=15)

        # Matrix Treeview Table
        table_card = ttk.LabelFrame(root,
                                    text=" Exhaustive Key-Space Search Grid (Lengths 6 to 20 vs. Common Character Sets) ",
                                    padding=8)
        table_card.pack(fill=tk.BOTH, expand=True)

        cols = ("length", "numeric", "lower", "alphanumeric", "all_ascii")
        self.tree_matrix = ttk.Treeview(table_card, columns=cols, show="headings")
        self.tree_matrix.heading("length", text="Length (L)")
        self.tree_matrix.heading("numeric", text="Digits Only (R=10)")
        self.tree_matrix.heading("lower", text="Lowercase (R=26)")
        self.tree_matrix.heading("alphanumeric", text="Alphanumeric (R=62)")
        self.tree_matrix.heading("all_ascii", text="Full ASCII (R=94)")

        self.tree_matrix.column("length", width=80, anchor=tk.CENTER)
        self.tree_matrix.column("numeric", width=200, anchor=tk.W)
        self.tree_matrix.column("lower", width=200, anchor=tk.W)
        self.tree_matrix.column("alphanumeric", width=220, anchor=tk.W)
        self.tree_matrix.column("all_ascii", width=220, anchor=tk.W)

        self.tree_matrix.pack(fill=tk.BOTH, expand=True)
        self._generate_search_space_matrix()

    def _generate_search_space_matrix(self):
        selected_threat_name = self.matrix_threat_var.get()
        threat = next((m for m in STANDARD_THREAT_MODELS if m.name == selected_threat_name), STANDARD_THREAT_MODELS[4])

        self.tree_matrix.delete(*self.tree_matrix.get_children())

        # Lengths from 6 up to 20
        for l in range(6, 21):
            _, log10_10 = EntropyEngine.get_search_space_digits(l, 10)
            _, log10_26 = EntropyEngine.get_search_space_digits(l, 26)
            _, log10_62 = EntropyEngine.get_search_space_digits(l, 62)
            _, log10_94 = EntropyEngine.get_search_space_digits(l, 94)

            t_10 = EntropyEngine.compute_crack_time(log10_10, threat.rate_per_sec)["formatted"]
            t_26 = EntropyEngine.compute_crack_time(log10_26, threat.rate_per_sec)["formatted"]
            t_62 = EntropyEngine.compute_crack_time(log10_62, threat.rate_per_sec)["formatted"]
            t_94 = EntropyEngine.compute_crack_time(log10_94, threat.rate_per_sec)["formatted"]

            self.tree_matrix.insert("", tk.END, values=(
                f"{l} chars",
                t_10,
                t_26,
                t_62,
                t_94
            ))

    # --------------------------------------------------------------------------
    # TAB 3: SHORT VS. LONG PASSWORD DEEP DIVE COMPARISON
    # --------------------------------------------------------------------------
    def _build_tab_comparison_view(self):
        root = self.tab_comparison

        banner = ttk.LabelFrame(root, text=" The Exponential Law of Length vs. Character Complexity ", padding=10)
        banner.pack(fill=tk.X, pady=(0, 10))

        expl = (
            "MATHEMATICAL PRINCIPLE: Search space scales exponentially with length (R^L), but only polynomially with character set size R.\n"
            "A long, simple passphrase (e.g., 18 lowercase letters) vastly outperforms a short, high-complexity password (e.g., 8 mixed characters)."
        )
        tk.Label(banner, text=expl, bg="#1e1e2f", fg="#00d2d3", justify=tk.LEFT, font=("Consolas", 9)).pack(anchor=tk.W)

        # Comparison Arena Form
        arena = tk.Frame(root, bg="#141420")
        arena.pack(fill=tk.BOTH, expand=True)

        # Card A: Complex Short Password
        card_a = ttk.LabelFrame(arena, text=" Profile A: Short & Complex (e.g., 8-Char Max Complexity) ", padding=10)
        card_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(card_a, text="Password Example:", bg="#1e1e2f", fg="#8e8ea8").pack(anchor=tk.W)
        self.prof_a_input = tk.Entry(card_a, font=("Consolas", 11), bg="#2c2c44", fg="#ffffff",
                                     insertbackground="#00d2d3")
        self.prof_a_input.insert(0, "P@$$w0rd")
        self.prof_a_input.pack(fill=tk.X, pady=(2, 10))
        self.prof_a_input.bind("<KeyRelease>", lambda e: self._update_comparison_cards())

        self.lbl_a_res = tk.Label(card_a, text="", bg="#1e1e2f", fg="#f5f6fa", justify=tk.LEFT, font=("Segoe UI", 9))
        self.lbl_a_res.pack(fill=tk.BOTH, expand=True)

        # Card B: Long Passphrase
        card_b = ttk.LabelFrame(arena, text=" Profile B: Long & Simple (e.g., 16-Char Lowercase Passphrase) ",
                                padding=10)
        card_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(card_b, text="Password Example:", bg="#1e1e2f", fg="#8e8ea8").pack(anchor=tk.W)
        self.prof_b_input = tk.Entry(card_b, font=("Consolas", 11), bg="#2c2c44", fg="#ffffff",
                                     insertbackground="#00d2d3")
        self.prof_b_input.insert(0, "correcthorsebatterystaple")
        self.prof_b_input.pack(fill=tk.X, pady=(2, 10))
        self.prof_b_input.bind("<KeyRelease>", lambda e: self._update_comparison_cards())

        self.lbl_b_res = tk.Label(card_b, text="", bg="#1e1e2f", fg="#f5f6fa", justify=tk.LEFT, font=("Segoe UI", 9))
        self.lbl_b_res.pack(fill=tk.BOTH, expand=True)

        self._update_comparison_cards()

    def _update_comparison_cards(self):
        p_a = self.prof_a_input.get()
        p_b = self.prof_b_input.get()

        comp_a = EntropyEngine.analyze_composition(p_a)
        comp_b = EntropyEngine.analyze_composition(p_b)

        ent_a = EntropyEngine.calculate_hartley_entropy(comp_a["length"], comp_a["pool_size"])
        ent_b = EntropyEngine.calculate_hartley_entropy(comp_b["length"], comp_b["pool_size"])

        _, log_a = EntropyEngine.get_search_space_digits(comp_a["length"], comp_a["pool_size"])
        _, log_b = EntropyEngine.get_search_space_digits(comp_b["length"], comp_b["pool_size"])

        fast_gpu_rate = 100_000_000_000  # 100 GH/s
        time_a = EntropyEngine.compute_crack_time(log_a, fast_gpu_rate)["formatted"]
        time_b = EntropyEngine.compute_crack_time(log_b, fast_gpu_rate)["formatted"]

        txt_a = (
            f"Length (L): {comp_a['length']} characters\n"
            f"Pool Size (R): {comp_a['pool_size']} symbols\n"
            f"Combinatorial Entropy: {ent_a:.2f} bits\n"
            f"Search Space: 10^{log_a:.2f}\n"
            f"--------------------------------------------------\n"
            f"Crack Time @ 100 GH/s GPU Rig:\n"
            f"➤ {time_a}\n"
        )
        self.lbl_a_res.config(text=txt_a)

        txt_b = (
            f"Length (L): {comp_b['length']} characters\n"
            f"Pool Size (R): {comp_b['pool_size']} symbols\n"
            f"Combinatorial Entropy: {ent_b:.2f} bits\n"
            f"Search Space: 10^{log_b:.2f}\n"
            f"--------------------------------------------------\n"
            f"Crack Time @ 100 GH/s GPU Rig:\n"
            f"➤ {time_b}\n"
        )
        self.lbl_b_res.config(text=txt_b)

    # --------------------------------------------------------------------------
    # TAB 4: CUSTOM HARDWARE THREAT & FINANCIAL COST SIMULATOR
    # --------------------------------------------------------------------------
    def _build_tab_simulator_view(self):
        root = self.tab_simulator

        form_frame = ttk.LabelFrame(root, text=" Hardware Rig & Energy Cost Economics ", padding=12)
        form_frame.pack(fill=tk.X, pady=(0, 10))

        grid = tk.Frame(form_frame, bg="#1e1e2f")
        grid.pack(fill=tk.X)

        # Input 1: Custom Guesses/sec
        tk.Label(grid, text="Custom Hash Rate (Guesses/sec):", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0,
                                                                                                sticky=tk.W, pady=4)
        self.custom_rate_var = tk.StringVar(value="50000000000")  # 50 GH/s
        tk.Entry(grid, textvariable=self.custom_rate_var, font=("Consolas", 10), bg="#2c2c44", fg="#ffffff",
                 width=22).grid(row=0, column=1, sticky=tk.W, padx=10)

        # Input 2: Power Consumption (Watts)
        tk.Label(grid, text="Rig Electrical Draw (Watts):", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0,
                                                                                             sticky=tk.W, pady=4)
        self.custom_power_var = tk.StringVar(value="2400")  # 2.4 kW rig
        tk.Entry(grid, textvariable=self.custom_power_var, font=("Consolas", 10), bg="#2c2c44", fg="#ffffff",
                 width=22).grid(row=1, column=1, sticky=tk.W, padx=10)

        # Input 3: Energy Cost per kWh
        tk.Label(grid, text="Electricity Rate ($ per kWh):", bg="#1e1e2f", fg="#f5f6fa").grid(row=2, column=0,
                                                                                              sticky=tk.W, pady=4)
        self.custom_kwh_var = tk.StringVar(value="0.15")  # $0.15 / kWh
        tk.Entry(grid, textvariable=self.custom_kwh_var, font=("Consolas", 10), bg="#2c2c44", fg="#ffffff",
                 width=22).grid(row=2, column=1, sticky=tk.W, padx=10)

        btn_calc_sim = ttk.Button(grid, text="Compute Economic Attack Burden", style="Primary.TButton",
                                  command=self._calculate_financial_cost)
        btn_calc_sim.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.W)

        # Output Card
        self.card_econ = ttk.LabelFrame(root, text=" Adversary Economic & Resource Requirements ", padding=12)
        self.card_econ.pack(fill=tk.BOTH, expand=True)

        self.txt_econ = tk.Text(self.card_econ, bg="#1a1a2b", fg="#00d2d3", font=("Consolas", 10), relief="flat")
        self.txt_econ.pack(fill=tk.BOTH, expand=True)

    def _calculate_financial_cost(self):
        pwd = self.pwd_var.get()
        comp = EntropyEngine.analyze_composition(pwd)
        _, log10_s = EntropyEngine.get_search_space_digits(comp["length"], comp["pool_size"])

        try:
            rate = float(self.custom_rate_var.get().replace(",", "").strip())
            watts = float(self.custom_power_var.get().replace(",", "").strip())
            kwh_price = float(self.custom_kwh_var.get().replace(",", "").strip())
        except ValueError:
            messagebox.showerror("Invalid Input",
                                 "Please ensure rate, watts, and kWh prices are valid positive numbers.")
            return

        time_res = EntropyEngine.compute_crack_time(log10_s, rate)
        seconds = time_res["seconds"]

        self.txt_econ.delete("1.0", tk.END)
        out = []
        out.append("================================================================================")
        out.append(f"ADVERSARY ATTACK RESOURCE ESTIMATION FOR: '{pwd}'")
        out.append("================================================================================")
        out.append(f"• Target Search Space : 10^{log10_s:.2f} permutations")
        out.append(f"• Attack Throughput   : {rate:,.0f} guesses/sec")
        out.append(f"• Expected Crack Time : {time_res['formatted']}")

        if math.isinf(seconds) or seconds > 3.15e12:  # > 100,000 years
            out.append("• Total Energy Needed : Economically and physically impossible for civilization.")
            out.append("• Total Financial Cost: > Thousands of Trillions of USD (Exceeds Global GDP).")
        else:
            hours = seconds / 3600.0
            kwh_used = (watts / 1000.0) * hours
            cost_usd = kwh_used * kwh_price
            out.append(f"• Energy Consumed     : {kwh_used:,.2f} kWh")
            out.append(f"• Electric Utility Bill: ${cost_usd:,.2f} USD")

            # Carbon emission equivalence (approx 0.85 lbs CO2 / kWh)
            co2_lbs = kwh_used * 0.85
            out.append(f"• Carbon Footprint    : {co2_lbs:,.1f} lbs of CO2 emissions")

        self.txt_econ.insert(tk.END, "\n".join(out))

    # --------------------------------------------------------------------------
    # TAB 5: COMPREHENSIVE AUDIT REPORT EXPORTER
    # --------------------------------------------------------------------------
    def _build_tab_report_view(self):
        root = self.tab_report

        ctrl = tk.Frame(root, bg="#141420")
        ctrl.pack(fill=tk.X, pady=(0, 10))

        btn_gen = ttk.Button(ctrl, text="Compile Full Security Report", style="Primary.TButton",
                             command=self._generate_report_text)
        btn_gen.pack(side=tk.LEFT, padx=(0, 10))

        btn_save = ttk.Button(ctrl, text="Save to File (.txt)...", style="Secondary.TButton",
                              command=self._save_report_to_disk)
        btn_save.pack(side=tk.LEFT)

        report_card = ttk.LabelFrame(root, text=" Generated Audit Dossier ", padding=8)
        report_card.pack(fill=tk.BOTH, expand=True)

        self.txt_report = scrolledtext.ScrolledText(report_card, bg="#1a1a2b", fg="#f5f6fa", font=("Consolas", 9),
                                                    relief="flat")
        self.txt_report.pack(fill=tk.BOTH, expand=True)

    def _generate_report_text(self):
        pwd = self.pwd_var.get()
        comp = EntropyEngine.analyze_composition(pwd)
        hartley = EntropyEngine.calculate_hartley_entropy(comp["length"], comp["pool_size"])
        shannon = EntropyEngine.calculate_shannon_entropy(pwd)
        heuristic, penalties = EntropyEngine.calculate_heuristic_entropy(pwd)
        _, log10_s = EntropyEngine.get_search_space_digits(comp["length"], comp["pool_size"])

        lines = [
            "================================================================================",
            "             CRYPTOGRAPHIC ENTROPY & KEY-SPACE AUDIT REPORT                     ",
            "================================================================================",
            f"Generated On          : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Evaluated Target      : [REDACTED FOR COMPLIANCE] (Length: {comp['length']})",
            f"Character Pool (R)    : {comp['pool_size']} symbol variations",
            f"Pool Constituents     : {comp['pool_desc']}",
            "--------------------------------------------------------------------------------",
            "1. THEORETICAL ENTROPY METRICS",
            "--------------------------------------------------------------------------------",
            f"• Combinatorial Hartley Entropy : {hartley:.2f} bits",
            f"• Information Shannon Entropy   : {shannon:.2f} bits",
            f"• NIST Heuristic Effective Score: {heuristic:.2f} bits",
            f"• Total Theoretical Key-Space   : 10^{log10_s:.2f} permutations",
            "",
            "--------------------------------------------------------------------------------",
            "2. HEURISTIC & PATTERN DEDUCTION AUDIT",
            "--------------------------------------------------------------------------------"
        ]

        if penalties:
            for p in penalties:
                lines.append(f"  [CRITICAL] {p}")
        else:
            lines.append("  [CLEAN] No heuristic pattern vulnerabilities identified.")

        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            "3. EXHAUSTIVE OFFLINE ATTACK SCENARIO TIMELINES",
            "--------------------------------------------------------------------------------"
        ])

        for model in STANDARD_THREAT_MODELS:
            res = EntropyEngine.compute_crack_time(log10_s, model.rate_per_sec)
            rate_fmt = f"{model.rate_per_sec:,.0f} guesses/s" if model.rate_per_sec >= 1 else f"{model.rate_per_sec * 3600:.0f} guesses/hr"
            lines.append(f"• {model.name:<38} | Rate: {rate_fmt:<18} | Time: {res['formatted']}")

        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            "4. ARCHITECTURAL DEFENSE RECOMMENDATIONS",
            "--------------------------------------------------------------------------------",
            "1. ENFORCE MULTI-WORD PASSPHRASES: Prioritize lengths >= 16 characters over symbol complexity.",
            "2. KEY DERIVATION STRETCHING: Always hash credentials with Argon2id (m=64MB, t=3, p=4)",
            "   or bcrypt with work factor >= 12 to enforce slow offline cracking speeds.",
            "3. DEFEND WITH RATE LIMITING: Implement proof-of-work challenges and progressive timeouts",
            "   on public endpoints to constrain brute-force attempts to < 100 requests per hour.",
            "================================================================================"
        ])

        report_string = "\n".join(lines)
        self.txt_report.delete("1.0", tk.END)
        self.txt_report.insert(tk.END, report_string)

    def _save_report_to_disk(self):
        content = self.txt_report.get("1.0", tk.END).strip()
        if not content:
            self._generate_report_text()
            content = self.txt_report.get("1.0", tk.END).strip()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")],
            title="Save Entropy Security Dossier"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Report Exported", f"Security Dossier saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save file:\n{e}")


# ==============================================================================
# 4. ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Prevent fuzzy rendering on high-DPI Windows displays
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PasswordEntropyApp()
    app.mainloop()
import os
import sys
import math
import time
import json
import string
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font as tkFont

# Dynamic inspection for optional Matplotlib installation
try:
    import matplotlib

    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ==============================================================================
# 1. CONSTANTS, ENUMS & HARDWARE PRESETS
# ==============================================================================

class HardwarePreset:
    """Pre-calibrated attack velocity and electrical draw profiles."""

    def __init__(self, name: str, rate_per_sec: float, watts: float, cloud_cost_per_hr: float, category: str):
        self.name = name
        self.rate_per_sec = rate_per_sec
        self.watts = watts
        self.cloud_cost_per_hr = cloud_cost_per_hr
        self.category = category


HARDWARE_PROFILES = [
    HardwarePreset("Single CPU Core (Web Script)", 100_000, 65.0, 0.05, "CPU"),
    HardwarePreset("Modern Desktop GPU (RTX 4090 - SHA256)", 2_500_000_000, 450.0, 0.45, "GPU"),
    HardwarePreset("8x RTX 4090 Dedicated Rig (MD5/Fast Hash)", 100_000_000_000, 3_600.0, 2.50, "Rig"),
    HardwarePreset("Enterprise ASIC Cluster / Botnet Array", 100_000_000_000_000, 50_000.0, 25.00, "Supercluster"),
]


# ==============================================================================
# 2. LOGARITHMIC MATHEMATICAL & ESTIMATION CORE
# ==============================================================================

class CostEstimatorCore:
    """
    Logarithmic arithmetic engine that handles astronomical numbers (S > 10^300)
    without encountering Python float OverflowError exceptions.
    """

    LOG10_MINUTE = math.log10(60.0)
    LOG10_HOUR = math.log10(3600.0)
    LOG10_DAY = math.log10(86400.0)
    LOG10_YEAR = math.log10(31_557_600.0)  # Julian year (365.25 days)
    LOG10_UNIVERSE = LOG10_YEAR + math.log10(13.8e9)  # 13.8 billion years

    @classmethod
    def calculate_pool_size(
            cls,
            has_lower: bool,
            has_upper: bool,
            has_digits: bool,
            has_symbols: bool,
            has_space: bool,
            has_extended: bool,
            custom_chars: str = ""
    ) -> int:
        """Derives effective character set pool size R."""
        pool = 0
        if has_lower: pool += 26
        if has_upper: pool += 26
        if has_digits: pool += 10
        if has_symbols: pool += 33
        if has_space: pool += 1
        if has_extended: pool += 128

        # Deduplicate custom additions
        if custom_chars:
            unique_custom = set(custom_chars)
            pool += len(unique_custom)
        return max(pool, 1)

    @classmethod
    def format_log_time(cls, log10_seconds: float) -> str:
        """Translates log10(seconds) into a human-readable duration."""
        if log10_seconds < -3:
            return "< 1 Millisecond"
        elif log10_seconds < 0:
            val = (10 ** log10_seconds) * 1000.0
            return f"{val:.2f} Milliseconds"
        elif log10_seconds < cls.LOG10_MINUTE:
            val = 10 ** log10_seconds
            return f"{val:.2f} Seconds"
        elif log10_seconds < cls.LOG10_HOUR:
            val = 10 ** (log10_seconds - cls.LOG10_MINUTE)
            return f"{val:.2f} Minutes"
        elif log10_seconds < cls.LOG10_DAY:
            val = 10 ** (log10_seconds - cls.LOG10_HOUR)
            return f"{val:.2f} Hours"
        elif log10_seconds < cls.LOG10_YEAR:
            val = 10 ** (log10_seconds - cls.LOG10_DAY)
            return f"{val:.2f} Days"
        elif log10_seconds < cls.LOG10_YEAR + 3:
            val = 10 ** (log10_seconds - cls.LOG10_YEAR)
            return f"{val:.2f} Years"
        elif log10_seconds < cls.LOG10_YEAR + 6:
            val = 10 ** (log10_seconds - (cls.LOG10_YEAR + 3))
            return f"{val:.2f} Thousand Years"
        elif log10_seconds < cls.LOG10_YEAR + 9:
            val = 10 ** (log10_seconds - (cls.LOG10_YEAR + 6))
            return f"{val:.2f} Million Years"
        elif log10_seconds < cls.LOG10_UNIVERSE:
            val = 10 ** (log10_seconds - (cls.LOG10_YEAR + 9))
            return f"{val:.2f} Billion Years"
        else:
            universes = 10 ** (log10_seconds - cls.LOG10_UNIVERSE)
            if universes < 1e6:
                return f"{universes:.2f} × Age of Universe"
            exp = log10_seconds - cls.LOG10_YEAR
            return f"10^{exp:.1f} Years (Infeasible)"

    @classmethod
    def evaluate_attack(
            cls,
            length: int,
            pool_size: int,
            rate_per_sec: float,
            watts: float = 450.0,
            kwh_price: float = 0.15,
            cloud_rate_per_hr: float = 0.45
    ) -> Dict[str, Any]:
        """
        Executes full theoretical evaluation of search space, attack bounds,
        economic power draw, and cloud computation costs.
        """
        if length <= 0 or pool_size <= 0 or rate_per_sec <= 0:
            return {}

        # Log-space calculations: log10(S) = L * log10(R)
        log10_s = length * math.log10(pool_size)
        log10_rate = math.log10(rate_per_sec)
        entropy_bits = length * math.log2(pool_size)

        # 1. Best Case: 1st guess success (T = 1 / rate)
        log10_t_best = -log10_rate

        # 2. Average Case: 50% search space (S / 2) -> log10(S) - log10(2) - log10(rate)
        log10_t_avg = log10_s - math.log10(2.0) - log10_rate

        # 3. Worst Case: 100% search space exhaustion -> log10(S) - log10(rate)
        log10_t_worst = log10_s - log10_rate

        # Confidence intervals: 10%, 90%, 99%
        log10_t_10 = log10_s + math.log10(0.10) - log10_rate
        log10_t_90 = log10_s + math.log10(0.90) - log10_rate
        log10_t_99 = log10_s + math.log10(0.99) - log10_rate

        # Economic estimations based on Average-Case time
        is_economically_feasible = (log10_t_avg < (cls.LOG10_YEAR + 2))  # < 100 years

        if is_economically_feasible and log10_t_avg < 11:
            seconds_avg = 10 ** log10_t_avg
            hours_avg = seconds_avg / 3600.0
            kwh_used = (watts / 1000.0) * hours_avg
            electric_cost = kwh_used * kwh_price
            cloud_cost = hours_avg * cloud_rate_per_hr
            co2_kg = kwh_used * 0.385  # ~0.385 kg CO2 per kWh grid average
        else:
            kwh_used = float('inf')
            electric_cost = float('inf')
            cloud_cost = float('inf')
            co2_kg = float('inf')

        return {
            "length": length,
            "pool_size": pool_size,
            "entropy_bits": entropy_bits,
            "log10_search_space": log10_s,
            "rate_per_sec": rate_per_sec,
            "time_best_formatted": cls.format_log_time(log10_t_best),
            "time_avg_formatted": cls.format_log_time(log10_t_avg),
            "time_worst_formatted": cls.format_log_time(log10_t_worst),
            "time_10_formatted": cls.format_log_time(log10_t_10),
            "time_90_formatted": cls.format_log_time(log10_t_90),
            "time_99_formatted": cls.format_log_time(log10_t_99),
            "log10_t_avg": log10_t_avg,
            "is_feasible": is_economically_feasible,
            "kwh_used": kwh_used,
            "electric_cost": electric_cost,
            "cloud_cost": cloud_cost,
            "co2_kg": co2_kg
        }


# ==============================================================================
# 3. NATIVE CANVAS CHARTING ENGINE (ZERO EXTERNAL PLUGINS)
# ==============================================================================

class NativeVectorChart(tk.Canvas):
    """
    Pure Tkinter Vector Canvas Charting Engine.
    Plots logarithmic curves and comparative bar charts without third-party dependencies.
    """

    def __init__(self, master, width=640, height=340, bg="#1a1a2b", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height

    def render_length_curves(self, current_pool: int, rate_per_sec: float):
        """Plots Log10(Time in Years) curves across lengths 6 to 20 for multiple charsets."""
        self.delete("all")
        pad_l, pad_r, pad_t, pad_b = 65, 30, 30, 45
        w = self.width - pad_l - pad_r
        h = self.height - pad_t - pad_b

        # Datasets to plot: (Name, Pool Size, Color)
        series = [
            ("Digits [0-9] (10)", 10, "#e74c3c"),
            ("Lowercase [a-z] (26)", 26, "#f39c12"),
            ("Alphanumeric (62)", 62, "#2ecc71"),
            ("All Printable (95)", 95, "#00d2d3"),
        ]

        # X scale: Lengths 6 to 20
        min_l, max_l = 6, 20
        # Y scale: Log10 Years from -8 (milliseconds) to +15 (quadrillion years)
        min_y, max_y = -6.0, 14.0

        # Draw Grid & Y-Axis Labels
        y_ticks = [(-6, "ms"), (-3, "sec"), (0, "1 hr"), (2, "1 yr"), (6, "1M yr"), (10, "10B yr"), (14, "Universe")]
        for val, label in y_ticks:
            y = pad_t + h - ((val - min_y) / (max_y - min_y)) * h
            self.create_line(pad_l, y, pad_l + w, y, fill="#2c2c44", width=1)
            self.create_text(pad_l - 8, y, text=label, anchor=tk.E, font=("Segoe UI", 7), fill="#8e8ea8")

        # Draw X-Axis Labels
        for l in range(min_l, max_l + 1, 2):
            x = pad_l + ((l - min_l) / (max_l - min_l)) * w
            self.create_line(x, pad_t, x, pad_t + h, fill="#2c2c44", width=1)
            self.create_text(x, pad_t + h + 14, text=f"L={l}", anchor=tk.CENTER, font=("Segoe UI", 8), fill="#8e8ea8")

        # Plot Curves
        for name, pool, col in series:
            pts = []
            for l in range(min_l, max_l + 1):
                eval_res = CostEstimatorCore.evaluate_attack(l, pool, rate_per_sec)
                # Convert log10 seconds to log10 years
                log_yr = eval_res["log10_t_avg"] - CostEstimatorCore.LOG10_YEAR
                clamped_yr = max(min_y, min(max_y, log_yr))

                x = pad_l + ((l - min_l) / (max_l - min_l)) * w
                y = pad_t + h - ((clamped_yr - min_y) / (max_y - min_y)) * h
                pts.extend([x, y])

            # Draw smooth polyline
            if len(pts) >= 4:
                self.create_line(pts, fill=col, width=2, smooth=True)

        # Outer Axis Bounds
        self.create_line(pad_l, pad_t, pad_l, pad_t + h, fill="#474766", width=2)
        self.create_line(pad_l, pad_t + h, pad_l + w, pad_t + h, fill="#474766", width=2)

        # Legend
        lx = pad_l + 15
        ly = pad_t + 10
        for name, _, col in series:
            self.create_rectangle(lx, ly, lx + 12, ly + 8, fill=col, outline="")
            self.create_text(lx + 18, ly + 4, text=name, anchor=tk.W, font=("Segoe UI", 8, "bold"), fill="#f5f6fa")
            lx += 135

    def render_hardware_comparison(self, length: int, pool_size: int):
        """Plots comparative bar chart contrasting crack times across hardware tiers."""
        self.delete("all")
        pad_l, pad_r, pad_t, pad_b = 60, 20, 25, 45
        w = self.width - pad_l - pad_r
        h = self.height - pad_t - pad_b

        bars = len(HARDWARE_PROFILES)
        bar_w = (w / bars) * 0.55
        gap = (w / bars)

        # Determine relative log10 years range
        min_y, max_y = -6.0, 12.0

        # Background grid
        for val in range(-6, 13, 3):
            y = pad_t + h - ((val - min_y) / (max_y - min_y)) * h
            self.create_line(pad_l, y, pad_l + w, y, fill="#2c2c44", width=1)
            lbl = CostEstimatorCore.format_log_time(val + CostEstimatorCore.LOG10_YEAR)
            self.create_text(pad_l - 6, y, text=lbl[:7], anchor=tk.E, font=("Segoe UI", 7), fill="#8e8ea8")

        for idx, hw in enumerate(HARDWARE_PROFILES):
            res = CostEstimatorCore.evaluate_attack(length, pool_size, hw.rate_per_sec)
            log_yr = res["log10_t_avg"] - CostEstimatorCore.LOG10_YEAR
            clamped_yr = max(min_y, min(max_y, log_yr))

            bx = pad_l + (idx * gap) + (gap - bar_w) / 2
            by = pad_t + h - ((clamped_yr - min_y) / (max_y - min_y)) * h
            base_y = pad_t + h - ((0 - min_y) / (max_y - min_y)) * h

            col = "#2ecc71" if log_yr >= 2 else ("#f1c40f" if log_yr >= -1 else "#e74c3c")
            self.create_rectangle(bx, by, bx + bar_w, base_y, fill=col, outline="")

            # Hardware label
            self.create_text(bx + bar_w / 2, pad_t + h + 14, text=hw.category, anchor=tk.CENTER,
                             font=("Segoe UI", 8, "bold"), fill="#f5f6fa")
            # Result time text above bar
            self.create_text(bx + bar_w / 2, max(pad_t + 5, by - 8), text=res["time_avg_formatted"][:12],
                             anchor=tk.CENTER, font=("Segoe UI", 7), fill="#ffffff")

        self.create_line(pad_l, pad_t, pad_l, pad_t + h, fill="#474766", width=2)
        self.create_line(pad_l, pad_t + h, pad_l + w, pad_t + h, fill="#474766", width=2)


# ==============================================================================
# 4. INTERACTIVE GRAPHICAL USER INTERFACE
# ==============================================================================

class CostEstimatorApp(tk.Tk):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.title("Password Attack Cost & Theoretical Search Estimator")
        self.geometry("1160x840")
        self.minsize(1020, 720)
        self.configure(bg="#141420")

        self._setup_styles()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Initial trigger
        self.after(50, self.recalculate)

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
        self.style.configure("Treeview", background="#1a1a2b", foreground="#f5f6fa", fieldbackground="#1a1a2b",
                             rowheight=26, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", background="#27273f", foreground="#00d2d3", relief="flat",
                             font=("Segoe UI", 9, "bold"))
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

        title = tk.Label(hdr, text="PASSWORD ATTACK COST & THEORETICAL SEARCH ESTIMATOR", font=("Segoe UI", 12, "bold"),
                         bg="#1e1e2f", fg="#ffffff")
        title.pack(side=tk.LEFT, padx=20, pady=8)

        engine_badge = "MATPLOTLIB INTEGRATED" if HAS_MATPLOTLIB else "NATIVE VECTOR CANVAS"
        lbl = tk.Label(hdr, text=f"ENGINE: {engine_badge}", font=("Consolas", 9, "bold"), bg="#1e1e2f", fg="#00d2d3")
        lbl.pack(side=tk.RIGHT, padx=20, pady=12)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

        self.tab_calculator = ttk.Frame(self.notebook, padding=12)
        self.tab_visuals = ttk.Frame(self.notebook, padding=12)
        self.tab_matrix = ttk.Frame(self.notebook, padding=12)
        self.tab_economics = ttk.Frame(self.notebook, padding=12)
        self.tab_dossier = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_calculator, text=" Search Cost Calculator ")
        self.notebook.add(self.tab_visuals, text=" Visual Comparison Curves ")
        self.notebook.add(self.tab_matrix, text=" Exhaustive Length Matrix ")
        self.notebook.add(self.tab_economics, text=" Financial & Power Burden ")
        self.notebook.add(self.tab_dossier, text=" Audit Dossier Exporter ")

        self._build_tab_calculator()
        self._build_tab_visuals()
        self._build_tab_matrix()
        self._build_tab_economics()
        self._build_tab_dossier()

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self, bg="#1a1a2b", height=24)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.statusbar.pack_propagate(False)

        self.status_lbl = tk.Label(self.statusbar, text="Combinatorial Engine Ready. Running log-space arithmetic.",
                                   font=("Segoe UI", 8), bg="#1a1a2b", fg="#8e8ea8")
        self.status_lbl.pack(side=tk.LEFT, padx=15)

    # --------------------------------------------------------------------------
    # TAB 1: CALCULATOR & TELEMETRY
    # --------------------------------------------------------------------------
    def _build_tab_calculator(self):
        root = self.tab_calculator

        # Upper Controls Frame
        ctrl_card = ttk.LabelFrame(root, text=" Target Search Parameters & Velocity ", padding=12)
        ctrl_card.pack(fill=tk.X, pady=(0, 10))

        c_grid = tk.Frame(ctrl_card, bg="#1e1e2f")
        c_grid.pack(fill=tk.X)

        # Row 1: Length Slider & Input
        tk.Label(c_grid, text="Password Length (L):", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0, sticky=tk.W,
                                                                                       pady=4)
        self.length_var = tk.IntVar(value=10)
        self.slider_len = ttk.Scale(c_grid, from_=4, to=32, orient=tk.HORIZONTAL, variable=self.length_var,
                                    command=lambda v: self._sync_length(int(float(v))))
        self.slider_len.grid(row=0, column=1, sticky=tk.EW, padx=8)

        self.lbl_len_val = tk.Label(c_grid, text="10 chars", font=("Consolas", 10, "bold"), bg="#1e1e2f", fg="#00d2d3",
                                    width=8)
        self.lbl_len_val.grid(row=0, column=2, sticky=tk.W)

        # Row 2: Character Sets
        tk.Label(c_grid, text="Character Set Pools:", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0, sticky=tk.W,
                                                                                       pady=6)
        cs_frame = tk.Frame(c_grid, bg="#1e1e2f")
        cs_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W)

        self.cb_lower = tk.BooleanVar(value=True)
        self.cb_upper = tk.BooleanVar(value=True)
        self.cb_digits = tk.BooleanVar(value=True)
        self.cb_symbols = tk.BooleanVar(value=False)
        self.cb_space = tk.BooleanVar(value=False)

        for text, var in [
            ("Lower [a-z] (26)", self.cb_lower),
            ("Upper [A-Z] (26)", self.cb_upper),
            ("Digits [0-9] (10)", self.cb_digits),
            ("Symbols (!@#) (33)", self.cb_symbols),
            ("Space (1)", self.cb_space)
        ]:
            cb = tk.Checkbutton(cs_frame, text=text, variable=var, bg="#1e1e2f", fg="#f5f6fa", selectcolor="#2c2c44",
                                command=self.recalculate)
            cb.pack(side=tk.LEFT, padx=5)

        # Row 3: Hardware Profile
        tk.Label(c_grid, text="Attacker Hardware Profile:", bg="#1e1e2f", fg="#f5f6fa").grid(row=2, column=0,
                                                                                             sticky=tk.W, pady=6)
        self.hw_var = tk.StringVar(value=HARDWARE_PROFILES[2].name)  # Default: 8x RTX 4090
        combo_hw = ttk.Combobox(c_grid, textvariable=self.hw_var, values=[h.name for h in HARDWARE_PROFILES],
                                state="readonly", width=36)
        combo_hw.grid(row=2, column=1, sticky=tk.W, padx=8)
        combo_hw.bind("<<ComboboxSelected>>", self._on_hw_selected)

        # Row 4: Custom Velocity
        tk.Label(c_grid, text="Custom Hash Velocity (/s):", bg="#1e1e2f", fg="#f5f6fa").grid(row=3, column=0,
                                                                                             sticky=tk.W, pady=6)
        self.rate_var = tk.StringVar(value=f"{HARDWARE_PROFILES[2].rate_per_sec:,.0f}")
        self.entry_rate = ttk.Entry(c_grid, textvariable=self.rate_var, width=24)
        self.entry_rate.grid(row=3, column=1, sticky=tk.W, padx=8)
        self.entry_rate.bind("<KeyRelease>", lambda e: self.recalculate())

        # Middle Metric KPI Display
        kpi_card = ttk.LabelFrame(root, text=" Theoretical Search Space & Attack Estimates ", padding=12)
        kpi_card.pack(fill=tk.BOTH, expand=True)

        kpi_grid = tk.Frame(kpi_card, bg="#1e1e2f")
        kpi_grid.pack(fill=tk.BOTH, expand=True)

        self.kpi_space = self._create_kpi_card(kpi_grid, "Exhaustive Key Space (R^L)", "0", 0, 0, "#00d2d3")
        self.kpi_entropy = self._create_kpi_card(kpi_grid, "Shannon / Hartley Entropy", "0 bits", 0, 1, "#f5f6fa")
        self.kpi_pool = self._create_kpi_card(kpi_grid, "Effective Charset (R)", "0 symbols", 0, 2, "#f5f6fa")

        self.kpi_best = self._create_kpi_card(kpi_grid, "Best-Case (1st Attempt Luck)", "0s", 1, 0, "#2ecc71")
        self.kpi_avg = self._create_kpi_card(kpi_grid, "Average-Case (50% Probability)", "0s", 1, 1, "#f1c40f")
        self.kpi_worst = self._create_kpi_card(kpi_grid, "Worst-Case (100% Exhaustion)", "0s", 1, 2, "#e74c3c")

        # Lower Probability Milestones
        prob_card = ttk.LabelFrame(root, text=" Attack Completion Odds Timeline ", padding=10)
        prob_card.pack(fill=tk.X, pady=(10, 0))

        self.lbl_prob_timeline = tk.Label(prob_card, text="", bg="#1e1e2f", fg="#f5f6fa", font=("Consolas", 9),
                                          justify=tk.LEFT)
        self.lbl_prob_timeline.pack(anchor=tk.W)

    def _create_kpi_card(self, parent, title: str, val: str, r: int, c: int, color: str) -> tk.Label:
        f = tk.Frame(parent, bg="#27273f", padx=12, pady=10)
        f.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
        parent.grid_columnconfigure(c, weight=1)
        parent.grid_rowconfigure(r, weight=1)

        tk.Label(f, text=title, font=("Segoe UI", 8), bg="#27273f", fg="#8e8ea8").pack(anchor=tk.W)
        lbl = tk.Label(f, text=val, font=("Segoe UI", 14, "bold"), bg="#27273f", fg=color)
        lbl.pack(anchor=tk.W, pady=(4, 0))
        return lbl

    def _sync_length(self, val: int):
        self.length_var.set(val)
        self.lbl_len_val.config(text=f"{val} chars")
        self.recalculate()

    def _on_hw_selected(self, event=None):
        name = self.hw_var.get()
        hw = next((h for h in HARDWARE_PROFILES if h.name == name), HARDWARE_PROFILES[0])
        self.rate_var.set(f"{hw.rate_per_sec:,.0f}")
        self.recalculate()

    # --------------------------------------------------------------------------
    # TAB 2: VISUAL COMPARISON CURVES
    # --------------------------------------------------------------------------
    def _build_tab_visuals(self):
        root = self.tab_visuals

        top_ctrl = tk.Frame(root, bg="#141420")
        top_ctrl.pack(fill=tk.X, pady=(0, 8))

        tk.Label(top_ctrl, text="Select Comparison Visualization:", bg="#141420", fg="#f5f6fa").pack(side=tk.LEFT,
                                                                                                     padx=(0, 8))
        self.chart_type_var = tk.StringVar(value="Length Exponential Curve")
        combo = ttk.Combobox(top_ctrl, textvariable=self.chart_type_var,
                             values=["Length Exponential Curve", "Hardware Tier Bar Chart"], state="readonly", width=28)
        combo.pack(side=tk.LEFT, padx=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self._render_visuals())

        chart_card = ttk.LabelFrame(root, text=" Visual Vector Graph ", padding=8)
        chart_card.pack(fill=tk.BOTH, expand=True)

        self.native_canvas = NativeVectorChart(chart_card, width=720, height=380, bg="#1a1a2b")
        self.native_canvas.pack(fill=tk.BOTH, expand=True)

    def _render_visuals(self):
        ctype = self.chart_type_var.get()
        length = self.length_var.get()
        pool = CostEstimatorCore.calculate_pool_size(
            self.cb_lower.get(), self.cb_upper.get(), self.cb_digits.get(),
            self.cb_symbols.get(), self.cb_space.get(), False
        )
        rate = self._get_active_rate()

        if ctype == "Length Exponential Curve":
            self.native_canvas.render_length_curves(pool, rate)
        else:
            self.native_canvas.render_hardware_comparison(length, pool)

    # --------------------------------------------------------------------------
    # TAB 3: EXHAUSTIVE LENGTH MATRIX
    # --------------------------------------------------------------------------
    def _build_tab_matrix(self):
        root = self.tab_matrix

        cols = ("length", "num", "lower", "alpha", "alphanum", "full")
        self.tree_mat = ttk.Treeview(root, columns=cols, show="headings")
        self.tree_mat.heading("length", text="Length (L)")
        self.tree_mat.heading("num", text="Numeric (R=10)")
        self.tree_mat.heading("lower", text="Lowercase (R=26)")
        self.tree_mat.heading("alpha", text="Letters (R=52)")
        self.tree_mat.heading("alphanum", text="Alphanumeric (R=62)")
        self.tree_mat.heading("full", text="All Printable (R=95)")

        self.tree_mat.column("length", width=80, anchor=tk.CENTER)
        self.tree_mat.column("num", width=160)
        self.tree_mat.column("lower", width=160)
        self.tree_mat.column("alpha", width=160)
        self.tree_mat.column("alphanum", width=170)
        self.tree_mat.column("full", width=180)

        self.tree_mat.pack(fill=tk.BOTH, expand=True)

    def _populate_matrix(self):
        self.tree_mat.delete(*self.tree_mat.get_children())
        rate = self._get_active_rate()

        for l in range(6, 25):
            t_num = CostEstimatorCore.evaluate_attack(l, 10, rate)["time_avg_formatted"]
            t_low = CostEstimatorCore.evaluate_attack(l, 26, rate)["time_avg_formatted"]
            t_alpha = CostEstimatorCore.evaluate_attack(l, 52, rate)["time_avg_formatted"]
            t_alphanum = CostEstimatorCore.evaluate_attack(l, 62, rate)["time_avg_formatted"]
            t_full = CostEstimatorCore.evaluate_attack(l, 95, rate)["time_avg_formatted"]

            self.tree_mat.insert("", tk.END, values=(f"{l} chars", t_num, t_low, t_alpha, t_alphanum, t_full))

    # --------------------------------------------------------------------------
    # TAB 4: ECONOMIC & ENERGY BURDEN
    # --------------------------------------------------------------------------
    def _build_tab_economics(self):
        root = self.tab_economics

        f_card = ttk.LabelFrame(root, text=" Power Grid & Financial Cost Assumptions ", padding=12)
        f_card.pack(fill=tk.X, pady=(0, 10))

        grid = tk.Frame(f_card, bg="#1e1e2f")
        grid.pack(fill=tk.X)

        tk.Label(grid, text="Rig Electrical Draw (Watts):", bg="#1e1e2f", fg="#f5f6fa").grid(row=0, column=0,
                                                                                             sticky=tk.W, pady=4)
        self.watts_var = tk.StringVar(value="3600")
        ttk.Entry(grid, textvariable=self.watts_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=6)

        tk.Label(grid, text="Utility Electricity Rate ($/kWh):", bg="#1e1e2f", fg="#f5f6fa").grid(row=1, column=0,
                                                                                                  sticky=tk.W, pady=4)
        self.kwh_var = tk.StringVar(value="0.15")
        ttk.Entry(grid, textvariable=self.kwh_var, width=12).grid(row=1, column=1, sticky=tk.W, padx=6)

        tk.Label(grid, text="Cloud GPU Rental Rate ($/hour):", bg="#1e1e2f", fg="#f5f6fa").grid(row=2, column=0,
                                                                                                sticky=tk.W, pady=4)
        self.cloud_var = tk.StringVar(value="2.50")
        ttk.Entry(grid, textvariable=self.cloud_var, width=12).grid(row=2, column=1, sticky=tk.W, padx=6)

        btn_calc_econ = ttk.Button(grid, text="Update Economic Projections", style="Primary.TButton",
                                   command=self.recalculate)
        btn_calc_econ.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.W)

        # Output Dossier
        res_card = ttk.LabelFrame(root, text=" Adversary Economic & Resource Requirements ", padding=10)
        res_card.pack(fill=tk.BOTH, expand=True)

        self.txt_econ = scrolledtext.ScrolledText(res_card, bg="#1a1a2b", fg="#00d2d3", font=("Consolas", 10),
                                                  relief="flat")
        self.txt_econ.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # TAB 5: AUDIT DOSSIER EXPORTER
    # --------------------------------------------------------------------------
    def _build_tab_dossier(self):
        root = self.tab_dossier

        bar = tk.Frame(root, bg="#141420")
        bar.pack(fill=tk.X, pady=(0, 10))

        btn_txt = ttk.Button(bar, text="Save Assessment Report (.txt)...", style="Primary.TButton",
                             command=self._export_txt)
        btn_txt.pack(side=tk.LEFT, padx=(0, 8))

        btn_json = ttk.Button(bar, text="Export Raw Assessment (.json)...", style="Secondary.TButton",
                              command=self._export_json)
        btn_json.pack(side=tk.LEFT)

        card = ttk.LabelFrame(root, text=" Generated Threat Assessment Dossier ", padding=8)
        card.pack(fill=tk.BOTH, expand=True)

        self.txt_dossier = scrolledtext.ScrolledText(card, bg="#1a1a2b", fg="#f5f6fa", font=("Consolas", 10),
                                                     relief="flat")
        self.txt_dossier.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # CORE CALCULATION DISPATCHER
    # --------------------------------------------------------------------------
    def _get_active_rate(self) -> float:
        try:
            return float(self.rate_var.get().replace(",", "").strip())
        except ValueError:
            return 100_000_000_000.0

    def recalculate(self):
        length = self.length_var.get()
        pool = CostEstimatorCore.calculate_pool_size(
            self.cb_lower.get(), self.cb_upper.get(), self.cb_digits.get(),
            self.cb_symbols.get(), self.cb_space.get(), False
        )
        rate = self._get_active_rate()

        try:
            watts = float(self.watts_var.get().replace(",", "").strip())
            kwh_p = float(self.kwh_var.get().replace(",", "").strip())
            cloud_p = float(self.cloud_var.get().replace(",", "").strip())
        except ValueError:
            watts, kwh_p, cloud_p = 3600.0, 0.15, 2.50

        res = CostEstimatorCore.evaluate_attack(length, pool, rate, watts, kwh_p, cloud_p)
        if not res:
            return

        # Update KPI Cards
        log10_s = res["log10_search_space"]
        if log10_s < 12:
            exact_s = pool ** length
            self.kpi_space.config(text=f"{exact_s:,}")
        else:
            self.kpi_space.config(text=f"10^{log10_s:.2f} keys")

        self.kpi_entropy.config(text=f"{res['entropy_bits']:.1f} bits")
        self.kpi_pool.config(text=f"{pool} symbols")
        self.kpi_best.config(text=res["time_best_formatted"])
        self.kpi_avg.config(text=res["time_avg_formatted"])
        self.kpi_worst.config(text=res["time_worst_formatted"])

        # Timeline Odds
        odds_str = (
            f"• 10% Probability of Compromise: {res['time_10_formatted']}\n"
            f"• 50% Probability of Compromise: {res['time_avg_formatted']}\n"
            f"• 90% Probability of Compromise: {res['time_90_formatted']}\n"
            f"• 99% Probability of Compromise: {res['time_99_formatted']}"
        )
        self.lbl_prob_timeline.config(text=odds_str)

        # Update Economics Text
        self._update_economics_text(res, watts, kwh_p, cloud_p)

        # Update Visuals
        self._render_visuals()

        # Update Matrix
        self._populate_matrix()

        # Update Report Dossier
        self._render_dossier_text(res)

    def _update_economics_text(self, res: Dict[str, Any], watts: float, kwh_p: float, cloud_p: float):
        self.txt_econ.delete("1.0", tk.END)
        lines = [
            "================================================================================",
            "        ECONOMIC & ADVERSARY ENERGY BURDEN ASSESSMENT                           ",
            "================================================================================",
            f"Target Key Space        : 10^{res['log10_search_space']:.2f} combinations ({res['entropy_bits']:.1f} bits)",
            f"Attack Hardware Power   : {watts:,.0f} Watts",
            f"Electricity Utility Cost: ${kwh_p:.2f} per kWh",
            f"Cloud Compute Rental    : ${cloud_p:.2f} per hour",
            f"Average Crack Time (50%): {res['time_avg_formatted']}",
            "--------------------------------------------------------------------------------",
            "ADVERSARY FINANCIAL & CARBON IMPACT:"
        ]

        if not res["is_feasible"]:
            lines.extend([
                "• Energy Consumption  : INFEASIBLE (Exceeds total planetary grid capacity).",
                "• Financial Cost      : INFEASIBLE (Exceeds global civilization gross product).",
                "• Carbon Impact       : Astronomical.",
                "• Security Assessment : Cryptographically robust against offline exhaustive search."
            ])
        else:
            lines.extend([
                f"• Power Consumed      : {res['kwh_used']:,.2f} kWh",
                f"• Utility Electric Bill: ${res['electric_cost']:,.2f} USD",
                f"• Cloud GPU Cost      : ${res['cloud_cost']:,.2f} USD",
                f"• Carbon Footprint    : {res['co2_kg']:,.2f} kg CO2 equivalent"
            ])

        lines.append("================================================================================")
        self.txt_econ.insert(tk.END, "\n".join(lines))

    def _render_dossier_text(self, res: Dict[str, Any]):
        self.txt_dossier.delete("1.0", tk.END)
        lines = [
            "================================================================================",
            "             THEORETICAL PASSWORD ATTACK COST ASSESSMENT REPORT                 ",
            "================================================================================",
            f"Generated On          : {time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Audited Length (L)    : {res['length']} characters",
            f"Effective Pool (R)    : {res['pool_size']} symbol variations",
            f"Combinatorial Entropy : {res['entropy_bits']:.2f} bits",
            f"Total Permutations    : 10^{res['log10_search_space']:.2f} combinations",
            f"Evaluated Hash Rate   : {res['rate_per_sec']:,.0f} guesses/sec",
            "--------------------------------------------------------------------------------",
            "1. PROBABILISTIC CRACK TIMELINES",
            "--------------------------------------------------------------------------------",
            f"• Best-Case (1st Attempt Luck)  : {res['time_best_formatted']}",
            f"• 10% Odds of Compromise        : {res['time_10_formatted']}",
            f"• 50% Average Odds of Breaching : {res['time_avg_formatted']}",
            f"• 90% High-Confidence Breach    : {res['time_90_formatted']}",
            f"• 100% Worst-Case Full Search   : {res['time_worst_formatted']}",
            "",
            "--------------------------------------------------------------------------------",
            "2. ADVERSARY ECONOMIC BURDEN",
            "--------------------------------------------------------------------------------",
            f"• Economic Feasibility : {'FEASIBLE (VULNERABLE)' if res['is_feasible'] else 'UNFEASIBLE (SECURE)'}",
            f"• Estimated Power Draw : {res['kwh_used']:,.2f} kWh" if res[
                'is_feasible'] else "• Estimated Power Draw : Infeasible",
            f"• Estimated Cloud Cost : ${res['cloud_cost']:,.2f} USD" if res[
                'is_feasible'] else "• Estimated Cloud Cost : Infeasible",
            "",
            "--------------------------------------------------------------------------------",
            "3. RECOMMENDATIONS & DEFENSE POSTURE",
            "--------------------------------------------------------------------------------",
            "1. Minimum Length >= 14: Each added character multiplies effort by pool size R.",
            "2. Enforce Multi-Word Passphrases: 4 random words (70+ bits) defeats GPU rigs.",
            "3. Slow KDF Enforcement: Transition from SHA-256 to Argon2id / bcrypt to constrain",
            "   attacker velocities from billions/sec down to thousands/sec.",
            "================================================================================"
        ]
        self.txt_dossier.insert(tk.END, "\n".join(lines))

    def _export_txt(self):
        content = self.txt_dossier.get("1.0", tk.END).strip()
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Documents", "*.txt")],
                                            title="Save Assessment Dossier")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Export Success", f"Report saved to:\n{path}")

    def _export_json(self):
        length = self.length_var.get()
        pool = CostEstimatorCore.calculate_pool_size(
            self.cb_lower.get(), self.cb_upper.get(), self.cb_digits.get(),
            self.cb_symbols.get(), self.cb_space.get(), False
        )
        rate = self._get_active_rate()
        res = CostEstimatorCore.evaluate_attack(length, pool, rate)

        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")],
                                            title="Export Raw Assessment JSON")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            messagebox.showinfo("Export Success", f"JSON data exported to:\n{path}")


# ==============================================================================
# 5. PROGRAM ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Prevent scaling blur on High-DPI Windows displays
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = CostEstimatorApp()
    app.mainloop()
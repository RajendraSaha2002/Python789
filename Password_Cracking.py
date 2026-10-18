import sys
import os
import time
import math
import string
import itertools
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font as tkFont

# ==============================================================================
# EMBEDDED WORDLIST FOR OUT-OF-THE-BOX DICTIONARY ATTACKS
# ==============================================================================
DEFAULT_DICTIONARY = (
    "password", "123456", "123456789", "guest", "qwerty", "12345678", "111111",
    "12345", "123123", "dragon", "welcome", "ninja", "master", "monkey",
    "shadow", "football", "baseball", "superman", "jordan", "killer", "trustno1",
    "hunter2", "princess", "sunshine", "iloveyou", "admin", "admin123", "pass123",
    "secret", "secret123", "root", "toor", "system", "oracle", "login",
    "default", "access", "test", "testing", "letmein", "changeme", "computer",
    "internet", "qwertyuiop", "asdfghjkl", "zxcvbnm", "charlie", "merlin",
    "ranger", "wizard", "starwars", "pokemon", "spider", "ginger", "chester",
    "thunder", "freedom", "matrix", "falcon", "phantom", "bullet", "bandit",
    "silver", "patriot", "corvette", "rooster", "cobra", "mustang", "firebird",
    "harley", "diamond", "genesis", "eclipse", "knight", "galaxy", "spitfire",
    "tiger", "target", "danger", "champion", "vampire", "barbie", "superstar",
    "legend", "phoenix", "apollo", "cannon", "sniper", "blaster", "destroyer",
    "overkill", "stealth", "justice", "titan", "blades", "vortex", "terminator",
    "p@ssword", "p@ssw0rd", "admin@123", "root123", "P@sswOrd123!", "pass@123"
)


# ==============================================================================
# CRYPTOGRAPHIC & ENTROPY ANALYSIS ENGINE
# ==============================================================================
class SecurityAnalyzer:
    """Calculates mathematical search space, Shannon entropy, and cracking metrics."""

    @staticmethod
    def calculate_pool_size(has_lower, has_upper, has_digits, has_symbols, has_space=False):
        pool = 0
        if has_lower:
            pool += 26
        if has_upper:
            pool += 26
        if has_digits:
            pool += 10
        if has_symbols:
            pool += len(string.punctuation)
        if has_space:
            pool += 1
        return pool

    @staticmethod
    def analyze_password(password):
        length = len(password)
        if length == 0:
            return {
                "length": 0, "pool_size": 0, "entropy": 0.0,
                "search_space": 0, "strength": "Empty",
                "has_lower": False, "has_upper": False,
                "has_digits": False, "has_symbols": False
            }

        has_lower = any(c in string.ascii_lowercase for c in password)
        has_upper = any(c in string.ascii_uppercase for c in password)
        has_digits = any(c in string.digits for c in password)
        has_symbols = any(c in string.punctuation for c in password)
        has_space = any(c == ' ' for c in password)

        pool = SecurityAnalyzer.calculate_pool_size(
            has_lower, has_upper, has_digits, has_symbols, has_space
        )
        if pool == 0:
            pool = 1

        # Shannon Entropy formula: H = L * log2(R)
        entropy = length * math.log2(pool)
        search_space = pool ** length

        if entropy < 28:
            strength = "Very Weak"
        elif entropy < 45:
            strength = "Weak"
        elif entropy < 65:
            strength = "Reasonable"
        elif entropy < 85:
            strength = "Strong"
        else:
            strength = "Very Strong"

        return {
            "length": length,
            "pool_size": pool,
            "entropy": round(entropy, 2),
            "search_space": search_space,
            "strength": strength,
            "has_lower": has_lower,
            "has_upper": has_upper,
            "has_digits": has_digits,
            "has_symbols": has_symbols
        }

    @staticmethod
    def format_time(seconds):
        if seconds == float('inf') or seconds > 3.154e17:
            return "Centuries (Astronomical)"
        if seconds < 0.001:
            return "< 1 millisecond"
        if seconds < 1.0:
            return f"{seconds * 1000:.1f} ms"
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        if seconds < 3600:
            return f"{seconds / 60:.2f} minutes"
        if seconds < 86400:
            return f"{seconds / 3600:.2f} hours"
        if seconds < 3.154e7:
            return f"{seconds / 86400:.2f} days"
        years = seconds / 3.154e7
        if years < 1000:
            return f"{years:.2f} years"
        return f"{years:.2e} years"

    @staticmethod
    def estimate_crack_times(search_space):
        # Average attempts needed to guess is 50% of total search space
        avg_attempts = search_space / 2.0

        # Typical speeds in attempts per second
        cpu_single_core = 1e5       # 100,000 / sec
        gpu_high_end = 1e8          # 100,000,000 / sec (Fast hash / single modern GPU)
        gpu_rig_cluster = 1e11      # 100 Billion / sec (Dedicated cracking rig)

        return {
            "cpu_time": SecurityAnalyzer.format_time(avg_attempts / cpu_single_core),
            "gpu_time": SecurityAnalyzer.format_time(avg_attempts / gpu_high_end),
            "cluster_time": SecurityAnalyzer.format_time(avg_attempts / gpu_rig_cluster)
        }


# ==============================================================================
# CORE WORKER ENGINE (RUNS IN SEPARATE THREAD)
# ==============================================================================
class CrackingEngine:
    """Handles pure brute-force, smart incremental brute-force, and mutated dictionary attacks."""

    def __init__(self, target_password, char_set, strategy, max_attempts, dictionary_list, update_queue, stop_event):
        self.target = target_password
        self.char_set = char_set
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.dictionary_list = dictionary_list
        self.queue = update_queue
        self.stop_event = stop_event
        self.attempts = 0
        self.start_time = 0

    def run(self):
        self.start_time = time.time()
        found = False
        matched_password = None

        self.queue.put(("log", f"[INIT] Engine started. Strategy: {self.strategy}"))
        self.queue.put(("log", f"[INIT] Target: '{self.target}' | Length: {len(self.target)}"))
        self.queue.put(("log", f"[INIT] Active Charset: [{self.char_set}] (Size: {len(self.char_set)})"))

        try:
            if self.strategy == "Brute-Force (Exact Length)":
                matched_password = self._brute_force_fixed(len(self.target))
            elif self.strategy == "Brute-Force (Incremental 1..N)":
                matched_password = self._brute_force_incremental(len(self.target))
            elif self.strategy == "Pure Dictionary Attack":
                matched_password = self._dictionary_attack(mutations=False)
            elif self.strategy == "Hybrid / Mutated Dictionary":
                matched_password = self._dictionary_attack(mutations=True)

            elapsed = max(time.time() - self.start_time, 0.0001)

            if matched_password is not None:
                self.queue.put(("success", {
                    "password": matched_password,
                    "attempts": self.attempts,
                    "elapsed": elapsed
                }))
            elif self.stop_event.is_set():
                self.queue.put(("stopped", {
                    "attempts": self.attempts,
                    "elapsed": elapsed
                }))
            else:
                self.queue.put(("failed", {
                    "attempts": self.attempts,
                    "elapsed": elapsed
                }))

        except Exception as ex:
            self.queue.put(("error", str(ex)))

    def _brute_force_fixed(self, length):
        total_chars = len(self.char_set)
        if total_chars == 0:
            return None

        # Iterative Cartesian product without pre-allocating memory
        for item in itertools.product(self.char_set, repeat=length):
            if self.stop_event.is_set():
                return None

            guess = "".join(item)
            self.attempts += 1

            if guess == self.target:
                return guess

            if self.attempts % 7500 == 0:
                elapsed = max(time.time() - self.start_time, 0.0001)
                self.queue.put(("progress", {
                    "attempts": self.attempts,
                    "current_guess": guess,
                    "elapsed": elapsed
                }))

            if 0 < self.max_attempts <= self.attempts:
                return None

        return None

    def _brute_force_incremental(self, max_len):
        for current_len in range(1, max_len + 1):
            self.queue.put(("log", f"[STAGE] Testing all candidate combinations of length {current_len}..."))
            for item in itertools.product(self.char_set, repeat=current_len):
                if self.stop_event.is_set():
                    return None

                guess = "".join(item)
                self.attempts += 1

                if guess == self.target:
                    return guess

                if self.attempts % 7500 == 0:
                    elapsed = max(time.time() - self.start_time, 0.0001)
                    self.queue.put(("progress", {
                        "attempts": self.attempts,
                        "current_guess": guess,
                        "elapsed": elapsed
                    }))

                if 0 < self.max_attempts <= self.attempts:
                    return None
        return None

    def _generate_mutations(self, base_word):
        """Generates real-world password mutations (leet, cases, affixes)."""
        mutations = set()
        mutations.add(base_word)
        mutations.add(base_word.lower())
        mutations.add(base_word.upper())
        mutations.add(base_word.capitalize())

        # Leetspeak basic mapping
        leet_chars = {
            'a': ['4', '@'], 'e': ['3'], 'i': ['1', '!'],
            'o': ['0'], 's': ['5', '$'], 't': ['7']
        }
        word_l = base_word.lower()
        leet1 = word_l
        for k, v in leet_chars.items():
            leet1 = leet1.replace(k, v[0])
        mutations.add(leet1)

        # Standard suffixes
        suffixes = ["1", "12", "123", "2023", "2024", "2025", "!", "@", "#", "!!"]
        prefixes = ["!", "@", "#", "123"]

        for w in list(mutations):
            for s in suffixes:
                mutations.add(w + s)
            for p in prefixes:
                mutations.add(p + w)

        return mutations

    def _dictionary_attack(self, mutations=False):
        word_candidates = []

        if not mutations:
            word_candidates = self.dictionary_list
        else:
            self.queue.put(("log", "[DICTIONARY] Generating mutation variants (case, leet, symbols, years)..."))
            expanded = set()
            for raw_word in self.dictionary_list:
                expanded.update(self._generate_mutations(raw_word))
            word_candidates = list(expanded)
            self.queue.put(("log", f"[DICTIONARY] Expanded dictionary size: {len(word_candidates):,} rulesets."))

        for guess in word_candidates:
            if self.stop_event.is_set():
                return None

            self.attempts += 1
            if guess == self.target:
                return guess

            if self.attempts % 1500 == 0:
                elapsed = max(time.time() - self.start_time, 0.0001)
                self.queue.put(("progress", {
                    "attempts": self.attempts,
                    "current_guess": guess,
                    "elapsed": elapsed
                }))

            if 0 < self.max_attempts <= self.attempts:
                return None

        return None


# ==============================================================================
# MAIN GRAPHICAL USER INTERFACE
# ==============================================================================
class AdvancedCrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Password Cracking & Defense Simulator")
        self.geometry("980x820")
        self.minsize(880, 700)

        # Threading and Communication
        self.update_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.is_running = False

        # Custom Dictionary Store
        self.loaded_dictionary = list(DEFAULT_DICTIONARY)
        self.custom_dict_path = None

        # Setup Fonts & Visual Styles
        self._setup_styles()

        # Build UI Architecture
        self._build_layout()

        # Initial calculation
        self._recalculate_entropy()

        # Start periodic queue polling
        self.after(40, self._poll_queue)

    def _setup_styles(self):
        self.style = ttk.Style(self)
        # Use native 'clam' or 'alt' for consistent styling across platforms
        available_themes = self.style.theme_names()
        if 'clam' in available_themes:
            self.style.theme_use('clam')

        self.font_title = tkFont.Font(family="Segoe UI", size=15, weight="bold")
        self.font_section = tkFont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_regular = tkFont.Font(family="Segoe UI", size=10)
        self.font_mono = tkFont.Font(family="Consolas", size=9)

        # Base style configs
        self.style.configure(".", font=self.font_regular)
        self.style.configure("TLabelframe", padding=10)
        self.style.configure("TLabelframe.Label", font=self.font_section, foreground="#0f3460")
        self.style.configure("TButton", padding=6)
        self.style.configure("Primary.TButton", font=self.font_section, foreground="#ffffff", background="#1a5276")
        self.style.map("Primary.TButton", background=[('active', '#2471a3'), ('pressed', '#154360')])
        self.style.configure("Danger.TButton", font=self.font_section, foreground="#ffffff", background="#922b21")
        self.style.map("Danger.TButton", background=[('active', '#b03a2e'), ('pressed', '#78281f')])
        self.style.configure("Header.TLabel", font=self.font_title, foreground="#1b2631")

    def _build_layout(self):
        # Master Notebook Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Live Simulator
        self.tab_simulator = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_simulator, text=" Cracking Simulator ")

        # Tab 2: Security & Entropy Analyzer
        self.tab_analyzer = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_analyzer, text=" Entropy & Defense Analysis ")

        # Tab 3: Strategy Benchmark Matrix
        self.tab_benchmark = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_benchmark, text=" Strategy Comparison ")

        # Build contents of each tab
        self._build_tab_simulator()
        self._build_tab_analyzer()
        self._build_tab_benchmark()

    # --------------------------------------------------------------------------
    # TAB 1: SIMULATION CONTROLS & MONITOR
    # --------------------------------------------------------------------------
    def _build_tab_simulator(self):
        # Row 1: Target Password & Strategy Setup
        cfg_frame = ttk.LabelFrame(self.tab_simulator, text="Target Configuration & Attack Vector")
        cfg_frame.pack(fill=tk.X, pady=(0, 10))

        # Target entry row
        r1 = ttk.Frame(cfg_frame)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="Test Password:", width=16).pack(side=tk.LEFT)
        self.target_var = tk.StringVar(value="p@ss1")
        self.target_entry = ttk.Entry(r1, textvariable=self.target_var, font=self.font_mono, width=32)
        self.target_entry.pack(side=tk.LEFT, padx=6)
        self.target_var.trace_add("write", lambda *args: self._recalculate_entropy())

        self.show_pass_var = tk.BooleanVar(value=True)
        cb_show = ttk.Checkbutton(r1, text="Show Characters", variable=self.show_pass_var, command=self._toggle_mask)
        cb_show.pack(side=tk.LEFT, padx=8)

        # Strategy selection row
        r2 = ttk.Frame(cfg_frame)
        r2.pack(fill=tk.X, pady=4)
        ttk.Label(r2, text="Attack Strategy:", width=16).pack(side=tk.LEFT)
        self.strategy_var = tk.StringVar(value="Brute-Force (Exact Length)")
        strategies = [
            "Brute-Force (Exact Length)",
            "Brute-Force (Incremental 1..N)",
            "Pure Dictionary Attack",
            "Hybrid / Mutated Dictionary"
        ]
        self.strategy_combo = ttk.Combobox(r2, textvariable=self.strategy_var, values=strategies, state="readonly", width=30)
        self.strategy_combo.pack(side=tk.LEFT, padx=6)
        self.strategy_combo.bind("<<ComboboxSelected>>", self._on_strategy_changed)

        # Max attempts row
        ttk.Label(r2, text="Max Attempts (0=Inf):", width=20).pack(side=tk.LEFT, padx=(15, 0))
        self.max_attempts_var = tk.StringVar(value="5000000")
        self.entry_max = ttk.Entry(r2, textvariable=self.max_attempts_var, width=14)
        self.entry_max.pack(side=tk.LEFT, padx=4)

        # Row 2: Character-set Checklist
        self.charset_frame = ttk.LabelFrame(self.tab_simulator, text="Brute-Force Character Set Space (R)")
        self.charset_frame.pack(fill=tk.X, pady=(0, 10))

        cb_row = ttk.Frame(self.charset_frame)
        cb_row.pack(fill=tk.X, pady=2)

        self.cs_lower_var = tk.BooleanVar(value=True)
        self.cs_upper_var = tk.BooleanVar(value=False)
        self.cs_digits_var = tk.BooleanVar(value=True)
        self.cs_symbols_var = tk.BooleanVar(value=True)

        for text, var in [
            ("Lowercase (a-z)", self.cs_lower_var),
            ("Uppercase (A-Z)", self.cs_upper_var),
            ("Digits (0-9)", self.cs_digits_var),
            ("Symbols (!@#$...)", self.cs_symbols_var)
        ]:
            cb = ttk.Checkbutton(cb_row, text=text, variable=var, command=self._recalculate_entropy)
            cb.pack(side=tk.LEFT, padx=12)

        # Custom Dictionary File Selector (for Dictionary modes)
        self.dict_row = ttk.Frame(self.charset_frame)
        self.dict_row.pack(fill=tk.X, pady=4)
        ttk.Label(self.dict_row, text="Active Wordlist:").pack(side=tk.LEFT)
        self.lbl_dict_status = ttk.Label(self.dict_row, text=f"Embedded Wordlist ({len(self.loaded_dictionary)} words)", foreground="#196f3d")
        self.lbl_dict_status.pack(side=tk.LEFT, padx=8)
        self.btn_load_dict = ttk.Button(self.dict_row, text="Browse Custom .txt...", command=self._load_custom_dictionary)
        self.btn_load_dict.pack(side=tk.LEFT, padx=6)
        self.btn_reset_dict = ttk.Button(self.dict_row, text="Reset Default", command=self._reset_default_dictionary)
        self.btn_reset_dict.pack(side=tk.LEFT, padx=4)

        # Row 3: Action Buttons
        btn_bar = ttk.Frame(self.tab_simulator)
        btn_bar.pack(fill=tk.X, pady=(0, 10))

        self.btn_start = ttk.Button(btn_bar, text="▶ Start Simulation", style="Primary.TButton", command=self._start_simulation)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ttk.Button(btn_bar, text="⏹ Stop Simulation", style="Danger.TButton", state=tk.DISABLED, command=self._stop_simulation)
        self.btn_stop.pack(side=tk.LEFT, padx=8)

        self.btn_clear_log = ttk.Button(btn_bar, text="Clear Logs", command=self._clear_logs)
        self.btn_clear_log.pack(side=tk.LEFT, padx=8)

        # Row 4: Real-time Telemetry Dashboard
        telemetry_frame = ttk.LabelFrame(self.tab_simulator, text="Real-Time Telemetry & Progress")
        telemetry_frame.pack(fill=tk.X, pady=(0, 10))

        t_grid = ttk.Frame(telemetry_frame)
        t_grid.pack(fill=tk.X, pady=2)

        # Column 1
        ttk.Label(t_grid, text="Attempts Completed:", font=self.font_section).grid(row=0, column=0, sticky=tk.W, padx=6, pady=2)
        self.lbl_attempts = ttk.Label(t_grid, text="0", font=self.font_mono)
        self.lbl_attempts.grid(row=0, column=1, sticky=tk.W, padx=6, pady=2)

        ttk.Label(t_grid, text="Elapsed Time:", font=self.font_section).grid(row=1, column=0, sticky=tk.W, padx=6, pady=2)
        self.lbl_elapsed = ttk.Label(t_grid, text="0.000s", font=self.font_mono)
        self.lbl_elapsed.grid(row=1, column=1, sticky=tk.W, padx=6, pady=2)

        # Column 2
        ttk.Label(t_grid, text="Hash / Guess Rate:", font=self.font_section).grid(row=0, column=2, sticky=tk.W, padx=16, pady=2)
        self.lbl_rate = ttk.Label(t_grid, text="0 attempts/sec", font=self.font_mono)
        self.lbl_rate.grid(row=0, column=3, sticky=tk.W, padx=6, pady=2)

        ttk.Label(t_grid, text="Current Candidate:", font=self.font_section).grid(row=1, column=2, sticky=tk.W, padx=16, pady=2)
        self.lbl_candidate = ttk.Label(t_grid, text="None", font=self.font_mono, foreground="#2980b9")
        self.lbl_candidate.grid(row=1, column=3, sticky=tk.W, padx=6, pady=2)

        # Progress bar
        p_row = ttk.Frame(telemetry_frame)
        p_row.pack(fill=tk.X, pady=(6, 2))
        self.prog_bar = ttk.Progressbar(p_row, orient=tk.HORIZONTAL, mode='determinate')
        self.prog_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.lbl_percent = ttk.Label(p_row, text="0.0%", width=8, font=self.font_mono)
        self.lbl_percent.pack(side=tk.RIGHT)

        # Row 5: Scrolled Console Output
        log_frame = ttk.LabelFrame(self.tab_simulator, text="Simulation Audit Console")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.console = scrolledtext.ScrolledText(log_frame, font=self.font_mono, height=9, bg="#17202a", fg="#ecf0f1")
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.tag_config("SUCCESS", foreground="#2ecc71", font=(self.font_mono.actual()["family"], 9, "bold"))
        self.console.tag_config("WARN", foreground="#f39c12")
        self.console.tag_config("ERROR", foreground="#e74c3c", font=(self.font_mono.actual()["family"], 9, "bold"))
        self.console.tag_config("INFO", foreground="#3498db")

    # --------------------------------------------------------------------------
    # TAB 2: ENTROPY, MATHEMATICS & DEFENSE ANALYSIS
    # --------------------------------------------------------------------------
    def _build_tab_analyzer(self):
        f = self.tab_analyzer

        # Section: Information Theory Overview
        info_frame = ttk.LabelFrame(f, text="Mathematical Key-Space & Shannon Entropy")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        grid = ttk.Frame(info_frame)
        grid.pack(fill=tk.X, pady=4)

        ttk.Label(grid, text="Password Length (L):", font=self.font_section).grid(row=0, column=0, sticky=tk.W, padx=6, pady=3)
        self.lbl_ana_len = ttk.Label(grid, text="0", font=self.font_mono)
        self.lbl_ana_len.grid(row=0, column=1, sticky=tk.W, padx=6, pady=3)

        ttk.Label(grid, text="Character Pool Size (R):", font=self.font_section).grid(row=1, column=0, sticky=tk.W, padx=6, pady=3)
        self.lbl_ana_pool = ttk.Label(grid, text="0", font=self.font_mono)
        self.lbl_ana_pool.grid(row=1, column=1, sticky=tk.W, padx=6, pady=3)

        ttk.Label(grid, text="Total Search Space (R^L):", font=self.font_section).grid(row=2, column=0, sticky=tk.W, padx=6, pady=3)
        self.lbl_ana_space = ttk.Label(grid, text="0", font=self.font_mono)
        self.lbl_ana_space.grid(row=2, column=1, sticky=tk.W, padx=6, pady=3)

        ttk.Label(grid, text="Shannon Entropy:", font=self.font_section).grid(row=3, column=0, sticky=tk.W, padx=6, pady=3)
        self.lbl_ana_entropy = ttk.Label(grid, text="0.00 bits", font=self.font_mono)
        self.lbl_ana_entropy.grid(row=3, column=1, sticky=tk.W, padx=6, pady=3)

        ttk.Label(grid, text="Classification:", font=self.font_section).grid(row=4, column=0, sticky=tk.W, padx=6, pady=3)
        self.lbl_ana_strength = ttk.Label(grid, text="Empty", font=(self.font_section.actual()["family"], 10, "bold"))
        self.lbl_ana_strength.grid(row=4, column=1, sticky=tk.W, padx=6, pady=3)

        # Section: Hardware Exhaustion Estimates
        hw_frame = ttk.LabelFrame(f, text="Real-World Hardware Exhaustion Projections (Average Time to Crack)")
        hw_frame.pack(fill=tk.X, pady=(0, 10))

        hw_grid = ttk.Frame(hw_frame)
        hw_grid.pack(fill=tk.X, pady=4)

        ttk.Label(hw_grid, text="Single CPU Core (~100k attempts/sec):", font=self.font_section).grid(row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self.lbl_hw_cpu = ttk.Label(hw_grid, text="N/A", font=self.font_mono)
        self.lbl_hw_cpu.grid(row=0, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(hw_grid, text="Modern High-End GPU (~100M attempts/sec):", font=self.font_section).grid(row=1, column=0, sticky=tk.W, padx=6, pady=4)
        self.lbl_hw_gpu = ttk.Label(hw_grid, text="N/A", font=self.font_mono)
        self.lbl_hw_gpu.grid(row=1, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(hw_grid, text="Enterprise Cluster Rig (~100B attempts/sec):", font=self.font_section).grid(row=2, column=0, sticky=tk.W, padx=6, pady=4)
        self.lbl_hw_cluster = ttk.Label(hw_grid, text="N/A", font=self.font_mono)
        self.lbl_hw_cluster.grid(row=2, column=1, sticky=tk.W, padx=6, pady=4)

        # Defense Guidance
        guide_frame = ttk.LabelFrame(f, text="Security Defense Principles & Takeaways")
        guide_frame.pack(fill=tk.BOTH, expand=True)

        guide_text = (
            "1. Password Length is Exponential: Every additional character multiplies the total\n"
            "   search space by the character pool size R, exponentially increasing cracking time.\n\n"
            "2. Complexity vs. Passphrases: A 16-character passphrase made of simple random words\n"
            "   (e.g., 'correct-horse-battery-staple') provides vastly higher entropy than a complex\n"
            "   7-character password (e.g., 'P@$$w1').\n\n"
            "3. Dictionary Attacks render character complexity useless if the base root word\n"
            "   exists in standard leak repositories (RockYou, SecLists) or uses predictable leetspeak.\n\n"
            "4. Defend with Key Stretching: Production systems must employ slow hashing algorithms\n"
            "   such as Argon2id, bcrypt, or PBKDF2 with high work factors to throttle offline cracking."
        )
        lbl_guide = ttk.Label(guide_frame, text=guide_text, justify=tk.LEFT, font=self.font_regular)
        lbl_guide.pack(fill=tk.BOTH, padx=8, pady=8)

    # --------------------------------------------------------------------------
    # TAB 3: BENCHMARK MATRIX
    # --------------------------------------------------------------------------
    def _build_tab_benchmark(self):
        f = self.tab_benchmark
        ttk.Label(f, text="Strategy Comparison Matrix", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        desc = (
            "This table contrasts attack paradigms against different password compositions.\n"
            "It illustrates why hybrid attacks succeed on human-generated passwords while\n"
            "failing against true high-entropy cryptographic strings."
        )
        ttk.Label(f, text=desc).pack(anchor=tk.W, pady=(0, 10))

        # Comparative Treeview Table
        columns = ("strategy", "best_against", "worst_against", "search_efficiency", "resource_cost")
        self.tree = ttk.Treeview(f, columns=columns, show="headings", height=8)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree.heading("strategy", text="Attack Strategy")
        self.tree.heading("best_against", text="Optimal Target Category")
        self.tree.heading("worst_against", text="Defended By")
        self.tree.heading("search_efficiency", text="Search Efficiency")
        self.tree.heading("resource_cost", text="Computational Cost")

        self.tree.column("strategy", width=190)
        self.tree.column("best_against", width=190)
        self.tree.column("worst_against", width=170)
        self.tree.column("search_efficiency", width=140)
        self.tree.column("resource_cost", width=130)

        data = [
            ("Pure Brute-Force", "Short passwords (< 6 chars)", "Length >= 12 chars", "Very Low (Exhaustive)", "Maximum (High CPU/GPU)"),
            ("Smart Incremental", "Unknown-length short passwords", "Length >= 10 chars", "Low to Moderate", "Extremely High"),
            ("Pure Dictionary", "Unmodified common dictionary words", "Random character sequences", "Extremely High (Targeted)", "Minimal (Fast Lookup)"),
            ("Mutated / Hybrid", "Human passwords with year/symbol tags", "Long random passphrases", "High (Behavioral Heuristics)", "Moderate to High"),
            ("Rainbow Tables", "Unsalted static MD5/SHA1 hashes", "Unique cryptographic salts", "Instantaneous Lookup", "High Storage, Zero CPU")
        ]
        for row in data:
            self.tree.insert("", tk.END, values=row)

    # --------------------------------------------------------------------------
    # GUI HELPER & EVENT HANDLERS
    # --------------------------------------------------------------------------
    def _toggle_mask(self):
        if self.show_pass_var.get():
            self.target_entry.config(show="")
        else:
            self.target_entry.config(show="*")

    def _on_strategy_changed(self, event=None):
        strat = self.strategy_var.get()
        if "Dictionary" in strat:
            self.dict_row.pack(fill=tk.X, pady=4)
        else:
            self.dict_row.pack(fill=tk.X, pady=4)  # Keep visible for awareness

    def _load_custom_dictionary(self):
        filepath = filedialog.askopenfilename(
            title="Select Custom Wordlist (.txt)",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    words = [line.strip() for line in f if line.strip()]
                if not words:
                    messagebox.showwarning("Empty File", "Selected file contains no valid words.")
                    return
                self.loaded_dictionary = words
                self.custom_dict_path = filepath
                fname = os.path.basename(filepath)
                self.lbl_dict_status.config(text=f"{fname} ({len(words):,} words)", foreground="#2980b9")
                self._log(f"[DICT] Loaded custom wordlist: {filepath} ({len(words):,} entries)", "INFO")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load dictionary: {e}")

    def _reset_default_dictionary(self):
        self.loaded_dictionary = list(DEFAULT_DICTIONARY)
        self.custom_dict_path = None
        self.lbl_dict_status.config(text=f"Embedded Wordlist ({len(self.loaded_dictionary)} words)", foreground="#196f3d")
        self._log("[DICT] Reset to embedded built-in dictionary.", "INFO")

    def _build_active_charset(self):
        """Constructs active character string based on user checkboxes without syntax bugs."""
        chars = []
        if self.cs_lower_var.get():
            chars.append(string.ascii_lowercase)
        if self.cs_upper_var.get():
            chars.append(string.ascii_uppercase)
        if self.cs_digits_var.get():
            chars.append(string.digits)
        if self.cs_symbols_var.get():
            chars.append(string.punctuation)

        combined = "".join(chars)
        # Sort and deduplicate safely
        unique_sorted = "".join(sorted(list(set(combined))))
        return unique_sorted

    def _recalculate_entropy(self):
        target = self.target_var.get()
        analysis = SecurityAnalyzer.analyze_password(target)

        # Update Tab 2 Metrics
        self.lbl_ana_len.config(text=str(analysis["length"]))
        self.lbl_ana_pool.config(text=f"{analysis['pool_size']} characters")
        if analysis["search_space"] > 1e15:
            self.lbl_ana_space.config(text=f"{analysis['search_space']:.3e} combinations")
        else:
            self.lbl_ana_space.config(text=f"{analysis['search_space']:,} combinations")

        self.lbl_ana_entropy.config(text=f"{analysis['entropy']} bits")
        self.lbl_ana_strength.config(text=analysis["strength"])

        # Color-code strength label
        color_map = {
            "Very Weak": "#c0392b",
            "Weak": "#d35400",
            "Reasonable": "#f39c12",
            "Strong": "#27ae60",
            "Very Strong": "#1e8449",
            "Empty": "#7f8c8d"
        }
        self.lbl_ana_strength.config(foreground=color_map.get(analysis["strength"], "#000000"))

        # Hardware crack times
        times = SecurityAnalyzer.estimate_crack_times(analysis["search_space"])
        self.lbl_hw_cpu.config(text=times["cpu_time"])
        self.lbl_hw_gpu.config(text=times["gpu_time"])
        self.lbl_hw_cluster.config(text=times["cluster_time"])

    def _log(self, message, tag=""):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        self.console.insert(tk.END, formatted, tag)
        self.console.see(tk.END)

    def _clear_logs(self):
        self.console.delete(1.0, tk.END)

    # --------------------------------------------------------------------------
    # SIMULATION EXECUTION & THREAD DISPATCH
    # --------------------------------------------------------------------------
    def _start_simulation(self):
        if self.is_running:
            return

        target = self.target_var.get()
        if not target:
            messagebox.showerror("Error", "Target password cannot be empty.")
            return

        charset = self._build_active_charset()
        strategy = self.strategy_var.get()

        if "Brute-Force" in strategy and not charset:
            messagebox.showerror("Error", "Please select at least one character set checkbox for Brute-Force.")
            return

        # Validate max attempts
        try:
            max_attempts = int(self.max_attempts_var.get().replace(",", "").strip())
            if max_attempts < 0:
                max_attempts = 0
        except ValueError:
            messagebox.showerror("Error", "Max Attempts must be a valid non-negative integer.")
            return

        # Prepare UI
        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.target_entry.config(state=tk.DISABLED)
        self.strategy_combo.config(state=tk.DISABLED)

        # Reset Telemetry
        self.lbl_attempts.config(text="0")
        self.lbl_elapsed.config(text="0.000s")
        self.lbl_rate.config(text="0 attempts/sec")
        self.lbl_candidate.config(text="Starting...")
        self.prog_bar["value"] = 0
        self.lbl_percent.config(text="0.0%")

        # Instantiate engine and launch thread
        engine = CrackingEngine(
            target_password=target,
            char_set=charset,
            strategy=strategy,
            max_attempts=max_attempts,
            dictionary_list=self.loaded_dictionary,
            update_queue=self.update_queue,
            stop_event=self.stop_event
        )

        self.worker_thread = threading.Thread(target=engine.run, daemon=True)
        self.worker_thread.start()

    def _stop_simulation(self):
        if not self.is_running:
            return
        self._log("[SIGNAL] Stopping simulation requested by operator...", "WARN")
        self.stop_event.set()
        self.btn_stop.config(state=tk.DISABLED)

    def _finalize_ui_state(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.target_entry.config(state=tk.NORMAL)
        self.strategy_combo.config(state="readonly")

    # --------------------------------------------------------------------------
    # THREAD-SAFE QUEUE POLLER
    # --------------------------------------------------------------------------
    def _poll_queue(self):
        """Processes messages emitted by background cracking thread."""
        try:
            while True:
                msg_type, data = self.update_queue.get_nowait()

                if msg_type == "log":
                    self._log(data)

                elif msg_type == "progress":
                    attempts = data["attempts"]
                    guess = data["current_guess"]
                    elapsed = data["elapsed"]
                    rate = attempts / elapsed if elapsed > 0 else 0

                    self.lbl_attempts.config(text=f"{attempts:,}")
                    self.lbl_elapsed.config(text=f"{elapsed:.3f}s")
                    self.lbl_rate.config(text=f"{rate:,.0f} att/sec")
                    self.lbl_candidate.config(text=guess)

                    # Update progress bar if max_attempts is specified
                    try:
                        max_att = int(self.max_attempts_var.get())
                        if max_att > 0:
                            pct = min((attempts / max_att) * 100, 100.0)
                            self.prog_bar["value"] = pct
                            self.lbl_percent.config(text=f"{pct:.1f}%")
                    except ValueError:
                        pass

                elif msg_type == "success":
                    self._finalize_ui_state()
                    pwd = data["password"]
                    attempts = data["attempts"]
                    elapsed = data["elapsed"]
                    rate = attempts / elapsed if elapsed > 0 else 0

                    self.lbl_attempts.config(text=f"{attempts:,}")
                    self.lbl_elapsed.config(text=f"{elapsed:.3f}s")
                    self.lbl_rate.config(text=f"{rate:,.0f} att/sec")
                    self.lbl_candidate.config(text=pwd)
                    self.prog_bar["value"] = 100
                    self.lbl_percent.config(text="100.0%")

                    msg = f"PASSWORD COMPROMISED! Decrypted: '{pwd}' in {elapsed:.4f}s after {attempts:,} attempts."
                    self._log(f"[SUCCESS] {msg}", "SUCCESS")
                    messagebox.showinfo("Simulation Success", msg)

                elif msg_type == "stopped":
                    self._finalize_ui_state()
                    attempts = data["attempts"]
                    elapsed = data["elapsed"]
                    self._log(f"[HALTED] Simulation stopped by user. Attempts made: {attempts:,}. Time: {elapsed:.3f}s", "WARN")

                elif msg_type == "failed":
                    self._finalize_ui_state()
                    attempts = data["attempts"]
                    elapsed = data["elapsed"]
                    self._log(f"[EXHAUSTED] Search finished without match. Attempts: {attempts:,}. Time: {elapsed:.3f}s", "WARN")
                    messagebox.showwarning("Exhausted", "Password was not found within the selected parameters / wordlist.")

                elif msg_type == "error":
                    self._finalize_ui_state()
                    self._log(f"[CRITICAL ERROR] {data}", "ERROR")
                    messagebox.showerror("Execution Error", f"Simulation aborted due to error:\n{data}")

                self.update_queue.task_done()

        except queue.Empty:
            pass

        # Schedule next poll
        self.after(40, self._poll_queue)


# ==============================================================================
# SCRIPT ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    # Prevent scaling glitches on High-DPI Windows monitors
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = AdvancedCrackerApp()
    app.mainloop()
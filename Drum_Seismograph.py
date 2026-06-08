

import tkinter as tk
from tkinter import font as tkfont
import math
import random
import time
import collections
from dataclasses import dataclass, field
from typing import Deque, List, Optional


# =============================================================================
#  PHYSICS & TIMING CONSTANTS
# =============================================================================

SAMPLE_RATE   = 100          # Hz  – simulated samples per second
TICK_MS       = 16           # ~62 fps UI refresh  (16 ms per frame)
SAMPLES_TICK  = max(1, int(SAMPLE_RATE * TICK_MS / 1000))  # samples per frame

VP            = 6.0          # km/s  P-wave
VS            = 3.5          # km/s  S-wave
STATION_DIST  = 80.0         # km    simulated station distance from epicenter


# =============================================================================
#  CANVAS GEOMETRY
# =============================================================================

DRUM_W        = 900          # scrolling waveform canvas width
DRUM_H        = 280          # scrolling waveform canvas height
DRUM_MIDLINE  = DRUM_H // 2  # zero-amplitude baseline pixel
TRACE_SCALE   = 100          # pixels per unit amplitude (before gain)


# =============================================================================
#  COLOUR PALETTE
# =============================================================================

BG_DARK      = "#0a0f14"
BG_MID       = "#0f1923"
BG_PANEL     = "#111d2b"
BG_WIDGET    = "#162232"
PAPER_COL    = "#0b1520"
GRID_DARK    = "#0d1e2e"
GRID_BRIGHT  = "#0f2840"
TRACE_COL    = "#00e5a0"       # default calm trace (green)
TRACE_WATCH  = "#f0c040"
TRACE_WARN   = "#e07020"
TRACE_ALARM  = "#ff2040"
ACCENT       = "#38b6ff"
WHITE        = "#ddeeff"
GREY         = "#5a7a9a"
GREEN        = "#30d060"
YELLOW       = "#d4a020"
RED          = "#ff3040"
ORANGE       = "#e07030"


# =============================================================================
#  DATA CLASSES
# =============================================================================

@dataclass
class QuakeParams:
    magnitude:  float
    depth:      float
    label:      str
    p_delay:    float = field(init=False)   # seconds until P arrives
    s_delay:    float = field(init=False)   # seconds until S arrives

    def __post_init__(self):
        self.p_delay = STATION_DIST / VP
        self.s_delay = STATION_DIST / VS

    @property
    def surface_amplitude(self) -> float:
        """Wadati-attenuated surface amplitude."""
        return self.magnitude * math.exp(-0.10 * self.depth)


@dataclass
class ActiveEvent:
    quake:        QuakeParams
    birth_time:   float          # sim-time when event was injected
    p_fired:      bool = False
    s_fired:      bool = False
    burst_active: bool = False
    burst_elapsed:float = 0.0
    burst_type:   str  = ""      # "P" or "S"


# =============================================================================
#  NOISE GENERATOR
# =============================================================================

class NoiseEngine:
    """
    Layered noise model:
      • Microseismic band  0.1–0.3 Hz  (ocean swell)
      • Cultural noise     1–5   Hz  (traffic, industry)
      • Thermal drift      0.005 Hz  (instrument wander)
    """
    def __init__(self):
        self.t = 0.0
        self.dt = 1.0 / SAMPLE_RATE
        # State for band-limited random walk
        self._bw1 = 0.0   # microseismic integrator
        self._bw2 = 0.0   # cultural integrator

    def next_sample(self) -> float:
        self.t += self.dt

        # Ocean microseism  (0.1–0.2 Hz dominant)
        micro = (0.012 * math.sin(2 * math.pi * 0.14 * self.t) +
                 0.008 * math.sin(2 * math.pi * 0.22 * self.t + 1.1))

        # Cultural / anthropogenic noise  (band-limited random walk)
        self._bw1 += random.gauss(0, 0.0018) - 0.12 * self._bw1
        self._bw2 += random.gauss(0, 0.0006) - 0.35 * self._bw2

        # Thermal drift
        drift = 0.004 * math.sin(2 * math.pi * 0.003 * self.t)

        # Occasional teleseismic micro-tick
        tick = 0.0
        if random.random() < 0.001:
            tick = random.uniform(-0.03, 0.03)

        return micro + self._bw1 + self._bw2 + drift + tick


# =============================================================================
#  WAVEFORM BURST GENERATOR
# =============================================================================

def generate_burst_sample(elapsed: float,
                           amplitude: float,
                           wave_type: str,
                           magnitude: float) -> float:
    """
    Realistic seismic burst: exponential envelope × band-limited oscillation.
    P-wave: high frequency, sharper onset, smaller amplitude.
    S-wave: lower frequency, slower decay, 1.6× larger amplitude.
    """
    if wave_type == "P":
        freq    = 3.5 + magnitude * 0.4
        decay   = 1.2 / max(amplitude, 0.1)
        amp_fac = 0.55
        phase   = 0.0
    else:   # S
        freq    = 1.8 + magnitude * 0.2
        decay   = 0.7 / max(amplitude, 0.1)
        amp_fac = 1.0
        phase   = 0.4

    envelope   = amplitude * amp_fac * math.exp(-decay * elapsed)
    carrier    = math.sin(2 * math.pi * freq * elapsed + phase)
    # Add coda: secondary higher-frequency oscillation
    coda       = 0.25 * math.sin(2 * math.pi * (freq * 1.8) * elapsed)
    noise_frac = 0.12 * random.gauss(0, 1)

    return envelope * (carrier + coda + noise_frac)


# =============================================================================
#  MAIN APPLICATION
# =============================================================================

class DrumSeismograph(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Real-Time Drum Seismograph Simulator")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        # ── Simulation state ──────────────────────────────────────────────
        self.noise     = NoiseEngine()
        self.sim_time  = 0.0             # seconds elapsed
        self.running   = True
        self.paused    = False

        # Sample buffer: stores (amplitude_raw, timestamp) pairs
        self.buffer: Deque[float] = collections.deque()
        self.pixel_buffer: List[float] = []   # one value per canvas column

        # Active earthquake events
        self.events: List[ActiveEvent] = []

        # Gain & threshold
        self.gain_var      = tk.DoubleVar(value=1.0)
        self.threshold_var = tk.DoubleVar(value=0.55)

        # Alarm state
        self.alarm_active    = False
        self.alarm_hold_secs = 0.0
        self.alarm_blink     = False

        # Stats
        self.event_count   = 0
        self.peak_amplitude= 0.0
        self.last_alarm_t  = 0.0

        # Scrolling pixel write head
        self.write_col = 0

        # Canvas line IDs
        self._line_ids: List[int] = []

        self._build_fonts()
        self._build_ui()
        self._init_canvas_lines()
        self._tick()

    # ─────────────────────────────────────────────────────────────────────────
    #  FONTS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_fonts(self):
        self.fn_title = tkfont.Font(family="Courier", size=11, weight="bold")
        self.fn_mono  = tkfont.Font(family="Courier", size=9)
        self.fn_small = tkfont.Font(family="Courier", size=8)
        self.fn_large = tkfont.Font(family="Courier", size=20, weight="bold")
        self.fn_med   = tkfont.Font(family="Courier", size=10, weight="bold")
        self.fn_label = tkfont.Font(family="Courier", size=7)

    # ─────────────────────────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Title bar ─────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_MID, height=36)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◈  REAL-TIME DRUM SEISMOGRAPH SIMULATOR",
                 bg=BG_MID, fg=ACCENT,
                 font=self.fn_title, padx=10).pack(side="left")
        self.lbl_clock = tk.Label(hdr, text="", bg=BG_MID,
                                  fg=GREY, font=self.fn_mono)
        self.lbl_clock.pack(side="right", padx=10)
        self.lbl_net_status = tk.Label(hdr, text="● RECORDING",
                                       bg=BG_MID, fg=GREEN, font=self.fn_mono)
        self.lbl_net_status.pack(side="right", padx=8)

        # ── Drum canvas frame ──────────────────────────────────────────────
        drum_frame = tk.Frame(self, bg=BG_DARK)
        drum_frame.pack(fill="x", padx=6, pady=(4, 0))

        # Amplitude axis labels (left)
        ax_frame = tk.Frame(drum_frame, bg=PAPER_COL, width=30)
        ax_frame.pack(side="left", fill="y")
        ax_frame.pack_propagate(False)
        for label, pos in [("+", 10), ("0", DRUM_MIDLINE - 4), ("−", DRUM_H - 20)]:
            tk.Label(ax_frame, text=label, bg=PAPER_COL,
                     fg=GREY, font=self.fn_label).place(x=8, y=pos)

        self.drum = tk.Canvas(drum_frame, width=DRUM_W, height=DRUM_H,
                              bg=PAPER_COL, highlightthickness=1,
                              highlightbackground=ACCENT)
        self.drum.pack(side="left")
        self._draw_drum_grid()

        # ── Time axis ──────────────────────────────────────────────────────
        time_bar = tk.Frame(self, bg=BG_DARK)
        time_bar.pack(fill="x", padx=6)
        self.lbl_time_axis = tk.Label(time_bar, text="",
                                      bg=BG_DARK, fg=GREY, font=self.fn_label)
        self.lbl_time_axis.pack(side="left", padx=34)

        # ── Main body (controls + readouts) ───────────────────────────────
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=6, pady=4)

        self._build_left_controls(body)
        self._build_center_readouts(body)
        self._build_right_log(body)

    def _draw_drum_grid(self):
        """Permanent gridlines on the drum canvas."""
        c = self.drum
        # Horizontal: amplitude reference lines
        for frac, dash in [(0.25, (3, 6)), (0.5, (2, 3)), (0.75, (3, 6))]:
            y = int(DRUM_H * frac)
            col = GRID_BRIGHT if frac == 0.5 else GRID_DARK
            c.create_line(0, y, DRUM_W, y, fill=col,
                          width=1 if frac == 0.5 else 0.5,
                          dash=dash if frac != 0.5 else ())

        # Threshold lines (will be updated dynamically)
        self.thr_line_hi = c.create_line(
            0, DRUM_MIDLINE, DRUM_W, DRUM_MIDLINE,
            fill=RED, width=1, dash=(4, 4))
        self.thr_line_lo = c.create_line(
            0, DRUM_MIDLINE, DRUM_W, DRUM_MIDLINE,
            fill=RED, width=1, dash=(4, 4))

        # Vertical tick marks every 60 px
        for x in range(0, DRUM_W + 1, 60):
            c.create_line(x, DRUM_H - 10, x, DRUM_H,
                          fill=GRID_BRIGHT, width=1)

        # Write-head indicator
        self.write_head = c.create_line(
            0, 0, 0, DRUM_H, fill=ACCENT, width=1, dash=(2, 2))

    def _init_canvas_lines(self):
        """Pre-create DRUM_W vertical line segments (one per pixel column)."""
        c = self.drum
        self._line_ids = []
        for col in range(DRUM_W):
            lid = c.create_line(col, DRUM_MIDLINE, col, DRUM_MIDLINE,
                                fill=TRACE_COL, width=2, tags="trace")
            self._line_ids.append(lid)
        self.pixel_buffer = [0.0] * DRUM_W

    # ─────────────────────────────────────────────────────────────────────────
    #  CONTROL PANELS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_left_controls(self, parent):
        lp = tk.Frame(parent, bg=BG_PANEL, width=230)
        lp.pack(side="left", fill="y", padx=(0, 4))
        lp.pack_propagate(False)

        def section(text):
            tk.Label(lp, text=f"─── {text} ───",
                     bg=BG_PANEL, fg=ACCENT,
                     font=self.fn_small).pack(pady=(10, 3))

        # ── Earthquake injection buttons ───────────────────────────────────
        section("INJECT EARTHQUAKE")

        quake_presets = [
            ("Micro    Mw 1.5  d=5km",   1.5,  5.0, "MICRO"),
            ("Minor    Mw 3.2  d=10km",  3.2, 10.0, "MINOR"),
            ("Moderate Mw 5.0  d=20km",  5.0, 20.0, "MODERATE"),
            ("Strong   Mw 6.5  d=15km",  6.5, 15.0, "STRONG"),
            ("Major    Mw 7.8  d=30km",  7.8, 30.0, "MAJOR"),
            ("Great    Mw 9.0  d=10km",  9.0, 10.0, "GREAT"),
        ]
        btn_colors = [GREY, GREEN, YELLOW, ORANGE, RED, "#ff00aa"]
        for (label, mag, dep, lbl), col in zip(quake_presets, btn_colors):
            tk.Button(
                lp, text=label, bg=BG_WIDGET, fg=col,
                font=self.fn_small, relief="flat", anchor="w",
                padx=6, pady=3, cursor="hand2",
                activebackground="#1e3050", activeforeground=col,
                command=lambda m=mag, d=dep, lb=lbl:
                    self._inject_quake(m, d, lb)
            ).pack(fill="x", padx=8, pady=1)

        # ── Custom injection ───────────────────────────────────────────────
        section("CUSTOM EVENT")

        row_mag = tk.Frame(lp, bg=BG_PANEL)
        row_mag.pack(fill="x", padx=8)
        tk.Label(row_mag, text="Mag:", bg=BG_PANEL,
                 fg=WHITE, font=self.fn_small, width=5).pack(side="left")
        self.custom_mag = tk.Scale(
            row_mag, from_=0.5, to=9.5, resolution=0.1,
            orient="horizontal", bg=BG_PANEL, fg=WHITE,
            troughcolor=BG_WIDGET, highlightthickness=0, length=150,
            showvalue=True, font=self.fn_label)
        self.custom_mag.set(4.0)
        self.custom_mag.pack(side="left")

        row_dep = tk.Frame(lp, bg=BG_PANEL)
        row_dep.pack(fill="x", padx=8, pady=2)
        tk.Label(row_dep, text="Dep:", bg=BG_PANEL,
                 fg=WHITE, font=self.fn_small, width=5).pack(side="left")
        self.custom_dep = tk.Scale(
            row_dep, from_=2, to=700, resolution=1,
            orient="horizontal", bg=BG_PANEL, fg=WHITE,
            troughcolor=BG_WIDGET, highlightthickness=0, length=150,
            showvalue=True, font=self.fn_label)
        self.custom_dep.set(15)
        self.custom_dep.pack(side="left")

        tk.Button(lp, text="⚡ Fire Custom Event",
                  bg="#2a1520", fg=RED, font=self.fn_small,
                  relief="flat", cursor="hand2", pady=5,
                  command=lambda: self._inject_quake(
                      self.custom_mag.get(),
                      self.custom_dep.get(), "CUSTOM")
                  ).pack(fill="x", padx=8, pady=4)

        # ── Playback controls ──────────────────────────────────────────────
        section("PLAYBACK")
        row_pb = tk.Frame(lp, bg=BG_PANEL)
        row_pb.pack(padx=8)
        self.btn_pause = tk.Button(
            row_pb, text="⏸ PAUSE", bg=BG_WIDGET, fg=YELLOW,
            font=self.fn_small, relief="flat", width=10,
            command=self._toggle_pause)
        self.btn_pause.pack(side="left", padx=2)
        tk.Button(row_pb, text="⏹ CLEAR",
                  bg=BG_WIDGET, fg=GREY, font=self.fn_small,
                  relief="flat", width=9,
                  command=self._clear_trace).pack(side="left", padx=2)

    def _build_center_readouts(self, parent):
        cp = tk.Frame(parent, bg=BG_PANEL)
        cp.pack(side="left", fill="both", expand=True, padx=4)

        def section(text):
            tk.Label(cp, text=f"─── {text} ───",
                     bg=BG_PANEL, fg=ACCENT,
                     font=self.fn_small).pack(pady=(10, 3))

        # ── Alarm indicator ────────────────────────────────────────────────
        self.alarm_frame = tk.Frame(cp, bg=BG_PANEL)
        self.alarm_frame.pack(fill="x", padx=10, pady=4)
        self.alarm_label = tk.Label(
            self.alarm_frame,
            text="● NOMINAL", bg="#0d1e10",
            fg=GREEN, font=self.fn_large,
            relief="solid", bd=1, padx=12, pady=6)
        self.alarm_label.pack(fill="x")

        # ── Gain control ───────────────────────────────────────────────────
        section("GAIN  (Filter Sensitivity)")
        gain_row = tk.Frame(cp, bg=BG_PANEL)
        gain_row.pack(fill="x", padx=10)
        tk.Label(gain_row, text="×0.1", bg=BG_PANEL,
                 fg=GREY, font=self.fn_small).pack(side="left")
        self.gain_slider = tk.Scale(
            gain_row, from_=0.1, to=8.0, resolution=0.05,
            orient="horizontal", variable=self.gain_var,
            bg=BG_PANEL, fg=WHITE, troughcolor=BG_WIDGET,
            highlightthickness=0, length=260,
            command=self._on_gain_change, font=self.fn_label)
        self.gain_slider.pack(side="left", padx=4)
        tk.Label(gain_row, text="×8.0", bg=BG_PANEL,
                 fg=GREY, font=self.fn_small).pack(side="left")

        self.lbl_gain_val = tk.Label(
            cp, text="Gain: ×1.00  (Normal sensitivity)",
            bg=BG_PANEL, fg=ACCENT, font=self.fn_mono)
        self.lbl_gain_val.pack()

        # ── Alarm threshold ────────────────────────────────────────────────
        section("ALARM THRESHOLD")
        thr_row = tk.Frame(cp, bg=BG_PANEL)
        thr_row.pack(fill="x", padx=10)
        tk.Label(thr_row, text="Low", bg=BG_PANEL,
                 fg=GREY, font=self.fn_small).pack(side="left")
        self.thr_slider = tk.Scale(
            thr_row, from_=0.05, to=2.0, resolution=0.01,
            orient="horizontal", variable=self.threshold_var,
            bg=BG_PANEL, fg=WHITE, troughcolor=BG_WIDGET,
            highlightthickness=0, length=260,
            command=self._on_threshold_change, font=self.fn_label)
        self.thr_slider.pack(side="left", padx=4)
        tk.Label(thr_row, text="High", bg=BG_PANEL,
                 fg=GREY, font=self.fn_small).pack(side="left")

        self.lbl_thr_val = tk.Label(
            cp, text="Threshold: 0.55",
            bg=BG_PANEL, fg=RED, font=self.fn_mono)
        self.lbl_thr_val.pack()

        # ── Live readout gauges ────────────────────────────────────────────
        section("LIVE TELEMETRY")
        gauge_frame = tk.Frame(cp, bg=BG_WIDGET,
                               relief="sunken", bd=1)
        gauge_frame.pack(fill="x", padx=10, pady=2)

        gauge_defs = [
            ("Sim Time",    "lbl_simtime",  WHITE),
            ("Sample Rate", "lbl_sps",      ACCENT),
            ("Raw Amp",     "lbl_raw",      GREEN),
            ("Gain Amp",    "lbl_gain_amp", YELLOW),
            ("Peak Amp",    "lbl_peak",     ORANGE),
            ("Threshold",   "lbl_thr",      RED),
            ("Events",      "lbl_evcount",  ACCENT),
            ("Alarms",      "lbl_alarms",   RED),
        ]
        self._gauge_labels = {}
        for row_idx, (key, attr, col) in enumerate(gauge_defs):
            row = tk.Frame(gauge_frame, bg=BG_WIDGET)
            row.pack(fill="x", padx=6, pady=1)
            tk.Label(row, text=f"{key:<14}",
                     bg=BG_WIDGET, fg=GREY,
                     font=self.fn_small, width=14, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="---",
                           bg=BG_WIDGET, fg=col,
                           font=self.fn_mono, anchor="w")
            lbl.pack(side="left")
            self._gauge_labels[attr] = lbl

        self.alarm_count = 0

    def _build_right_log(self, parent):
        rp = tk.Frame(parent, bg=BG_PANEL, width=220)
        rp.pack(side="right", fill="y", padx=(4, 0))
        rp.pack_propagate(False)

        def section(text):
            tk.Label(rp, text=f"─── {text} ───",
                     bg=BG_PANEL, fg=ACCENT,
                     font=self.fn_small).pack(pady=(10, 3))

        # ── Phase arrival ticker ───────────────────────────────────────────
        section("PHASE ARRIVALS")
        self.phase_box = tk.Text(
            rp, height=7, width=26,
            bg=BG_WIDGET, fg=WHITE,
            font=self.fn_small, state="disabled",
            relief="flat", wrap="char")
        self.phase_box.pack(fill="x", padx=6)
        for tag, col in [("P", ACCENT), ("S", YELLOW),
                          ("ALM", RED), ("INFO", GREY)]:
            self.phase_box.tag_config(tag, foreground=col)

        # ── Event log ─────────────────────────────────────────────────────
        section("EVENT LOG")
        log_frame = tk.Frame(rp, bg=BG_WIDGET, relief="sunken", bd=1)
        log_frame.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        sb = tk.Scrollbar(log_frame, bg=BG_WIDGET,
                          troughcolor=BG_PANEL)
        sb.pack(side="right", fill="y")

        self.log_box = tk.Text(
            log_frame, height=30, width=26,
            bg=BG_WIDGET, fg=WHITE,
            font=self.fn_small, state="disabled",
            relief="flat", wrap="word",
            yscrollcommand=sb.set)
        self.log_box.pack(side="left", fill="both", expand=True)
        sb.config(command=self.log_box.yview)

        for tag, col in [
            ("MICRO",    GREY),   ("MINOR",  GREEN),
            ("MODERATE", YELLOW), ("STRONG", ORANGE),
            ("MAJOR",    RED),    ("GREAT",  "#ff00cc"),
            ("CUSTOM",   ACCENT), ("SYS",    GREY),
            ("ALM",      RED),    ("NOMINAL",GREEN),
            ("TIME",     GREY),
        ]:
            self.log_box.tag_config(tag, foreground=col)

        self._log("SYS", "Seismograph online.")
        self._log("SYS", f"Station dist: {STATION_DIST} km")
        self._log("SYS", f"Vp={VP}  Vs={VS} km/s")

    # ─────────────────────────────────────────────────────────────────────────
    #  SIMULATION TICK  (called every TICK_MS milliseconds)
    # ─────────────────────────────────────────────────────────────────────────

    def _tick(self):
        if not self.running:
            return

        if not self.paused:
            dt = TICK_MS / 1000.0
            self.sim_time += dt

            # Generate SAMPLES_TICK samples this frame
            frame_samples: List[float] = []
            for _ in range(SAMPLES_TICK):
                s = self.noise.next_sample()
                s += self._sum_event_contributions()
                frame_samples.append(s)

            # Downsample to single canvas column value (RMS of frame)
            rms_val = math.sqrt(
                sum(v * v for v in frame_samples) / len(frame_samples))
            sign    = 1 if frame_samples[-1] >= 0 else -1
            col_val = sign * rms_val

            # Apply gain
            gained = col_val * self.gain_var.get()

            # Track peak
            if abs(gained) > self.peak_amplitude:
                self.peak_amplitude = abs(gained) * 0.99   # slow decay

            # Check threshold alarm
            self._check_alarm(gained)

            # Push to canvas
            self._push_pixel(gained)
            self._update_gauges(col_val, gained)
            self._update_write_head()
            self._update_threshold_lines()
            self._update_clock_label()

            # Advance and check event P/S arrivals
            self._advance_events(dt)

        # Alarm blink
        if self.alarm_active:
            self._blink_alarm()

        self.after(TICK_MS, self._tick)

    # ─────────────────────────────────────────────────────────────────────────
    #  EVENT ENGINE
    # ─────────────────────────────────────────────────────────────────────────

    def _inject_quake(self, mag: float, dep: float, label: str):
        q   = QuakeParams(magnitude=mag, depth=dep, label=label)
        ev  = ActiveEvent(quake=q, birth_time=self.sim_time)
        self.events.append(ev)
        self.event_count += 1
        self._log(label,
                  f"#{self.event_count} Mw{mag:.1f} "
                  f"d={dep:.0f}km")
        self._log("SYS",
                  f"  P in {q.p_delay:.1f}s  "
                  f"S in {q.s_delay:.1f}s")

    def _advance_events(self, dt: float):
        """Step all active event timers and fire bursts."""
        for ev in self.events[:]:
            age = self.sim_time - ev.birth_time

            # P-wave arrival
            if not ev.p_fired and age >= ev.quake.p_delay:
                ev.p_fired    = True
                ev.burst_active = True
                ev.burst_elapsed = 0.0
                ev.burst_type   = "P"
                self._phase_log("P",
                    f"P  {ev.quake.label[:8]:<8} "
                    f"Mw{ev.quake.magnitude:.1f}")

            # S-wave arrival (starts new burst after P coda)
            if not ev.s_fired and age >= ev.quake.s_delay:
                ev.s_fired      = True
                ev.burst_active = True
                ev.burst_elapsed = 0.0
                ev.burst_type   = "S"
                self._phase_log("S",
                    f"S  {ev.quake.label[:8]:<8} "
                    f"Mw{ev.quake.magnitude:.1f}")

            # Advance burst elapsed time
            if ev.burst_active:
                ev.burst_elapsed += dt
                # Coda duration proportional to magnitude
                coda_dur = ev.quake.magnitude * 3.5
                if ev.burst_elapsed > coda_dur and ev.s_fired:
                    ev.burst_active = False

        # Remove fully-spent events
        self.events = [e for e in self.events
                       if not (e.s_fired and not e.burst_active)]

    def _sum_event_contributions(self) -> float:
        """Sum all active event waveform contributions."""
        total = 0.0
        for ev in self.events:
            if not ev.burst_active:
                continue
            amp = ev.quake.surface_amplitude
            total += generate_burst_sample(
                ev.burst_elapsed,
                amp,
                ev.burst_type,
                ev.quake.magnitude)
        return total

    # ─────────────────────────────────────────────────────────────────────────
    #  CANVAS DRAWING
    # ─────────────────────────────────────────────────────────────────────────

    def _push_pixel(self, gained: float):
        """Write one pixel column on the scrolling drum canvas."""
        c   = self.drum
        col = self.write_col

        # Store value
        self.pixel_buffer[col] = gained

        # Pixel Y coordinate (clamped)
        amp_px = gained * TRACE_SCALE
        amp_px = max(-DRUM_MIDLINE + 4, min(DRUM_MIDLINE - 4, amp_px))
        y_bot  = DRUM_MIDLINE
        y_top  = DRUM_MIDLINE - int(amp_px)

        # Colour by alarm state / amplitude
        thr = self.threshold_var.get() * self.gain_var.get()
        abv = abs(gained)
        if   abv >= thr * 1.5: col_trace = TRACE_ALARM
        elif abv >= thr:       col_trace = TRACE_WARN
        elif abv >= thr * 0.6: col_trace = TRACE_WATCH
        else:                  col_trace = TRACE_COL

        # Update pre-created line segment
        lid = self._line_ids[col]
        c.coords(lid, col, y_bot, col, y_top)
        c.itemconfig(lid, fill=col_trace)

        # Erase the next N columns to create the "write head gap"
        erase_w = 6
        for i in range(1, erase_w + 1):
            ec = (col + i) % DRUM_W
            c.coords(self._line_ids[ec],
                     ec, DRUM_MIDLINE, ec, DRUM_MIDLINE)
            c.itemconfig(self._line_ids[ec], fill=PAPER_COL)

        self.write_col = (col + 1) % DRUM_W

    def _update_write_head(self):
        x = self.write_col
        self.drum.coords(self.write_head, x, 0, x, DRUM_H)

    def _update_threshold_lines(self):
        thr    = self.threshold_var.get()
        gain   = self.gain_var.get()
        # Convert to pixel offset from midline
        thr_px = int(thr * TRACE_SCALE)
        y_hi   = DRUM_MIDLINE - thr_px
        y_lo   = DRUM_MIDLINE + thr_px
        y_hi   = max(2, min(DRUM_H - 2, y_hi))
        y_lo   = max(2, min(DRUM_H - 2, y_lo))
        self.drum.coords(self.thr_line_hi,
                         0, y_hi, DRUM_W, y_hi)
        self.drum.coords(self.thr_line_lo,
                         0, y_lo, DRUM_W, y_lo)

    # ─────────────────────────────────────────────────────────────────────────
    #  ALARM SYSTEM
    # ─────────────────────────────────────────────────────────────────────────

    def _check_alarm(self, gained: float):
        thr = self.threshold_var.get()
        if abs(gained) >= thr:
            if not self.alarm_active:
                self.alarm_count += 1
                self.last_alarm_t = self.sim_time
                self._log("ALM",
                          f"⚠ ALARM #{self.alarm_count} "
                          f"amp={abs(gained):.3f}")
                self._phase_log("ALM",
                                f"ALARM  amp={abs(gained):.3f}")
            self.alarm_active    = True
            self.alarm_hold_secs = 3.0   # hold alarm for 3 s after last trigger
        elif self.alarm_active:
            self.alarm_hold_secs -= TICK_MS / 1000.0
            if self.alarm_hold_secs <= 0:
                self.alarm_active = False
                self.alarm_label.config(
                    text="● NOMINAL", fg=GREEN, bg="#0d1e10")
                self._log("NOMINAL", "Alarm cleared.")

    def _blink_alarm(self):
        self.alarm_blink = not self.alarm_blink
        if self.alarm_blink:
            self.alarm_label.config(
                text="⚠  ALARM  ⚠",
                fg=RED, bg="#2a0808")
        else:
            self.alarm_label.config(
                text="⚠  ALARM  ⚠",
                fg=ORANGE, bg="#1a0505")

    # ─────────────────────────────────────────────────────────────────────────
    #  GAUGE & LABEL UPDATES
    # ─────────────────────────────────────────────────────────────────────────

    def _update_gauges(self, raw: float, gained: float):
        g = self._gauge_labels
        t = self.threshold_var.get()
        g["lbl_simtime"].config( text=f"{self.sim_time:9.2f} s")
        g["lbl_sps"].config(     text=f"{SAMPLE_RATE} Hz")
        g["lbl_raw"].config(     text=f"{raw:+.5f}")
        g["lbl_gain_amp"].config(text=f"{gained:+.5f}")
        g["lbl_peak"].config(    text=f"{self.peak_amplitude:.5f}")
        g["lbl_thr"].config(     text=f"{t:.3f}")
        g["lbl_evcount"].config( text=str(self.event_count))
        g["lbl_alarms"].config(  text=str(self.alarm_count))

    def _update_clock_label(self):
        self.lbl_clock.config(text=time.strftime("UTC  %H:%M:%S"))

    def _on_gain_change(self, val):
        g = float(val)
        desc = ("Ultra-low" if g < 0.3 else "Low"      if g < 0.7 else
                "Normal"    if g < 1.5 else "High"      if g < 3.0 else
                "Very high" if g < 5.0 else "Max")
        self.lbl_gain_val.config(text=f"Gain: ×{g:.2f}  ({desc} sensitivity)")

    def _on_threshold_change(self, val):
        self.lbl_thr_val.config(text=f"Threshold: {float(val):.3f}")

    # ─────────────────────────────────────────────────────────────────────────
    #  PLAYBACK
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.config(text="▶ RESUME", fg=GREEN)
            self.lbl_net_status.config(text="● PAUSED", fg=YELLOW)
        else:
            self.btn_pause.config(text="⏸ PAUSE", fg=YELLOW)
            self.lbl_net_status.config(text="● RECORDING", fg=GREEN)

    def _clear_trace(self):
        c = self.drum
        for col, lid in enumerate(self._line_ids):
            c.coords(lid, col, DRUM_MIDLINE, col, DRUM_MIDLINE)
            c.itemconfig(lid, fill=PAPER_COL)
        self.pixel_buffer = [0.0] * DRUM_W
        self.peak_amplitude = 0.0
        self.write_col  = 0
        self._log("SYS", "Trace cleared.")

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, tag: str, msg: str):
        ts = f"[{self.sim_time:7.1f}s] "
        t  = self.log_box
        t.config(state="normal")
        t.insert("end", ts,  "TIME")
        t.insert("end", msg + "\n", tag)
        t.see("end")
        t.config(state="disabled")

    def _phase_log(self, tag: str, msg: str):
        t = self.phase_box
        t.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        t.insert("end", f"{ts} {msg}\n", tag)
        t.see("end")
        lines = int(t.index("end-1c").split(".")[0])
        if lines > 10:
            t.delete("1.0", f"{lines - 10}.0")
        t.config(state="disabled")


# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app = DrumSeismograph()
    app.mainloop()
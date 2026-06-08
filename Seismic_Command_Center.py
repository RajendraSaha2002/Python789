

import tkinter as tk
from tkinter import ttk, font as tkfont
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# =============================================================================
#  CONSTANTS & PHYSICS
# =============================================================================

VP           = 6.0      # km/s  P-wave velocity
VS           = 3.5      # km/s  S-wave velocity
ANIM_FPS     = 40       # frames per second
ANIM_MS      = 1000 // ANIM_FPS
KM_PER_PX    = 0.8      # map scale: 1 pixel ≈ 0.8 km
DEPTH_FACTOR = 0.12     # how much focal depth damps surface amplitude

# Canvas dimensions
MAP_W, MAP_H = 780, 520

# Colour palette  (dark-theme emergency console)
BG_DARK   = "#0d1117"
BG_MID    = "#161b22"
BG_PANEL  = "#1c2128"
BG_WIDGET = "#21262d"
ACCENT    = "#58a6ff"
GREEN     = "#3fb950"
YELLOW    = "#d29922"
RED       = "#f85149"
ORANGE    = "#e3723a"
WHITE     = "#e6edf3"
GREY      = "#8b949e"
GRID_COL  = "#21262d"

# Station status colours
STATUS_COLORS = {
    "IDLE":    GREEN,
    "WATCH":   YELLOW,
    "WARNING": ORANGE,
    "ALARM":   RED,
}


# =============================================================================
#  DATA CLASSES
# =============================================================================

@dataclass
class Station:
    name:      str
    x:         int       # canvas pixel x
    y:         int       # canvas pixel y
    region:    str
    status:    str = "IDLE"
    p_time:    float = 0.0   # seconds to P-wave arrival
    s_time:    float = 0.0
    p_arrived: bool = False
    s_arrived: bool = False
    canvas_id: int  = 0      # triangle icon canvas tag
    label_id:  int  = 0
    ring_id:   int  = 0      # animated pulse ring
    glow_id:   int  = 0

    @property
    def km_x(self) -> float:
        return self.x * KM_PER_PX

    @property
    def km_y(self) -> float:
        return self.y * KM_PER_PX

    def distance_to_px(self, ex: float, ey: float) -> float:
        return math.hypot(self.x - ex, self.y - ey)

    def distance_km(self, ex: float, ey: float) -> float:
        return self.distance_to_px(ex, ey) * KM_PER_PX


@dataclass
class EarthquakeEvent:
    x:         float
    y:         float
    magnitude: float
    depth:     float
    timestamp: float = field(default_factory=time.time)

    @property
    def energy_joules(self) -> float:
        return 10 ** (1.5 * self.magnitude + 4.8)

    @property
    def surface_amplitude(self) -> float:
        return self.magnitude * math.exp(-DEPTH_FACTOR * self.depth)


# =============================================================================
#  STATION NETWORK  (pixel coordinates on MAP_W×MAP_H canvas)
# =============================================================================

STATION_DATA = [
    ("KYO",  98,  88,  "Kanto North"),
    ("NGN", 240,  65,  "Central Alps"),
    ("SNS", 420,  45,  "Tohoku South"),
    ("AKT", 640,  80,  "Tohoku North"),
    ("AOM", 710, 170,  "Aomori"),
    ("OSK", 130, 210,  "Kinki"),
    ("NGY", 300, 195,  "Chubu"),
    ("SHZ", 440, 215,  "Shizuoka"),
    ("CHB", 590, 200,  "Chiba"),
    ("HRS", 100, 355,  "Chugoku"),
    ("OKY", 200, 380,  "Okayama"),
    ("MTS", 350, 360,  "Shikoku"),
    ("KCH", 490, 340,  "Kochi"),
    ("FKO", 680, 310,  "Fukuoka"),
    ("KMM", 700, 420,  "Kumamoto"),
    ("KGS", 620, 460,  "Kagoshima"),
    ("NGS", 200, 470,  "Nagasaki"),
    ("MSK", 360, 460,  "Miyazaki"),
]


# =============================================================================
#  MAIN APPLICATION
# =============================================================================

class SeismicCommandCenter(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Seismic Command & Simulation Center  v3.0")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        # State
        self.stations:       List[Station]         = []
        self.current_event:  Optional[EarthquakeEvent] = None
        self.anim_running:   bool   = False
        self.anim_elapsed:   float  = 0.0
        self.anim_job:       Optional[str] = None
        self.epicenter_mode: bool   = False
        self.event_count:    int    = 0
        self.eq_x:           float  = MAP_W / 2
        self.eq_y:           float  = MAP_H / 2
        self.p_ring_id:      int    = 0
        self.s_ring_id:      int    = 0
        self.epicenter_id:   int    = 0
        self.shockwave_ids:  List[int] = []
        self.selected_sta:   Optional[Station] = None

        self._build_fonts()
        self._build_layout()
        self._draw_map_base()
        self._draw_stations()
        self._update_clock()

    # ─────────────────────────────────────────────────────────────────────────
    #  FONTS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_fonts(self):
        self.fn_title  = tkfont.Font(family="Courier", size=11, weight="bold")
        self.fn_mono   = tkfont.Font(family="Courier", size=9)
        self.fn_small  = tkfont.Font(family="Courier", size=8)
        self.fn_large  = tkfont.Font(family="Courier", size=14, weight="bold")
        self.fn_label  = tkfont.Font(family="Courier", size=7)
        self.fn_alert  = tkfont.Font(family="Courier", size=9, weight="bold")

    # ─────────────────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self):
        """Three-column layout: left controls │ center map │ right panels."""

        # ── Header bar ───────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_MID, height=38)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="◈  SEISMIC COMMAND & SIMULATION CENTER",
                 bg=BG_MID, fg=ACCENT, font=self.fn_title,
                 padx=10).pack(side="left")
        self.lbl_clock = tk.Label(hdr, text="", bg=BG_MID,
                                  fg=GREY, font=self.fn_mono)
        self.lbl_clock.pack(side="right", padx=10)
        tk.Label(hdr, text="NETWORK: ONLINE  ●",
                 bg=BG_MID, fg=GREEN, font=self.fn_mono).pack(side="right", padx=6)

        # ── Body row ─────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        self._build_left_panel(body)
        self._build_center_map(body)
        self._build_right_panel(body)

    # ── LEFT CONTROL PANEL ───────────────────────────────────────────────────

    def _build_left_panel(self, parent):
        lp = tk.Frame(parent, bg=BG_PANEL, width=200)
        lp.pack(side="left", fill="y", padx=(4, 2), pady=4)
        lp.pack_propagate(False)

        def section(text):
            tk.Label(lp, text=f"─── {text} ───",
                     bg=BG_PANEL, fg=ACCENT,
                     font=self.fn_small).pack(pady=(10, 2))

        # ── Epicenter location ───────────────────────────────────────────────
        section("EPICENTER")
        self.lbl_eq_pos = tk.Label(lp, text="X: ---  Y: ---",
                                   bg=BG_PANEL, fg=WHITE, font=self.fn_mono)
        self.lbl_eq_pos.pack()

        self.btn_pick = tk.Button(
            lp, text="📍 Click Map to Set",
            bg=BG_WIDGET, fg=ACCENT, font=self.fn_small,
            relief="flat", cursor="crosshair",
            command=self._toggle_epicenter_mode)
        self.btn_pick.pack(fill="x", padx=8, pady=3)

        tk.Button(lp, text="🎲 Random Epicenter",
                  bg=BG_WIDGET, fg=WHITE, font=self.fn_small,
                  relief="flat", command=self._random_epicenter
                  ).pack(fill="x", padx=8, pady=2)

        # ── Magnitude slider ─────────────────────────────────────────────────
        section("MAGNITUDE  (Mw)")
        self.var_mag = tk.DoubleVar(value=5.5)
        self.lbl_mag = tk.Label(lp, text="Mw  5.5",
                                bg=BG_PANEL, fg=YELLOW, font=self.fn_large)
        self.lbl_mag.pack()
        tk.Scale(lp, from_=2.0, to=9.0, resolution=0.1,
                 orient="horizontal", variable=self.var_mag,
                 bg=BG_PANEL, fg=WHITE, troughcolor=BG_WIDGET,
                 highlightthickness=0, length=180,
                 command=self._on_mag_change).pack(padx=8)

        # ── Depth slider ─────────────────────────────────────────────────────
        section("FOCAL DEPTH  (km)")
        self.var_depth = tk.DoubleVar(value=10.0)
        self.lbl_depth = tk.Label(lp, text="10 km  |  Shallow",
                                  bg=BG_PANEL, fg=ACCENT, font=self.fn_mono)
        self.lbl_depth.pack()
        tk.Scale(lp, from_=2.0, to=700.0, resolution=1.0,
                 orient="horizontal", variable=self.var_depth,
                 bg=BG_PANEL, fg=WHITE, troughcolor=BG_WIDGET,
                 highlightthickness=0, length=180,
                 command=self._on_depth_change).pack(padx=8)

        # ── Energy readout ───────────────────────────────────────────────────
        section("ENERGY ESTIMATE")
        self.lbl_energy = tk.Label(lp, text="",
                                   bg=BG_PANEL, fg=ORANGE, font=self.fn_small,
                                   wraplength=180, justify="center")
        self.lbl_energy.pack(padx=4)
        self._update_energy_label()

        # ── Wave velocities (display only) ───────────────────────────────────
        section("WAVE VELOCITIES")
        for label, val, col in [("P-wave:", f"{VP} km/s", ACCENT),
                                  ("S-wave:", f"{VS} km/s", YELLOW)]:
            row = tk.Frame(lp, bg=BG_PANEL)
            row.pack(fill="x", padx=10)
            tk.Label(row, text=label, bg=BG_PANEL, fg=GREY,
                     font=self.fn_small, width=9, anchor="w").pack(side="left")
            tk.Label(row, text=val,   bg=BG_PANEL, fg=col,
                     font=self.fn_mono).pack(side="left")

        # ── Trigger button ───────────────────────────────────────────────────
        tk.Frame(lp, bg=BG_PANEL, height=12).pack()
        self.btn_sim = tk.Button(
            lp, text="⚡  SIMULATE SLIP",
            bg="#3d1515", fg=RED, font=self.fn_title,
            relief="flat", cursor="hand2",
            activebackground="#5c1f1f", activeforeground=RED,
            command=self._trigger_simulation, pady=8)
        self.btn_sim.pack(fill="x", padx=8, pady=4)

        tk.Button(lp, text="↺  RESET ALL",
                  bg=BG_WIDGET, fg=GREY, font=self.fn_small,
                  relief="flat", command=self._reset_all
                  ).pack(fill="x", padx=8, pady=2)

        # ── Station counter ──────────────────────────────────────────────────
        section("NETWORK STATUS")
        self.lbl_net = tk.Label(lp, text="", bg=BG_PANEL, fg=WHITE,
                                font=self.fn_small, justify="left")
        self.lbl_net.pack(padx=8, anchor="w")
        self._update_net_status()

    # ── CENTER MAP CANVAS ────────────────────────────────────────────────────

    def _build_center_map(self, parent):
        mid = tk.Frame(parent, bg=BG_DARK)
        mid.pack(side="left", fill="both", expand=True, pady=4)

        # Title strip
        tk.Label(mid, text="REGIONAL SEISMIC MONITORING NETWORK  —  JAPAN AREA",
                 bg=BG_DARK, fg=GREY, font=self.fn_small).pack(pady=(2, 0))

        self.canvas = tk.Canvas(mid, width=MAP_W, height=MAP_H,
                                bg="#0b1520", highlightthickness=1,
                                highlightbackground=ACCENT, cursor="crosshair")
        self.canvas.pack(padx=4, pady=2)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>",   self._on_canvas_hover)

        # Scale bar + legend strip
        bot = tk.Frame(mid, bg=BG_DARK, height=22)
        bot.pack(fill="x", padx=4)
        tk.Label(bot, text=f"Scale: 1 px = {KM_PER_PX} km  │  "
                            f"Map: {MAP_W*KM_PER_PX:.0f} × {MAP_H*KM_PER_PX:.0f} km",
                 bg=BG_DARK, fg=GREY, font=self.fn_small).pack(side="left", padx=6)
        for txt, col in [("▲ Station IDLE", GREEN), ("▲ WATCH", YELLOW),
                          ("▲ WARNING", ORANGE),     ("▲ ALARM", RED)]:
            tk.Label(bot, text=txt, bg=BG_DARK,
                     fg=col, font=self.fn_label).pack(side="left", padx=4)

    # ── RIGHT PANEL ──────────────────────────────────────────────────────────

    def _build_right_panel(self, parent):
        rp = tk.Frame(parent, bg=BG_PANEL, width=220)
        rp.pack(side="right", fill="y", padx=(2, 4), pady=4)
        rp.pack_propagate(False)

        def section(text):
            tk.Label(rp, text=f"─── {text} ───",
                     bg=BG_PANEL, fg=ACCENT,
                     font=self.fn_small).pack(pady=(10, 2))

        # ── Station inspector ────────────────────────────────────────────────
        section("STATION INSPECTOR")
        tk.Label(rp, text="Click a station node ↓",
                 bg=BG_PANEL, fg=GREY, font=self.fn_label).pack()

        self.inspector_frame = tk.Frame(rp, bg=BG_WIDGET,
                                        relief="sunken", bd=1)
        self.inspector_frame.pack(fill="x", padx=6, pady=3)
        self.lbl_insp = tk.Label(
            self.inspector_frame,
            text="No station selected",
            bg=BG_WIDGET, fg=GREY, font=self.fn_small,
            justify="left", padx=6, pady=6, anchor="w")
        self.lbl_insp.pack(fill="x")

        # ── Event ticker ─────────────────────────────────────────────────────
        section("ARRIVAL TICKER")
        ticker_frame = tk.Frame(rp, bg=BG_WIDGET, relief="sunken", bd=1)
        ticker_frame.pack(fill="x", padx=6, pady=2)
        self.ticker_text = tk.Text(
            ticker_frame, height=6, width=26,
            bg=BG_WIDGET, fg=WHITE, font=self.fn_label,
            state="disabled", relief="flat",
            insertbackground=WHITE)
        self.ticker_text.pack()

        # ── Alert log ────────────────────────────────────────────────────────
        section("EVENT ALERT LOG")
        log_frame = tk.Frame(rp, bg=BG_WIDGET, relief="sunken", bd=1)
        log_frame.pack(fill="both", expand=True, padx=6, pady=(2, 4))

        scrollbar = tk.Scrollbar(log_frame, bg=BG_WIDGET,
                                 troughcolor=BG_PANEL)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_frame, height=20, width=26,
            bg=BG_WIDGET, fg=WHITE, font=self.fn_small,
            state="disabled", relief="flat",
            yscrollcommand=scrollbar.set,
            wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Configure text tags for colour coding
        for tag, col in [("IDLE",    GREEN), ("WATCH",   YELLOW),
                          ("WARNING", ORANGE), ("ALARM",   RED),
                          ("INFO",    ACCENT), ("SYSTEM",  GREY),
                          ("TIME",    GREY)]:
            self.log_text.tag_config(tag, foreground=col)

        self._log("SYSTEM", "System initialised.")
        self._log("SYSTEM", f"{len(STATION_DATA)} stations online.")

        # ── Event counter ────────────────────────────────────────────────────
        section("SIMULATION COUNTER")
        self.lbl_counter = tk.Label(rp, text="Events simulated:  0",
                                    bg=BG_PANEL, fg=WHITE, font=self.fn_mono)
        self.lbl_counter.pack()

    # ─────────────────────────────────────────────────────────────────────────
    #  MAP DRAWING
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_map_base(self):
        """Draw permanent background: grid, region shading, ocean texture."""
        c = self.canvas

        # Ocean gradient bands (horizontal stripes to fake depth)
        for i in range(0, MAP_H, 4):
            shade = int(11 + (i / MAP_H) * 8)
            col   = f"#{shade:02x}{shade + 2:02x}{shade + 8:02x}"
            c.create_rectangle(0, i, MAP_W, i + 4,
                                fill=col, outline="", tags="bg")

        # Latitude / longitude grid
        for gx in range(0, MAP_W, 60):
            c.create_line(gx, 0, gx, MAP_H,
                          fill=GRID_COL, width=1, dash=(2, 6), tags="grid")
            c.create_text(gx + 2, MAP_H - 6,
                          text=f"{gx}", fill="#2a3a4a",
                          font=self.fn_label, tags="grid")
        for gy in range(0, MAP_H, 60):
            c.create_line(0, gy, MAP_W, gy,
                          fill=GRID_COL, width=1, dash=(2, 6), tags="grid")
            c.create_text(3, gy + 2,
                          text=f"{gy}", fill="#2a3a4a",
                          font=self.fn_label, anchor="nw", tags="grid")

        # Region label overlays
        regions = [
            (390, 130, "TOHOKU"),
            (550, 230, "KANTO"),
            (220, 270, "CHUBU"),
            (130, 300, "KINKI"),
            (180, 430, "KYUSHU"),
            (380, 410, "SHIKOKU"),
        ]
        for rx, ry, rname in regions:
            c.create_text(rx, ry, text=rname,
                          fill="#1a2a3a", font=("Courier", 18, "bold"),
                          tags="regionlabel")

        # North arrow
        c.create_text(MAP_W - 20, 25, text="N↑",
                      fill=GREY, font=self.fn_mono, tags="compass")

    def _draw_stations(self):
        """Render all station icons (triangles) and name labels."""
        self.stations.clear()
        for name, sx, sy, region in STATION_DATA:
            sta = Station(name=name, x=sx, y=sy, region=region)
            self._draw_station_icon(sta)
            self.stations.append(sta)

    def _draw_station_icon(self, sta: Station):
        c  = self.canvas
        sx, sy = sta.x, sta.y
        col    = STATUS_COLORS[sta.status]
        r      = 7

        # Triangle (upward-pointing ▲)
        pts = [sx, sy - r, sx - r, sy + r, sx + r, sy + r]
        if sta.canvas_id:
            c.coords(sta.canvas_id, *pts)
            c.itemconfig(sta.canvas_id, fill=col, outline=WHITE)
        else:
            sta.canvas_id = c.create_polygon(
                *pts, fill=col, outline=WHITE, width=1.2,
                tags=("station", f"sta_{sta.name}"))
            c.tag_bind(f"sta_{sta.name}", "<Button-1>",
                       lambda e, s=sta: self._select_station(s))
            c.tag_bind(f"sta_{sta.name}", "<Enter>",
                       lambda e, s=sta: self._hover_station(s))

        # Name label
        if sta.label_id:
            c.itemconfig(sta.label_id, fill=col)
        else:
            sta.label_id = c.create_text(
                sx + 10, sy - 4, text=sta.name,
                fill=col, font=self.fn_label,
                anchor="w", tags="stalabel")

    def _refresh_station_icon(self, sta: Station):
        col = STATUS_COLORS[sta.status]
        self.canvas.itemconfig(sta.canvas_id, fill=col)
        self.canvas.itemconfig(sta.label_id,  fill=col)

    # ─────────────────────────────────────────────────────────────────────────
    #  EPICENTER CONTROLS
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_epicenter_mode(self):
        self.epicenter_mode = not self.epicenter_mode
        if self.epicenter_mode:
            self.btn_pick.config(bg="#1a3a1a", fg=GREEN,
                                 text="✔ Click map now…")
            self._log("INFO", "Click map to place epicenter.")
        else:
            self.btn_pick.config(bg=BG_WIDGET, fg=ACCENT,
                                 text="📍 Click Map to Set")

    def _random_epicenter(self):
        self.eq_x = random.randint(60, MAP_W - 60)
        self.eq_y = random.randint(60, MAP_H - 60)
        self._place_epicenter_marker(self.eq_x, self.eq_y)

    def _place_epicenter_marker(self, cx, cy):
        self.eq_x, self.eq_y = cx, cy
        c = self.canvas
        if self.epicenter_id:
            c.delete(self.epicenter_id)
        # Red crosshair star
        r = 10
        self.epicenter_id = c.create_text(
            cx, cy, text="✦",
            fill=RED, font=("Courier", 14, "bold"),
            tags="epicenter")
        self.lbl_eq_pos.config(
            text=f"X: {cx:4d}  Y: {cy:4d}\n"
                 f"≈ ({cx*KM_PER_PX:.0f}, {cy*KM_PER_PX:.0f}) km")

    # ─────────────────────────────────────────────────────────────────────────
    #  SLIDER CALLBACKS
    # ─────────────────────────────────────────────────────────────────────────

    def _on_mag_change(self, val):
        m = float(val)
        self.lbl_mag.config(text=f"Mw  {m:.1f}")
        self._update_energy_label()

    def _on_depth_change(self, val):
        d = float(val)
        label = ("Shallow (<70 km)" if d < 70 else
                 "Intermediate"     if d < 300 else
                 "Deep (>300 km)")
        self.lbl_depth.config(text=f"{d:.0f} km  |  {label}")
        self._update_energy_label()

    def _update_energy_label(self):
        m = self.var_mag.get()
        d = self.var_depth.get()
        e = 10 ** (1.5 * m + 4.8)
        amp = m * math.exp(-DEPTH_FACTOR * d)
        if   e >= 1e18: e_str = f"{e:.2e} J  (Major)"
        elif e >= 1e15: e_str = f"{e:.2e} J  (Strong)"
        elif e >= 1e12: e_str = f"{e:.2e} J  (Moderate)"
        else:           e_str = f"{e:.2e} J  (Minor)"
        self.lbl_energy.config(
            text=f"{e_str}\nSurface amp: {amp:.2f}")

    # ─────────────────────────────────────────────────────────────────────────
    #  SIMULATION TRIGGER
    # ─────────────────────────────────────────────────────────────────────────

    def _trigger_simulation(self):
        if self.anim_running:
            return

        self._reset_stations_only()
        self.event_count += 1
        self.lbl_counter.config(text=f"Events simulated:  {self.event_count}")

        mag   = self.var_mag.get()
        depth = self.var_depth.get()

        self.current_event = EarthquakeEvent(
            x=self.eq_x, y=self.eq_y,
            magnitude=mag, depth=depth)

        self._place_epicenter_marker(self.eq_x, self.eq_y)
        self._precompute_arrivals()
        self._log("INFO", "─" * 24)
        self._log("INFO",
                  f"EVENT #{self.event_count}  Mw {mag:.1f}  "
                  f"D={depth:.0f}km")
        self._log("INFO",
                  f"Epicenter: ({self.eq_x:.0f}, {self.eq_y:.0f}) px")

        # Flash the simulate button
        self.btn_sim.config(bg="#5c1f1f")
        self.after(200, lambda: self.btn_sim.config(bg="#3d1515"))

        self.anim_elapsed = 0.0
        self.anim_running = True
        self._animate_step()

    def _precompute_arrivals(self):
        """Calculate P and S arrival times for all stations."""
        for sta in self.stations:
            dist_km  = sta.distance_km(self.eq_x, self.eq_y)
            sta.p_time   = dist_km / VP
            sta.s_time   = dist_km / VS
            sta.p_arrived = False
            sta.s_arrived = False
            sta.status    = "IDLE"
            self._refresh_station_icon(sta)

    # ─────────────────────────────────────────────────────────────────────────
    #  ANIMATION LOOP
    # ─────────────────────────────────────────────────────────────────────────

    def _animate_step(self):
        if not self.anim_running:
            return

        t   = self.anim_elapsed
        c   = self.canvas
        ev  = self.current_event
        mag = ev.magnitude
        amp = ev.surface_amplitude

        # P-wave ring radius (pixels)
        p_radius_px = (t * VP) / KM_PER_PX
        s_radius_px = (t * VS) / KM_PER_PX

        # Ring width scales with magnitude
        p_width = max(1.5, amp * 0.8)
        s_width = max(2.0, amp * 1.2)

        # Alpha-like effect: fade rings after they leave the map
        p_alpha_col = self._wave_color("P", p_radius_px, mag)
        s_alpha_col = self._wave_color("S", s_radius_px, mag)

        # Draw P-wave ring
        if self.p_ring_id:
            c.delete(self.p_ring_id)
        self.p_ring_id = c.create_oval(
            ev.x - p_radius_px, ev.y - p_radius_px,
            ev.x + p_radius_px, ev.y + p_radius_px,
            outline=p_alpha_col, width=p_width, tags="pwave")

        # Draw S-wave ring
        if self.s_ring_id:
            c.delete(self.s_ring_id)
        self.s_ring_id = c.create_oval(
            ev.x - s_radius_px, ev.y - s_radius_px,
            ev.x + s_radius_px, ev.y + s_radius_px,
            outline=s_alpha_col, width=s_width, tags="swave")

        # Add extra shockwave rings for large quakes (Mw ≥ 6)
        if mag >= 6.0 and int(t * ANIM_FPS) % 8 == 0:
            trail_id = c.create_oval(
                ev.x - p_radius_px + 6, ev.y - p_radius_px + 6,
                ev.x + p_radius_px - 6, ev.y + p_radius_px - 6,
                outline=p_alpha_col, width=0.8,
                dash=(4, 6), tags="shockwave")
            self.shockwave_ids.append(trail_id)
            if len(self.shockwave_ids) > 15:
                c.delete(self.shockwave_ids.pop(0))

        # Check station arrivals
        self._check_arrivals(t)

        # Advance timer
        self.anim_elapsed += 1.0 / ANIM_FPS

        # Stop when both waves have crossed the entire map diagonal
        max_dist = math.hypot(MAP_W, MAP_H) / 2
        if s_radius_px < max_dist * 1.1:
            self.anim_job = self.after(ANIM_MS, self._animate_step)
        else:
            self._finish_animation()

    def _wave_color(self, wave_type: str,
                    radius_px: float, mag: float) -> str:
        """Interpolate ring colour from intense to dim as it expands."""
        max_r  = math.hypot(MAP_W, MAP_H) / 2
        frac   = min(radius_px / max(max_r, 1), 1.0)
        bright = int(255 * (1.0 - frac * 0.75))

        if wave_type == "P":   # Blue → dim blue
            r = int(20  * (1 - frac) + 40  * frac)
            g = int(120 * (1 - frac) + 60  * frac)
            b = bright
        else:                  # Yellow-orange → dim orange
            r = bright
            g = int(200 * (1 - frac) + 80  * frac)
            b = int(20  * (1 - frac) + 10  * frac)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _check_arrivals(self, t: float):
        """Promote station status as P and S waves pass through."""
        for sta in self.stations:
            changed = False

            if not sta.p_arrived and t >= sta.p_time:
                sta.p_arrived = True
                prev = sta.status
                sta.status = "WATCH" if sta.status == "IDLE" else sta.status
                changed = True
                self._ticker_add(f"P  {sta.name}  t={t:.2f}s")
                self._log("WATCH",
                          f"P-wave → {sta.name} "
                          f"(t={t:.2f}s, d={sta.distance_km(self.eq_x,self.eq_y):.1f}km)")

            if not sta.s_arrived and t >= sta.s_time:
                sta.s_arrived = True
                amp = self.current_event.surface_amplitude
                sta.status = ("ALARM"   if amp >= 3.0 else
                              "WARNING" if amp >= 1.5 else
                              "WATCH")
                changed = True
                self._ticker_add(f"S  {sta.name}  t={t:.2f}s")
                self._log(sta.status,
                          f"S-wave → {sta.name} "
                          f"[{sta.status}]  "
                          f"amp={amp:.2f}")
                # Pulse ring on station icon
                self._flash_station(sta)

            if changed:
                self._refresh_station_icon(sta)
                self._update_net_status()
                if self.selected_sta and self.selected_sta.name == sta.name:
                    self._update_inspector(sta)

    def _flash_station(self, sta: Station):
        """Briefly expand a glowing ring around the station on S-arrival."""
        c = self.canvas
        col = STATUS_COLORS[sta.status]
        if sta.glow_id:
            c.delete(sta.glow_id)
        r = 18
        sta.glow_id = c.create_oval(
            sta.x - r, sta.y - r, sta.x + r, sta.y + r,
            outline=col, width=2.5, tags="glow")

        def fade(step=0):
            if step > 6:
                c.delete(sta.glow_id)
                return
            alpha = 1.0 - step / 6.0
            nr    = 18 + step * 5
            c.coords(sta.glow_id,
                     sta.x - nr, sta.y - nr, sta.x + nr, sta.y + nr)
            c.itemconfig(sta.glow_id, width=max(0.5, 2.5 * alpha))
            self.after(50, lambda: fade(step + 1))
        fade()

    def _finish_animation(self):
        self.anim_running = False
        alarm_count = sum(1 for s in self.stations if s.status == "ALARM")
        warn_count  = sum(1 for s in self.stations
                          if s.status in ("WARNING", "WATCH"))
        self._log("INFO",
                  f"Simulation complete.  "
                  f"ALARM: {alarm_count}  WARN: {warn_count}")
        self._update_net_status()

    # ─────────────────────────────────────────────────────────────────────────
    #  STATION INSPECTOR
    # ─────────────────────────────────────────────────────────────────────────

    def _select_station(self, sta: Station):
        self.selected_sta = sta
        self._update_inspector(sta)

    def _hover_station(self, sta: Station):
        if not self.selected_sta:
            self._update_inspector(sta)

    def _update_inspector(self, sta: Station):
        dist = (sta.distance_km(self.eq_x, self.eq_y)
                if self.current_event else 0.0)
        lines = [
            f"Station : {sta.name}",
            f"Region  : {sta.region}",
            f"Status  : {sta.status}",
            f"Pos     : ({sta.x}, {sta.y}) px",
            f"         ({sta.km_x:.0f}, {sta.km_y:.0f}) km",
        ]
        if self.current_event:
            lines += [
                f"Dist    : {dist:.1f} km",
                f"P arr   : {sta.p_time:.3f} s",
                f"S arr   : {sta.s_time:.3f} s",
                f"P-S gap : {sta.s_time - sta.p_time:.3f} s",
            ]
        col = STATUS_COLORS[sta.status]
        self.lbl_insp.config(
            text="\n".join(lines),
            fg=col)

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG / TICKER
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, tag: str, message: str):
        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        t    = self.log_text
        t.config(state="normal")
        t.insert("end", f"[{ts}] ", "TIME")
        t.insert("end", f"{message}\n", tag)
        t.see("end")
        t.config(state="disabled")

    def _ticker_add(self, text: str):
        t = self.ticker_text
        t.config(state="normal")
        t.insert("end", text + "\n")
        t.see("end")
        # Keep only last 8 lines
        lines = int(t.index("end-1c").split(".")[0])
        if lines > 8:
            t.delete("1.0", f"{lines-8}.0")
        t.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    #  NET STATUS
    # ─────────────────────────────────────────────────────────────────────────

    def _update_net_status(self):
        counts: Dict[str, int] = {"IDLE": 0, "WATCH": 0,
                                   "WARNING": 0, "ALARM": 0}
        for sta in self.stations:
            counts[sta.status] += 1
        self.lbl_net.config(
            text=(f"IDLE   : {counts['IDLE']:2d}\n"
                  f"WATCH  : {counts['WATCH']:2d}\n"
                  f"WARNING: {counts['WARNING']:2d}\n"
                  f"ALARM  : {counts['ALARM']:2d}"))

    # ─────────────────────────────────────────────────────────────────────────
    #  CANVAS INTERACTION
    # ─────────────────────────────────────────────────────────────────────────

    def _on_canvas_click(self, event):
        if self.anim_running:
            return
        if self.epicenter_mode:
            self._place_epicenter_marker(event.x, event.y)
            self.epicenter_mode = False
            self.btn_pick.config(bg=BG_WIDGET, fg=ACCENT,
                                 text="📍 Click Map to Set")
            self._log("INFO",
                      f"Epicenter set: ({event.x}, {event.y})")

    def _on_canvas_hover(self, event):
        # Show live coordinates in title bar
        km_x = event.x * KM_PER_PX
        km_y = event.y * KM_PER_PX
        self.title(
            f"Seismic Command Center  │  "
            f"Cursor: ({event.x}, {event.y}) px  "
            f"≈ ({km_x:.0f}, {km_y:.0f}) km")

    # ─────────────────────────────────────────────────────────────────────────
    #  RESET
    # ─────────────────────────────────────────────────────────────────────────

    def _reset_stations_only(self):
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None
        self.anim_running = False
        c = self.canvas
        c.delete("pwave")
        c.delete("swave")
        c.delete("shockwave")
        c.delete("glow")
        for sid in self.shockwave_ids:
            c.delete(sid)
        self.shockwave_ids.clear()
        self.p_ring_id = 0
        self.s_ring_id = 0
        for sta in self.stations:
            sta.status     = "IDLE"
            sta.p_arrived  = False
            sta.s_arrived  = False
            self._refresh_station_icon(sta)
        self._update_net_status()

    def _reset_all(self):
        self._reset_stations_only()
        self.canvas.delete("epicenter")
        self.epicenter_id = 0
        self.lbl_eq_pos.config(text="X: ---  Y: ---")
        self.ticker_text.config(state="normal")
        self.ticker_text.delete("1.0", "end")
        self.ticker_text.config(state="disabled")
        self._log("SYSTEM", "Full reset complete.")
        self._update_net_status()

    # ─────────────────────────────────────────────────────────────────────────
    #  CLOCK
    # ─────────────────────────────────────────────────────────────────────────

    def _update_clock(self):
        self.lbl_clock.config(text=time.strftime("UTC  %Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._update_clock)


# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app = SeismicCommandCenter()
    app.mainloop()
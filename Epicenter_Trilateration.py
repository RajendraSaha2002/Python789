
import math
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.optimize import least_squares
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# =============================================================================
#  PHYSICAL & NETWORK CONSTANTS
# =============================================================================

VP          = 6.0    # km/s  — P-wave velocity  (typical crustal value)
VS          = 3.5    # km/s  — S-wave velocity  (Vp/Vs ≈ 1.73, Poisson solid)
ORIGIN_TIME = 0.0    # seconds — simulated quake origin time

# Wadati relationship: distance = (Ts - Tp) * Vp*Vs / (Vp - Vs)
# This constant combines the velocities into one multiplier
WADATI_K    = (VP * VS) / (VP - VS)   # ≈ 8.4 km/s-equivalent

# =============================================================================
#  STATION NETWORK  (coordinates in km, arbitrary Cartesian frame)
# =============================================================================

@dataclass
class Station:
    name:  str
    x:     float   # km east
    y:     float   # km north

    def distance_to(self, x: float, y: float) -> float:
        return math.hypot(self.x - x, self.y - y)


STATIONS: List[Station] = [
    Station("STA-1  (Northgate)",    x=10.0,  y=20.0),
    Station("STA-2  (Eastfield)",    x=80.0,  y=15.0),
    Station("STA-3  (Highvale)",     x=45.0,  y=90.0),
    # Optional 4th station for overdetermined LSQ solve (uncomment to activate)
    # Station("STA-4  (Westport)",   x=5.0,   y=60.0),
]

GRID_BOUNDS = (0, 100, 0, 100)   # (x_min, x_max, y_min, y_max) km


# =============================================================================
#  DATA CLASSES
# =============================================================================

@dataclass
class ArrivalRecord:
    station:    Station
    t_p:        float   # P-wave arrival time (s)
    t_s:        float   # S-wave arrival time (s)
    ps_gap:     float   # Ts - Tp  (seconds)
    distance:   float   # Wadati-derived distance (km)

    def __str__(self):
        return (f"  {self.station.name:<28} │ "
                f"Tp={self.t_p:7.4f}s  Ts={self.t_s:7.4f}s  "
                f"ΔT={self.ps_gap:6.4f}s  D={self.distance:7.3f} km")


@dataclass
class TrilaterationResult:
    x:          float
    y:           float
    method:     str
    residuals:  List[float] = field(default_factory=list)
    rms_error:  float       = 0.0

    @property
    def coords(self) -> Tuple[float, float]:
        return (self.x, self.y)


# =============================================================================
#  FORWARD MODEL — simulate what stations would record
# =============================================================================

def simulate_earthquake(
    eq_x: float, eq_y: float,
    stations: List[Station],
    noise_std: float = 0.0
) -> List[ArrivalRecord]:
    """
    Given a true epicenter, compute P and S arrival times at every station.
    Optional Gaussian timing noise simulates real digitiser jitter (±noise_std s).
    """
    records = []
    for sta in stations:
        true_dist = sta.distance_to(eq_x, eq_y)

        t_p = ORIGIN_TIME + true_dist / VP
        t_s = ORIGIN_TIME + true_dist / VS

        # Inject measurement noise if requested
        if noise_std > 0.0:
            t_p += random.gauss(0, noise_std)
            t_s += random.gauss(0, noise_std)

        ps_gap   = t_s - t_p
        distance = ps_gap * WADATI_K   # Wadati inversion

        records.append(ArrivalRecord(
            station  = sta,
            t_p      = t_p,
            t_s      = t_s,
            ps_gap   = ps_gap,
            distance = distance,
        ))
    return records


# =============================================================================
#  ANALYTICAL TRILATERATION  (exact 3-circle intersection)
# =============================================================================

def trilaterate_analytical(records: List[ArrivalRecord]) -> Optional[TrilaterationResult]:
    """
    Exact closed-form solution for the intersection of three circles.

    Given circles centred at (x1,y1), (x2,y2), (x3,y3) with radii r1, r2, r3:

    Subtract circle-1 equation from circle-2 → linear equation in x, y
    Subtract circle-1 equation from circle-3 → second linear equation
    Solve the 2x2 linear system using Cramer's rule.

    This works only when exactly 3 stations are used.  For ≥4 stations the
    system is overdetermined and least-squares (below) is more appropriate.
    """
    if len(records) < 3:
        return None

    x1, y1, r1 = records[0].station.x, records[0].station.y, records[0].distance
    x2, y2, r2 = records[1].station.x, records[1].station.y, records[1].distance
    x3, y3, r3 = records[2].station.x, records[2].station.y, records[2].distance

    # Circle equation:  (x - xi)² + (y - yi)² = ri²
    # Expand and subtract C1 from C2:
    #   -2(x2-x1)x  - 2(y2-y1)y  = r2² - r1² - x2² + x1² - y2² + y1²
    # Same for C3 - C1

    A  = -2 * (x2 - x1)
    B  = -2 * (y2 - y1)
    C  =  r2**2 - r1**2 - x2**2 + x1**2 - y2**2 + y1**2

    D  = -2 * (x3 - x1)
    E  = -2 * (y3 - y1)
    F  =  r3**2 - r1**2 - x3**2 + x1**2 - y3**2 + y1**2

    # 2x2 system: [A B; D E] * [x; y] = [C; F]
    det = A * E - B * D
    if abs(det) < 1e-10:
        print("  [WARNING] Stations are collinear — system singular, cannot solve analytically.")
        return None

    x_est = (C * E - B * F) / det
    y_est = (A * F - C * D) / det

    # Compute residuals (how well each circle passes through the solution)
    residuals = [
        abs(math.hypot(x_est - rec.station.x, y_est - rec.station.y) - rec.distance)
        for rec in records
    ]
    rms = math.sqrt(sum(r**2 for r in residuals) / len(residuals))

    return TrilaterationResult(
        x=x_est, y=y_est, method="Analytical (Cramer's Rule)",
        residuals=residuals, rms_error=rms
    )


# =============================================================================
#  LEAST-SQUARES TRILATERATION  (robust, handles N ≥ 3 stations + noise)
# =============================================================================

def trilaterate_lsq(records: List[ArrivalRecord],
                    x0: float = 50.0, y0: float = 50.0) -> TrilaterationResult:
    """
    Non-linear least-squares minimisation of circle-fit residuals.
    Uses scipy.optimize.least_squares with the Levenberg-Marquardt algorithm.

    Objective (per station i):
        f_i(x, y) = sqrt( (x - xi)² + (y - yi)² ) - ri

    This is the signed distance residual: positive if estimated point is
    outside the circle, negative if inside.
    """
    xs = np.array([r.station.x  for r in records])
    ys = np.array([r.station.y  for r in records])
    rs = np.array([r.distance   for r in records])

    def residual_fn(params):
        px, py = params
        return np.sqrt((px - xs)**2 + (py - ys)**2) - rs

    result = least_squares(residual_fn, x0=[x0, y0], method="lm")

    x_est, y_est = result.x
    residuals    = list(np.abs(result.fun))
    rms          = float(np.sqrt(np.mean(np.array(residuals)**2)))

    return TrilaterationResult(
        x=x_est, y=y_est, method="Least-Squares (Levenberg-Marquardt)",
        residuals=residuals, rms_error=rms
    )


# =============================================================================
#  WEIGHTED LEAST-SQUARES  (down-weight noisy stations)
# =============================================================================

def trilaterate_weighted_lsq(records: List[ArrivalRecord],
                               x0=50.0, y0=50.0) -> TrilaterationResult:
    """
    Weighted least-squares: stations with shorter P-S gaps (closer) get
    higher weight because timing errors have a smaller proportional impact.
    Weight = 1 / distance  (closer station → higher SNR → more trustworthy).
    """
    xs = np.array([r.station.x  for r in records])
    ys = np.array([r.station.y  for r in records])
    rs = np.array([r.distance   for r in records])
    ws = 1.0 / np.maximum(rs, 0.1)   # avoid /0

    def residual_fn(params):
        px, py = params
        return ws * (np.sqrt((px - xs)**2 + (py - ys)**2) - rs)

    result   = least_squares(residual_fn, x0=[x0, y0], method="lm")
    x_est, y_est = result.x
    residuals    = list(np.abs(result.fun / ws))   # unscale for display
    rms          = float(np.sqrt(np.mean(np.array(residuals)**2)))

    return TrilaterationResult(
        x=x_est, y=y_est, method="Weighted LSQ (distance-inverse weights)",
        residuals=residuals, rms_error=rms
    )


# =============================================================================
#  CONSOLE REPORT
# =============================================================================

def print_arrival_table(records: List[ArrivalRecord]) -> None:
    print("\n  ARRIVAL RECORD TABLE")
    print("  " + "─" * 66)
    print(f"  {'Station':<28} │ {'Tp':>9}   {'Ts':>9}   {'ΔT':>8}   {'Distance':>9}")
    print("  " + "─" * 66)
    for rec in records:
        print(rec)
    print("  " + "─" * 66)


def print_result(label: str, true_x: float, true_y: float,
                 res: TrilaterationResult) -> None:
    err = math.hypot(res.x - true_x, res.y - true_y)
    print(f"\n  ┌─ {label}")
    print(f"  │  Method    : {res.method}")
    print(f"  │  Estimated : ({res.x:8.4f},  {res.y:8.4f})  km")
    print(f"  │  True      : ({true_x:8.4f},  {true_y:8.4f})  km")
    print(f"  │  Error     : {err:.6f} km  ({err*1000:.2f} m)")
    print(f"  │  RMS resid : {res.rms_error:.6f} km")
    res_str = ", ".join(f"{r:.4f}" for r in res.residuals)
    print(f"  └  Residuals : [{res_str}]  km")


# =============================================================================
#  AUTOMATED SIMULATION TESTER
# =============================================================================

def run_simulation_suite(n_trials: int = 500,
                          noise_std: float = 0.0,
                          verbose: bool = False) -> None:
    """
    Randomly place N earthquakes within the grid, invert them with all three
    solvers, and report accuracy statistics.
    """
    x_min, x_max, y_min, y_max = GRID_BOUNDS
    errors = {"analytical": [], "lsq": [], "wlsq": []}

    for trial in range(n_trials):
        eq_x = random.uniform(x_min + 5, x_max - 5)
        eq_y = random.uniform(y_min + 5, y_max - 5)

        records = simulate_earthquake(eq_x, eq_y, STATIONS, noise_std=noise_std)

        r_an  = trilaterate_analytical(records)
        r_lsq = trilaterate_lsq(records)
        r_wlq = trilaterate_weighted_lsq(records)

        if r_an:
            errors["analytical"].append(math.hypot(r_an.x  - eq_x, r_an.y  - eq_y))
        errors["lsq" ].append(math.hypot(r_lsq.x - eq_x, r_lsq.y - eq_y))
        errors["wlsq"].append(math.hypot(r_wlq.x - eq_x, r_wlq.y - eq_y))

        if verbose and trial < 3:
            print(f"\n  Trial {trial+1}: true=({eq_x:.2f},{eq_y:.2f})  "
                  f"lsq=({r_lsq.x:.4f},{r_lsq.y:.4f})")

    print(f"\n{'='*70}")
    print(f"  SIMULATION SUITE — {n_trials} random trials  "
          f"(timing noise σ = {noise_std:.4f} s)")
    print(f"{'='*70}")
    headers = [("Analytical",   errors["analytical"]),
               ("LSQ",          errors["lsq"]),
               ("Weighted LSQ", errors["wlsq"])]
    for name, errs in headers:
        if errs:
            print(f"  {name:<18}│ "
                  f"Mean={np.mean(errs)*1000:8.3f} m  "
                  f"Max={np.max(errs)*1000:8.3f} m  "
                  f"P95={np.percentile(errs,95)*1000:8.3f} m")
    print(f"{'='*70}\n")

    # Plot error histogram
    fig, ax = plt.subplots(figsize=(9, 4), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    bins = np.linspace(0, max(max(e) for e in errors.values()) * 1000 * 1.05, 40)
    clrs = ["#f9c74f", "#4ecdc4", "#ef476f"]
    for (name, errs), c in zip(headers, clrs):
        if errs:
            ax.hist(np.array(errs) * 1000, bins=bins, alpha=0.65,
                    color=c, label=name, edgecolor="none")
    ax.set_xlabel("Location Error  (metres)", color="white")
    ax.set_ylabel("Count", color="white")
    ax.set_title(f"Trilateration Accuracy — {n_trials} random trials  "
                 f"(noise σ={noise_std:.4f} s)",
                 color="white", fontsize=10)
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#2a2a4a")
    ax.grid(True, color="#2a2a4a", ls="--", alpha=0.5, lw=0.6)
    ax.legend(facecolor="#0f3460", edgecolor="#2a2a4a",
              labelcolor="white", fontsize=9)
    plt.tight_layout()
    plt.show()


# =============================================================================
#  VISUALISATION  — map + circles + comparison
# =============================================================================

def plot_trilateration(
    records:      List[ArrivalRecord],
    true_x:       float,
    true_y:       float,
    res_an:       Optional[TrilaterationResult],
    res_lsq:      TrilaterationResult,
    res_wlsq:     TrilaterationResult,
) -> None:

    fig, axes = plt.subplots(1, 2, figsize=(15, 7), facecolor="#1a1a2e")
    DARK_BG  = "#1a1a2e"
    PANEL_BG = "#16213e"
    GRID_COL = "#2a2a4a"

    # ── Left panel: geographic map ───────────────────────────────────────────
    ax = axes[0]
    ax.set_facecolor(PANEL_BG)
    ax.set_xlim(-5, 110)
    ax.set_ylim(-5, 110)
    ax.set_aspect("equal")
    ax.grid(True, color=GRID_COL, ls="--", alpha=0.5, lw=0.6)
    ax.tick_params(colors="white")
    ax.spines[:].set_color(GRID_COL)
    ax.set_xlabel("East  (km)", color="white", fontsize=10)
    ax.set_ylabel("North  (km)", color="white", fontsize=10)
    ax.set_title("Trilateration Map — Circle Intersections",
                 color="white", fontsize=11, fontweight="bold")

    sta_colors = ["#ffd166", "#06d6a0", "#a8edea", "#ff6b6b"]

    # Draw distance circles
    for rec, sc in zip(records, sta_colors):
        circle = plt.Circle((rec.station.x, rec.station.y),
                             rec.distance, fill=False,
                             color=sc, lw=1.4, alpha=0.6, ls="--")
        ax.add_patch(circle)

    # Draw stations
    for rec, sc in zip(records, sta_colors):
        ax.plot(rec.station.x, rec.station.y, "^", color=sc,
                markersize=11, zorder=5)
        ax.annotate(rec.station.name.split()[0],
                    xy=(rec.station.x, rec.station.y),
                    xytext=(4, 5), textcoords="offset points",
                    color=sc, fontsize=8, fontweight="bold")
        # Distance label on circle
        ang = math.atan2(true_y - rec.station.y, true_x - rec.station.x)
        lx  = rec.station.x + rec.distance * math.cos(ang + 0.35)
        ly  = rec.station.y + rec.distance * math.sin(ang + 0.35)
        ax.annotate(f"{rec.distance:.1f} km",
                    xy=(lx, ly), color=sc, fontsize=7.5, alpha=0.85)

    # True epicenter
    ax.plot(true_x, true_y, "*", color="white", markersize=18, zorder=10,
            markeredgecolor="#ef476f", markeredgewidth=1.5)
    ax.annotate("True\nEpicenter",
                xy=(true_x, true_y), xytext=(8, -14),
                textcoords="offset points", color="white", fontsize=8)

    # Solver estimates
    sol_styles = [
        (res_an,   "#ef476f", "D", "Analytical"),
        (res_lsq,  "#4ecdc4", "s", "LSQ"),
        (res_wlsq, "#f9c74f", "P", "Weighted LSQ"),
    ]
    for res, c, mk, lbl in sol_styles:
        if res is not None:
            ax.plot(res.x, res.y, mk, color=c, markersize=9, zorder=9,
                    label=lbl, markeredgecolor="white", markeredgewidth=0.6)
            # Error line to true position
            ax.plot([res.x, true_x], [res.y, true_y],
                    "--", color=c, lw=0.9, alpha=0.6)

    ax.legend(facecolor="#0f3460", edgecolor=GRID_COL,
              labelcolor="white", fontsize=8, loc="upper left")

    # ── Right panel: residual comparison bar chart ───────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor(PANEL_BG)
    ax2.grid(True, color=GRID_COL, ls="--", alpha=0.5, lw=0.6, axis="y")
    ax2.tick_params(colors="white")
    ax2.spines[:].set_color(GRID_COL)
    ax2.set_title("Per-Station Circle Residuals (km)",
                  color="white", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Station", color="white")
    ax2.set_ylabel("Residual  (km)", color="white")

    n_sta   = len(records)
    labels  = [r.station.name.split()[0] for r in records]
    x_pos   = np.arange(n_sta)
    width   = 0.25
    clrs    = ["#ef476f", "#4ecdc4", "#f9c74f"]
    lbls    = ["Analytical", "LSQ", "Weighted LSQ"]

    for idx, (res, c, lbl) in enumerate(
            [(res_an, clrs[0], lbls[0]),
             (res_lsq, clrs[1], lbls[1]),
             (res_wlsq, clrs[2], lbls[2])]):
        if res is not None:
            bars = ax2.bar(x_pos + idx * width, res.residuals,
                           width=width * 0.85, color=c, alpha=0.85, label=lbl)
            for bar in bars:
                h = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2,
                         h + 0.0002, f"{h:.4f}",
                         ha="center", va="bottom",
                         color=c, fontsize=7.5)

    ax2.set_xticks(x_pos + width)
    ax2.set_xticklabels(labels, color="white", fontsize=9)
    ax2.legend(facecolor="#0f3460", edgecolor=GRID_COL,
               labelcolor="white", fontsize=8)

    # RMS annotation box
    rms_lines = []
    for res, lbl in [(res_an, "Analytical"), (res_lsq, "LSQ"), (res_wlsq, "WLSQ")]:
        if res:
            rms_lines.append(f"{lbl}: RMS={res.rms_error*1000:.4f} m")
    ax2.text(0.98, 0.97, "\n".join(rms_lines),
             transform=ax2.transAxes, color="white", fontsize=8,
             va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#0f3460",
                       edgecolor=GRID_COL, alpha=0.9))

    plt.tight_layout()
    plt.show()


# =============================================================================
#  MAIN
# =============================================================================

def main():
    random.seed(7)   # reproducible demo

    # ── 1. Define a single demo earthquake ──────────────────────────────────
    EQ_X, EQ_Y = 42.7, 53.1   # km — the "hidden" epicenter

    print("\n" + "=" * 70)
    print("  EPICENTER TRILATERATION ENGINE")
    print("=" * 70)
    print(f"\n  Network     : {len(STATIONS)} stations")
    print(f"  Vp / Vs     : {VP} / {VS} km/s")
    print(f"  Wadati K    : {WADATI_K:.4f} km/s")
    print(f"\n  TRUE EPICENTER  →  ({EQ_X}, {EQ_Y})  km  [HIDDEN from solvers]")
    print(f"\n  STATIONS:")
    for s in STATIONS:
        print(f"    {s.name:<28} at ({s.x:.1f}, {s.y:.1f}) km")

    # ── 2. Perfect (noiseless) forward model ────────────────────────────────
    print("\n── CASE 1 : PERFECT ARRIVALS (zero timing noise) ──────────────────")
    records_clean = simulate_earthquake(EQ_X, EQ_Y, STATIONS, noise_std=0.0)
    print_arrival_table(records_clean)

    res_an   = trilaterate_analytical(records_clean)
    res_lsq  = trilaterate_lsq(records_clean)
    res_wlsq = trilaterate_weighted_lsq(records_clean)

    print("\n  INVERSION RESULTS:")
    if res_an:
        print_result("Analytical Solver", EQ_X, EQ_Y, res_an)
    print_result("Least-Squares Solver",          EQ_X, EQ_Y, res_lsq)
    print_result("Weighted Least-Squares Solver",  EQ_X, EQ_Y, res_wlsq)

    plot_trilateration(records_clean, EQ_X, EQ_Y, res_an, res_lsq, res_wlsq)

    # ── 3. Noisy arrivals (simulates real digitiser jitter) ──────────────────
    NOISE = 0.05   # ± 50 ms timing uncertainty
    print(f"\n── CASE 2 : NOISY ARRIVALS (σ = {NOISE} s = ±{NOISE*1000:.0f} ms) ───")
    records_noisy = simulate_earthquake(EQ_X, EQ_Y, STATIONS, noise_std=NOISE)
    print_arrival_table(records_noisy)

    res_an_n   = trilaterate_analytical(records_noisy)
    res_lsq_n  = trilaterate_lsq(records_noisy)
    res_wlsq_n = trilaterate_weighted_lsq(records_noisy)

    print("\n  INVERSION RESULTS (with noise):")
    if res_an_n:
        print_result("Analytical Solver", EQ_X, EQ_Y, res_an_n)
    print_result("Least-Squares Solver",          EQ_X, EQ_Y, res_lsq_n)
    print_result("Weighted Least-Squares Solver",  EQ_X, EQ_Y, res_wlsq_n)

    plot_trilateration(records_noisy, EQ_X, EQ_Y,
                       res_an_n, res_lsq_n, res_wlsq_n)

    # ── 4. Automated 500-trial accuracy suite ────────────────────────────────
    print("\n── CASE 3 : 500-TRIAL SIMULATION SUITE ─────────────────────────────")
    run_simulation_suite(n_trials=500, noise_std=0.0,  verbose=True)
    run_simulation_suite(n_trials=500, noise_std=0.05, verbose=False)


if __name__ == "__main__":
    main()
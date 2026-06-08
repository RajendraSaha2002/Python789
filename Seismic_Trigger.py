
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.signal import butter, filtfilt
from dataclasses import dataclass
from typing import List, Tuple


# =============================================================================
#  CONFIGURATION  ─ tweak these to experiment
# =============================================================================

SAMPLE_RATE      = 100       # Hz  ─ samples per second (typical short-period seismometer)
DURATION         = 180       # seconds of simulated data
NOISE_AMPLITUDE  = 0.05      # background microseismic noise level

# STA / LTA windows
STA_WINDOW_SEC   = 1.0       # Short-Term Average window  (seconds)
LTA_WINDOW_SEC   = 30.0      # Long-Term Average window   (seconds)

# Trigger thresholds
TRIGGER_ON       = 3.5       # ratio must EXCEED this  → event starts
TRIGGER_OFF      = 1.5       # ratio must DROP BELOW this → event ends

# Simulated earthquake catalogue  (time_sec, amplitude, duration_sec, freq_hz)
QUAKE_CATALOGUE = [
    ( 40,  0.8,  8,  3.5),   # small local quake
    ( 85,  2.5, 15,  2.0),   # moderate regional quake
    (120,  0.4,  5,  5.0),   # micro-tremor (might not trigger)
    (150,  1.8, 12,  2.8),   # second moderate quake
]


# =============================================================================
#  DATA CLASSES
# =============================================================================

@dataclass
class TriggerEvent:
    """Stores metadata for each detected seismic event."""
    event_id:    int
    on_time:     float   # seconds from start
    off_time:    float
    peak_ratio:  float
    peak_amp:    float

    @property
    def duration(self) -> float:
        return self.off_time - self.on_time

    def __str__(self):
        return (f"  Event #{self.event_id:02d} │ "
                f"ON={self.on_time:6.1f}s  OFF={self.off_time:6.1f}s  "
                f"Dur={self.duration:5.1f}s  "
                f"Peak Ratio={self.peak_ratio:5.2f}  "
                f"Peak Amp={self.peak_amp:.4f}")


# =============================================================================
#  SIGNAL SYNTHESIS
# =============================================================================

def generate_seismic_signal(
    sample_rate: int,
    duration: int,
    noise_amp: float,
    catalogue: List[Tuple]
) -> np.ndarray:
    """
    Synthesise a realistic continuous seismogram:
      - Gaussian white noise as background microseismic activity
      - Exponentially-decaying sinusoidal bursts for earthquake arrivals
      - Subtle amplitude modulation to simulate ocean microseisms
    """
    n_samples = sample_rate * duration
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Background noise with ocean-microseism modulation (~0.1–0.2 Hz band)
    noise = noise_amp * np.random.randn(n_samples)
    noise *= (1.0 + 0.3 * np.sin(2 * np.pi * 0.12 * t))

    signal = noise.copy()

    for (t_start, amp, dur, freq) in catalogue:
        idx_start = int(t_start * sample_rate)
        idx_end   = min(int((t_start + dur * 3) * sample_rate), n_samples)
        t_local   = t[idx_start:idx_end] - t_start

        # P-wave onset: sharp rise, exponential coda
        envelope  = amp * np.exp(-t_local / (dur * 0.8))
        waveform  = envelope * np.sin(2 * np.pi * freq * t_local)

        # Add a subtle S-wave arrival (larger, slightly delayed)
        s_delay   = int(dur * 0.3 * sample_rate)
        if idx_start + s_delay < idx_end:
            t_s       = t_local[s_delay:]
            s_env     = (amp * 1.6) * np.exp(-t_s / (dur * 0.5))
            s_wave    = s_env * np.sin(2 * np.pi * (freq * 0.7) * t_s + 0.8)
            waveform[s_delay:] += s_wave

        signal[idx_start:idx_end] += waveform

    return t, signal


def bandpass_filter(signal: np.ndarray, lowcut: float, highcut: float,
                    fs: int, order: int = 4) -> np.ndarray:
    """
    Apply a Butterworth bandpass filter (standard practice in seismology).
    Seismologists typically filter 1–10 Hz for local/regional events.
    """
    nyq = 0.5 * fs
    low  = lowcut  / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)


# =============================================================================
#  STA/LTA ALGORITHM  (recursive / causal implementation)
# =============================================================================

def compute_stalta(signal: np.ndarray, fs: int,
                   sta_sec: float, lta_sec: float) -> np.ndarray:
    """
    Classic recursive STA/LTA on the squared signal (energy proxy).

    STA[i] = mean( x²[i-nSTA : i] )
    LTA[i] = mean( x²[i-nLTA : i] )
    ratio   = STA[i] / LTA[i]   (set to 0 during LTA warm-up)

    Uses a fast cumulative-sum trick for O(N) computation — the same
    approach implemented in ObsPy's classic_sta_lta().
    """
    nSTA = int(sta_sec * fs)
    nLTA = int(lta_sec * fs)
    n    = len(signal)

    energy = signal ** 2                      # instantaneous energy

    # Cumulative sum for sliding window means in O(N)
    cumsum = np.cumsum(np.insert(energy, 0, 0))

    sta = np.zeros(n)
    lta = np.zeros(n)

    for i in range(nLTA, n):
        sta[i] = (cumsum[i + 1] - cumsum[max(0, i + 1 - nSTA)]) / nSTA
        lta[i] = (cumsum[i + 1] - cumsum[i + 1 - nLTA])          / nLTA

    # Avoid division by zero during warm-up
    ratio = np.where(lta > 1e-12, sta / lta, 0.0)

    return ratio, sta, lta


# =============================================================================
#  TRIGGER LOGIC  (two-threshold Baer & Kradolfer style)
# =============================================================================

def extract_triggers(ratio: np.ndarray, t: np.ndarray,
                     thr_on: float, thr_off: float) -> List[TriggerEvent]:
    """
    Two-threshold trigger:
      - Armed when ratio rises above TRIGGER_ON
      - Disarmed when ratio falls below TRIGGER_OFF
      - Records peak ratio and peak amplitude within each event window
    """
    events       = []
    in_event     = False
    event_start  = 0.0
    peak_ratio   = 0.0
    event_id     = 0

    for i in range(len(ratio)):
        if not in_event and ratio[i] >= thr_on:
            in_event    = True
            event_start = t[i]
            peak_ratio  = ratio[i]

        elif in_event:
            if ratio[i] > peak_ratio:
                peak_ratio = ratio[i]
            if ratio[i] <= thr_off:
                event_id += 1
                events.append(TriggerEvent(
                    event_id   = event_id,
                    on_time    = event_start,
                    off_time   = t[i],
                    peak_ratio = peak_ratio,
                    peak_amp   = 0.0,          # filled below
                ))
                in_event = False

    # Patch: close any event still open at the end of the record
    if in_event:
        event_id += 1
        events.append(TriggerEvent(
            event_id   = event_id,
            on_time    = event_start,
            off_time   = t[-1],
            peak_ratio = peak_ratio,
            peak_amp   = 0.0,
        ))

    return events


def annotate_peak_amplitudes(events: List[TriggerEvent],
                              signal: np.ndarray,
                              t: np.ndarray) -> None:
    """Fill in peak absolute amplitude for each trigger window."""
    for ev in events:
        mask         = (t >= ev.on_time) & (t <= ev.off_time)
        ev.peak_amp  = float(np.max(np.abs(signal[mask]))) if mask.any() else 0.0


# =============================================================================
#  CONSOLE REPORT
# =============================================================================

def print_report(events: List[TriggerEvent],
                 fs: int, sta_sec: float, lta_sec: float,
                 thr_on: float, thr_off: float) -> None:
    print("\n" + "=" * 70)
    print("  STA/LTA SEISMIC TRIGGER  ─  DETECTION REPORT")
    print("=" * 70)
    print(f"  Sample rate : {fs} Hz")
    print(f"  STA window  : {sta_sec:.1f} s  ({int(sta_sec*fs)} samples)")
    print(f"  LTA window  : {lta_sec:.1f} s  ({int(lta_sec*fs)} samples)")
    print(f"  ON thresh   : {thr_on}")
    print(f"  OFF thresh  : {thr_off}")
    print("-" * 70)

    if not events:
        print("  No triggers detected.")
    else:
        print(f"  {len(events)} event(s) detected:\n")
        for ev in events:
            print(ev)
            strength = ("MICRO" if ev.peak_ratio < 4 else
                        "MINOR" if ev.peak_ratio < 7 else
                        "MODERATE" if ev.peak_ratio < 12 else "STRONG")
            print(f"          └─ Classification: {strength} (ratio={ev.peak_ratio:.2f})")
    print("=" * 70 + "\n")


# =============================================================================
#  VISUALISATION  (4-panel figure)
# =============================================================================

def plot_results(t: np.ndarray,
                 raw: np.ndarray,
                 filtered: np.ndarray,
                 ratio: np.ndarray,
                 events: List[TriggerEvent],
                 thr_on: float,
                 thr_off: float) -> None:

    fig, axes = plt.subplots(4, 1, figsize=(14, 10),
                             sharex=True, facecolor="#1a1a2e")
    fig.suptitle("STA/LTA Seismic Signal Trigger",
                 color="white", fontsize=15, fontweight="bold", y=0.98)

    DARK_BG  = "#1a1a2e"
    PANEL_BG = "#16213e"
    GRID_COL = "#2a2a4a"

    colors = {
        "raw":       "#4ecdc4",
        "filtered":  "#a8edea",
        "sta":       "#ffd166",
        "lta":       "#06d6a0",
        "ratio":     "#f9c74f",
        "threshold": "#ef476f",
        "event":     "#ff6b6b",
    }

    def style_ax(ax, ylabel, ylim=None):
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors="white", labelsize=8)
        ax.set_ylabel(ylabel, color="white", fontsize=9)
        ax.spines[:].set_color(GRID_COL)
        ax.grid(True, color=GRID_COL, linestyle="--", alpha=0.5, linewidth=0.6)
        if ylim:
            ax.set_ylim(ylim)
        for ev in events:
            ax.axvspan(ev.on_time, ev.off_time,
                       alpha=0.18, color=colors["event"], zorder=0)

    # ── Panel 1: Raw seismogram ──────────────────────────────────────────────
    ax1 = axes[0]
    ax1.plot(t, raw, color=colors["raw"], lw=0.6, alpha=0.9)
    style_ax(ax1, "Raw Signal\n(counts)")
    ax1.set_title("Raw Seismogram  (1–10 Hz channel)", color="white",
                  fontsize=9, loc="left", pad=3)

    # ── Panel 2: Bandpass-filtered seismogram ────────────────────────────────
    ax2 = axes[1]
    ax2.plot(t, filtered, color=colors["filtered"], lw=0.8)
    style_ax(ax2, "Filtered\n(1–10 Hz)")
    ax2.set_title("Bandpass-Filtered  (Butterworth 4th order)", color="white",
                  fontsize=9, loc="left", pad=3)

    # ── Panel 3: STA and LTA energy curves ──────────────────────────────────
    ax3 = axes[2]
    # Compute STA and LTA separately for plotting
    nSTA   = int(STA_WINDOW_SEC * SAMPLE_RATE)
    nLTA   = int(LTA_WINDOW_SEC  * SAMPLE_RATE)
    energy = filtered ** 2
    cs     = np.cumsum(np.insert(energy, 0, 0))
    sta_p  = np.array([(cs[i+1] - cs[max(0, i+1-nSTA)]) / nSTA for i in range(len(filtered))])
    lta_p  = np.array([(cs[i+1] - cs[max(0, i+1-nLTA)]) / nLTA
                        if i >= nLTA else 0 for i in range(len(filtered))])

    ax3.plot(t, sta_p, color=colors["sta"],  lw=0.9, label=f"STA ({STA_WINDOW_SEC:.0f}s)")
    ax3.plot(t, lta_p, color=colors["lta"],  lw=1.1, label=f"LTA ({LTA_WINDOW_SEC:.0f}s)")
    style_ax(ax3, "Energy\n(amplitude²)")
    ax3.set_title("STA & LTA Energy Envelopes", color="white", fontsize=9, loc="left", pad=3)
    ax3.legend(facecolor="#0f3460", edgecolor=GRID_COL, labelcolor="white",
               fontsize=8, loc="upper right")

    # ── Panel 4: STA/LTA ratio + thresholds ─────────────────────────────────
    ax4 = axes[3]
    ax4.plot(t, ratio, color=colors["ratio"], lw=0.9, label="STA/LTA ratio")
    ax4.axhline(thr_on,  color=colors["threshold"], lw=1.4, ls="--",
                label=f"ON  threshold = {thr_on}")
    ax4.axhline(thr_off, color="#98c1d9",            lw=1.0, ls=":",
                label=f"OFF threshold = {thr_off}")
    style_ax(ax4, "STA/LTA\nRatio")
    ax4.set_xlabel("Time  (seconds)", color="white", fontsize=10)
    ax4.set_title("Trigger Ratio  ─  coloured spans = detected events",
                  color="white", fontsize=9, loc="left", pad=3)
    ax4.legend(facecolor="#0f3460", edgecolor=GRID_COL, labelcolor="white",
               fontsize=8, loc="upper right")

    # ── Annotate event markers ───────────────────────────────────────────────
    for ev in events:
        for ax in axes:
            ax.axvline(ev.on_time,  color="#ef476f", lw=1.2, alpha=0.85, ls="-")
            ax.axvline(ev.off_time, color="#06d6a0", lw=1.0, alpha=0.7,  ls="--")
        ax1.annotate(f"E{ev.event_id}",
                     xy=(ev.on_time, ax1.get_ylim()[1] * 0.85),
                     fontsize=8, color="#ef476f", fontweight="bold",
                     ha="center")

    # ── Legend patch for event spans ────────────────────────────────────────
    ev_patch   = mpatches.Patch(color=colors["event"], alpha=0.4, label="Triggered window")
    on_line    = plt.Line2D([0], [0], color="#ef476f", lw=1.2, label="Trigger ON")
    off_line   = plt.Line2D([0], [0], color="#06d6a0", lw=1.0, ls="--", label="Trigger OFF")
    fig.legend(handles=[ev_patch, on_line, off_line],
               loc="lower center", ncol=3, facecolor="#0f3460",
               edgecolor=GRID_COL, labelcolor="white", fontsize=8,
               bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.subplots_adjust(hspace=0.35)
    plt.show()


# =============================================================================
#  MAIN
# =============================================================================

def main():
    print("\n[1/5]  Synthesising seismic waveform ...")
    np.random.seed(42)       # reproducible noise
    t, raw_signal = generate_seismic_signal(
        SAMPLE_RATE, DURATION, NOISE_AMPLITUDE, QUAKE_CATALOGUE
    )

    print("[2/5]  Applying 1–10 Hz bandpass filter ...")
    filtered = bandpass_filter(raw_signal, lowcut=1.0, highcut=10.0, fs=SAMPLE_RATE)

    print("[3/5]  Computing STA/LTA ratio ...")
    ratio, _, _ = compute_stalta(filtered, SAMPLE_RATE,
                                 STA_WINDOW_SEC, LTA_WINDOW_SEC)

    print("[4/5]  Extracting triggers ...")
    events = extract_triggers(ratio, t, TRIGGER_ON, TRIGGER_OFF)
    annotate_peak_amplitudes(events, filtered, t)

    print_report(events, SAMPLE_RATE, STA_WINDOW_SEC, LTA_WINDOW_SEC,
                 TRIGGER_ON, TRIGGER_OFF)

    print("[5/5]  Rendering 4-panel plot ...")
    plot_results(t, raw_signal, filtered, ratio, events, TRIGGER_ON, TRIGGER_OFF)


if __name__ == "__main__":
    main()
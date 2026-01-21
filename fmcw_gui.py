import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import chirp
from scipy.fft import rfft, rfftfreq


class FMCWRadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FMCW Radar Simulator (Adaptive Cruise Control)")
        self.root.geometry("1100x800")

        # --- Radar Configuration ---
        self.c = 3e8  # Speed of Light
        self.sample_rate = 1e6  # 1 MHz sampling
        self.chirp_duration = 0.001  # 1 ms

        # --- Variables ---
        self.var_dist = tk.DoubleVar(value=150.0)
        self.var_bw = tk.DoubleVar(value=150.0)  # MHz

        # --- Layout ---
        self.create_controls()
        self.create_plots()
        self.update_simulation()

    def create_controls(self):
        panel = ttk.LabelFrame(self.root, text="Radar Controls", padding="10")
        panel.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Grid Setup
        panel.columnconfigure(1, weight=1)

        # Distance Slider
        ttk.Label(panel, text="Target Distance (m):").grid(row=0, column=0, sticky="w")
        s_dist = ttk.Scale(panel, from_=10, to=400, variable=self.var_dist,
                           command=lambda e: self.update_simulation())
        s_dist.grid(row=0, column=1, sticky="ew", padx=10)
        self.lbl_dist = ttk.Label(panel, text="150 m")
        self.lbl_dist.grid(row=0, column=2, padx=10)

        # Bandwidth Slider
        ttk.Label(panel, text="Chirp Bandwidth (MHz):").grid(row=1, column=0, sticky="w")
        s_bw = ttk.Scale(panel, from_=50, to=300, variable=self.var_bw,
                         command=lambda e: self.update_simulation())
        s_bw.grid(row=1, column=1, sticky="ew", padx=10)
        self.lbl_bw = ttk.Label(panel, text="150 MHz")
        self.lbl_bw.grid(row=1, column=2, padx=10)

        # Info Box
        self.lbl_info = ttk.Label(panel, text="Calculating...", font=("Courier", 10), foreground="blue")
        self.lbl_info.grid(row=2, column=0, columnspan=3, pady=(10, 0))

    def create_plots(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.fig.subplots_adjust(hspace=0.4)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_simulation(self):
        # 1. Get User Inputs
        dist = self.var_dist.get()
        bw_mhz = self.var_bw.get()
        bw = bw_mhz * 1e6

        self.lbl_dist.config(text=f"{dist:.1f} m")
        self.lbl_bw.config(text=f"{bw_mhz:.0f} MHz")

        # 2. Physics & Calc
        tau = 2 * dist / self.c
        slope = bw / self.chirp_duration

        # Theoretical Beat Freq
        f_beat_theory = slope * tau

        self.lbl_info.config(
            text=f"Round Trip: {tau * 1e6:.2f} µs | Beat Freq: {f_beat_theory / 1000:.2f} kHz"
        )

        # 3. Generate Signals
        num_samples = int(self.sample_rate * self.chirp_duration)
        t = np.linspace(0, self.chirp_duration, num_samples)

        # Tx (Baseband sweep 0 -> BW)
        sig_tx = chirp(t, f0=0, t1=self.chirp_duration, f1=bw, method='linear')

        # Rx (Delayed)
        # We calculate the phase of the delayed signal
        # The signal is 0 before time 'tau'
        t_delay = t - tau
        sig_rx = np.zeros_like(t)

        # Only compute chirp for t > tau
        mask = t > tau
        sig_rx[mask] = chirp(t_delay[mask], f0=0, t1=self.chirp_duration, f1=bw, method='linear')

        # Add Noise
        noise = np.random.normal(0, 0.2, size=len(t))
        sig_rx += noise

        # 4. Mix & FFT
        sig_mix = sig_tx * sig_rx

        # Cut off the start (invalid mixing region)
        valid_start = int(tau * self.sample_rate) + 20
        if valid_start < len(sig_mix):
            mix_valid = sig_mix[valid_start:]

            # FFT
            yf = rfft(mix_valid)
            xf = rfftfreq(len(mix_valid), 1 / self.sample_rate)

            mag = np.abs(yf)

            # Peak Finding
            idx = np.argmax(mag)
            f_measured = xf[idx]
            d_measured = (self.c * self.chirp_duration * f_measured) / (2 * bw)
        else:
            # Target too far
            xf = np.linspace(0, 100, 100)
            mag = np.zeros(100)
            d_measured = 0.0

        # 5. Plotting
        self.ax1.clear()
        self.ax2.clear()

        # Plot 1: The Sawtooth / Chirp Visual
        self.ax1.set_title("FMCW Chirp Pattern (Frequency vs Time)")
        # We plot the frequency lines mathmatically rather than the raw signal for clarity
        self.ax1.plot(t * 1000, np.linspace(0, bw_mhz, len(t)), 'b', label="Tx (Sent)", linewidth=2)

        # The Rx line is shifted right by tau
        rx_time = (t + tau) * 1000
        self.ax1.plot(rx_time, np.linspace(0, bw_mhz, len(t)), 'r--', label="Rx (Echo)", linewidth=2)

        # Draw the vertical arrow representing the Beat Frequency (difference)
        mid_idx = len(t) // 2
        mid_t = t[mid_idx] * 1000
        mid_f_tx = (mid_idx / len(t)) * bw_mhz
        mid_f_rx = mid_f_tx  # Approx for visual

        self.ax1.annotate(f"Delay $\\tau$", xy=(mid_t, mid_f_tx), xytext=(mid_t + (tau * 1e6) / 100, mid_f_tx),
                          arrowprops=dict(arrowstyle='<->', color='green'))

        self.ax1.set_xlabel("Time (ms)")
        self.ax1.set_ylabel("Frequency (MHz)")
        self.ax1.set_xlim(0, self.chirp_duration * 1000 + 0.2)
        self.ax1.legend(loc="lower right")
        self.ax1.grid(True, alpha=0.3)

        # Plot 2: Range Profile (FFT)
        self.ax2.set_title(f"Range Profile (FFT) - Detected: {d_measured:.2f} m")

        # X-axis as Distance
        x_dist = xf * (self.c * self.chirp_duration) / (2 * bw)

        norm_mag = mag / (np.max(mag) + 1e-9)
        self.ax2.plot(x_dist, norm_mag, color='purple', label="Reflected Energy")
        self.ax2.fill_between(x_dist, norm_mag, color='purple', alpha=0.2)

        self.ax2.axvline(dist, color='green', linestyle='--', alpha=0.5, label="Actual Target")
        self.ax2.axvline(d_measured, color='red', linestyle=':', linewidth=2, label="Radar Estimate")

        self.ax2.set_xlim(0, 400)  # Max range view
        self.ax2.set_xlabel("Distance (meters)")
        self.ax2.set_ylabel("Signal Strength")
        self.ax2.legend()
        self.ax2.grid(True, alpha=0.3)

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = FMCWRadarGUI(root)
    root.mainloop()
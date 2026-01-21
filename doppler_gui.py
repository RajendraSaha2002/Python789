import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.fft import rfft, rfftfreq


class DopplerRadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Doppler Radar Simulator")
        self.root.geometry("1000x800")

        # --- Constants ---
        self.SAMPLE_RATE = 44100
        self.DURATION = 0.5
        self.C_WAVE = 343.0  # Speed of sound (m/s) for visualization

        # --- Control Variables ---
        self.var_speed = tk.DoubleVar(value=60.0)  # km/h
        self.var_tx_freq = tk.DoubleVar(value=1000.0)  # Hz
        self.var_noise = tk.DoubleVar(value=0.2)  # Noise level

        # --- Layout Setup ---
        self.create_controls()
        self.create_plots()

        # Initial Plot
        self.update_simulation()

    def create_controls(self):
        control_frame = ttk.LabelFrame(self.root, text="Radar Gun Controls", padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Grid config
        control_frame.columnconfigure(1, weight=1)

        # Target Speed Slider
        ttk.Label(control_frame, text="Target Speed (km/h):").grid(row=0, column=0, sticky="w")
        scale_speed = ttk.Scale(control_frame, from_=-150, to=150, variable=self.var_speed,
                                command=lambda e: self.update_simulation())
        scale_speed.grid(row=0, column=1, sticky="ew", padx=10)
        self.lbl_speed_val = ttk.Label(control_frame, text="60 km/h")
        self.lbl_speed_val.grid(row=0, column=2, padx=5)

        # Tx Frequency Slider
        ttk.Label(control_frame, text="Transmit Freq (Hz):").grid(row=1, column=0, sticky="w")
        scale_freq = ttk.Scale(control_frame, from_=500, to=2000, variable=self.var_tx_freq,
                               command=lambda e: self.update_simulation())
        scale_freq.grid(row=1, column=1, sticky="ew", padx=10)
        self.lbl_freq_val = ttk.Label(control_frame, text="1000 Hz")
        self.lbl_freq_val.grid(row=1, column=2, padx=5)

        # Noise Slider
        ttk.Label(control_frame, text="Signal Noise:").grid(row=2, column=0, sticky="w")
        scale_noise = ttk.Scale(control_frame, from_=0, to=2.0, variable=self.var_noise,
                                command=lambda e: self.update_simulation())
        scale_noise.grid(row=2, column=1, sticky="ew", padx=10)

        # Results Display
        self.result_frame = ttk.LabelFrame(self.root, text="Radar Readout", padding="10")
        self.result_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        self.lbl_readout = ttk.Label(self.result_frame, text="READY", font=("Courier", 16, "bold"), foreground="green")
        self.lbl_readout.pack()

    def create_plots(self):
        # Create Matplotlib Figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.fig.subplots_adjust(hspace=0.4)

        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_simulation(self):
        # 1. Get Values
        v_kph = self.var_speed.get()
        f_tx = self.var_tx_freq.get()
        noise_level = self.var_noise.get()

        # Update labels
        self.lbl_speed_val.config(text=f"{v_kph:.1f} km/h")
        self.lbl_freq_val.config(text=f"{int(f_tx)} Hz")

        # Convert speed to m/s
        # Note: If speed is negative (moving away), freq decreases
        v_ms = v_kph * (1000 / 3600)

        # 2. Physics Calculation (Doppler)
        # Formula: f_rx = f_tx * (c + v) / (c - v)
        # Note: We assume radar is stationary.
        # v_ms > 0: Approaching, v_ms < 0: Receding
        if self.C_WAVE - v_ms == 0: v_ms += 0.001  # Avoid div by zero

        f_rx_theoretical = f_tx * (self.C_WAVE + v_ms) / (self.C_WAVE - v_ms)

        # 3. Generate Signals
        t = np.linspace(0, self.DURATION, int(self.SAMPLE_RATE * self.DURATION), endpoint=False)

        # Tx Signal (Reference)
        sig_tx = np.sin(2 * np.pi * f_tx * t)

        # Rx Signal (Shifted + Noise)
        noise = np.random.normal(0, noise_level, size=t.shape)
        sig_rx = np.sin(2 * np.pi * f_rx_theoretical * t) + noise

        # 4. Perform FFT
        N = len(sig_rx)
        yf = rfft(sig_rx)
        xf = rfftfreq(N, 1 / self.SAMPLE_RATE)

        # Find Peak
        mag = np.abs(yf)
        idx_peak = np.argmax(mag)
        f_measured = xf[idx_peak]

        # 5. Calculate Speed from Spectrum
        # Reverse Doppler: v = c * (f_rx - f_tx) / (f_rx + f_tx)
        v_measured_ms = self.C_WAVE * (f_measured - f_tx) / (f_measured + f_tx)
        v_measured_kph = v_measured_ms * 3.6

        # Update Readout Text
        diff = abs(v_kph - v_measured_kph)
        status = "LOCKED" if diff < 5.0 else "SEARCHING..."
        color = "green" if diff < 5.0 else "red"

        self.lbl_readout.config(
            text=f"DETECTED: {v_measured_kph:.2f} km/h  |  SHIFT: {f_measured - f_tx:.1f} Hz  |  STATUS: {status}",
            foreground=color
        )

        # 6. Update Plots
        self.ax1.clear()
        self.ax2.clear()

        # Time Domain (Zoomed)
        zoom = 500  # First 500 samples
        self.ax1.set_title("Time Domain (First 10ms)")
        self.ax1.plot(t[:zoom] * 1000, sig_tx[:zoom], label="Tx (Transmitted)", color="blue", alpha=0.6)
        self.ax1.plot(t[:zoom] * 1000, sig_rx[:zoom], label="Rx (Received)", color="red", linestyle="--", alpha=0.8)
        self.ax1.set_xlabel("Time (ms)")
        self.ax1.set_ylabel("Amplitude")
        self.ax1.legend(loc="upper right")
        self.ax1.grid(True, alpha=0.3)

        # Frequency Domain
        self.ax2.set_title("Frequency Domain (FFT Spectrum)")

        # Normalize for plotting
        norm_mag = mag / (np.max(mag) + 1e-6)
        self.ax2.plot(xf, norm_mag, color="purple", label="Spectrum")

        # Highlight Tx and Rx Frequencies
        self.ax2.axvline(f_tx, color="blue", linestyle=":", alpha=0.5, label="Base Freq")
        self.ax2.axvline(f_measured, color="red", linestyle="--", alpha=0.5, label="Detected Peak")

        # Zoom FFT to relevant range
        center = (f_tx + f_measured) / 2
        span = max(abs(f_tx - f_measured) * 2, 500)  # Ensure window is wide enough
        self.ax2.set_xlim(max(0, center - span), center + span)

        self.ax2.set_xlabel("Frequency (Hz)")
        self.ax2.set_ylabel("Magnitude")
        self.ax2.legend()
        self.ax2.grid(True, alpha=0.3)

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = DopplerRadarGUI(root)
    root.mainloop()
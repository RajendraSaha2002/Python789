import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from collections import deque

# --- CONFIGURATION ---
C_LIGHT = 3e8  # Speed of light in m/s (approximated)
MAX_RANGE = 1000  # Meters
fs = 1000  # Sampling frequency for the simulation grid


class RadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Radar Control System: Master Synchronizer & Processor")
        self.root.geometry("1200x800")

        # --- SYSTEM STATE ---
        self.is_running = False
        self.target_distance = 400  # Initial target distance (m)
        self.noise_level = 0.2
        self.threshold = 0.6
        self.angle = 0  # Antenna angle

        # Data storage for PPI (Map) display
        self.ppi_data = np.zeros((360, 100))  # Angle vs Range intensity

        self._init_layout()
        self._init_plots()

        # Start the "Master Clock" loop
        self.update_interval_ms = 50  # 20 Hz Radar Refresh
        self.root.after(self.update_interval_ms, self.master_clock_tick)

    def _init_layout(self):
        # Main Layout: Control Panel (Left) vs Display (Right)
        control_frame = tk.Frame(self.root, width=250, bg="#2c3e50")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        display_frame = tk.Frame(self.root, bg="black")
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- CONTROLS ---
        tk.Label(control_frame, text="RADAR MASTER CONTROL", font=("Arial", 14, "bold"), fg="white", bg="#2c3e50").pack(
            pady=20)

        # Status Light
        self.status_lbl = tk.Label(control_frame, text="SYSTEM: STANDBY", fg="red", bg="#2c3e50", font=("Consolas", 12))
        self.status_lbl.pack(pady=10)

        # Start/Stop
        self.btn_toggle = tk.Button(control_frame, text="POWER ON (Start PRF)", command=self.toggle_radar, bg="green",
                                    fg="white", height=2)
        self.btn_toggle.pack(fill=tk.X, padx=20, pady=10)

        # Target Slider
        tk.Label(control_frame, text="Simulate Target Distance (m)", fg="white", bg="#2c3e50").pack(pady=(20, 0))
        self.slider_target = tk.Scale(control_frame, from_=50, to=900, orient=tk.HORIZONTAL, command=self.update_target)
        self.slider_target.set(self.target_distance)
        self.slider_target.pack(fill=tk.X, padx=20)

        # Noise Slider
        tk.Label(control_frame, text="Receiver Noise Floor", fg="white", bg="#2c3e50").pack(pady=(20, 0))
        self.slider_noise = tk.Scale(control_frame, from_=0, to=1.0, resolution=0.1, orient=tk.HORIZONTAL,
                                     command=self.update_noise)
        self.slider_noise.set(self.noise_level)
        self.slider_noise.pack(fill=tk.X, padx=20)

        # Logic Description
        desc = ("\nINTERNAL LOGIC:\n\n"
                "1. TRIGGER: Fires pulse at T=0\n"
                "2. RANGE CLOCK: Starts counting\n"
                "3. ECHO: Returns at T = 2R/c\n"
                "4. PROCESSOR: Detects peak > Thresh")
        tk.Label(control_frame, text=desc, justify=tk.LEFT, fg="#bdc3c7", bg="#2c3e50", wraplength=230).pack(pady=30,
                                                                                                             padx=10)

        self.lbl_readout = tk.Label(control_frame, text="DETECTED: --- m", font=("Courier", 16, "bold"), fg="#39ff14",
                                    bg="black")
        self.lbl_readout.pack(side=tk.BOTTOM, fill=tk.X, pady=20)

        self.display_frame = display_frame

    def _init_plots(self):
        # Create Matplotlib Figure
        self.fig = plt.Figure(figsize=(10, 8), dpi=100, facecolor='black')

        # 1. A-Scope (Oscilloscope View) - Top
        self.ax_scope = self.fig.add_subplot(211, facecolor='black')
        self.ax_scope.set_title("A-SCOPE: Signal Amplitude vs Time (Range)", color='white')
        self.ax_scope.set_xlim(0, MAX_RANGE)
        self.ax_scope.set_ylim(-1.5, 1.5)
        self.ax_scope.grid(color='green', linestyle='--', linewidth=0.5, alpha=0.5)
        self.ax_scope.tick_params(axis='x', colors='white')
        self.ax_scope.tick_params(axis='y', colors='white')

        # Lines for plotting
        self.line_signal, = self.ax_scope.plot([], [], color='#39ff14', lw=1.5, label='Rx Signal')
        self.line_thresh, = self.ax_scope.plot([], [], color='red', linestyle='--', alpha=0.5, label='Threshold')
        self.line_trigger, = self.ax_scope.plot([], [], color='cyan', alpha=0.8, label='Trigger (T0)')

        # 2. PPI (Map View) - Bottom
        self.ax_ppi = self.fig.add_subplot(212, projection='polar', facecolor='black')
        self.ax_ppi.set_title("PPI DISPLAY: 360 Scan", color='white', pad=20)
        self.ax_ppi.grid(color='green', linestyle=':', alpha=0.3)
        self.ax_ppi.tick_params(colors='white')
        self.ax_ppi.set_rlim(0, MAX_RANGE)
        self.ax_ppi.set_theta_zero_location('N')
        self.ax_ppi.set_theta_direction(-1)  # Clockwise

        # PPI Scatter point for target
        self.ppi_scatter = self.ax_ppi.scatter([], [], c='red', s=50, alpha=0.8)

        # Legend
        self.ax_scope.legend(loc='upper right', facecolor='black', labelcolor='white')

        # Canvas embedding
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def toggle_radar(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_toggle.config(text="POWER OFF", bg="red")
            self.status_lbl.config(text="SYSTEM: TRANSMITTING", fg="#39ff14")
        else:
            self.btn_toggle.config(text="POWER ON", bg="green")
            self.status_lbl.config(text="SYSTEM: STANDBY", fg="red")
            self.lbl_readout.config(text="DETECTED: --- m")

    def update_target(self, val):
        self.target_distance = float(val)

    def update_noise(self, val):
        self.noise_level = float(val)

    def master_clock_tick(self):
        """
        THIS IS THE SYNCHRONIZER HEARTBEAT.
        It runs every `update_interval_ms`.
        """
        if self.is_running:
            self.run_cycle()

        # Keep the clock ticking
        self.root.after(self.update_interval_ms, self.master_clock_tick)

    def run_cycle(self):
        # --- 1. THE TRIGGER PULSE (T=0) ---
        # We simulate the distance vector (Range Clock)
        # 1000 points from 0 to MAX_RANGE
        ranges = np.linspace(0, MAX_RANGE, 1000)

        # Create empty signal buffer
        signal = np.zeros_like(ranges)

        # Add Trigger Pulse at Range 0 (Leakage from Tx)
        signal[0:20] = 1.0

        # --- 2. THE ENVIRONMENT (Physics) ---
        # Add Noise
        noise = np.random.normal(0, self.noise_level, len(ranges))
        signal += noise

        # Add Target Echo (Gaussian shape at target_distance)
        # Logic: Find index corresponding to target distance
        idx = (np.abs(ranges - self.target_distance)).argmin()
        width = 15  # Echo pulse width
        # Ensure we don't go out of bounds
        start = max(0, idx - width)
        end = min(len(ranges), idx + width)

        # Add echo amplitude
        signal[start:end] += 1.0 * np.exp(-0.5 * ((np.arange(start, end) - idx) / (width / 3)) ** 2)

        # --- 3. THE RECEIVER/PROCESSOR ---
        # Update A-Scope Plot
        self.line_signal.set_data(ranges, signal)
        self.line_thresh.set_data(ranges, [self.threshold] * len(ranges))

        # Detection Logic (Comparator)
        # Ignore the first 50m (Trigger leakage)
        detection_zone_signal = signal[50:]
        detection_zone_ranges = ranges[50:]

        peaks = np.where(detection_zone_signal > self.threshold)[0]

        if len(peaks) > 0:
            # We found a target!
            detected_dist = detection_zone_ranges[peaks[0]]
            self.lbl_readout.config(text=f"DETECTED: {int(detected_dist)} m")

            # --- 4. SCANNER LOGIC (PPI) ---
            # Update the rotating angle
            self.angle = (self.angle + 5) % 360
            rad_angle = np.radians(self.angle)

            # If target detected and antenna is roughly pointing at target
            # (We simulate a target at bearing 45 degrees for demo)
            target_bearing = 45
            beam_width = 20

            if abs(self.angle - target_bearing) < beam_width:
                self.ppi_scatter.set_offsets([[rad_angle, detected_dist]])
                self.ppi_scatter.set_alpha(1.0)
            else:
                # Fade out if beam passes
                self.ppi_scatter.set_alpha(max(0, self.ppi_scatter.get_alpha() - 0.1))

        else:
            self.lbl_readout.config(text="SEARCHING...")
            self.angle = (self.angle + 5) % 360

        self.canvas.draw()


# --- MAIN ENTRY ---
if __name__ == "__main__":
    root = tk.Tk()
    app = RadarGUI(root)
    root.mainloop()
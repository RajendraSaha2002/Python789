import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
import random
import time

# --- Configuration ---
SAMPLE_RATE = 10  # Hz (Data points per second)
WINDOW_SIZE = 100  # Points to show on screen (10 seconds history)
NOISE_LEVEL = 0.5  # Background magnetic noise (nanoTesla)
THRESHOLD = 2.5  # Auto-Alert Threshold
ANOMALY_MAGNITUDE = 5.0  # Strength of the sub


class MADSimulator:
    def __init__(self):
        # Data Buffer (Circular buffer for scrolling)
        self.data = np.zeros(WINDOW_SIZE)
        self.time_axis = np.arange(WINDOW_SIZE)

        # State
        self.t = 0
        self.anomaly_active = False
        self.anomaly_start_time = 0
        self.anomaly_duration = 30  # ticks (3 seconds)

        # Game State
        self.score = 0
        self.last_mark_time = -999
        self.detection_status = "SEARCHING"

        # Schedule first anomaly
        self.next_anomaly_time = random.randint(30, 60)  # Start after 3-6 seconds

    def update(self):
        """Generates the next sensor reading."""
        self.t += 1

        # 1. Background Noise (Earth's Field + Sensor Noise)
        reading = np.random.normal(0, NOISE_LEVEL)

        # 2. Inject Anomaly (Submarine Dipole Signature)
        # We simulate the Anderson Function logic roughly using a Sine/Gaussian mix
        if self.t == self.next_anomaly_time:
            self.anomaly_active = True
            self.anomaly_start_time = self.t

        if self.anomaly_active:
            # Time since anomaly started
            dt = self.t - self.anomaly_start_time

            # Simple signature shape: A sine wave scaled by a gaussian envelope
            # This looks like the classic "Dipole" pass
            progress = dt / self.anomaly_duration  # 0.0 to 1.0

            if progress <= 1.0:
                # Math: sin(2pi * t) * exp(-(t-0.5)^2)
                # Creates an Up-Down wave typical of flying over a magnet
                wave = np.sin(progress * 2 * np.pi)
                envelope = np.exp(-((progress - 0.5) * 4) ** 2)
                signal = wave * envelope * ANOMALY_MAGNITUDE

                reading += signal
            else:
                self.anomaly_active = False
                # Schedule next sub
                self.next_anomaly_time = self.t + random.randint(50, 150)

        # 3. Update Buffer (Scroll Left)
        self.data[:-1] = self.data[1:]
        self.data[-1] = reading

        # 4. Auto-Alert Logic
        if abs(reading) > THRESHOLD:
            self.detection_status = "MAGNETIC ANOMALY DETECTED"
        else:
            self.detection_status = "SEARCHING..."

        return self.data

    def mark_contact(self):
        """Operator pressed MARK."""
        # Check if we are currently looking at an anomaly
        # We allow a window of error (buffer tail)
        # Check the last 10 points for high values
        recent_max = np.max(np.abs(self.data[-20:]))

        if recent_max > THRESHOLD:
            self.score += 1
            return True  # Hit
        else:
            self.score -= 1
            return False  # False Alarm


# --- Visualization ---

class MADDisplay:
    def __init__(self):
        self.sim = MADSimulator()

        # Setup Plot
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.canvas.manager.set_window_title("AN/ASQ-81 MAD SENSOR DISPLAY")

        # Plot Elements
        self.line, = self.ax.plot(self.sim.time_axis, self.sim.data, color='#00FF00', lw=2)

        # Threshold Lines
        self.ax.axhline(y=THRESHOLD, color='red', linestyle='--', alpha=0.5)
        self.ax.axhline(y=-THRESHOLD, color='red', linestyle='--', alpha=0.5)

        # Text Overlay
        self.status_text = self.ax.text(0.02, 0.95, "INIT", transform=self.ax.transAxes,
                                        color='white', fontsize=12, fontname='monospace')
        self.score_text = self.ax.text(0.85, 0.95, "SCORE: 0", transform=self.ax.transAxes,
                                       color='yellow', fontsize=12, fontweight='bold')

        # Axis Config
        self.ax.set_ylim(-10, 10)
        self.ax.set_xlim(0, WINDOW_SIZE)
        self.ax.set_title("MAGNETIC ANOMALY DETECTOR (MAD) TRACE")
        self.ax.set_ylabel("Field Strength (nT)")
        self.ax.set_xlabel("Time (History)")
        self.ax.grid(True, color='#004400')

        # Button
        ax_btn = plt.axes([0.4, 0.05, 0.2, 0.075])
        self.btn_mark = Button(ax_btn, 'MARK CONTACT', color='#333333', hovercolor='#555555')
        self.btn_mark.label.set_color('white')
        self.btn_mark.on_clicked(self.on_mark)

        # Keyboard Shortcut
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

        # Animation
        self.ani = animation.FuncAnimation(self.fig, self.animate, interval=1000 / SAMPLE_RATE, blit=False)

        plt.show()

    def animate(self, i):
        # Update Logic
        data = self.sim.update()

        # Update Visuals
        self.line.set_ydata(data)

        # Flash Alert
        status = self.sim.detection_status
        if "DETECTED" in status:
            self.status_text.set_color('red')
            self.status_text.set_weight('bold')
            # Simulated audio cue via text flash
            if i % 2 == 0:
                self.status_text.set_text(f"!!! {status} !!!")
            else:
                self.status_text.set_text(f"    {status}    ")
        else:
            self.status_text.set_color('#00FF00')
            self.status_text.set_weight('normal')
            self.status_text.set_text(status)

        return self.line, self.status_text

    def on_mark(self, event):
        hit = self.sim.mark_contact()
        self.update_score_display(hit)

    def on_key(self, event):
        if event.key == ' ':
            self.on_mark(None)

    def update_score_display(self, hit):
        self.score_text.set_text(f"SCORE: {self.sim.score}")
        if hit:
            self.score_text.set_color('#00FF00')  # Green
        else:
            self.score_text.set_color('#FF0000')  # Red (Penalty)


if __name__ == "__main__":
    app = MADDisplay()
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import math

# --- Configuration ---
RESOLUTION = 360  # 1 degree steps
NULL_WIDTH = 40  # Width of the "Cut out" slice in degrees
ROTATION_SPEED = 1.0  # Degrees per frame
REFRESH_RATE = 50  # Milliseconds


class BeamformerLogic:
    """
    The Math Engine.
    Simulates a digital signal processor adjusting antenna weights
    to create a 'Null' (zero sensitivity) in a specific direction.
    """

    def __init__(self):
        # Create the azimuth array (0 to 2pi)
        self.theta = np.linspace(0, 2 * np.pi, RESOLUTION, endpoint=False)

    def calculate_pattern(self, jammer_angle_deg):
        """
        Generates the Gain Pattern.
        Default: 1.0 (Omnidirectional)
        Null: 0.1 (Suppressed) at jammer angle
        """
        # Initialize Omni pattern (All 1s)
        # We use 0.8 as base gain for visual clarity
        gains = np.full(RESOLUTION, 0.9)

        # Calculate Logic Indices for Slicing
        # We need to wrap around the array (e.g., if angle is 5, null is 345 to 25)
        j_idx = int(jammer_angle_deg) % RESOLUTION
        half_width = NULL_WIDTH // 2

        start_idx = j_idx - half_width
        end_idx = j_idx + half_width

        # Apply the Null (Array Slicing)
        # We iterate to handle the wrap-around (negative indices work in Py, but range crossing 0 needs care)
        for i in range(start_idx, end_idx):
            # Modulo ensures -10 becomes 350
            idx = i % RESOLUTION
            gains[idx] = 0.05  # Crush signal to near zero

        return self.theta, gains


class AntennaDisplay:
    def __init__(self):
        # Setup Figure
        self.fig = plt.figure(figsize=(8, 8), facecolor='#111111')
        self.ax = self.fig.add_subplot(111, projection='polar')

        # Style
        self.ax.set_facecolor('#001100')
        self.ax.set_theta_zero_location("N")  # 0 is North/Up
        self.ax.set_theta_direction(-1)  # Clockwise
        self.ax.grid(color='#004400', linestyle='--', linewidth=1)
        self.ax.set_ylim(0, 1.1)
        self.ax.set_yticks([])  # Hide radial numbers
        self.ax.tick_params(axis='x', colors='green')

        # Plot Objects
        # 1. The Sensitivity Pattern (Green Area)
        # We initialize with empty data
        self.line_pattern, = self.ax.plot([], [], color='#00FF00', linewidth=2, label='Antenna Gain')
        self.fill_pattern = None  # Placeholder for polygon fill

        # 2. The Jammer (Red Line/Dot)
        self.line_jammer, = self.ax.plot([], [], color='red', linestyle='--', linewidth=2, label='Jammer Source')
        self.dot_jammer, = self.ax.plot([], [], 'ro', markersize=12)

        # State
        self.logic = BeamformerLogic()
        self.jammer_angle = 45.0
        self.paused = False

        # Interaction
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

    def on_click(self, event):
        """User clicks to place Jammer manually."""
        if event.inaxes != self.ax: return
        if event.xdata:
            # xdata in polar plot is theta (radians)
            self.jammer_angle = np.degrees(event.xdata)

    def on_key(self, event):
        if event.key == ' ':
            self.paused = not self.paused

    def update(self, frame):
        if not self.paused:
            self.jammer_angle = (self.jammer_angle + ROTATION_SPEED) % 360

        # 1. Logic Calculation
        theta, gains = self.logic.calculate_pattern(self.jammer_angle)

        # 2. Update Pattern Visual
        self.line_pattern.set_data(theta, gains)

        # Hack to update fill (Matplotlib doesn't make updating fill_between easy)
        # We remove the old polygon and draw a new one.
        if self.fill_pattern:
            self.fill_pattern.remove()
        self.fill_pattern = self.ax.fill(theta, gains, color='#00FF00', alpha=0.3)[0]

        # 3. Update Jammer Visual
        j_rad = np.radians(self.jammer_angle)
        self.line_jammer.set_data([j_rad, j_rad], [0, 1.1])
        self.dot_jammer.set_data([j_rad], [1.1])

        # 4. Text Info
        status = "TRACKING" if not self.paused else "LOCKED"
        self.ax.set_title(f"DIGITAL NULL-STEERING SYSTEM\nSTATUS: {status} | JAMMER AZ: {int(self.jammer_angle)}°",
                          color='white', fontsize=14, pad=20)

        return self.line_pattern, self.line_jammer, self.dot_jammer

    def start(self):
        print("--- NULL-STEERING SIMULATOR ---")
        print("Controls:")
        print(" [Click Map]: Move Jammer instantly")
        print(" [Spacebar]: Pause/Resume rotation")

        self.ani = FuncAnimation(self.fig, self.update, interval=REFRESH_RATE, blit=False)
        plt.show()


if __name__ == "__main__":
    sim = AntennaDisplay()
    sim.start()
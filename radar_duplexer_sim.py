import tkinter as tk
from tkinter import ttk
import time
import math

# --- CONFIGURATION ---
# We use "Simulation Units" for time to make it visible to the human eye.
# 1 tick = 1 microsecond equivalent
c_light_sim = 10  # Speed of signal pixels per tick


class DuplexerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Radar Duplexer & T/R Switch Controller")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e1e")

        # System Parameters
        self.pulse_width = 30  # Duration of Tx Pulse
        self.recovery_time = 10  # Time for switch to settle back to Rx
        self.target_dist = 150  # Distance in pixels

        # State Variables
        self.sim_time = 0
        self.is_running = False
        self.switch_state = "RX"  # Options: RX, TX, RECOVERY
        self.echo_status = "WAITING"
        self.signal_pos_out = -1  # Position of outgoing pulse
        self.signal_pos_in = -1  # Position of incoming echo

        self._init_ui()
        self._draw_schematic_static()

    def _init_ui(self):
        # Top Frame: schematic
        self.canvas = tk.Canvas(self.root, width=900, height=400, bg="#2d2d2d", highlightthickness=0)
        self.canvas.pack(pady=20)

        # Control Panel
        ctrl_frame = tk.Frame(self.root, bg="#1e1e1e")
        ctrl_frame.pack(fill=tk.X, padx=50)

        # Buttons
        self.btn_fire = tk.Button(ctrl_frame, text="FIRE PULSE SEQUENCE", command=self.start_sequence,
                                  bg="#d35400", fg="white", font=("Arial", 12, "bold"), padx=20, pady=10)
        self.btn_fire.pack(side=tk.LEFT)

        # Sliders
        frame_sliders = tk.Frame(ctrl_frame, bg="#1e1e1e")
        frame_sliders.pack(side=tk.RIGHT)

        tk.Label(frame_sliders, text="Target Distance (Blind Zone Test)", fg="white", bg="#1e1e1e").pack()
        self.scale_dist = tk.Scale(frame_sliders, from_=20, to=400, orient=tk.HORIZONTAL, length=200,
                                   command=self.update_dist)
        self.scale_dist.set(150)
        self.scale_dist.pack()

        # Status readout
        self.lbl_status = tk.Label(self.root, text="SYSTEM READY: RECEIVER CONNECTED",
                                   fg="#2ecc71", bg="#1e1e1e", font=("Consolas", 16, "bold"))
        self.lbl_status.pack(pady=20)

        self.lbl_blind = tk.Label(self.root, text="BLIND RANGE: 0m", fg="#95a5a6", bg="#1e1e1e")
        self.lbl_blind.pack()

    def update_dist(self, val):
        self.target_dist = int(val)
        self._draw_schematic_static()  # Redraw target

    def _draw_schematic_static(self):
        self.canvas.delete("all")

        # Coordinates
        cx, cy = 450, 200  # Center Antenna
        tx_x, tx_y = 150, 300  # Transmitter
        rx_x, rx_y = 750, 300  # Receiver

        # 1. ANTENNA (Top Center)
        self.canvas.create_line(cx, cy, cx, cy - 50, fill="white", width=3)
        self.canvas.create_polygon(cx - 30, cy - 50, cx + 30, cy - 50, cx, cy, fill="gray", outline="white")
        self.canvas.create_text(cx, cy - 70, text="ANTENNA", fill="white")

        # 2. TRANSMITTER (Left)
        color_tx = "#e74c3c" if self.switch_state == "TX" else "#555"
        self.canvas.create_rectangle(tx_x - 50, tx_y - 30, tx_x + 50, tx_y + 30, fill=color_tx, outline="white")
        self.canvas.create_text(tx_x, tx_y, text="HIGH POWER\nTRANSMITTER", fill="white", justify=tk.CENTER)

        # 3. RECEIVER (Right)
        color_rx = "#2ecc71" if self.switch_state == "RX" else "#555"
        self.canvas.create_rectangle(rx_x - 50, rx_y - 30, rx_x + 50, rx_y + 30, fill=color_rx, outline="white")
        self.canvas.create_text(rx_x, rx_y, text="SENSITIVE\nRECEIVER", fill="white", justify=tk.CENTER)

        # 4. PATHS (Circuit Lines)
        # Main T-Junction
        self.canvas.create_line(tx_x + 50, tx_y, cx, tx_y, fill="white", width=2)  # Tx to Junction
        self.canvas.create_line(rx_x - 50, rx_y, cx, rx_y, fill="white", width=2)  # Rx to Junction
        self.canvas.create_line(cx, tx_y, cx, cy, fill="white", width=2)  # Junction to Antenna

        # 5. THE DUPLEXER SWITCH (The Critical Component)
        # It sits between the Junction and the Receiver
        sw_x = cx + 50  # Switch location
        sw_y = rx_y

        # Draw Switch Hub
        self.canvas.create_oval(sw_x - 5, sw_y - 5, sw_x + 5, sw_y + 5, fill="white")

        # Draw Switch Arm based on State
        if self.switch_state == "TX" or self.switch_state == "RECOVERY":
            # Switch OPEN (Disconnected from Rx)
            self.canvas.create_line(sw_x, sw_y, sw_x + 30, sw_y - 30, fill="red", width=4)
            self.canvas.create_text(sw_x, sw_y - 40, text="OPEN (PROTECT)", fill="red", anchor="s")
        else:
            # Switch CLOSED (Connected to Rx)
            self.canvas.create_line(sw_x, sw_y, sw_x + 40, sw_y, fill="#2ecc71", width=4)
            self.canvas.create_text(sw_x, sw_y - 20, text="CLOSED (LISTEN)", fill="#2ecc71", anchor="s")

        # 6. TARGET
        t_x = cx
        t_y = cy - self.target_dist
        self.canvas.create_rectangle(t_x - 20, t_y - 10, t_x + 20, t_y + 10, fill="cyan", outline="white")
        self.canvas.create_text(t_x + 30, t_y, text="TARGET", fill="cyan", anchor="w")

        # 7. PULSE ANIMATION
        if self.signal_pos_out >= 0:
            # Drawing the outgoing pulse moving up from antenna
            py = cy - self.signal_pos_out
            self.canvas.create_oval(cx - 10, py - 10, cx + 10, py + 10, fill="orange", outline="red")

        if self.signal_pos_in >= 0:
            # Drawing the incoming echo moving down to antenna
            py = (cy - self.target_dist) + self.signal_pos_in
            self.canvas.create_oval(cx - 5, py - 5, cx + 5, py + 5, fill="#39ff14", outline="green")

    def start_sequence(self):
        if self.is_running: return
        self.is_running = True
        self.sim_time = 0
        self.signal_pos_out = 0
        self.signal_pos_in = -1
        self.echo_status = "WAITING"
        self._run_tick()

    def _run_tick(self):
        # 1. UPDATE STATE MACHINE
        if self.sim_time < self.pulse_width:
            self.switch_state = "TX"
            status_text = "MODE: TRANSMITTING (HIGH POWER)"
            status_color = "#e74c3c"
        elif self.sim_time < (self.pulse_width + self.recovery_time):
            self.switch_state = "RECOVERY"
            status_text = "MODE: DUPLEXER RECOVERY (SWITCHING)"
            status_color = "orange"
        else:
            self.switch_state = "RX"
            status_text = "MODE: RECEIVING (LISTENING)"
            status_color = "#2ecc71"

        # 2. UPDATE PHYSICS (Signal Movement)
        # Outgoing signal
        if self.signal_pos_out >= 0:
            self.signal_pos_out += c_light_sim
            # If it hits target, start echo
            if self.signal_pos_out >= self.target_dist:
                self.signal_pos_in = 0  # Start echo
                self.signal_pos_out = -1  # Stop outgoing

        # Incoming Echo
        if self.signal_pos_in >= 0:
            self.signal_pos_in += c_light_sim
            # If echo gets back to antenna (distance traveled = target_dist)
            if self.signal_pos_in >= self.target_dist:
                self._check_detection()
                self.signal_pos_in = -1  # Stop echo

        # 3. UPDATE UI
        self.lbl_status.config(text=status_text, fg=status_color)

        # Calc Blind Range Display
        blind_pixels = (self.pulse_width + self.recovery_time) * c_light_sim
        self.lbl_blind.config(text=f"BLIND ZONE LIMIT: {blind_pixels} pixels (Target is at {self.target_dist})")

        self._draw_schematic_static()

        # Loop
        self.sim_time += 1
        if self.sim_time < 150:  # Run for 150 ticks
            self.root.after(50, self._run_tick)  # 50ms per tick (Slow Motion)
        else:
            self.is_running = False
            self.switch_state = "RX"  # Reset to safe
            self._draw_schematic_static()

    def _check_detection(self):
        # The echo has returned to the antenna.
        # Can it get to the receiver?

        if self.switch_state == "RX":
            tk.messagebox.showinfo("RESULT",
                                   "TARGET DETECTED!\n\nThe switch was CLOSED, so the echo reached the receiver.")
        else:
            tk.messagebox.showwarning("RESULT",
                                      "TARGET LOST (BLIND ZONE)!\n\nThe echo returned while the radar was still Transmitting or Recovering.\nThe switch was OPEN to protect the receiver.")


if __name__ == "__main__":
    root = tk.Tk()
    app = DuplexerGUI(root)
    root.mainloop()
import numpy as np
import math
import tkinter as tk
from tkinter import ttk, messagebox


# --- Logic Class (The Math) ---
class LinkBudgetCalculator:
    def __init__(self):
        # Constants
        self.c = 3e8  # Speed of light in m/s
        self.GEO_ALTITUDE_KM = 35786  # Standard GEO altitude
        self.BOLTZMANN_K = -228.6  # dBW/K/Hz

    def watts_to_dbw(self, power_watts):
        """Converts Power in Watts to dBW."""
        if power_watts <= 0:
            return -np.inf
        return 10 * np.log10(power_watts)

    def calculate_antenna_gain(self, frequency_hz, diameter_m, efficiency=0.6):
        """
        Calculates Antenna Gain in dBi.
        Formula: G = 10 * log10(efficiency * (pi * D / lambda)^2)
        """
        wavelength = self.c / frequency_hz
        gain_linear = efficiency * (np.pi * diameter_m / wavelength) ** 2
        return 10 * np.log10(gain_linear)

    def calculate_fspl(self, distance_km, frequency_mhz):
        """
        Calculates Free Space Path Loss (FSPL) in dB.
        Formula: Lfs = 20log10(d) + 20log10(f) + 32.44
        """
        return 20 * np.log10(distance_km) + 20 * np.log10(frequency_mhz) + 32.44

    def calculate_noise_power(self, temp_k, bandwidth_hz):
        """
        Calculates Noise Power (N) in dBW.
        Formula: N = k + 10log10(T) + 10log10(B)
        """
        return self.BOLTZMANN_K + 10 * np.log10(temp_k) + 10 * np.log10(bandwidth_hz)


# --- GUI Class (The Interface) ---
class LinkBudgetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Satellite Link Budget & Visualizer")
        self.root.geometry("900x700")
        self.calc = LinkBudgetCalculator()

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", font=("Helvetica", 11))
        self.style.configure("TButton", font=("Helvetica", 11, "bold"))

        self.create_layout()

        # Animation Variables
        self.anim_running = False
        self.signal_pos = 0.0  # 0.0 to 1.0 (Earth to Sat)

    def create_layout(self):
        # Top Frame: Inputs and Results
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # --- Input Section (Left) ---
        input_frame = ttk.LabelFrame(top_frame, text="Link Parameters", padding="10")
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Helper to create inputs
        def add_input(parent, label, default_val, row):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
            entry = ttk.Entry(parent, width=15)
            entry.insert(0, str(default_val))
            entry.grid(row=row, column=1, sticky="e", pady=5, padx=5)
            return entry

        self.e_freq = add_input(input_frame, "Frequency (GHz):", "4.0", 0)
        self.e_power = add_input(input_frame, "Tx Power (Watts):", "50", 1)
        self.e_tx_diam = add_input(input_frame, "Tx Antenna Diam (m):", "2.4", 2)
        self.e_rx_diam = add_input(input_frame, "Rx Antenna Diam (m):", "1.2", 3)
        self.e_losses = add_input(input_frame, "Misc Losses (dB):", "3.0", 4)
        self.e_sens = add_input(input_frame, "Rx Sensitivity (dBW):", "-120", 5)

        # Calc Button
        self.btn_calc = ttk.Button(input_frame, text="CALCULATE & TRANSMIT", command=self.run_simulation)
        self.btn_calc.grid(row=6, column=0, columnspan=2, pady=15, sticky="ew")

        # --- Results Section (Right) ---
        result_frame = ttk.LabelFrame(top_frame, text="Link Analysis", padding="10")
        result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.res_labels = {}
        for i, key in enumerate(
                ["Tx Power (dBW)", "Tx Gain (dBi)", "Path Loss (dB)", "Rx Gain (dBi)", "Received Power (dBW)",
                 "Margin (dB)", "STATUS"]):
            ttk.Label(result_frame, text=f"{key}:").grid(row=i, column=0, sticky="w", pady=5)
            lbl = ttk.Label(result_frame, text="---", font=("Courier", 12, "bold"))
            lbl.grid(row=i, column=1, sticky="e", pady=5, padx=10)
            self.res_labels[key] = lbl

        # --- Visualization Section (Bottom) ---
        vis_frame = ttk.LabelFrame(self.root, text="Signal Visualization (Earth -> GEO)", padding="10")
        vis_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(vis_frame, bg="#0f0f1a", height=300)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Initial Draw
        self.draw_scene()

    def draw_scene(self):
        """Draws static Earth and Satellite."""
        w = 860
        h = 280

        # Draw Stars
        import random
        for _ in range(50):
            x, y = random.randint(0, w), random.randint(0, h)
            self.canvas.create_oval(x, y, x + 1, y + 1, fill="white")

        # Earth (Bottom Left)
        self.earth_x, self.earth_y = 100, h - 50
        self.canvas.create_arc(self.earth_x - 60, self.earth_y - 40, self.earth_x + 60, self.earth_y + 100, start=0,
                               extent=180, fill="#2e8b57", outline="#87ceeb", width=2)
        self.canvas.create_text(self.earth_x, self.earth_y + 20, text="Earth Station", fill="white", font=("Arial", 10))
        # Dish
        self.canvas.create_arc(self.earth_x - 15, self.earth_y - 30, self.earth_x + 15, self.earth_y, start=180,
                               extent=180, style=tk.ARC, outline="white", width=2)
        self.canvas.create_line(self.earth_x, self.earth_y - 15, self.earth_x + 20, self.earth_y - 50, fill="gray",
                                width=2)  # boom

        # Satellite (Top Right)
        self.sat_x, self.sat_y = w - 100, 60
        # Panels
        self.canvas.create_rectangle(self.sat_x - 40, self.sat_y - 10, self.sat_x - 15, self.sat_y + 10, fill="#4169e1")
        self.canvas.create_rectangle(self.sat_x + 15, self.sat_y - 10, self.sat_x + 40, self.sat_y + 10, fill="#4169e1")
        # Body
        self.canvas.create_rectangle(self.sat_x - 15, self.sat_y - 15, self.sat_x + 15, self.sat_y + 15, fill="gold")
        # Dish
        self.canvas.create_arc(self.sat_x - 20, self.sat_y, self.sat_x + 10, self.sat_y + 30, start=0, extent=180,
                               style=tk.ARC, outline="white", width=2)
        self.canvas.create_text(self.sat_x, self.sat_y - 30, text="GEO Sat", fill="white", font=("Arial", 10))

    def run_simulation(self):
        try:
            # 1. Get Inputs
            freq_ghz = float(self.e_freq.get())
            tx_watts = float(self.e_power.get())
            tx_diam = float(self.e_tx_diam.get())
            rx_diam = float(self.e_rx_diam.get())
            misc_loss = float(self.e_losses.get())
            sens = float(self.e_sens.get())

            # 2. Perform Calculation
            freq_hz = freq_ghz * 1e9
            freq_mhz = freq_ghz * 1e3

            pt_dbw = self.calc.watts_to_dbw(tx_watts)
            gt_dbi = self.calc.calculate_antenna_gain(freq_hz, tx_diam)
            gr_dbi = self.calc.calculate_antenna_gain(freq_hz, rx_diam)
            fspl = self.calc.calculate_fspl(self.calc.GEO_ALTITUDE_KM, freq_mhz)

            pr_dbw = pt_dbw + gt_dbi + gr_dbi - fspl - misc_loss
            margin = pr_dbw - sens

            # 3. Update Results
            self.res_labels["Tx Power (dBW)"].config(text=f"{pt_dbw:.2f}")
            self.res_labels["Tx Gain (dBi)"].config(text=f"{gt_dbi:.2f}")
            self.res_labels["Rx Gain (dBi)"].config(text=f"{gr_dbi:.2f}")
            self.res_labels["Path Loss (dB)"].config(text=f"-{fspl:.2f}")
            self.res_labels["Received Power (dBW)"].config(text=f"{pr_dbw:.2f}", foreground="cyan")

            marg_lbl = self.res_labels["Margin (dB)"]
            marg_lbl.config(text=f"{margin:.2f}")

            stat_lbl = self.res_labels["STATUS"]
            if margin >= 0:
                stat_lbl.config(text="LINK OK", foreground="#00ff00")
                self.link_success = True
            else:
                stat_lbl.config(text="LINK FAIL", foreground="#ff0000")
                self.link_success = False

            # 4. Start Animation
            self.canvas.delete("signal")  # Clear old signal
            self.canvas.delete("status_icon")
            self.signal_pos = 0.0
            self.animate_signal()

        except ValueError:
            messagebox.showerror("Input Error", "Please ensure all fields contain valid numbers.")

    def animate_signal(self):
        # Interpolate position
        start_x, start_y = self.earth_x + 20, self.earth_y - 50
        end_x, end_y = self.sat_x - 20, self.sat_y + 15

        cur_x = start_x + (end_x - start_x) * self.signal_pos
        cur_y = start_y + (end_y - start_y) * self.signal_pos

        # Clear previous frame signal
        self.canvas.delete("signal")

        # Draw Signal Packet
        color = "#00ffff"  # Cyan
        size = 8
        self.canvas.create_oval(cur_x - size, cur_y - size, cur_x + size, cur_y + size, fill=color, tags="signal")
        # Draw Tail
        self.canvas.create_line(start_x, start_y, cur_x, cur_y, fill=color, dash=(2, 4), tags="signal")

        if self.signal_pos < 1.0:
            self.signal_pos += 0.02  # Speed
            self.root.after(20, self.animate_signal)
        else:
            # Animation Done - Show Result on Satellite
            self.show_arrival_status()

    def show_arrival_status(self):
        color = "#00ff00" if self.link_success else "#ff0000"
        text = "✔" if self.link_success else "✘"

        # Flash effect
        self.canvas.create_oval(self.sat_x - 30, self.sat_y - 30, self.sat_x + 30, self.sat_y + 30, outline=color,
                                width=3, tags="status_icon")
        self.canvas.create_text(self.sat_x, self.sat_y - 45, text=text, fill=color, font=("Arial", 20, "bold"),
                                tags="status_icon")


if __name__ == "__main__":
    root = tk.Tk()
    app = LinkBudgetApp(root)
    root.mainloop()
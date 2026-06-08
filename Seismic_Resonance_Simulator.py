import math
import tkinter as tk
from dataclasses import dataclass


@dataclass
class Building:
    name: str
    x: int
    base_y: int
    width: int
    height: int
    nat_freq: float
    color: str
    warning_threshold_px: float

    def top_y(self) -> int:
        return self.base_y - self.height


class SeismicResonanceSimulator:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Seismic Engineering & Structural Resonance Simulator")
        self.root.geometry("1200x760")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#101820")

        self.time_tick = 0.0
        self.running = True

        # Main layout
        self.left_panel = tk.Frame(self.root, bg="#151b24", width=300)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas_frame = tk.Frame(self.root, bg="#101820")
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#0b1220", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Controls
        title = tk.Label(
            self.left_panel,
            text="Seismic Simulator",
            fg="white",
            bg="#151b24",
            font=("Arial", 20, "bold"),
            pady=10,
        )
        title.pack(anchor="w", padx=16, pady=(8, 0))

        subtitle = tk.Label(
            self.left_panel,
            text="Visualize structural resonance\nand earthquake response",
            fg="#b8c7e0",
            bg="#151b24",
            justify="left",
            font=("Arial", 10),
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 14))

        self.freq_var = tk.DoubleVar(value=1.0)
        self.intensity_var = tk.DoubleVar(value=1.0)

        self._build_slider(
            label="Ground Vibration Frequency (Hz)",
            variable=self.freq_var,
            from_=0.2,
            to=3.5,
            resolution=0.01,
        )
        self._build_slider(
            label="Earthquake Intensity",
            variable=self.intensity_var,
            from_=0.1,
            to=3.0,
            resolution=0.01,
        )

        info_box = tk.Frame(self.left_panel, bg="#1c2533", bd=0)
        info_box.pack(fill=tk.X, padx=16, pady=12)

        info_text = (
            "How it works:\n"
            "• Short building responds to high-frequency shaking\n"
            "• Tall building responds to low-frequency shaking\n"
            "• Resonance boosts sway near natural frequency\n"
            "• Warning flashes when deflection is critical"
        )
        tk.Label(
            info_box,
            text=info_text,
            fg="#d7e5ff",
            bg="#1c2533",
            justify="left",
            font=("Arial", 10),
            wraplength=260,
            padx=10,
            pady=10,
        ).pack(anchor="w")

        self.status_label = tk.Label(
            self.left_panel,
            text="Status: Monitoring structural response",
            fg="#90ee90",
            bg="#151b24",
            font=("Arial", 11, "bold"),
            wraplength=260,
            justify="left",
        )
        self.status_label.pack(anchor="w", padx=16, pady=(8, 4))

        self.warning_label = tk.Label(
            self.left_panel,
            text="",
            fg="#ff4d4d",
            bg="#151b24",
            font=("Arial", 12, "bold"),
            wraplength=260,
            justify="left",
        )
        self.warning_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.readout_label = tk.Label(
            self.left_panel,
            text="",
            fg="#dfe7f4",
            bg="#151b24",
            font=("Consolas", 10),
            justify="left",
        )
        self.readout_label.pack(anchor="w", padx=16, pady=(6, 10))

        self.buildings = []
        self._init_buildings()

        self.root.bind("<Configure>", self._on_resize)
        self._animate()

    def _build_slider(self, label: str, variable: tk.DoubleVar, from_: float, to: float, resolution: float):
        container = tk.Frame(self.left_panel, bg="#151b24")
        container.pack(fill=tk.X, padx=16, pady=(0, 10))

        lbl = tk.Label(
            container,
            text=label,
            fg="#e7eefc",
            bg="#151b24",
            font=("Arial", 11, "bold"),
            anchor="w",
        )
        lbl.pack(fill=tk.X, pady=(0, 4))

        scale = tk.Scale(
            container,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            resolution=resolution,
            variable=variable,
            length=250,
            showvalue=True,
            troughcolor="#243248",
            fg="#ffffff",
            bg="#151b24",
            highlightthickness=0,
            activebackground="#5aa9ff",
            relief=tk.FLAT,
        )
        scale.pack(fill=tk.X)

    def _init_buildings(self):
        # These heights and natural frequencies create the resonance behavior requested.
        self.buildings = [
            Building("Short", 140, 0, 120, 190, 2.9, "#6cc4ff", 55),
            Building("Medium", 360, 0, 120, 300, 1.6, "#8bd17c", 70),
            Building("Tall", 610, 0, 120, 440, 0.8, "#f3b267", 90),
        ]

    def _on_resize(self, event):
        # Recompute building bases when canvas size changes.
        self._layout_buildings()

    def _layout_buildings(self):
        w = max(self.canvas.winfo_width(), 900)
        h = max(self.canvas.winfo_height(), 560)
        ground_y = int(h * 0.83)

        positions = [int(w * 0.18), int(w * 0.47), int(w * 0.76)]
        widths = [120, 120, 120]
        heights = [190, 300, 440]

        for i, b in enumerate(self.buildings):
            b.x = positions[i]
            b.width = widths[i]
            b.height = heights[i]
            b.base_y = ground_y

    @staticmethod
    def amplitude_modifier(ground_freq: float, nat_freq: float) -> float:
        ratio = ground_freq / nat_freq
        return 1.0 / math.sqrt((1.0 - ratio * ratio) ** 2 + 0.1)

    def _draw_ground(self, w: int, h: int, ground_y: int, ground_shift: float):
        # Ground baseline with small motion.
        self.canvas.create_line(0, ground_y, w, ground_y, fill="#d8dde8", width=3)

        # Draw a slight ground waveform.
        points = []
        for x in range(0, w + 1, 12):
            y = ground_y + 8 * math.sin((x * 0.022) + self.time_tick * 0.65) + ground_shift * 0.35
            points.extend([x, y])
        self.canvas.create_line(*points, fill="#7aa2ff", width=2, smooth=True)

        self.canvas.create_text(
            16,
            ground_y - 28,
            text=f"Ground motion | freq = {self.freq_var.get():.2f} Hz",
            fill="#dbe7ff",
            anchor="w",
            font=("Arial", 11, "bold"),
        )

    def _draw_building(self, b: Building, ground_shift: float, intensity: float, ground_freq: float):
        # Resonance-based sway scaling.
        amp_mod = self.amplitude_modifier(ground_freq, b.nat_freq)

        # Dynamic roof displacement: stronger response near resonance.
        response = intensity * amp_mod
        # Different phases make the buildings look independent.
        phase = {
            "Short": 0.0,
            "Medium": 1.2,
            "Tall": 2.0,
        }.get(b.name, 0.0)

        sway = response * 16.0 * math.sin((self.time_tick * (ground_freq * 2.2)) + phase)
        sway += ground_shift * (0.25 + 0.08 * response)

        # Store for status/warnings.
        deflection_px = abs(sway)

        # Building geometry.
        x0 = b.x - b.width // 2
        x1 = b.x + b.width // 2
        y1 = b.base_y
        y0 = b.base_y - b.height

        # Sheared top line to visually show sway.
        top_left = (x0 + sway, y0)
        top_right = (x1 + sway, y0)
        bottom_left = (x0, y1)
        bottom_right = (x1, y1)

        # Shadow/base foundation.
        self.canvas.create_rectangle(x0 - 14, y1 + 10, x1 + 14, y1 + 16, fill="#000000", outline="")

        # Main building body as polygon.
        self.canvas.create_polygon(
            bottom_left,
            bottom_right,
            top_right,
            top_left,
            fill=b.color,
            outline="#e8eefc",
            width=2,
        )

        # Inner window lines for visual detail.
        window_color = "#1b2533"
        num_floors = max(5, b.height // 35)
        num_cols = 4
        for floor in range(1, num_floors):
            fy = y1 - (b.height * floor / num_floors)
            fy_shift = fy + (sway * (floor / num_floors) * 0.18)
            self.canvas.create_line(x0 + 12 + sway * 0.12, fy_shift, x1 - 12 + sway * 0.12, fy_shift, fill=window_color)

        for col in range(1, num_cols):
            cx = x0 + (b.width * col / num_cols)
            self.canvas.create_line(cx + sway * 0.08, y0 + 10, cx, y1 - 10, fill=window_color)

        # Roof displacement marker
        roof_center_x = (top_left[0] + top_right[0]) / 2.0
        roof_center_y = y0 - 14
        self.canvas.create_oval(
            roof_center_x - 6,
            roof_center_y - 6,
            roof_center_x + 6,
            roof_center_y + 6,
            fill="#ffffff",
            outline="#000000",
        )

        # Building label and readings.
        self.canvas.create_text(
            b.x,
            y0 - 36,
            text=f"{b.name} Building",
            fill="#f3f7ff",
            font=("Arial", 12, "bold"),
        )
        self.canvas.create_text(
            b.x,
            y1 + 34,
            text=f"Nat. Freq: {b.nat_freq:.1f} Hz",
            fill="#cdd8eb",
            font=("Arial", 10),
        )
        self.canvas.create_text(
            b.x,
            y1 + 52,
            text=f"Roof sway: {deflection_px:.1f} px",
            fill="#cdd8eb",
            font=("Arial", 10),
        )

        # Critical threshold warning.
        critical = deflection_px >= b.warning_threshold_px
        return deflection_px, critical, sway, amp_mod

    def _animate(self):
        if not self.running:
            return

        self._layout_buildings()
        self.canvas.delete("all")

        w = max(self.canvas.winfo_width(), 900)
        h = max(self.canvas.winfo_height(), 560)
        ground_y = int(h * 0.83)

        ground_freq = float(self.freq_var.get())
        intensity = float(self.intensity_var.get())

        # Ground shaking displacement.
        ground_shift = 10.0 * intensity * math.sin(self.time_tick * ground_freq * 2.0 * math.pi)

        # Background decorations.
        self.canvas.create_rectangle(0, 0, w, ground_y, fill="#0b1220", outline="")
        self.canvas.create_rectangle(0, ground_y, w, h, fill="#101820", outline="")

        # Distant grid lines for engineering feel.
        for gx in range(0, w, 60):
            self.canvas.create_line(gx, 0, gx, ground_y, fill="#152238", width=1)
        for gy in range(0, ground_y, 60):
            self.canvas.create_line(0, gy, w, gy, fill="#152238", width=1)

        self._draw_ground(w, h, ground_y, ground_shift)

        flash_warnings = []
        readout_lines = [
            f"time_tick = {self.time_tick:.2f}",
            f"ground freq = {ground_freq:.2f} Hz",
            f"intensity = {intensity:.2f}",
            "",
        ]

        # Draw each building and collect warnings.
        for b in self.buildings:
            deflection_px, critical, sway, amp_mod = self._draw_building(b, ground_shift, intensity, ground_freq)
            readout_lines.extend([
                f"{b.name}:",
                f"  nat_freq = {b.nat_freq:.2f} Hz",
                f"  amplitude modifier = {amp_mod:.3f}",
                f"  roof displacement = {sway:.2f}px",
                f"  critical = {'YES' if critical else 'no'}",
                "",
            ])
            if critical:
                flash_warnings.append(
                    f"WARNING: {b.name} building exceeds deflection limit ({deflection_px:.1f}px > {b.warning_threshold_px:.0f}px)"
                )

        self.readout_label.config(text="\n".join(readout_lines).rstrip())

        if flash_warnings:
            # Flashing warning effect.
            if int(self.time_tick * 8) % 2 == 0:
                self.warning_label.config(text="\n".join(flash_warnings), fg="#ff6b6b")
            else:
                self.warning_label.config(text="\n".join(flash_warnings), fg="#ffffff")
            self.status_label.config(text="Status: Critical structural deflection detected", fg="#ffb347")
        else:
            self.warning_label.config(text="")
            self.status_label.config(text="Status: Monitoring structural response", fg="#90ee90")

        # Labels along the bottom.
        self.canvas.create_text(
            w - 16,
            ground_y + 18,
            text="Earthquake Simulator | Resonance demonstration",
            fill="#8fa4c5",
            anchor="e",
            font=("Arial", 10),
        )

        self.time_tick += 0.03
        self.root.after(16, self._animate)


def main():
    root = tk.Tk()
    app = SeismicResonanceSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()

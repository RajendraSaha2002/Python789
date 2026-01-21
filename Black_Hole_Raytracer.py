"""
General Relativity Black Hole Ray Tracer
Visualizes gravitational lensing around a Schwarzschild black hole
Integrates geodesic equations to bend light rays in curved spacetime
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw
import threading


class BlackHoleRayTracer:
    def __init__(self):
        # Physical constants (normalized units: c=G=1, M=1)
        self.M = 1.0  # Black hole mass
        self.r_s = 2.0 * self.M  # Schwarzschild radius

        # Camera parameters
        self.camera_distance = 20.0  # Distance from black hole
        self.fov = 60.0  # Field of view in degrees

        # Rendering parameters
        self.width = 400
        self.height = 400
        self.max_steps = 1000
        self.step_size = 0.1

        # Current render
        self.rendered_image = None
        self.is_rendering = False

    def create_skybox(self):
        """Create a procedural starfield/galaxy skybox"""
        size = 1024
        img = np.zeros((size, size, 3), dtype=np.uint8)

        # Create Milky Way-like band
        y = np.arange(size)
        x = np.arange(size)
        X, Y = np.meshgrid(x, y)

        # Galaxy disk
        center_y = size // 2
        disk_width = size // 4
        disk_intensity = np.exp(-((Y - center_y) ** 2) / (2 * disk_width ** 2))

        # Add color gradient (reddish-yellow-blue)
        img[:, :, 0] = (disk_intensity * 180 + 20).astype(np.uint8)  # Red
        img[:, :, 1] = (disk_intensity * 150 + 15).astype(np.uint8)  # Green
        img[:, :, 2] = (disk_intensity * 100 + 30).astype(np.uint8)  # Blue

        # Add random stars
        np.random.seed(42)
        num_stars = 3000
        for _ in range(num_stars):
            sx = np.random.randint(0, size)
            sy = np.random.randint(0, size)
            brightness = np.random.randint(150, 255)
            star_size = np.random.choice([1, 1, 1, 2])

            for dy in range(-star_size, star_size + 1):
                for dx in range(-star_size, star_size + 1):
                    if 0 <= sy + dy < size and 0 <= sx + dx < size:
                        img[sy + dy, sx + dx] = [brightness, brightness, brightness]

        # Add some bright stars with glow
        num_bright = 100
        for _ in range(num_bright):
            sx = np.random.randint(0, size)
            sy = np.random.randint(0, size)
            brightness = 255
            glow_radius = 3

            for dy in range(-glow_radius, glow_radius + 1):
                for dx in range(-glow_radius, glow_radius + 1):
                    dist = np.sqrt(dx ** 2 + dy ** 2)
                    if dist <= glow_radius and 0 <= sy + dy < size and 0 <= sx + dx < size:
                        falloff = 1.0 - (dist / glow_radius)
                        color = int(brightness * falloff)
                        img[sy + dy, sx + dx] = np.maximum(img[sy + dy, sx + dx],
                                                           [color, color, color])

        return img

    def sample_skybox(self, theta, phi, skybox):
        """Sample skybox texture at spherical coordinates (theta, phi)"""
        # Convert to texture coordinates
        u = (phi / (2 * np.pi)) % 1.0
        v = (theta / np.pi) % 1.0

        h, w = skybox.shape[:2]
        x = int(u * w) % w
        y = int(v * h) % h

        return skybox[y, x]

    def schwarzschild_derivatives(self, state, L):
        """
        Compute derivatives for geodesic equation in Schwarzschild metric
        state = [r, theta, phi, p_r, p_theta, p_phi]
        L = angular momentum (conserved)
        """
        r, theta, phi, p_r, p_theta, p_phi = state

        # Avoid singularities
        if r < self.r_s * 1.01:
            return np.zeros(6)

        # Metric components
        f = 1.0 - self.r_s / r

        # Geodesic equations for photon (null geodesic)
        dr_dtau = p_r
        dtheta_dtau = p_theta / r ** 2
        dphi_dtau = p_phi / (r ** 2 * np.sin(theta) ** 2)

        # Christoffel symbols contributions
        dp_r_dtau = (
                -self.r_s / (2 * r ** 2 * f) * p_r ** 2 +
                f * (p_theta ** 2 / r ** 3 + p_phi ** 2 / (r ** 3 * np.sin(theta) ** 2))
        )

        dp_theta_dtau = (
                -2 * p_r * p_theta / r +
                p_phi ** 2 * np.cos(theta) / (r ** 2 * np.sin(theta) ** 3)
        )

        dp_phi_dtau = -2 * p_r * p_phi / r - 2 * p_theta * p_phi * np.cos(theta) / (r ** 2 * np.sin(theta))

        return np.array([dr_dtau, dtheta_dtau, dphi_dtau,
                         dp_r_dtau, dp_theta_dtau, dp_phi_dtau])

    def trace_ray(self, position, direction, skybox):
        """
        Trace a single light ray through curved spacetime
        Uses RK4 integration of geodesic equations
        """
        # Convert camera position to spherical coordinates
        r = np.linalg.norm(position)
        theta = np.arccos(position[2] / r)
        phi = np.arctan2(position[1], position[0])

        # Initial momentum (4-momentum for photon)
        # Normalize direction
        direction = direction / np.linalg.norm(direction)

        # Convert to spherical momentum components
        p_r = np.dot(direction, position / r)
        p_theta = direction[2] / r - p_r * position[2] / r ** 2
        p_phi = (direction[1] * position[0] - direction[0] * position[1]) / (r * np.sin(theta))

        # Angular momentum (conserved)
        L = r * np.sin(theta) * p_phi

        # State vector
        state = np.array([r, theta, phi, p_r, p_theta, p_phi])

        # Integrate geodesic
        for step in range(self.max_steps):
            # Check if hit event horizon
            if state[0] < self.r_s * 1.05:
                return np.array([0, 0, 0])  # Black

            # Check if escaped to infinity
            if state[0] > self.camera_distance * 3:
                # Sample skybox
                sample_theta = state[1] % np.pi
                sample_phi = state[2] % (2 * np.pi)
                return self.sample_skybox(sample_theta, sample_phi, skybox)

            # RK4 integration
            k1 = self.schwarzschild_derivatives(state, L)
            k2 = self.schwarzschild_derivatives(state + self.step_size * k1 / 2, L)
            k3 = self.schwarzschild_derivatives(state + self.step_size * k2 / 2, L)
            k4 = self.schwarzschild_derivatives(state + self.step_size * k3, L)

            state += self.step_size * (k1 + 2 * k2 + 2 * k3 + k4) / 6

            # Keep angles in valid range
            state[1] = np.clip(state[1], 0.01, np.pi - 0.01)
            state[2] = state[2] % (2 * np.pi)

        # Didn't converge, return black
        return np.array([0, 0, 0])

    def render(self, progress_callback=None):
        """Render the black hole image"""
        self.is_rendering = True

        # Create skybox
        skybox = self.create_skybox()

        # Output image
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Camera setup
        aspect = self.width / self.height
        fov_rad = np.radians(self.fov)

        # Camera position (on +x axis)
        camera_pos = np.array([self.camera_distance, 0.0, 0.0])

        total_pixels = self.width * self.height
        processed = 0

        # Render each pixel
        for y in range(self.height):
            if not self.is_rendering:
                break

            for x in range(self.width):
                # Normalized device coordinates
                ndc_x = (2.0 * x / self.width - 1.0) * aspect * np.tan(fov_rad / 2)
                ndc_y = (1.0 - 2.0 * y / self.height) * np.tan(fov_rad / 2)

                # Ray direction (from camera toward black hole)
                direction = np.array([-1.0, ndc_x, ndc_y])
                direction = direction / np.linalg.norm(direction)

                # Trace ray
                color = self.trace_ray(camera_pos, direction, skybox)
                image[y, x] = color

                processed += 1
                if progress_callback and processed % 100 == 0:
                    progress_callback(processed / total_pixels * 100)

        self.rendered_image = image
        self.is_rendering = False
        return image


class BlackHoleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("General Relativity Black Hole Ray Tracer")
        self.root.geometry("900x700")

        self.raytracer = BlackHoleRayTracer()

        self.setup_ui()

    def setup_ui(self):
        # Control panel
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Title
        title_label = ttk.Label(control_frame, text="Black Hole Gravitational Lensing",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        # Parameters frame
        params_frame = ttk.LabelFrame(control_frame, text="Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=5)

        # Camera distance
        ttk.Label(params_frame, text="Camera Distance:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.distance_var = tk.DoubleVar(value=20.0)
        distance_scale = ttk.Scale(params_frame, from_=10.0, to=50.0,
                                   variable=self.distance_var, orient=tk.HORIZONTAL, length=200)
        distance_scale.grid(row=0, column=1, padx=5)
        self.distance_label = ttk.Label(params_frame, text="20.0")
        self.distance_label.grid(row=0, column=2)
        distance_scale.configure(command=lambda v: self.distance_label.config(text=f"{float(v):.1f}"))

        # Field of view
        ttk.Label(params_frame, text="Field of View:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.fov_var = tk.DoubleVar(value=60.0)
        fov_scale = ttk.Scale(params_frame, from_=30.0, to=90.0,
                              variable=self.fov_var, orient=tk.HORIZONTAL, length=200)
        fov_scale.grid(row=1, column=1, padx=5)
        self.fov_label = ttk.Label(params_frame, text="60.0°")
        self.fov_label.grid(row=1, column=2)
        fov_scale.configure(command=lambda v: self.fov_label.config(text=f"{float(v):.1f}°"))

        # Resolution
        ttk.Label(params_frame, text="Resolution:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.res_var = tk.IntVar(value=400)
        res_combo = ttk.Combobox(params_frame, textvariable=self.res_var,
                                 values=[200, 300, 400, 500, 600], width=10, state='readonly')
        res_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        res_combo.current(2)

        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10)

        self.render_button = ttk.Button(button_frame, text="Render Black Hole",
                                        command=self.start_render, width=20)
        self.render_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                      command=self.stop_render, width=10, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.pack(pady=5)

        self.status_label = ttk.Label(control_frame, text="Ready to render")
        self.status_label.pack()

        # Canvas for display
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.ax.set_title("Black Hole with Einstein Ring")
        self.ax.axis('off')

        # Initial placeholder
        placeholder = np.zeros((400, 400, 3), dtype=np.uint8)
        self.ax.imshow(placeholder)

        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Info text
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)

        info_text = ("This ray tracer integrates geodesic equations in Schwarzschild spacetime.\n"
                     "Black region = Event horizon | Distorted stars = Gravitational lensing | "
                     "Bright ring = Einstein ring")
        ttk.Label(info_frame, text=info_text, font=("Arial", 9),
                  foreground="blue", wraplength=800).pack()

    def update_progress(self, value):
        """Update progress bar (thread-safe)"""
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.status_label.config(
            text=f"Rendering... {value:.1f}%"))

    def render_complete(self, image):
        """Called when rendering completes"""
        if image is not None:
            self.ax.clear()
            self.ax.imshow(image)
            self.ax.set_title("Black Hole with Gravitational Lensing")
            self.ax.axis('off')
            self.canvas.draw()

            self.status_label.config(text="Rendering complete!")
            messagebox.showinfo("Complete", "Black hole rendering finished!")
        else:
            self.status_label.config(text="Rendering stopped")

        self.render_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(0)

    def render_thread(self):
        """Background rendering thread"""
        try:
            image = self.raytracer.render(progress_callback=self.update_progress)
            self.root.after(0, lambda: self.render_complete(image))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Rendering failed: {str(e)}"))
            self.root.after(0, lambda: self.render_complete(None))

    def start_render(self):
        """Start rendering in background thread"""
        # Update parameters
        self.raytracer.camera_distance = self.distance_var.get()
        self.raytracer.fov = self.fov_var.get()
        res = self.res_var.get()
        self.raytracer.width = res
        self.raytracer.height = res

        # Update UI
        self.render_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Starting render...")
        self.progress_var.set(0)

        # Start rendering thread
        thread = threading.Thread(target=self.render_thread, daemon=True)
        thread.start()

    def stop_render(self):
        """Stop rendering"""
        self.raytracer.is_rendering = False
        self.status_label.config(text="Stopping...")
        self.stop_button.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = BlackHoleGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
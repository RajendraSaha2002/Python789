"""
Automated Vegetation Health Monitor (NDVI Calculator)
Analyzes satellite imagery to assess vegetation health using NDVI
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import threading
import time


class NDVIMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("🛰️ Vegetation Health Monitor - NDVI Analysis")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e2e")

        # Data storage
        self.red_band = None
        self.nir_band = None
        self.ndvi_data = None
        self.animation = None
        self.demo_mode = False

        self.setup_gui()

    def setup_gui(self):
        # Title Frame
        title_frame = tk.Frame(self.root, bg="#1e1e2e")
        title_frame.pack(pady=10)

        title_label = tk.Label(
            title_frame,
            text="🛰️ Automated Vegetation Health Monitor",
            font=("Arial", 24, "bold"),
            bg="#1e1e2e",
            fg="#89b4fa"
        )
        title_label.pack()

        subtitle = tk.Label(
            title_frame,
            text="NDVI Analysis using Sun-Synchronous Satellite Data",
            font=("Arial", 12),
            bg="#1e1e2e",
            fg="#cdd6f4"
        )
        subtitle.pack()

        # Control Panel
        control_frame = tk.Frame(self.root, bg="#313244", relief=tk.RAISED, bd=2)
        control_frame.pack(pady=10, padx=20, fill=tk.X)

        # File Upload Section
        upload_frame = tk.LabelFrame(
            control_frame,
            text="📁 Data Input",
            bg="#313244",
            fg="#cdd6f4",
            font=("Arial", 11, "bold")
        )
        upload_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.red_btn = tk.Button(
            upload_frame,
            text="Load Red Band (B4)",
            command=self.load_red_band,
            bg="#f38ba8",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=10
        )
        self.red_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.nir_btn = tk.Button(
            upload_frame,
            text="Load NIR Band (B5)",
            command=self.load_nir_band,
            bg="#89b4fa",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=10
        )
        self.nir_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Action Buttons
        action_frame = tk.LabelFrame(
            control_frame,
            text="⚙️ Actions",
            bg="#313244",
            fg="#cdd6f4",
            font=("Arial", 11, "bold")
        )
        action_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.calc_btn = tk.Button(
            action_frame,
            text="Calculate NDVI",
            command=self.calculate_ndvi,
            bg="#a6e3a1",
            fg="#1e1e2e",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            state=tk.DISABLED
        )
        self.calc_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.demo_btn = tk.Button(
            action_frame,
            text="🎬 Demo Mode",
            command=self.start_demo,
            bg="#f9e2af",
            fg="#1e1e2e",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15
        )
        self.demo_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_btn = tk.Button(
            action_frame,
            text="Clear All",
            command=self.clear_all,
            bg="#585b70",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Status Frame
        self.status_label = tk.Label(
            self.root,
            text="Status: Ready to load satellite imagery",
            bg="#1e1e2e",
            fg="#94e2d5",
            font=("Arial", 10),
            anchor="w"
        )
        self.status_label.pack(pady=5, padx=20, fill=tk.X)

        # Visualization Frame
        viz_frame = tk.Frame(self.root, bg="#1e1e2e")
        viz_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        # Create matplotlib figure
        self.fig, self.axes = plt.subplots(1, 3, figsize=(14, 5))
        self.fig.patch.set_facecolor('#1e1e2e')

        for ax in self.axes:
            ax.set_facecolor('#313244')
            ax.tick_params(colors='#cdd6f4')
            for spine in ax.spines.values():
                spine.set_edgecolor('#585b70')

        self.axes[0].set_title('Red Band (B4)', color='#f38ba8', fontsize=12, fontweight='bold')
        self.axes[1].set_title('NIR Band (B5)', color='#89b4fa', fontsize=12, fontweight='bold')
        self.axes[2].set_title('NDVI Heat Map', color='#a6e3a1', fontsize=12, fontweight='bold')

        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Info Panel
        info_frame = tk.Frame(self.root, bg="#313244", relief=tk.RAISED, bd=2)
        info_frame.pack(pady=10, padx=20, fill=tk.X)

        info_text = """
        📊 NDVI Formula: (NIR - Red) / (NIR + Red)  |  
        🟢 > 0.5: Healthy Vegetation  |  🟡 0.2-0.5: Moderate  |  🟤 < 0.2: Barren/Stressed
        """

        info_label = tk.Label(
            info_frame,
            text=info_text,
            bg="#313244",
            fg="#cdd6f4",
            font=("Arial", 9)
        )
        info_label.pack(pady=5)

    def load_red_band(self):
        try:
            file_path = filedialog.askopenfilename(
                title="Select Red Band Image",
                filetypes=[("Image files", "*.tif *.tiff *.png *.jpg *.jpeg"), ("All files", "*.*")]
            )

            if file_path:
                img = Image.open(file_path).convert('L')
                self.red_band = np.array(img).astype(float)

                # Normalize to 0-1 range
                if self.red_band.max() > 1:
                    self.red_band = self.red_band / 255.0

                self.axes[0].clear()
                self.axes[0].imshow(self.red_band, cmap='Reds')
                self.axes[0].set_title('Red Band (B4)', color='#f38ba8', fontsize=12, fontweight='bold')
                self.axes[0].axis('off')
                self.canvas.draw()

                self.status_label.config(text="✅ Red band loaded successfully")
                self.check_ready_to_calculate()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Red band: {str(e)}")

    def load_nir_band(self):
        try:
            file_path = filedialog.askopenfilename(
                title="Select NIR Band Image",
                filetypes=[("Image files", "*.tif *.tiff *.png *.jpg *.jpeg"), ("All files", "*.*")]
            )

            if file_path:
                img = Image.open(file_path).convert('L')
                self.nir_band = np.array(img).astype(float)

                # Normalize to 0-1 range
                if self.nir_band.max() > 1:
                    self.nir_band = self.nir_band / 255.0

                self.axes[1].clear()
                self.axes[1].imshow(self.nir_band, cmap='Blues')
                self.axes[1].set_title('NIR Band (B5)', color='#89b4fa', fontsize=12, fontweight='bold')
                self.axes[1].axis('off')
                self.canvas.draw()

                self.status_label.config(text="✅ NIR band loaded successfully")
                self.check_ready_to_calculate()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load NIR band: {str(e)}")

    def check_ready_to_calculate(self):
        if self.red_band is not None and self.nir_band is not None:
            if self.red_band.shape == self.nir_band.shape:
                self.calc_btn.config(state=tk.NORMAL)
            else:
                messagebox.showwarning("Warning", "Red and NIR bands must have the same dimensions!")
                self.calc_btn.config(state=tk.DISABLED)

    def calculate_ndvi(self):
        if self.red_band is None or self.nir_band is None:
            messagebox.showwarning("Warning", "Please load both Red and NIR bands first!")
            return

        try:
            self.status_label.config(text="🔄 Calculating NDVI...")
            self.root.update()

            # NDVI Calculation: (NIR - Red) / (NIR + Red)
            numerator = self.nir_band - self.red_band
            denominator = self.nir_band + self.red_band

            # Avoid division by zero
            denominator = np.where(denominator == 0, 0.0001, denominator)
            self.ndvi_data = numerator / denominator

            # Clip values to [-1, 1] range
            self.ndvi_data = np.clip(self.ndvi_data, -1, 1)

            # Create custom colormap
            colors = ['#8B4513', '#D2B48C', '#F4E4C1', '#FFFACD', '#90EE90', '#228B22', '#006400']
            n_bins = 100
            cmap = LinearSegmentedColormap.from_list('vegetation', colors, N=n_bins)

            # Display NDVI
            self.axes[2].clear()
            im = self.axes[2].imshow(self.ndvi_data, cmap=cmap, vmin=-1, vmax=1)
            self.axes[2].set_title('NDVI Heat Map', color='#a6e3a1', fontsize=12, fontweight='bold')
            self.axes[2].axis('off')

            # Add colorbar
            cbar = self.fig.colorbar(im, ax=self.axes[2], fraction=0.046, pad=0.04)
            cbar.set_label('NDVI Value', color='#cdd6f4')
            cbar.ax.tick_params(colors='#cdd6f4')

            self.canvas.draw()

            # Calculate statistics
            avg_ndvi = np.mean(self.ndvi_data)
            healthy_pct = (np.sum(self.ndvi_data > 0.5) / self.ndvi_data.size) * 100

            self.status_label.config(
                text=f"✅ NDVI calculated | Avg: {avg_ndvi:.3f} | Healthy vegetation: {healthy_pct:.1f}%"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate NDVI: {str(e)}")

    def start_demo(self):
        """Generate synthetic satellite data for demonstration"""
        self.demo_mode = True
        self.status_label.config(text="🎬 Generating synthetic satellite data...")

        # Generate synthetic data
        size = 300
        x = np.linspace(-2, 2, size)
        y = np.linspace(-2, 2, size)
        X, Y = np.meshgrid(x, y)

        # Synthetic Red band (higher in bare soil areas)
        self.red_band = 0.4 + 0.3 * np.exp(-(X ** 2 + Y ** 2) / 2) + 0.1 * np.random.rand(size, size)
        self.red_band = np.clip(self.red_band, 0, 1)

        # Synthetic NIR band (higher in vegetated areas)
        self.nir_band = 0.3 + 0.5 * np.exp(-(X ** 2 + Y ** 2) / 2) + 0.1 * np.random.rand(size, size)
        self.nir_band = np.clip(self.nir_band, 0, 1)

        # Display bands
        self.axes[0].clear()
        self.axes[0].imshow(self.red_band, cmap='Reds')
        self.axes[0].set_title('Red Band (B4) - Demo', color='#f38ba8', fontsize=12, fontweight='bold')
        self.axes[0].axis('off')

        self.axes[1].clear()
        self.axes[1].imshow(self.nir_band, cmap='Blues')
        self.axes[1].set_title('NIR Band (B5) - Demo', color='#89b4fa', fontsize=12, fontweight='bold')
        self.axes[1].axis('off')

        self.canvas.draw()

        self.calc_btn.config(state=tk.NORMAL)
        self.status_label.config(text="✅ Demo data generated | Click 'Calculate NDVI' to analyze")

        # Auto-calculate after a delay
        self.root.after(1000, self.calculate_ndvi)

    def clear_all(self):
        """Clear all data and visualizations"""
        self.red_band = None
        self.nir_band = None
        self.ndvi_data = None

        for ax in self.axes:
            ax.clear()
            ax.set_facecolor('#313244')
            ax.axis('off')

        self.axes[0].set_title('Red Band (B4)', color='#f38ba8', fontsize=12, fontweight='bold')
        self.axes[1].set_title('NIR Band (B5)', color='#89b4fa', fontsize=12, fontweight='bold')
        self.axes[2].set_title('NDVI Heat Map', color='#a6e3a1', fontsize=12, fontweight='bold')

        self.canvas.draw()
        self.calc_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Ready to load satellite imagery")


# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    app = NDVIMonitor(root)
    root.mainloop()
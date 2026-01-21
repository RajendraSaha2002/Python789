"""
RADAR Waveform Generator (DDS/DAC Simulator)
Python GUI Application for PyCharm

Requirements:
pip install numpy matplotlib scipy

Author: RADAR Waveform Generator
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scipy import signal


class RadarWaveformGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("RADAR Waveform Generator (DDS/DAC)")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e293b')

        # Default parameters
        self.waveform_type = tk.StringVar(value="chirp")
        self.samples = tk.IntVar(value=1024)
        self.amplitude = tk.DoubleVar(value=1.0)
        self.frequency = tk.DoubleVar(value=10.0)
        self.bandwidth = tk.DoubleVar(value=20.0)
        self.pulse_width = tk.DoubleVar(value=0.5)
        self.barker_code = tk.StringVar(value="13")
        self.dac_bits = tk.IntVar(value=12)
        self.sample_rate = tk.DoubleVar(value=100.0)

        self.current_waveform = None
        self.current_time = None

        self.setup_ui()
        self.generate_waveform()

    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e293b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Controls
        control_frame = tk.Frame(main_frame, bg='#334155', relief=tk.RAISED, borderwidth=2)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        # Title
        title_label = tk.Label(control_frame, text="⚡ RADAR Waveform Generator",
                               font=("Arial", 16, "bold"), bg='#334155', fg='#60a5fa')
        title_label.pack(pady=15)

        # Scrollable frame for controls
        canvas = tk.Canvas(control_frame, bg='#334155', highlightthickness=0, width=350)
        scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#334155')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")

        # Controls
        self.add_control_section(scrollable_frame)

        # Right panel - Plots
        plot_frame = tk.Frame(main_frame, bg='#1e293b')
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create matplotlib figures
        self.setup_plots(plot_frame)

    def add_control_section(self, parent):
        # Waveform Type
        self.create_label(parent, "Waveform Type")
        waveform_combo = ttk.Combobox(parent, textvariable=self.waveform_type,
                                      values=["chirp", "square", "gaussian", "barker", "prn"],
                                      state="readonly", width=30)
        waveform_combo.pack(pady=5)
        waveform_combo.bind("<<ComboboxSelected>>", lambda e: self.generate_waveform())

        # Samples
        self.create_slider(parent, "Samples", self.samples, 256, 4096, 256)

        # Amplitude
        self.create_slider(parent, "Amplitude", self.amplitude, 0.1, 2.0, 0.1)

        # DAC Resolution
        self.create_slider(parent, "DAC Resolution (bits)", self.dac_bits, 8, 16, 1)

        # Sample Rate
        self.create_slider(parent, "Sample Rate (MHz)", self.sample_rate, 10, 200, 10)

        # Frequency (for chirp and barker)
        self.create_slider(parent, "Start Frequency (MHz)", self.frequency, 1, 50, 1)

        # Bandwidth (for chirp)
        self.create_slider(parent, "Bandwidth (MHz)", self.bandwidth, 5, 100, 5)

        # Pulse Width (for square and gaussian)
        self.create_slider(parent, "Pulse Width (s)", self.pulse_width, 0.1, 1.0, 0.05)

        # Barker Code
        self.create_label(parent, "Barker Code Length")
        barker_combo = ttk.Combobox(parent, textvariable=self.barker_code,
                                    values=["7", "11", "13"],
                                    state="readonly", width=30)
        barker_combo.pack(pady=5)
        barker_combo.bind("<<ComboboxSelected>>", lambda e: self.generate_waveform())

        # Buttons
        button_frame = tk.Frame(parent, bg='#334155')
        button_frame.pack(pady=20)

        generate_btn = tk.Button(button_frame, text="🔄 Regenerate",
                                 command=self.generate_waveform,
                                 bg='#3b82f6', fg='white', font=("Arial", 10, "bold"),
                                 padx=20, pady=10, relief=tk.RAISED, borderwidth=2)
        generate_btn.pack(pady=5)

        export_btn = tk.Button(button_frame, text="💾 Export Python Script",
                               command=self.export_script,
                               bg='#10b981', fg='white', font=("Arial", 10, "bold"),
                               padx=20, pady=10, relief=tk.RAISED, borderwidth=2)
        export_btn.pack(pady=5)

        save_data_btn = tk.Button(button_frame, text="📊 Save Waveform Data",
                                  command=self.save_waveform_data,
                                  bg='#f59e0b', fg='white', font=("Arial", 10, "bold"),
                                  padx=20, pady=10, relief=tk.RAISED, borderwidth=2)
        save_data_btn.pack(pady=5)

    def create_label(self, parent, text):
        label = tk.Label(parent, text=text, bg='#334155', fg='#93c5fd',
                         font=("Arial", 10, "bold"))
        label.pack(pady=(10, 5))

    def create_slider(self, parent, label_text, variable, from_, to, resolution):
        self.create_label(parent, f"{label_text}: {variable.get()}")

        slider = tk.Scale(parent, from_=from_, to=to, resolution=resolution,
                          variable=variable, orient=tk.HORIZONTAL, length=300,
                          bg='#475569', fg='white', troughcolor='#1e293b',
                          highlightthickness=0)
        slider.pack(pady=5)
        slider.bind("<ButtonRelease-1>", lambda e: self.generate_waveform())

        # Update label
        def update_label(*args):
            for widget in parent.winfo_children():
                if isinstance(widget, tk.Label) and label_text in widget.cget("text"):
                    widget.config(text=f"{label_text}: {variable.get()}")

        variable.trace_add("write", update_label)

    def setup_plots(self, parent):
        # Create figure with subplots
        self.fig = Figure(figsize=(10, 8), facecolor='#1e293b')

        # Time domain plot
        self.ax1 = self.fig.add_subplot(211)
        self.ax1.set_facecolor('#0f172a')
        self.ax1.set_title('Time Domain Waveform', color='white', fontsize=12, fontweight='bold')
        self.ax1.set_xlabel('Time (s)', color='white')
        self.ax1.set_ylabel('Amplitude', color='white')
        self.ax1.tick_params(colors='white')
        self.ax1.grid(True, alpha=0.3, color='#475569')

        # Frequency domain plot
        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_facecolor('#0f172a')
        self.ax2.set_title('Frequency Spectrum', color='white', fontsize=12, fontweight='bold')
        self.ax2.set_xlabel('Frequency (MHz)', color='white')
        self.ax2.set_ylabel('Magnitude (dB)', color='white')
        self.ax2.tick_params(colors='white')
        self.ax2.grid(True, alpha=0.3, color='#475569')

        self.fig.tight_layout()

        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def generate_waveform(self):
        samples = self.samples.get()
        amplitude = self.amplitude.get()
        freq = self.frequency.get()
        bw = self.bandwidth.get()
        pw = self.pulse_width.get()
        wf_type = self.waveform_type.get()

        # Time vector
        duration = 1.0
        t = np.linspace(0, duration, samples)

        # Generate waveform
        if wf_type == "chirp":
            # Linear FM Chirp
            f0 = freq * 1e6
            f1 = (freq + bw) * 1e6
            chirp_sig = signal.chirp(t, f0, duration, f1, method='linear')
            waveform = amplitude * chirp_sig

        elif wf_type == "square":
            # Square pulse
            waveform = np.where(t < pw, amplitude, 0)

        elif wf_type == "gaussian":
            # Gaussian pulse
            tc = duration / 2
            sigma = pw / 6
            waveform = amplitude * np.exp(-(t - tc) ** 2 / (2 * sigma ** 2))

        elif wf_type == "barker":
            # Barker code
            codes = {
                '7': [1, 1, 1, -1, -1, 1, -1],
                '11': [1, 1, 1, -1, -1, -1, 1, -1, -1, 1, -1],
                '13': [1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1]
            }
            code = codes[self.barker_code.get()]
            chip_width = duration / len(code)
            chip_indices = np.floor(t / chip_width).astype(int)
            chip_indices = np.clip(chip_indices, 0, len(code) - 1)
            code_signal = np.array([code[i] for i in chip_indices])
            carrier = np.sin(2 * np.pi * freq * 1e6 * t)
            waveform = amplitude * code_signal * carrier

        else:  # PRN
            np.random.seed(42)
            waveform = amplitude * np.random.uniform(-1, 1, samples)

        # DAC Quantization
        dac_bits = self.dac_bits.get()
        max_val = 2 ** (dac_bits - 1) - 1
        quantized = np.round(waveform * max_val) / max_val

        # Store for export
        self.current_waveform = quantized
        self.current_time = t

        # Update plots
        self.update_plots(t, waveform, quantized)

    def update_plots(self, t, original, quantized):
        # Clear plots
        self.ax1.clear()
        self.ax2.clear()

        # Time domain
        self.ax1.plot(t, original, 'g-', alpha=0.5, linewidth=1, label='Original')
        self.ax1.plot(t, quantized, 'b-', linewidth=1.5, label='Quantized (DAC)')
        self.ax1.set_title('Time Domain Waveform', color='white', fontsize=12, fontweight='bold')
        self.ax1.set_xlabel('Time (s)', color='white')
        self.ax1.set_ylabel('Amplitude', color='white')
        self.ax1.tick_params(colors='white')
        self.ax1.grid(True, alpha=0.3, color='#475569')
        self.ax1.legend(facecolor='#1e293b', edgecolor='white', labelcolor='white')
        self.ax1.set_facecolor('#0f172a')

        # Frequency domain (FFT)
        N = len(quantized)
        fft_result = np.fft.fft(quantized)
        frequencies = np.fft.fftfreq(N, d=1.0 / self.sample_rate.get())

        # Positive frequencies only
        positive_freq_idx = frequencies > 0
        frequencies = frequencies[positive_freq_idx]
        magnitude_db = 20 * np.log10(np.abs(fft_result[positive_freq_idx]) + 1e-10)

        self.ax2.plot(frequencies, magnitude_db, 'orange', linewidth=2)
        self.ax2.set_title('Frequency Spectrum', color='white', fontsize=12, fontweight='bold')
        self.ax2.set_xlabel('Frequency (MHz)', color='white')
        self.ax2.set_ylabel('Magnitude (dB)', color='white')
        self.ax2.tick_params(colors='white')
        self.ax2.grid(True, alpha=0.3, color='#475569')
        self.ax2.set_facecolor('#0f172a')

        self.fig.tight_layout()
        self.canvas.draw()

    def export_script(self):
        if self.current_waveform is None:
            messagebox.showwarning("No Data", "Please generate a waveform first!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            initialfile="radar_waveform_script.py"
        )

        if filename:
            script_content = self.generate_python_script()
            with open(filename, 'w') as f:
                f.write(script_content)
            messagebox.showinfo("Success", f"Python script saved to:\n{filename}")

    def generate_python_script(self):
        wf_type = self.waveform_type.get()

        script = f'''"""
RADAR Waveform Generator Script
Generated DAC Configuration
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

# Parameters
SAMPLES = {self.samples.get()}
AMPLITUDE = {self.amplitude.get()}
DAC_BITS = {self.dac_bits.get()}
SAMPLE_RATE = {self.sample_rate.get()}  # MHz
WAVEFORM_TYPE = "{wf_type}"

# Waveform specific parameters
FREQUENCY = {self.frequency.get()}  # MHz
BANDWIDTH = {self.bandwidth.get()}  # MHz
PULSE_WIDTH = {self.pulse_width.get()}  # seconds
BARKER_CODE = "{self.barker_code.get()}"

# Generate time vector
duration = 1.0
t = np.linspace(0, duration, SAMPLES)

# Generate waveform
'''

        if wf_type == "chirp":
            script += '''f0 = FREQUENCY * 1e6
f1 = (FREQUENCY + BANDWIDTH) * 1e6
waveform = AMPLITUDE * signal.chirp(t, f0, duration, f1, method='linear')
'''
        elif wf_type == "square":
            script += '''waveform = np.where(t < PULSE_WIDTH, AMPLITUDE, 0)
'''
        elif wf_type == "gaussian":
            script += '''tc = duration / 2
sigma = PULSE_WIDTH / 6
waveform = AMPLITUDE * np.exp(-(t - tc)**2 / (2 * sigma**2))
'''
        elif wf_type == "barker":
            script += '''codes = {
    '7': [1, 1, 1, -1, -1, 1, -1],
    '11': [1, 1, 1, -1, -1, -1, 1, -1, -1, 1, -1],
    '13': [1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1]
}
code = codes[BARKER_CODE]
chip_width = duration / len(code)
chip_indices = np.floor(t / chip_width).astype(int)
chip_indices = np.clip(chip_indices, 0, len(code) - 1)
code_signal = np.array([code[i] for i in chip_indices])
carrier = np.sin(2 * np.pi * FREQUENCY * 1e6 * t)
waveform = AMPLITUDE * code_signal * carrier
'''
        else:
            script += '''np.random.seed(42)
waveform = AMPLITUDE * np.random.uniform(-1, 1, SAMPLES)
'''

        script += '''
# Quantize to DAC resolution
max_val = 2**(DAC_BITS - 1) - 1
quantized_signal = np.round(waveform * max_val).astype(int)

# Save to file
np.savetxt('waveform_data.csv', quantized_signal, delimiter=',', fmt='%d')
print(f"Generated {len(quantized_signal)} samples")
print(f"DAC range: [{quantized_signal.min()}, {quantized_signal.max()}]")

# Plot
plt.figure(figsize=(12, 6))
plt.subplot(211)
plt.plot(t, waveform, label='Original')
plt.plot(t, quantized_signal / max_val, label='Quantized')
plt.xlabel('Time (s)')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(True)
plt.title('RADAR Waveform - Time Domain')

plt.subplot(212)
fft_result = np.fft.fft(quantized_signal)
frequencies = np.fft.fftfreq(len(quantized_signal), d=1.0/SAMPLE_RATE)
plt.plot(frequencies[:len(frequencies)//2], 
         20*np.log10(np.abs(fft_result[:len(fft_result)//2]) + 1e-10))
plt.xlabel('Frequency (MHz)')
plt.ylabel('Magnitude (dB)')
plt.grid(True)
plt.title('RADAR Waveform - Frequency Domain')

plt.tight_layout()
plt.show()
'''
        return script

    def save_waveform_data(self):
        if self.current_waveform is None:
            messagebox.showwarning("No Data", "Please generate a waveform first!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="waveform_data.csv"
        )

        if filename:
            # Quantize to integer DAC values
            max_val = 2 ** (self.dac_bits.get() - 1) - 1
            dac_values = np.round(self.current_waveform * max_val).astype(int)

            np.savetxt(filename, dac_values, delimiter=',', fmt='%d',
                       header=f'DAC Values ({self.dac_bits.get()}-bit resolution)')
            messagebox.showinfo("Success", f"Waveform data saved to:\n{filename}")


def main():
    root = tk.Tk()
    app = RadarWaveformGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
import sys
import numpy as np
from scipy.signal import butter, lfilter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLCDNumber, QFrame)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont
import pyqtgraph as pg


# --- Signal Processing & Physics Engine ---

class ECGPhysics:
    def __init__(self, sample_rate=500):
        self.fs = sample_rate
        self.t_step = 1.0 / self.fs
        self.phase = 0.0
        self.heart_rate = 75.0  # Beats per minute
        self.target_heart_rate = 75.0
        self.noise_level = 0.0

        # Generate a standard P-QRS-T wave template
        # This is a synthetic "perfect" beat
        t = np.linspace(0, 1, self.fs)  # 1 second duration

        # Gaussian functions for P, Q, R, S, T waves
        # Form: A * exp(-(t - center)^2 / (2 * width^2))
        p_wave = 0.15 * np.exp(-((t - 0.2) ** 2) / (2 * 0.03 ** 2))
        q_wave = -0.15 * np.exp(-((t - 0.44) ** 2) / (2 * 0.01 ** 2))
        r_wave = 1.0 * np.exp(-((t - 0.5) ** 2) / (2 * 0.015 ** 2))  # The main spike
        s_wave = -0.25 * np.exp(-((t - 0.56) ** 2) / (2 * 0.01 ** 2))
        t_wave = 0.3 * np.exp(-((t - 0.8) ** 2) / (2 * 0.05 ** 2))

        # Baseline wander (simulating breathing)
        baseline = 0.05 * np.sin(2 * np.pi * 0.2 * t)

        self.beat_template = p_wave + q_wave + r_wave + s_wave + t_wave + baseline
        self.beat_len = len(self.beat_template)

    def get_data_chunk(self, num_samples):
        """Generates the next chunk of ECG data."""
        data = []
        for _ in range(num_samples):
            # Calculate current index in the beat template
            # Adjust playback speed based on Heart Rate
            # Normal beat is 60 BPM (1 second). If HR is 120, we skip through template 2x faster.
            speed_factor = self.heart_rate / 60.0

            idx = int(self.phase * self.beat_len)

            # Get base value
            if idx < self.beat_len:
                val = self.beat_template[idx]
            else:
                val = 0.0  # Isoelectric line

            # Advance phase
            self.phase += (1.0 / self.beat_len) * speed_factor
            if self.phase >= 1.0:
                self.phase = 0.0  # Loop back
                # Drift heart rate slightly for realism
                self.heart_rate += np.random.uniform(-2, 2)
                # Bound heart rate
                self.heart_rate = np.clip(self.heart_rate, 40, 160)

            # Add Noise (Muscle artifact / EMG)
            noise = np.random.normal(0, self.noise_level)

            # Add 60Hz Powerline Interference if noise is high
            if self.noise_level > 0.05:
                # We just track a simple counter for 60hz oscillation
                noise += 0.1 * np.sin(2 * np.pi * 60 * (self.phase * self.beat_len * self.t_step))

            data.append(val + noise)

        return np.array(data)


class SignalProcessor:
    def __init__(self, fs):
        self.fs = fs
        # Pan-Tompkins-ish filter parameters
        self.b, self.a = butter(2, [5.0, 15.0], btype='bandpass', fs=fs)

    def apply_filter(self, data):
        """Applies Bandpass filter (5-15Hz) to remove noise and baseline drift."""
        # Note: lfilter has state, but for a simple visual simulator,
        # filtering the buffer in chunks or the whole buffer is okay.
        # Ideally we use sosfilt for stability, but lfilter is standard.
        y = lfilter(self.b, self.a, data)
        return y

    def detect_qrs_peaks(self, data):
        """
        Simplified QRS detection logic.
        1. Square the signal (emphasize R-peaks).
        2. Thresholding.
        """
        # Enhance R-peaks
        squared = data ** 2

        # Dynamic Threshold (60% of max in the window)
        threshold = 0.6 * np.max(squared)

        # Find indices above threshold
        # We need a minimum distance between peaks to avoid double counting (refractory period)
        # 200ms refractory period = 0.2 * fs
        min_dist = int(0.2 * self.fs)

        peaks = []
        last_peak = -min_dist

        for i in range(len(squared)):
            if squared[i] > threshold:
                if i - last_peak > min_dist:
                    peaks.append(i)
                    last_peak = i

        return peaks


# --- Main GUI ---

class ArrhythmiaMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ICU Monitor: Real-Time Arrhythmia Detection")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #101010; color: #00FF00;")

        # Configuration
        self.fs = 250  # Sample Rate
        self.buffer_size = 1000  # 4 seconds of data
        self.data_buffer = np.zeros(self.buffer_size)
        self.display_buffer = np.zeros(self.buffer_size)

        # Modules
        self.physics = ECGPhysics(self.fs)
        self.dsp = SignalProcessor(self.fs)

        # State
        self.filter_enabled = False
        self.last_bpm_update = 0

        self.init_ui()

        # Timer for Animation (update every 20ms = 50 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_monitor)
        self.timer.start(20)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL: Controls & Vitals ---
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(20)

        # Heart Rate Display
        self.lcd_bpm = QLCDNumber()
        self.lcd_bpm.setDigitCount(3)
        self.lcd_bpm.setStyleSheet("border: 2px solid #333; color: #00FF00; background: #000;")
        self.lcd_bpm.setMinimumHeight(100)
        controls_layout.addWidget(QLabel("HEART RATE (BPM)"))
        controls_layout.addWidget(self.lcd_bpm)

        # Status Alarm
        self.lbl_status = QLabel("NORMAL SINUS RHYTHM")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.lbl_status.setStyleSheet("background-color: #003300; color: #00FF00; padding: 10px; border-radius: 5px;")
        controls_layout.addWidget(self.lbl_status)

        # Controls Group
        btn_noise = QPushButton("Inject Noise (Artifact)")
        btn_noise.setCheckable(True)
        btn_noise.setStyleSheet("""
            QPushButton { background-color: #333; color: white; padding: 10px; border: 1px solid #555; }
            QPushButton:checked { background-color: #FF4444; border: 1px solid red; }
        """)
        btn_noise.toggled.connect(self.toggle_noise)
        controls_layout.addWidget(btn_noise)

        btn_filter = QPushButton("Enable Digital Filter")
        btn_filter.setCheckable(True)
        btn_filter.setStyleSheet("""
            QPushButton { background-color: #333; color: white; padding: 10px; border: 1px solid #555; }
            QPushButton:checked { background-color: #4444FF; border: 1px solid blue; }
        """)
        btn_filter.toggled.connect(self.toggle_filter)
        controls_layout.addWidget(btn_filter)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout, 1)  # 20% width

        # --- RIGHT PANEL: Oscilloscope ---
        # PyQtGraph setup
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(-1.5, 2.5)
        self.plot_widget.setLabel('left', 'Voltage (mV)')
        self.plot_widget.setLabel('bottom', 'Time (samples)')
        self.plot_widget.hideAxis('bottom')  # Mimic hospital monitor

        # The Green Line
        pen = pg.mkPen(color=(0, 255, 0), width=2)
        self.curve = self.plot_widget.plot(self.display_buffer, pen=pen)

        main_layout.addWidget(self.plot_widget, 4)  # 80% width

    def toggle_noise(self, checked):
        # Adds gaussian noise to simulate muscle movement
        self.physics.noise_level = 0.15 if checked else 0.0

    def toggle_filter(self, checked):
        self.filter_enabled = checked

    def update_monitor(self):
        # 1. Get new data from "Patient"
        # We fetch a small chunk (e.g., 5 samples) to advance time
        samples_to_fetch = 5
        new_data = self.physics.get_data_chunk(samples_to_fetch)

        # 2. Update Data Buffer (Rolling)
        # Shift everything left, put new data at right
        self.data_buffer = np.roll(self.data_buffer, -samples_to_fetch)
        self.data_buffer[-samples_to_fetch:] = new_data

        # 3. Apply Filter (if enabled)
        if self.filter_enabled:
            # We filter the whole buffer for visual smoothness
            # In a real efficient C++ system we'd filter only new points stream-wise
            processed_data = self.dsp.apply_filter(self.data_buffer)
        else:
            processed_data = self.data_buffer

        # 4. Update Plot
        self.curve.setData(processed_data)

        # 5. Calculate BPM & Analyze (Every 0.5 seconds roughly)
        self.last_bpm_update += 1
        if self.last_bpm_update > 25:  # 25 * 20ms = 500ms
            self.analyze_signal(processed_data)
            self.last_bpm_update = 0

    def analyze_signal(self, data):
        # QRS Detection
        # Use a filtered version for detection even if display is noisy
        if not self.filter_enabled:
            analysis_data = self.dsp.apply_filter(data)
        else:
            analysis_data = data

        peaks = self.dsp.detect_qrs_peaks(analysis_data)

        if len(peaks) > 1:
            # Calculate RR intervals
            rr_intervals = np.diff(peaks)
            avg_samples = np.mean(rr_intervals)
            bpm = (self.fs * 60) / avg_samples

            # Update Display
            self.lcd_bpm.display(int(bpm))

            # Check Alarms
            if bpm < 60:
                self.lbl_status.setText("ALARM: BRADYCARDIA")
                self.lbl_status.setStyleSheet(
                    "background-color: #FF0000; color: white; padding: 10px; border-radius: 5px;")
            elif bpm > 100:
                self.lbl_status.setText("ALARM: TACHYCARDIA")
                self.lbl_status.setStyleSheet(
                    "background-color: #FF0000; color: white; padding: 10px; border-radius: 5px;")
            else:
                self.lbl_status.setText("NORMAL SINUS RHYTHM")
                self.lbl_status.setStyleSheet(
                    "background-color: #003300; color: #00FF00; padding: 10px; border-radius: 5px;")
        else:
            self.lcd_bpm.display("---")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArrhythmiaMonitor()
    window.show()
    sys.exit(app.exec_())
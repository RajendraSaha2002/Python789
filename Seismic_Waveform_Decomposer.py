import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, spectrogram
from matplotlib.collections import LineCollection


class SeismicDecomposer:
    def __init__(self, fs=100.0, duration=60.0):
        self.fs = fs  # Sampling rate in Hz
        self.duration = duration  # Total trace duration in seconds
        self.dt = 1.0 / fs
        self.t = np.arange(0, duration, self.dt)
        self.n_pts = len(self.t)

        # P and S wave arrival times
        self.p_arrival = 15.0
        self.s_arrival = 25.0

    def synthesize_data(self):
        """Generates realistic 3-component seismograms with noise, P, and S waves."""
        np.random.seed(42)  # For reproducibility

        # 1. Base random background noise
        z = np.random.normal(0, 0.1, self.n_pts)
        n = np.random.normal(0, 0.1, self.n_pts)
        e = np.random.normal(0, 0.1, self.n_pts)

        # 2. Add Low-Frequency microseismic noise (~0.2 Hz) & High-Frequency electrical noise (40 Hz)
        lf_noise = 0.5 * np.sin(2 * np.pi * 0.2 * self.t)
        hf_noise = 0.3 * np.sin(2 * np.pi * 40.0 * self.t)

        for comp in (z, n, e):
            comp += lf_noise + hf_noise

        # 3. P-Wave (Compressional): Dominant on Z (Vertical) and N (Radial) components. Faster, higher freq.
        p_idx = self.t >= self.p_arrival
        p_env = np.zeros(self.n_pts)
        # Exponentially decaying envelope
        p_env[p_idx] = np.exp(-(self.t[p_idx] - self.p_arrival) * 2.5) * (self.t[p_idx] - self.p_arrival) * 8

        p_wave_z = p_env * np.sin(2 * np.pi * 6.5 * self.t) * 2.5  # 6.5 Hz main frequency
        p_wave_n = p_env * np.sin(2 * np.pi * 6.5 * self.t + 0.2) * 1.2

        # 4. S-Wave (Shear): Dominant on N and E (Horizontal) components. Slower, lower freq, larger amplitude.
        s_idx = self.t >= self.s_arrival
        s_env = np.zeros(self.n_pts)
        s_env[s_idx] = np.exp(-(self.t[s_idx] - self.s_arrival) * 1.2) * (self.t[s_idx] - self.s_arrival) * 5

        s_wave_n = s_env * np.sin(2 * np.pi * 3.5 * self.t) * 4.0  # 3.5 Hz main frequency
        s_wave_e = s_env * np.sin(2 * np.pi * 3.0 * self.t + np.pi / 4) * 5.0
        s_wave_z = s_env * np.sin(2 * np.pi * 3.5 * self.t + 0.5) * 1.0

        # Inject waves into base traces
        z += p_wave_z + s_wave_z
        n += p_wave_n + s_wave_n
        e += s_wave_e

        return z, n, e

    def bandpass_filter(self, data, lowcut=1.0, highcut=10.0, order=4):
        """Applies a Butterworth bandpass filter using Second-Order Sections (SOS)."""
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        # We use 'sos' output format for numerical stability, especially for tight bands
        sos = butter(order, [low, high], btype='bandpass', output='sos')

        # sosfiltfilt applies the filter forward and backward to ensure ZERO phase shift,
        # which is absolutely critical so the P/S arrivals don't shift in time.
        filtered_data = sosfiltfilt(sos, data)
        return filtered_data

    def colorline(self, ax, x, y, z=None, cmap='viridis'):
        """Helper to plot multicolored hodogram lines mapping to time progression."""
        z = np.linspace(0.0, 1.0, len(x)) if z is None else z
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        norm = plt.Normalize(z.min(), z.max())
        lc = LineCollection(segments, cmap=cmap, norm=norm, alpha=0.8, linewidth=2)
        lc.set_array(z)
        ax.add_collection(lc)
        return lc

    def plot_dashboard(self, z, n, e, z_filt, n_filt, e_filt):
        """Builds the 6-panel diagnostic matplotlib figure."""
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axs = plt.subplots(3, 2, figsize=(15, 11))
        fig.suptitle('Seismic Waveform Decomposer & Triaxial Analysis', fontsize=16, fontweight='bold', y=0.96)

        # ==========================================
        # Panel 1: Raw 3C Traces
        # ==========================================
        ax1 = axs[0, 0]
        offset = 15
        ax1.plot(self.t, z + offset, 'k', label='Z (Vertical)', linewidth=0.8)
        ax1.plot(self.t, n, 'r', label='N (North)', linewidth=0.8)
        ax1.plot(self.t, e - offset, 'g', label='E (East)', linewidth=0.8)
        ax1.set_title('1. Raw 3C Synthetics (Includes LF & HF Noise)')
        ax1.set_ylabel('Amplitude (Velocity)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.set_xlim([0, self.duration])

        # ==========================================
        # Panel 2: Bandpass Filtered Traces (1-10 Hz)
        # ==========================================
        ax2 = axs[0, 1]
        ax2.plot(self.t, z_filt + offset, 'k', label='Z Filt', linewidth=1)
        ax2.plot(self.t, n_filt, 'r', label='N Filt', linewidth=1)
        ax2.plot(self.t, e_filt - offset, 'g', label='E Filt', linewidth=1)
        # Highlight Arrivals
        ax2.axvline(self.p_arrival, color='b', linestyle='--', alpha=0.5, label='P-Arrival')
        ax2.axvline(self.s_arrival, color='orange', linestyle='--', alpha=0.5, label='S-Arrival')
        ax2.set_title('2. Filtered Traces (SOS Bandpass: 1–10 Hz)')
        ax2.legend(loc='upper right', fontsize=8)
        ax2.set_xlim([0, self.duration])

        # ==========================================
        # Panel 3: Spectrogram (Z-Component)
        # ==========================================
        ax3 = axs[1, 0]
        # Using Hann windowing for optimal frequency-time resolution tradeoff
        f, t_spec, Sxx = spectrogram(z_filt, fs=self.fs, window='hann', nperseg=256, noverlap=240)
        # Convert to dB for visual clarity
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        im = ax3.pcolormesh(t_spec, f, Sxx_db, shading='gouraud', cmap='magma')
        ax3.set_title('3. Spectrogram of Filtered Z-Component')
        ax3.set_ylabel('Frequency (Hz)')
        ax3.set_ylim([0, 15])  # Zoom in on the 0-15 Hz range
        ax3.axvline(self.p_arrival, color='w', linestyle=':', alpha=0.6)
        ax3.axvline(self.s_arrival, color='w', linestyle=':', alpha=0.6)
        fig.colorbar(im, ax=ax3, label='Power (dB)', format='%+2.0f')

        # ==========================================
        # Panel 4: FFT Amplitude Spectrum
        # ==========================================
        ax4 = axs[1, 1]
        N = len(self.t)
        yf_raw = np.abs(np.fft.rfft(z)) / N
        yf_filt = np.abs(np.fft.rfft(z_filt)) / N
        xf = np.fft.rfftfreq(N, self.dt)

        ax4.plot(xf, yf_raw, color='grey', alpha=0.6, label='Raw Z Spectrum')
        ax4.plot(xf, yf_filt, color='black', linewidth=1.5, label='Filtered Z Spectrum (1-10 Hz)')
        ax4.set_title('4. Frequency Spectrum (FFT) Resolution')
        ax4.set_xlim([0, 50])
        ax4.set_xlabel('Frequency (Hz)')
        ax4.set_ylabel('Magnitude')
        ax4.legend(loc='upper right')

        # ==========================================
        # Panel 5: P-Wave Hodogram (Z vs N, Vertical Plane)
        # ==========================================
        ax5 = axs[2, 0]
        # Extract window specific to the P-Wave (14.5s to 18.0s)
        p_mask = (self.t >= self.p_arrival - 0.5) & (self.t <= self.p_arrival + 3.0)
        p_t, p_z, p_n = self.t[p_mask], z_filt[p_mask], n_filt[p_mask]

        self.colorline(ax5, p_n, p_z, z=p_t, cmap='winter')
        ax5.set_xlim([min(p_n) * 1.2, max(p_n) * 1.2])
        ax5.set_ylim([min(p_z) * 1.2, max(p_z) * 1.2])
        ax5.set_title('5. P-Wave Particle Motion (Z vs N)')
        ax5.set_xlabel('Radial Amplitude (North)')
        ax5.set_ylabel('Vertical Amplitude (Z)')
        ax5.axhline(0, color='black', linewidth=0.5, alpha=0.5)
        ax5.axvline(0, color='black', linewidth=0.5, alpha=0.5)

        # ==========================================
        # Panel 6: S-Wave Hodogram (N vs E, Horizontal Plane)
        # ==========================================
        ax6 = axs[2, 1]
        # Extract window specific to the S-Wave (24.5s to 30.0s)
        s_mask = (self.t >= self.s_arrival - 0.5) & (self.t <= self.s_arrival + 5.0)
        s_t, s_n, s_e = self.t[s_mask], n_filt[s_mask], e_filt[s_mask]

        lc = self.colorline(ax6, s_e, s_n, z=s_t, cmap='autumn')
        ax6.set_xlim([min(s_e) * 1.2, max(s_e) * 1.2])
        ax6.set_ylim([min(s_n) * 1.2, max(s_n) * 1.2])
        ax6.set_title('6. S-Wave Particle Motion (N vs E)')
        ax6.set_xlabel('Transverse Amplitude (East)')
        ax6.set_ylabel('Radial Amplitude (North)')
        ax6.axhline(0, color='black', linewidth=0.5, alpha=0.5)
        ax6.axvline(0, color='black', linewidth=0.5, alpha=0.5)
        fig.colorbar(lc, ax=ax6, label='Time Window (s)')

        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        plt.show()


if __name__ == '__main__':
    # Initialize Engine
    decomposer = SeismicDecomposer(fs=100.0, duration=60.0)

    # 1. Generate Synthetic Ground Motion
    z_raw, n_raw, e_raw = decomposer.synthesize_data()

    # 2. Apply DSP SOS Bandpass Filters (1.0 to 10.0 Hz)
    z_filtered = decomposer.bandpass_filter(z_raw)
    n_filtered = decomposer.bandpass_filter(n_raw)
    e_filtered = decomposer.bandpass_filter(e_raw)

    # 3. Process Visualizations & Render
    decomposer.plot_dashboard(z_raw, n_raw, e_raw, z_filtered, n_filtered, e_filtered)
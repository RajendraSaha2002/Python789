import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks


class RadarSystem:
    def __init__(self, fc, bandwidth, pulse_width, fs):
        """
        Initialize Radar Control Parameters
        :param fc: Carrier Frequency (Hz)
        :param bandwidth: Bandwidth of the chirp (Hz)
        :param pulse_width: Duration of the pulse (seconds)
        :param fs: Sampling Frequency (Hz)
        """
        self.c = 3e8  # Speed of light (m/s)
        self.fc = fc
        self.B = bandwidth
        self.T = pulse_width
        self.fs = fs
        self.t = np.arange(0, self.T, 1 / self.fs)  # Time vector for one pulse

    def generate_waveform(self):
        """
        CONTROL LOGIC: Generate a Linear Frequency Modulated (LFM) Chirp
        This mimics the signal sent to the DAC/Transmitter.
        """
        # LFM Chirp formula: exp(j * (2*pi*fc*t + pi*(B/T)*t^2))
        k = self.B / self.T  # Chirp slope
        tx_signal = np.exp(1j * (np.pi * k * self.t ** 2))
        return tx_signal

    def receive_signal(self, tx_signal, target_range, noise_level=0.5):
        """
        ENVIRONMENT SIMULATION:
        Simulates the signal traveling to target, bouncing, and returning.
        """
        # Calculate time delay: t_delay = 2 * R / c
        t_delay = 2 * target_range / self.c

        # Convert delay to samples
        delay_samples = int(t_delay * self.fs)

        # Create a total receive window (longer than pulse to capture echo)
        total_samples = len(tx_signal) + delay_samples + 1000
        rx_signal = np.zeros(total_samples, dtype=complex)

        # Place the delayed echo in the receive buffer
        rx_signal[delay_samples:delay_samples + len(tx_signal)] = tx_signal

        # Add White Gaussian Noise (Thermal noise in receiver)
        noise = np.random.normal(0, noise_level, total_samples) + \
                1j * np.random.normal(0, noise_level, total_samples)

        return rx_signal + noise

    def process_data(self, tx_signal, rx_signal):
        """
        DSP LOGIC: Pulse Compression (Matched Filter)
        Correlates the received signal with the transmitted signal to find the echo.
        """
        # Matched Filter: Convolution of Rx with time-reversed conjugate of Tx
        matched_filter_output = np.correlate(rx_signal, tx_signal, mode='full')

        # Get the magnitude (amplitude) of the result
        magnitude = np.abs(matched_filter_output)

        # Create a distance axis for plotting
        # The correlation peak index roughly corresponds to delay samples
        lags = np.arange(len(magnitude)) - (len(tx_signal) - 1)
        distances = (lags / self.fs) * self.c / 2

        return distances, magnitude


# --- MAIN CONTROL SCRIPT ---
if __name__ == "__main__":
    # 1. SETUP: Configure the Radar Controller
    radar = RadarSystem(
        fc=24e9,  # 24 GHz (Automotive Radar band)
        bandwidth=50e6,  # 50 MHz Bandwidth
        pulse_width=10e-6,  # 10 microseconds pulse
        fs=2e6  # 2 MHz Sampling Rate
    )

    # 2. INPUT: Define a simulated target
    real_target_distance = 300.0  # meters
    print(f"--- Radar System Initialized ---")
    print(f"Scanning for target at approx {real_target_distance}m...")

    # 3. TRANSMIT: Generate the pulse
    tx_pulse = radar.generate_waveform()

    # 4. ENVIRONMENT: Simulate the echo return
    rx_pulse = radar.receive_signal(tx_pulse, target_range=real_target_distance)

    # 5. PROCESS: Run the DSP chain
    range_axis, response = radar.process_data(tx_pulse, rx_pulse)

    # 6. DETECT: Find the peak in the response
    peaks, _ = find_peaks(response, height=np.max(response) * 0.5)  # Threshold at 50% max

    if len(peaks) > 0:
        detected_range = range_axis[peaks[0]]
        print(f"Target DETECTED at: {detected_range:.2f} meters")
    else:
        print("No target detected.")

    # 7. DISPLAY: Visualize the 'Scope'
    plt.figure(figsize=(10, 6))

    # Plot 1: The Raw signals
    plt.subplot(2, 1, 1)
    plt.title("Time Domain: Transmitted Pulse vs Received Echo (Noisy)")
    plt.plot(np.real(rx_pulse), label='Received (Rx) + Noise', color='green', alpha=0.7)
    # Scale Tx for visibility
    plt.plot(np.real(tx_pulse), label='Transmitted (Tx)', color='red', linestyle='--')
    plt.legend()
    plt.grid(True)

    # Plot 2: The Processed Radar Image (A-Scope)
    plt.subplot(2, 1, 2)
    plt.title("Processed Output (Matched Filter Response)")
    plt.plot(range_axis, response, color='blue')
    plt.xlabel("Distance (meters)")
    plt.ylabel("Signal Strength (dB)")
    plt.xlim(0, real_target_distance * 1.5)  # Zoom in on the relevant range
    plt.grid(True)
    plt.axvline(x=real_target_distance, color='r', linestyle=':', label='Actual Target Pos')
    plt.legend()

    plt.tight_layout()
    plt.show()
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
from scipy.fft import fft, fftfreq

# --- Configuration ---
FS = 44100  # Sample Rate (Hz)
DURATION = 4.0  # Seconds
HOP_DURATION = 0.2  # Duration of each hop (seconds)
NUM_CHANNELS = 10  # Number of available frequency channels
BASE_FREQ = 2000  # Starting frequency of the lowest channel (Hz)
CHANNEL_WIDTH = 1500  # Width of each channel (Hz)
SECRET_KEY = 42  # The shared key for the pseudorandom generator

# Jamming Config
JAMMER_FREQ = 8000  # Center frequency of the jammer (Hz)
JAMMER_BW = 2000  # Bandwidth of the jammer (Hz)
JAMMER_POWER = 5.0  # Amplitude of the jammer (Signal is usually 1.0)


class FHSS_System:
    def __init__(self):
        self.t = np.linspace(0, DURATION, int(FS * DURATION), endpoint=False)
        self.hop_samples = int(FS * HOP_DURATION)
        self.num_hops = int(len(self.t) / self.hop_samples)

        # Define Channel Frequencies (Carrier Frequencies)
        self.channels = [BASE_FREQ + i * CHANNEL_WIDTH for i in range(NUM_CHANNELS)]

    def generate_message(self):
        """Generates a baseband message (e.g., a chirp/sweep signal)."""
        # A chirp signal (rising tone) is easy to distinguish visually and audibly
        # It goes from 100Hz to 800Hz
        msg = signal.chirp(self.t, f0=100, f1=800, t1=DURATION, method='linear')
        return msg

    def generate_hopping_sequence(self, key):
        """Generates the pseudorandom sequence of channels based on the key."""
        np.random.seed(key)
        # Randomly select a channel index for each hop time slot
        sequence = np.random.randint(0, NUM_CHANNELS, self.num_hops)
        return sequence

    def modulate(self, message, sequence):
        """
        Modulates the message onto the hopping carrier frequencies.
        Splits the message into chunks and mixes each with the carrier.
        """
        tx_signal = np.zeros_like(message)

        print(f"Transmitting over {self.num_hops} hops...")

        for i, channel_idx in enumerate(sequence):
            carrier_freq = self.channels[channel_idx]

            # Determine start and end indices for this chunk
            start = i * self.hop_samples
            end = start + self.hop_samples

            # Get the message chunk
            chunk = message[start:end]

            # Generate Carrier Sine Wave for this chunk's time window
            t_chunk = self.t[start:end]
            carrier = np.cos(2 * np.pi * carrier_freq * t_chunk)

            # Modulation (DSB-SC: Double Sideband Suppressed Carrier)
            # In simple terms: shift the audio up to the carrier frequency
            tx_signal[start:end] = chunk * carrier

        return tx_signal

    def generate_jammer(self):
        """Creates a high-power noise signal on a specific band."""
        # Create white noise
        noise = np.random.normal(0, 1, len(self.t))

        # Filter it to be band-limited around JAMMER_FREQ
        nyquist = 0.5 * FS
        low = (JAMMER_FREQ - JAMMER_BW / 2) / nyquist
        high = (JAMMER_FREQ + JAMMER_BW / 2) / nyquist
        b, a = signal.butter(4, [low, high], btype='band')

        jammer_signal = signal.lfilter(b, a, noise) * JAMMER_POWER
        return jammer_signal

    def demodulate(self, received_signal, sequence):
        """
        Demodulates the signal using the shared secret key/sequence.
        """
        rx_message = np.zeros_like(received_signal)

        # Design a Low Pass Filter to recover the baseband message
        # Cutoff at 1000Hz (since our chirp max is 800Hz)
        nyquist = 0.5 * FS
        b, a = signal.butter(6, 1000 / nyquist, btype='low')

        for i, channel_idx in enumerate(sequence):
            carrier_freq = self.channels[channel_idx]
            start = i * self.hop_samples
            end = start + self.hop_samples

            chunk = received_signal[start:end]
            t_chunk = self.t[start:end]

            # Coherent Detection: Multiply by the same carrier again
            # This shifts the signal to 0Hz (Baseband) and 2*fc (High freq)
            demod_chunk = chunk * np.cos(2 * np.pi * carrier_freq * t_chunk)

            rx_message[start:end] = demod_chunk

        # Apply Low Pass Filter to remove the high frequency components (2*fc)
        # and the noise from other channels
        recovered_signal = signal.filtfilt(b, a, rx_message)

        # Normalize amplitude
        recovered_signal = recovered_signal / np.max(np.abs(recovered_signal))

        return recovered_signal


def plot_waterfall(signal_data, title, ax):
    """Generates a Spectrogram (Waterfall Plot)."""
    f, t, Sxx = signal.spectrogram(signal_data, FS, nperseg=1024, noverlap=512)

    # Use Log scale for visualization (dB)
    Sxx_log = 10 * np.log10(Sxx + 1e-10)

    # Plot
    img = ax.pcolormesh(t, f, Sxx_log, shading='gouraud', cmap='inferno')
    ax.set_ylabel('Frequency [Hz]')
    ax.set_xlabel('Time [sec]')
    ax.set_title(title)
    ax.set_ylim(0, 20000)
    return img


def main():
    # 1. Initialize System
    fhss = FHSS_System()

    # 2. Generate Original Data (The "Tactical Order")
    original_msg = fhss.generate_message()

    # 3. Generate Hopping Pattern (The "Secret Key")
    key_seq = fhss.generate_hopping_sequence(SECRET_KEY)

    # 4. Transmitter (Hopper)
    # Modulate message onto the hopping carriers
    tx_signal = fhss.modulate(original_msg, key_seq)

    # 5. The Battlefield Environment
    # Add Jamming (Enemy EW system)
    jammer_signal = fhss.generate_jammer()

    # Add Background Noise (Thermal/Atmospheric)
    thermal_noise = np.random.normal(0, 0.05, len(tx_signal))

    # The "Air" Channel
    air_signal = tx_signal + jammer_signal + thermal_noise

    # 6. Receiver
    # Demodulate using the SAME key
    recovered_msg = fhss.demodulate(air_signal, key_seq)

    # --- Visualization ---
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(f"FHSS Simulation (Key: {SECRET_KEY}, {NUM_CHANNELS} Channels)", fontsize=16)

    # Plot 1: Original Message
    ax1 = fig.add_subplot(3, 1, 1)
    ax1.plot(fhss.t, original_msg, 'g')
    ax1.set_title("1. Original Message (Baseband Chirp)")
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, DURATION)

    # Plot 2: The Waterfall (Spectrogram)
    ax2 = fig.add_subplot(3, 1, 2)
    plot_waterfall(air_signal, "2. Battlefield Spectrum (Waterfall Plot)", ax2)

    # Annotate the Jammer
    ax2.text(0.1, JAMMER_FREQ, " <-- STATIC JAMMER (High Power)", color='cyan', fontweight='bold')

    # Plot 3: Recovered Message
    ax3 = fig.add_subplot(3, 1, 3)
    ax3.plot(fhss.t, recovered_msg, 'b', label="Recovered")
    # Plot faint original for comparison
    ax3.plot(fhss.t, original_msg, 'g--', alpha=0.5, label="Original")
    ax3.set_title("3. Receiver Output (Demodulated & Filtered)")
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(0, DURATION)

    plt.tight_layout()
    plt.subplots_adjust(top=0.92)

    print("Simulation Complete. Displaying plots...")
    plt.show()


if __name__ == "__main__":
    main()
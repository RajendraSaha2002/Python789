import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq


def simulate_radar_gun():
    # --- Configuration ---
    # We use speed of sound (343 m/s) instead of light so we can visualize
    # the waveform shift easily without needing a 10GHz sampling rate.
    C_WAVE = 343.0  # Wave speed (m/s)
    F_TX = 2000.0  # Transmit Frequency (Hz)
    DURATION = 0.5  # Duration of sample (seconds)
    SAMPLE_RATE = 44100  # Hz (Standard audio rate)

    # User Input
    print(f"--- Doppler Radar Simulator (Wave Speed: {C_WAVE} m/s) ---")
    try:
        v_target_kph = float(input("Enter Target Speed (km/h): "))
    except ValueError:
        v_target_kph = 50.0  # Default
        print("Invalid input. Defaulting to 50 km/h")

    # Convert km/h to m/s
    v_target = v_target_kph * (1000 / 3600)

    # --- 1. Calculate Theoretical Physics ---
    # Doppler Formula for reflection (Radar): f_rx = f_tx * (c + v) / (c - v)
    # Note: Positive velocity = approaching (Higher pitch/freq)
    # We assume target is moving TOWARDS radar for this formula
    f_rx_theoretical = F_TX * (C_WAVE + v_target) / (C_WAVE - v_target)
    shift_hz = f_rx_theoretical - F_TX

    print(f"\n[Physics]")
    print(f"Transmit Freq: {F_TX} Hz")
    print(f"Target Speed:  {v_target:.2f} m/s")
    print(f"Expected Rx:   {f_rx_theoretical:.2f} Hz")
    print(f"Doppler Shift: {shift_hz:.2f} Hz")

    # --- 2. Generate Signals (Time Domain) ---
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)

    # Transmitted Wave (Pure Sine)
    signal_tx = np.sin(2 * np.pi * F_TX * t)

    # Received Wave (Shifted Sine + Noise)
    # We add some random noise to simulate real-world conditions
    noise = np.random.normal(0, 0.5, size=t.shape)
    signal_rx = np.sin(2 * np.pi * f_rx_theoretical * t) + noise

    # --- 3. Apply FFT (Frequency Domain) ---
    N = len(signal_rx)

    # Calculate FFT for Received Signal
    yf = rfft(signal_rx)
    xf = rfftfreq(N, 1 / SAMPLE_RATE)

    # Find the peak frequency magnitude
    idx_peak = np.argmax(np.abs(yf))
    f_measured = xf[idx_peak]

    # --- 4. Reverse Calculate Speed from FFT ---
    # Reverse the formula: v = c * (f_rx - f_tx) / (f_rx + f_tx)
    v_measured = C_WAVE * (f_measured - F_TX) / (f_measured + F_TX)
    v_measured_kph = v_measured * 3.6

    print(f"\n[Radar Processing]")
    print(f"Peak Freq Detected: {f_measured:.2f} Hz")
    print(f"Calculated Speed:   {v_measured_kph:.2f} km/h")

    # --- 5. Visualization ---
    plt.figure(figsize=(12, 8))

    # Plot 1: Time Domain (Zoomed in)
    plt.subplot(2, 1, 1)
    plt.title(f"Time Domain (Zoomed 10ms) - Target: {v_target_kph} km/h")
    # Only show first 10ms to make waves visible
    zoom_samples = int(SAMPLE_RATE * 0.01)
    plt.plot(t[:zoom_samples] * 1000, signal_tx[:zoom_samples], label='Tx (Original)', alpha=0.7)
    plt.plot(t[:zoom_samples] * 1000, signal_rx[:zoom_samples], label='Rx (Echo)', linestyle='--', alpha=0.7)
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)

    # Plot 2: Frequency Domain (FFT)
    plt.subplot(2, 1, 2)
    plt.title(f"Frequency Domain (FFT) - Shift Detected: {f_measured - F_TX:.2f} Hz")

    # Normalize magnitude
    mag = np.abs(yf)
    mag = mag / np.max(mag)

    plt.plot(xf, mag, color='purple')

    # Zoom FFT view around the interesting area
    plt.xlim(F_TX - 200, F_TX + 400)
    plt.axvline(F_TX, color='blue', linestyle='--', label='Tx Freq')
    plt.axvline(f_measured, color='red', linestyle='--', label='Rx Peak')

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Normalized Magnitude")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    simulate_radar_gun()
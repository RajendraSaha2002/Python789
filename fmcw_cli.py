import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import chirp
from scipy.fft import rfft, rfftfreq


def simulate_fmcw_radar():
    # --- Configuration (Automotive Radar Specs) ---
    c = 3e8  # Speed of Light (m/s)

    # Radar Parameters
    f_start = 24e9  # Start Frequency (24 GHz - ISM Band)
    bandwidth = 150e6  # 150 MHz Bandwidth
    f_stop = f_start + bandwidth
    chirp_duration = 0.001  # 1 ms chirp duration (T)

    # Simulation Resolution
    # We need a sampling rate high enough to capture the "Beat Frequency",
    # not the carrier frequency (24GHz). The beat freq is usually < 500kHz.
    sample_rate = 1e6  # 1 MHz Sampling Rate

    print(f"--- FMCW Radar Simulator (c={c:.0e} m/s) ---")
    print(f"Specs: 150MHz Bandwidth, 1ms Chirp")

    try:
        target_dist = float(input("Enter Target Distance (meters): "))
    except ValueError:
        target_dist = 100.0
        print("Invalid input. Defaulting to 100m")

    # --- 1. Physics Calculations ---
    # Time Delay: How long does it take for light to go there and back?
    # tau = 2 * d / c
    tau = 2 * target_dist / c

    # Expected Beat Frequency
    # f_beat = (Bandwidth / Duration) * tau
    slope = bandwidth / chirp_duration
    f_beat_theoretical = slope * tau

    print(f"\n[Physics]")
    print(f"Round Trip Time: {tau * 1e6:.3f} microseconds")
    print(f"Chirp Slope:     {slope:.2e} Hz/s")
    print(f"Expected Beat:   {f_beat_theoretical / 1000:.3f} kHz")

    # --- 2. Signal Generation ---
    num_samples = int(sample_rate * chirp_duration)
    t = np.linspace(0, chirp_duration, num_samples)

    # Generate Transmit Signal (Tx) - Linear Chirp
    # Note: We simulate the 'phase' directly to avoid generating 24GHz waves
    # which requires massive RAM. We only need the frequency difference.
    # However, to be scientifically accurate with scipy.signal.chirp:
    # We will simulate the "Baseband" chirp (0 to 150MHz) for easier visualization,
    # because the mixing math is identical whether centered at 24GHz or 0Hz.

    # Tx: Frequency sweeps from 0 to Bandwidth
    sig_tx = chirp(t, f0=0, t1=chirp_duration, f1=bandwidth, method='linear')

    # Rx: Same signal, but delayed by tau
    # For simulation, we just shift the time array by tau
    # Any time t < tau corresponds to silence (signal hasn't returned yet)
    t_delayed = t - tau
    sig_rx = chirp(t_delayed, f0=0, t1=chirp_duration, f1=bandwidth, method='linear')

    # Zero out the part of Rx where the echo hasn't arrived yet
    # (The first few microseconds)
    sig_rx[t < tau] = 0

    # --- 3. Mixer (De-chirping) ---
    # In hardware, this is a multiply operation.
    # Mixing Tx and Rx produces sum (f1+f2) and difference (f1-f2) frequencies.
    # We want the difference (Beat Frequency).
    sig_mix = sig_tx * sig_rx

    # --- 4. FFT Processing ---
    # We ignore the start of the mix where Rx was 0 to avoid artifacts
    valid_start_idx = int(tau * sample_rate) + 10  # +10 safety buffer
    if valid_start_idx >= num_samples:
        print("Error: Target too far for this chirp duration!")
        return

    # Slice the valid portion of the mixed signal
    mix_valid = sig_mix[valid_start_idx:]

    yf = rfft(mix_valid)
    xf = rfftfreq(len(mix_valid), 1 / sample_rate)

    # Find Peak
    idx_peak = np.argmax(np.abs(yf))
    f_measured = xf[idx_peak]

    # Calculate Distance from Frequency
    # d = (c * T * f_beat) / (2 * B)
    d_measured = (c * chirp_duration * f_measured) / (2 * bandwidth)

    print(f"\n[Signal Processing]")
    print(f"Measured Beat:   {f_measured / 1000:.3f} kHz")
    print(f"Measured Dist:   {d_measured:.2f} m")

    # --- 5. Visualization ---
    plt.figure(figsize=(12, 10))

    # Plot 1: Chirps (Frequency vs Time representation)
    plt.subplot(3, 1, 1)
    plt.title(f"FMCW Chirps (Frequency vs Time) - Distance: {target_dist}m")
    plt.plot(t * 1000, np.linspace(0, bandwidth / 1e6, len(t)), 'b', label='Tx (Outgoing)')
    # Plot Rx shifted
    plt.plot((t + tau) * 1000, np.linspace(0, bandwidth / 1e6, len(t)), 'r--', label='Rx (Incoming)')
    plt.xlabel("Time (ms)")
    plt.ylabel("Frequency (MHz)")
    plt.legend()
    plt.grid(True)

    # Plot 2: The Mixed Signal (Time Domain)
    plt.subplot(3, 1, 2)
    plt.title("Mixed Signal (beat frequency in time domain)")
    # Show a zoomed in section to see the sine wave structure
    limit = 200  # samples to show
    plt.plot(t[valid_start_idx:valid_start_idx + limit] * 1000, sig_mix[valid_start_idx:valid_start_idx + limit],
             color='green')
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude")
    plt.grid(True)

    # Plot 3: FFT (The Range Profile)
    plt.subplot(3, 1, 3)
    plt.title(f"Range Profile (FFT) - Peak at {d_measured:.2f}m")

    # Convert X-axis from Frequency to Distance for easier reading
    # x_dist = xf * (c * chirp_duration) / (2 * bandwidth)
    # Actually, let's keep it freq but add secondary axis logic mentally

    mag = np.abs(yf)
    mag = mag / np.max(mag)

    plt.plot(xf / 1000, mag, color='purple')
    plt.xlabel("Beat Frequency (kHz)")
    plt.ylabel("Normalized Amplitude")

    # Add Distance marker text
    plt.axvline(f_measured / 1000, color='r', linestyle='--')
    plt.text(f_measured / 1000 + 5, 0.8, f"Target: {d_measured:.1f}m", color='red')

    plt.xlim(0, max(f_measured / 1000 * 2, 50))
    plt.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    simulate_fmcw_radar()
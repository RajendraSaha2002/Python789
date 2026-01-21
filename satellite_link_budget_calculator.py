import numpy as np
import math


class LinkBudgetCalculator:
    def __init__(self):
        # Constants
        self.c = 3e8  # Speed of light in m/s
        self.GEO_ALTITUDE_KM = 35786  # Standard GEO altitude
        self.BOLTZMANN_K = -228.6  # dBW/K/Hz

    def watts_to_dbw(self, power_watts):
        """Converts Power in Watts to dBW."""
        if power_watts <= 0:
            return -np.inf
        return 10 * np.log10(power_watts)

    def calculate_antenna_gain(self, frequency_hz, diameter_m, efficiency=0.6):
        """
        Calculates Antenna Gain in dBi.
        Formula: G = 10 * log10(efficiency * (pi * D / lambda)^2)
        """
        wavelength = self.c / frequency_hz
        gain_linear = efficiency * (np.pi * diameter_m / wavelength) ** 2
        return 10 * np.log10(gain_linear)

    def calculate_fspl(self, distance_km, frequency_mhz):
        """
        Calculates Free Space Path Loss (FSPL) in dB.
        Formula: Lfs = 20log10(d) + 20log10(f) + 32.44
        """
        return 20 * np.log10(distance_km) + 20 * np.log10(frequency_mhz) + 32.44

    def calculate_noise_power(self, temp_k, bandwidth_hz):
        """
        Calculates Noise Power (N) in dBW.
        Formula: N = k + 10log10(T) + 10log10(B)
        """
        return self.BOLTZMANN_K + 10 * np.log10(temp_k) + 10 * np.log10(bandwidth_hz)

    def run_interactive(self):
        print("=== Satellite Link Budget Calculator (GEO Focus) ===")
        print("Calculate Uplink/Downlink budgets based on Friis Transmission Equation.\n")

        try:
            # --- 1. User Inputs ---
            freq_ghz = float(input("Enter Frequency (GHz) [e.g., 4.0 for C-band, 12.0 for Ku]: "))
            freq_hz = freq_ghz * 1e9
            freq_mhz = freq_ghz * 1e3

            tx_power_w = float(input("Enter Transmitter Power (Watts) [e.g., 50]: "))

            print("\n--- Antenna Configuration ---")
            use_diam = input("Calculate Gain from diameter? (y/n) [y]: ").lower() != 'n'

            if use_diam:
                tx_diam = float(input("  Tx Antenna Diameter (m) [e.g., 2.4]: "))
                rx_diam = float(input("  Rx Antenna Diameter (m) [e.g., 1.2]: "))
                efficiency = 0.6  # Typical efficiency

                gt_dbi = self.calculate_antenna_gain(freq_hz, tx_diam, efficiency)
                gr_dbi = self.calculate_antenna_gain(freq_hz, rx_diam, efficiency)
                print(f"  -> Calculated Tx Gain: {gt_dbi:.2f} dBi")
                print(f"  -> Calculated Rx Gain: {gr_dbi:.2f} dBi")
            else:
                gt_dbi = float(input("  Enter Tx Antenna Gain (dBi): "))
                gr_dbi = float(input("  Enter Rx Antenna Gain (dBi): "))

            misc_losses = float(input("\nEnter Misc Losses (Cable, Atmospheric, Pointing) [dB, typical 3-5]: "))

            # Receiver Sensitivity Threshold
            sensitivity = float(input("Enter Receiver Sensitivity Threshold (dBW) [e.g., -120]: "))

            # --- 2. Calculations ---

            # Convert Tx Power to dBW
            pt_dbw = self.watts_to_dbw(tx_power_w)

            # Path Loss (using GEO altitude as default distance)
            path_loss = self.calculate_fspl(self.GEO_ALTITUDE_KM, freq_mhz)

            # Link Budget Equation: Pr = Pt + Gt + Gr - Lfs - Lmisc
            pr_dbw = pt_dbw + gt_dbi + gr_dbi - path_loss - misc_losses

            # Margin
            margin = pr_dbw - sensitivity

            # --- 3. Carrier to Noise (Optional Estimate) ---
            # Assuming typical noise temp (T) and Bandwidth (B) for context
            temp_k = 290  # Standard noise temp
            bw_hz = 36e6  # Standard transponder 36 MHz
            noise_dbw = self.calculate_noise_power(temp_k, bw_hz)
            cn_ratio = pr_dbw - noise_dbw

            # --- 4. Display Results ---
            print("\n" + "=" * 40)
            print("           LINK BUDGET RESULTS")
            print("=" * 40)
            print(f"Frequency:          {freq_ghz} GHz")
            print(f"Distance (GEO):     {self.GEO_ALTITUDE_KM:,} km")
            print("-" * 40)
            print(f"Tx Power:           {pt_dbw:.2f} dBW ({tx_power_w} W)")
            print(f"Tx Antenna Gain:    {gt_dbi:.2f} dBi")
            print(f"Rx Antenna Gain:    {gr_dbi:.2f} dBi")
            print(f"Free Space Loss:    -{path_loss:.2f} dB")
            print(f"Misc Losses:        -{misc_losses:.2f} dB")
            print("-" * 40)
            print(f"RECEIVED POWER (Pr): {pr_dbw:.2f} dBW")
            print(f"Required Sensitivity: {sensitivity:.2f} dBW")
            print(f"Link Margin:          {margin:.2f} dB")
            print("-" * 40)
            print(f"Est. Noise Floor:    {noise_dbw:.2f} dBW (assuming 290K, 36MHz)")
            print(f"Carrier-to-Noise (C/N): {cn_ratio:.2f} dB")
            print("=" * 40)

            if margin >= 0:
                print(">>> STATUS: [ GO ] - Link is viable.")
            else:
                print(">>> STATUS: [ NO-GO ] - Signal too weak!")

        except ValueError:
            print("Invalid input. Please enter numeric values.")


if __name__ == "__main__":
    calc = LinkBudgetCalculator()
    calc.run_interactive()
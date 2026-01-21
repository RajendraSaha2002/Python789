import numpy as np
import matplotlib.pyplot as plt

# --- 555 Timer Components ---
R1 = 1000  # 1k Ohm
R2 = 2000  # 2k Ohm (Change this to change Duty Cycle)
C = 100e-6  # 100 uF Capacitor
VCC = 9  # 9V Battery

# --- Timings (Formulae) ---
# t_high = 0.693 * (R1 + R2) * C
# t_low  = 0.693 * R2 * C
t_high = 0.693 * (R1 + R2) * C
t_low = 0.693 * R2 * C
period = t_high + t_low

print(f"Frequency: {1 / period:.2f} Hz")
print(f"Duty Cycle: {t_high / period * 100:.1f} %")

# --- Generate Data for Plotting ---
# We create 3 cycles of the waveform
time_points = []
cap_voltage = []
out_voltage = []

current_time = 0
for i in range(3):
    # CHARGING PHASE (Output HIGH)
    # Capacitor goes from 1/3 Vcc (3V) to 2/3 Vcc (6V)
    t_charge = np.linspace(0, t_high, 50)
    vc_rise = VCC - (VCC - VCC / 3) * np.exp(-t_charge / ((R1 + R2) * C))

    time_points.extend(current_time + t_charge)
    cap_voltage.extend(vc_rise)
    out_voltage.extend([VCC] * len(t_charge))  # Output is HIGH (Vcc)

    current_time += t_high

    # DISCHARGING PHASE (Output LOW)
    # Capacitor goes from 2/3 Vcc (6V) down to 1/3 Vcc (3V)
    t_discharge = np.linspace(0, t_low, 50)
    vc_fall = (2 * VCC / 3) * np.exp(-t_discharge / (R2 * C))

    time_points.extend(current_time + t_discharge)
    cap_voltage.extend(vc_fall)
    out_voltage.extend([0] * len(t_discharge))  # Output is LOW (0V)

    current_time += t_low

# --- Plotting ---
plt.figure("555 Timer Astable Mode")
plt.plot(time_points, out_voltage, 'b-', label='Output (Pin 3)')
plt.plot(time_points, cap_voltage, 'r--', label='Capacitor (Pin 6)')

# Draw threshold lines
plt.axhline(2 * VCC / 3, color='gray', linestyle=':', label='2/3 Vcc')
plt.axhline(VCC / 3, color='gray', linestyle=':', label='1/3 Vcc')

plt.title("555 Timer: Capacitor vs Output")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.legend(loc='upper right')
plt.grid(True)
plt.show()
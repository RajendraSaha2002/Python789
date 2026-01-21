import numpy as np
import matplotlib.pyplot as plt

# --- Setup ---
t = np.linspace(0, 0.05, 500) # Time: 0 to 50ms
Vin = 1.0 * np.sin(2 * np.pi * 50 * t) # 1V Peak Input Sine Wave

# --- Op-Amp Settings ---
Gain = 10           # Try changing this to 5 or 20!
Supply_Pos = 8.0    # +Vcc
Supply_Neg = -8.0   # -Vee

# --- Calculation ---
Vout_Ideal = Vin * Gain

# Apply Clipping (Saturation) Theory
# If Vout > 8, make it 8. If Vout < -8, make it -8.
Vout_Real = np.clip(Vout_Ideal, Supply_Neg, Supply_Pos)

# --- Plotting ---
plt.figure("Op-Amp Clipping")
plt.plot(t, Vin, 'g-', label='Input (1V)')
plt.plot(t, Vout_Ideal, 'b:', alpha=0.5, label='Ideal Output')
plt.plot(t, Vout_Real, 'r-', linewidth=2, label='Actual Output (Clipped)')

plt.axhline(Supply_Pos, color='black', linestyle='--', alpha=0.3)
plt.axhline(Supply_Neg, color='black', linestyle='--', alpha=0.3)
plt.title(f"Op-Amp Saturation (Gain={Gain})")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.legend(loc='upper right')
plt.grid(True)
plt.show()
import numpy as np
import matplotlib.pyplot as plt

# --- Constants ---
Is = 1e-12    # Saturation Current (very small)
Vt = 0.026    # Thermal Voltage (approx 26mV at room temp)
n = 1.5       # Ideality factor (1 for ideal, 2 for real)

# --- Voltage Sweep ---
# Sweep voltage from -1V to +0.8V
Vd = np.linspace(-1, 0.8, 100)

# --- The Physics Formula (Shockley Equation) ---
# I = Is * (e^(V/nVt) - 1)
Id = Is * (np.exp(Vd / (n * Vt)) - 1)

# --- Plotting ---
plt.figure("Diode Characteristic")
plt.plot(Vd, Id * 1000, color='red') # Convert Amps to mA
plt.axhline(0, color='black', linewidth=0.5) # X-axis line
plt.axvline(0, color='black', linewidth=0.5) # Y-axis line
plt.title("Silicon Diode I-V Curve")
plt.xlabel("Diode Voltage (V)")
plt.ylabel("Diode Current (mA)")
plt.grid(True)
plt.show()
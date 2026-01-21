import numpy as np
import matplotlib.pyplot as plt

# --- Circuit Constants ---
R = 100       # Resistance in Ohms
L = 20e-3     # Inductance (20 milliHenry)
C = 10e-6     # Capacitance (10 microFarad)
V_source = 10 # Source Voltage (10V)

# --- Frequency Range ---
# Check frequencies from 10Hz to 1000Hz
f = np.linspace(10, 1000, 500)
w = 2 * np.pi * f  # Angular frequency (omega)

# --- The Physics Formulas ---
XL = w * L            # Inductive Reactance
XC = 1 / (w * C)      # Capacitive Reactance
Z = np.sqrt(R**2 + (XL - XC)**2) # Total Impedance

I = V_source / Z      # Current (Ohm's Law)

# --- Plotting ---
plt.figure("RLC Resonance")
plt.plot(f, I, color='blue', linewidth=2)
plt.title("Series RLC Frequency Response")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Current (Amps)")
plt.grid(True)

# Find the Peak automatically
max_current = np.max(I)
resonant_freq = f[np.argmax(I)]
print(f"Resonant Frequency found at: {resonant_freq:.2f} Hz")
print(f"Max Current: {max_current:.4f} A")

plt.show()
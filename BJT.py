import numpy as np
import matplotlib.pyplot as plt

# --- Circuit Parameters ---
VCC = 12  # Supply Voltage (Volts)
RC = 1000  # Collector Resistor (Ohms)
Beta = 100  # Transistor Gain (hfe)

# --- 1. Plot Transistor Characteristic Curves ---
# We simulate how the transistor behaves for different Base Currents (Ib)
Vce = np.linspace(0, VCC, 100)  # Sweep Vce from 0 to 12V

plt.figure("BJT Load Line Analysis")

# Plot curves for Ib = 20uA, 40uA, 60uA...
base_currents = [20e-6, 40e-6, 60e-6, 80e-6]

for Ib in base_currents:
    # Simplified theory: Ic = Beta * Ib (in active region)
    # We add a "saturation" knee effect for realism using np.tanh
    Ic_saturation = Vce / 100  # rapid rise at low voltage
    Ic_active = np.full_like(Vce, Beta * Ib)
    Ic = np.minimum(Ic_saturation, Ic_active)  # Pick the lower current

    plt.plot(Vce, Ic * 1000, label=f'Ib={Ib * 1e6:.0f}uA')  # Plot in mA

# --- 2. Plot the DC Load Line ---
# Theory: Vce = VCC - Ic*RC  -->  Ic = (VCC - Vce) / RC
Ic_load = (VCC - Vce) / RC
plt.plot(Vce, Ic_load * 1000, 'r--', linewidth=3, label='DC Load Line')

# --- Formatting ---
plt.title(f"BJT Q-Point Analysis (Vcc={VCC}V, Rc={RC}Ω)")
plt.xlabel("Collector-Emitter Voltage Vce (V)")
plt.ylabel("Collector Current Ic (mA)")
plt.legend()
plt.grid(True)
plt.ylim(0, 15)
plt.show()
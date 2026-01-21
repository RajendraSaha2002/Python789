# --- LAB READINGS ---
# Values measured from the Oscilloscope (CRO)
V_max = 5.2  # Volts (Peak-to-Peak)
V_min = 1.8  # Volts (Peak-to-Peak)

# --- CALCULATION ---
# Calculate Index (m)
m = (V_max - V_min) / (V_max + V_min)

# Calculate Percentage
m_percent = m * 100

# Calculate Carrier and Message Amplitude (Side Calculation)
# V_carrier = (Vmax + Vmin) / 2
# V_message = (Vmax - Vmin) / 2
Vc = (V_max + V_min) / 4 # Divided by 4 if Vmax/min are Peak-to-Peak
Vm = (V_max - V_min) / 4

# --- OUTPUT ---
print("--- AM Modulation Analysis ---")
print(f"V_max measured: {V_max} V")
print(f"V_min measured: {V_min} V")
print("-" * 25)
print(f"Modulation Index (m): {m:.3f}")
print(f"Modulation Percentage: {m_percent:.1f} %")

if m > 1:
    print("WARNING: Over-Modulation Detected! (Distortion)")
elif m == 1:
    print("Status: 100% Modulation (Ideal)")
else:
    print("Status: Under-Modulation (Standard)")
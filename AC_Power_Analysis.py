import cmath
import math

# --- INPUTS (Phasor Form) ---
# Voltage: 230V at 0 degrees
V_mag = 230
V_angle = 0  # degrees

# Current: 5A at -30 degrees (Lagging)
I_mag = 5
I_angle = -30 # degrees

# --- CALCULATIONS ---
# 1. Convert Polar to Rectangular (Complex Number)
# Note: Python math requires Radians, not Degrees
V = cmath.rect(V_mag, math.radians(V_angle))
I = cmath.rect(I_mag, math.radians(I_angle))

# 2. Calculate Complex Power (S = V * Conjugate of I)
S = V * I.conjugate()

# 3. Extract Components
P = S.real      # Real Power (Watts)
Q = S.imag      # Reactive Power (VAR)
S_mag = abs(S)  # Apparent Power (VA)

# 4. Calculate Power Factor
pf = math.cos(math.radians(V_angle - I_angle))

# --- OUTPUT ---
print("--- AC Power Analysis ---")
print(f"Voltage Phasor: {V:.2f} V")
print(f"Current Phasor: {I:.2f} A")
print("-" * 20)
print(f"Active Power (P)   : {P:.2f} Watts")
print(f"Reactive Power (Q) : {Q:.2f} VAR")
print(f"Apparent Power (S) : {S_mag:.2f} VA")
print(f"Power Factor       : {pf:.3f}")

if Q > 0:
    print("System is INDUCTIVE (Lagging)")
else:
    print("System is CAPACITIVE (Leading)")
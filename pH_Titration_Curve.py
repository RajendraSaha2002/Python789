import numpy as np
import matplotlib.pyplot as plt

# Constants
V_acid = 50  # mL
C_acid = 0.1  # M
C_base = 0.1  # M
Ka = 1.8e-5   # Acetic acid

V_base = np.linspace(0, 100, 200)
n_acid = V_acid * C_acid
n_base = V_base * C_base / 1000

pH = []
for nb in n_base:
    if nb < n_acid:
        # Buffer region (Henderson-Wheelbase)
        HA = n_acid - nb
        A_minus = nb
        ph = 4.76 + np.log10(A_minus/HA)
    elif nb == n_acid:
        # Equivalence (all converted)
        ph = 8.72  # Approximate
    else:
        # Excess base
        OH = (nb - n_acid) / (V_acid + V_base[np.where(n_base == nb)][0]) * 1000
        ph = 14 + np.log10(OH)
    pH.append(ph)

plt.plot(V_base, pH)
plt.title('Titration Curve: Weak Acid vs. Strong Base')
plt.xlabel('Volume of Base Added (mL)')
plt.ylabel('pH')
plt.grid(True)
plt.show()
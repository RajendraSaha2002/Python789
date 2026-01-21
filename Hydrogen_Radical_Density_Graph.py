import numpy as np
import matplotlib.pyplot as plt

# Constants
a0 = 1  # Bohr radius (set to 1 for simplicity)

# Radial probability density for 1s orbital
r = np.linspace(0, 5*a0, 500)
P = 4 * r**2 * np.exp(-2*r/a0) / a0**3

plt.plot(r, P)
plt.title('Radial Probability Density for Hydrogen 1s Orbital')
plt.xlabel('Radius (r)')
plt.ylabel('Probability Density')
plt.grid(True)
plt.show()
import numpy as np
import matplotlib.pyplot as plt

m = 1  # mass (kg)
c = 3e8  # speed of light (m/s)
v = np.linspace(0, 0.99 * c, 500)
E = m * c**2 / np.sqrt(1 - (v**2 / c**2))

plt.plot(v, E)
plt.title('Relativistic Energy vs Velocity')
plt.xlabel('Velocity (m/s)')
plt.ylabel('Total Energy (J)')
plt.grid(True)
plt.show()
import numpy as np
import matplotlib.pyplot as plt

k = 0.5  # Rate constant
t = np.linspace(0, 10, 100)
A0 = 1   # Initial concentration

A = A0 * np.exp(-k * t)

plt.plot(t, A)
plt.title('First-Order Reaction Kinetics')
plt.xlabel('Time')
plt.ylabel('Concentration [A]')
plt.grid(True)
plt.show()
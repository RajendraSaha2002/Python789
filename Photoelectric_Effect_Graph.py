import numpy as np
import matplotlib.pyplot as plt

h = 6.626e-34  # Planck's constant
e = 1.602e-19  # elementary charge
work_function = 2.3 * e  # in Joules

frequency = np.linspace(5e14, 1.2e15, 100)
stopping_potential = (h * frequency - work_function) / e
stopping_potential = np.maximum(stopping_potential, 0)

plt.plot(frequency, stopping_potential)
plt.title('Photoelectric Effect')
plt.xlabel('Frequency (Hz)')
plt.ylabel('Stopping Potential (V)')
plt.grid(True)
plt.show()
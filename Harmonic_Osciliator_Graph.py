import numpy as np
import matplotlib.pyplot as plt

A = 1      # amplitude
omega = 2  # angular frequency
phi = 0    # phase

t = np.linspace(0, 10, 200)
x = A * np.cos(omega * t + phi)

plt.plot(t, x)
plt.title('Simple Harmonic Oscillator')
plt.xlabel('Time (s)')
plt.ylabel('Displacement (m)')
plt.grid(True)
plt.show()
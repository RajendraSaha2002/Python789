import numpy as np
import matplotlib.pyplot as plt

# Parametric curve: Lissajous figure
t = np.linspace(0, 2 * np.pi, 500)
x = np.sin(3 * t)
y = np.sin(4 * t)
plt.figure()
plt.plot(x, y)
plt.title('Parametric Curve (Lissajous)')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True)
plt.show()

# Polar curve: r = 1 + 2*cos(theta)
theta = np.linspace(0, 2 * np.pi, 500)
r = 1 + 2 * np.cos(theta)
plt.figure()
plt.polar(theta, r)
plt.title('Polar Curve: r = 1 + 2*cos(theta)')
plt.show()
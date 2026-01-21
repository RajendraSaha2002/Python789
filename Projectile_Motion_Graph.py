import numpy as np
import matplotlib.pyplot as plt

g = 9.81  # gravity (m/s^2)
v0 = 20   # initial velocity (m/s)
angle = 45  # launch angle (degrees)
theta = np.radians(angle)

# Time of flight
t_flight = 2 * v0 * np.sin(theta) / g
t = np.linspace(0, t_flight, num=100)

# Trajectory equations
x = v0 * np.cos(theta) * t
y = v0 * np.sin(theta) * t - 0.5 * g * t**2

plt.plot(x, y)
plt.title('Projectile Motion')
plt.xlabel('Horizontal Distance (m)')
plt.ylabel('Vertical Distance (m)')
plt.grid(True)
plt.show()
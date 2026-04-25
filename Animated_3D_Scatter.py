import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Create figure
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Data
n = 500
t = np.linspace(0, 4 * np.pi, n)

# Initial plot
x = np.sin(t)
y = np.cos(t)
z = np.sin(2 * t)

scat = ax.scatter(x, y, z)

# Axis limits
ax.set_xlim(-1.5, 1.5)
ax.set_ylim(-1.5, 1.5)
ax.set_zlim(-1.5, 1.5)


# Animation function
def update(frame):
    ax.cla()

    x = np.sin(t + frame * 0.1)
    y = np.cos(t + frame * 0.1)
    z = np.sin(2 * (t + frame * 0.1))

    ax.scatter(x, y, z, c='red', s=5)

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_zlim(-1.5, 1.5)
    ax.set_title("Animated 3D Scatter")


# Run animation
ani = FuncAnimation(fig, update, frames=100, interval=50)

plt.show()
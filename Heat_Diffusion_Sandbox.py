import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Parameters
nx, ny = 80, 80
dx = dy = 1.0
alpha = 0.15   # thermal diffusivity
dt = 0.2
steps = 500

u = np.zeros((ny, nx))
# Initial condition: hot square in center
u[30:50, 30:50] = 100.0

def step(U):
    lap = (
                  np.roll(U, 1, 0) + np.roll(U, -1, 0) +
                  np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U
    ) / (dx*dy)
    return U + alpha * dt * lap

fig, ax = plt.subplots()
im = ax.imshow(u, cmap='inferno', vmin=0, vmax=100)
ax.set_title("2D Heat Diffusion")

def update(_):
    global u
    u = step(u)
    im.set_data(u)
    return [im]

ani = animation.FuncAnimation(fig, update, frames=steps, interval=30, blit=True)
plt.show()
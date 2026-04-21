# advanced_satellite_simulation.py

import warnings
warnings.filterwarnings("ignore")

from vpython import *
from math import sqrt

# ===============================
# Scene Setup
# ===============================
scene.width = 1000
scene.height = 700
scene.background = color.black
scene.title = "Advanced Satellite Simulation (Physics-Based)"
scene.autoscale = False

# ===============================
# Starfield Background
# ===============================
stars = []
for _ in range(200):
    stars.append(
        sphere(
            pos=vector.random() * 50,
            radius=0.1,
            color=color.white,
            emissive=True
        )
    )

# ===============================
# Earth (Rotating)
# ===============================
earth = sphere(
    pos=vector(0, 0, 0),
    radius=2,
    texture=textures.earth,
    emissive=True
)

earth_spin_rate = 0.01  # rotation speed

# ===============================
# Physics Constants
# ===============================
G = 1       # scaled gravitational constant
M = 1000    # mass of Earth

# ===============================
# Satellite Class
# ===============================
class Satellite:
    def __init__(self, pos, velocity, color_val):
        self.body = sphere(
            pos=pos,
            radius=0.2,
            color=color_val,
            make_trail=True,
            retain=150
        )
        self.velocity = velocity

    def update(self, dt):
        r = self.body.pos
        r_mag = mag(r)

        # Avoid division by zero
        if r_mag == 0:
            return

        # Gravitational acceleration
        acc = -G * M * r / (r_mag**3)

        # Update velocity and position
        self.velocity += acc * dt
        self.body.pos += self.velocity * dt

# ===============================
# Create Multiple Satellites
# ===============================
satellites = [
    Satellite(vector(6, 0, 0), vector(0, 2.5, 0), color.red),
    Satellite(vector(8, 0, 0), vector(0, 2.0, 1.0), color.cyan),
    Satellite(vector(10, 0, 0), vector(0, 1.8, -1.0), color.green)
]

# ===============================
# Simulation Control
# ===============================
dt = 0.01
duration = 30   # seconds
fps = 60
steps = duration * fps

# ===============================
# Simulation Loop
# ===============================
for i in range(int(steps)):
    rate(fps)

    # Rotate Earth
    earth.rotate(angle=earth_spin_rate, axis=vector(0, 1, 0))

    # Update satellites
    for sat in satellites:
        sat.update(dt)

print("Simulation complete 🚀")
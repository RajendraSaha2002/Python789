# satellite_orbit_realistic.py

import warnings
warnings.filterwarnings("ignore")

from vpython import *
from math import cos, sin

# ===============================
# Scene Setup
# ===============================
scene.width = 900
scene.height = 650
scene.background = color.black
scene.title = "Realistic Satellite Orbit (Timed Simulation)"
scene.autoscale = False

# ===============================
# Earth (Glowing Effect)
# ===============================
earth = sphere(
    pos=vector(0, 0, 0),
    radius=2,
    texture=textures.earth,
    emissive=True   # glow effect
)

# ===============================
# Satellite with Trail
# ===============================
sat = box(
    pos=vector(5, 0, 0),
    size=vector(0.4, 0.4, 0.4),
    color=color.white,
    make_trail=True,
    retain=200   # trail length control
)

# ===============================
# Orbit Parameters
# ===============================
a = 0.0
dt = 0.02

duration = 20     # seconds
fps = 60
steps = duration * fps

# ===============================
# Simulation Loop (Timed)
# ===============================
for i in range(int(steps)):
    rate(fps)

    sat.pos = vector(5 * cos(a), 0, 5 * sin(a))
    a += dt

print("Simulation completed successfully")
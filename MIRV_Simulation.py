import numpy as np
import plotly.graph_objects as go
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

# --- Physics Constants ---
EARTH_RADIUS = 6371.0  # km
MU = 398600.4418  # Standard gravitational parameter (km^3/s^2)
G_ACCEL = 9.81  # m/s^2 (approx for launch calc)


# --- Coordinate Systems ---

def lla_to_ecef(lat, lon, alt):
    """
    Convert Latitude, Longitude, Altitude to Earth-Centered Earth-Fixed (Cartesian).
    """
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    r = EARTH_RADIUS + alt

    x = r * np.cos(lat_rad) * np.cos(lon_rad)
    y = r * np.cos(lat_rad) * np.sin(lon_rad)
    z = r * np.sin(lat_rad)
    return np.array([x, y, z])


def gravity(r_vec):
    """
    Newtonian Gravity: a = -mu * r / |r|^3
    """
    r_mag = np.linalg.norm(r_vec)
    return -MU * r_vec / (r_mag ** 3)


def dynamics(t, state):
    """
    Differential Equations of Motion [x, y, z, vx, vy, vz]
    """
    r = state[:3]
    v = state[3:]

    a = gravity(r)

    return np.concatenate((v, a))


# --- Ballistics Engine (The "Brain") ---

class BallisticComputer:
    """
    Solves the Lambert Problem:
    Find the initial velocity vector required to go from r1 to r2 in time dt.
    """

    @staticmethod
    def solve_lambert(r1, r2, time_of_flight):
        # We use an optimization approach (Shooting Method) to find the required velocity.
        # This avoids complex universal variable formulations for a cleaner demo.

        def miss_distance(v0_guess):
            # Propagate orbit for time_of_flight
            y0 = np.concatenate((r1, v0_guess))
            sol = solve_ivp(dynamics, [0, time_of_flight], y0, rtol=1e-6)
            r_final = sol.y[:3, -1]
            # Error = distance between actual landing and target
            return np.linalg.norm(r_final - r2)

        # Initial guess: Simple straight line velocity
        # v = d / t
        v_guess = (r2 - r1) / time_of_flight
        # Add 'up' component to clear the earth (lob it)
        r1_norm = r1 / np.linalg.norm(r1)
        v_guess += r1_norm * 2.0

        # Optimize
        res = minimize(miss_distance, v_guess, method='Nelder-Mead', tol=1e-2)
        return res.x  # The required Velocity Vector


# --- Simulation Entities ---

class Warhead:
    def __init__(self, name, position, velocity):
        self.name = name
        self.history_r = [position]
        self.state = np.concatenate((position, velocity))
        self.active = True

    def update(self, dt):
        if not self.active: return

        # Propagate Physics
        sol = solve_ivp(dynamics, [0, dt], self.state, rtol=1e-5)
        self.state = sol.y[:, -1]
        self.history_r.append(self.state[:3])

        # Ground Collision Check
        alt = np.linalg.norm(self.state[:3]) - EARTH_RADIUS
        if alt <= 0:
            self.active = False
            # Snap to surface
            r_norm = self.state[:3] / np.linalg.norm(self.state[:3])
            self.state[:3] = r_norm * EARTH_RADIUS
            self.history_r[-1] = self.state[:3]


class PostBoostVehicle:
    def __init__(self):
        # Initial Orbit (Sub-orbital trajectory)
        # Starting high above Atlantic
        start_lat, start_lon = 40.0, -50.0
        self.pos = lla_to_ecef(start_lat, start_lon, 800.0)  # 800km Altitude

        # Velocity pointing East-ish
        self.vel = np.array([4.0, 3.0, 1.0])  # km/s

        self.state = np.concatenate((self.pos, self.vel))
        self.history_r = [self.pos]
        self.warheads = []
        self.fuel = 100.0  # Percentage

    def maneuver(self, target_pos, time_to_impact):
        """
        Calculates firing solution for a specific target and adjusts velocity.
        """
        current_pos = self.state[:3]
        current_vel = self.state[3:]

        print(f"[BUS] Calculating solution for target...")

        # 1. Calculate Required Velocity to hit Target
        v_req = BallisticComputer.solve_lambert(current_pos, target_pos, time_to_impact)

        # 2. Calculate Delta-V (Burn needed)
        delta_v_vec = v_req - current_vel
        delta_v_mag = np.linalg.norm(delta_v_vec) * 1000  # m/s

        print(f"[BUS] Burn Logic: Delta-V {delta_v_mag:.2f} m/s required.")

        # 3. Apply Burn (Update State)
        self.state[3:] = v_req
        self.fuel -= delta_v_mag * 0.05  # Mock fuel usage

        return v_req  # Return the release velocity

    def release_warhead(self, name):
        w = Warhead(name, self.state[:3].copy(), self.state[3:].copy())
        self.warheads.append(w)
        print(f"[BUS] Payload Released: {name}")

    def update(self, dt):
        sol = solve_ivp(dynamics, [0, dt], self.state, rtol=1e-5)
        self.state = sol.y[:, -1]
        self.history_r.append(self.state[:3])


# --- Main Simulation Loop ---

def run_simulation():
    # Targets (Lat, Lon)
    targets = {
        "Target A (London)": (51.5, -0.12),
        "Target B (Paris)": (48.8, 2.35),
        "Target C (Berlin)": (52.5, 13.4)
    }

    # Convert targets to Cartesian
    target_vectors = {}
    for name, coords in targets.items():
        pos = lla_to_ecef(coords[0], coords[1], 0)
        target_vectors[name] = pos

    bus = PostBoostVehicle()

    # Simulation Parameters
    total_time = 1500  # seconds
    step_size = 10  # seconds
    time_elapsed = 0

    # Deployment Schedule
    # (Time in simulation, Target Name, Time of Flight for warhead)
    schedule = [
        (100, "Target A (London)", 900),
        (250, "Target B (Paris)", 850),
        (400, "Target C (Berlin)", 800)
    ]
    schedule_idx = 0

    print("--- MIRV DEPLOYMENT SEQUENCE STARTED ---")

    while time_elapsed < total_time:
        # Check Schedule
        if schedule_idx < len(schedule):
            trigger_time, t_name, tof = schedule[schedule_idx]

            if time_elapsed >= trigger_time:
                # 1. Maneuver Bus
                target_pos = target_vectors[t_name]
                bus.maneuver(target_pos, tof)

                # 2. Release
                bus.release_warhead(t_name)

                schedule_idx += 1

        # Update Bus
        bus.update(step_size)

        # Update Warheads
        for w in bus.warheads:
            w.update(step_size)

        time_elapsed += step_size

    return bus, target_vectors


# --- Visualization (Plotly) ---

def visualize(bus, targets):
    fig = go.Figure()

    # 1. Draw Earth
    # Create sphere mesh
    phi = np.linspace(0, 2 * np.pi, 40)
    theta = np.linspace(0, np.pi, 40)
    x = EARTH_RADIUS * np.outer(np.cos(phi), np.sin(theta))
    y = EARTH_RADIUS * np.outer(np.sin(phi), np.sin(theta))
    z = EARTH_RADIUS * np.outer(np.ones(np.size(phi)), np.cos(theta))

    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        colorscale='Earth',
        showscale=False,
        opacity=0.8,
        name="Earth"
    ))

    # 2. Draw Targets
    tx, ty, tz = [], [], []
    tnames = []
    for name, pos in targets.items():
        tx.append(pos[0])
        ty.append(pos[1])
        tz.append(pos[2])
        tnames.append(name)

    fig.add_trace(go.Scatter3d(
        x=tx, y=ty, z=tz,
        mode='markers+text',
        marker=dict(size=5, color='red', symbol='x'),
        text=tnames,
        textposition="top center",
        name="Targets"
    ))

    # 3. Draw Bus Trajectory
    bx = [p[0] for p in bus.history_r]
    by = [p[1] for p in bus.history_r]
    bz = [p[2] for p in bus.history_r]

    fig.add_trace(go.Scatter3d(
        x=bx, y=by, z=bz,
        mode='lines',
        line=dict(color='cyan', width=4),
        name="Bus (Post-Boost Vehicle)"
    ))

    # 4. Draw Warhead Trajectories
    colors = ['#FF5733', '#FFBD33', '#DBFF33']
    for i, w in enumerate(bus.warheads):
        wx = [p[0] for p in w.history_r]
        wy = [p[1] for p in w.history_r]
        wz = [p[2] for p in w.history_r]

        fig.add_trace(go.Scatter3d(
            x=wx, y=wy, z=wz,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=2, dash='dash'),
            name=f"RV: {w.name}"
        ))

    # Layout Config
    fig.update_layout(
        title="MIRV Deployment Pattern Analysis (Lambert Solver)",
        scene=dict(
            xaxis_title='X (km)',
            yaxis_title='Y (km)',
            zaxis_title='Z (km)',
            aspectmode='data',  # Keeps the earth spherical
            bgcolor="black"
        ),
        margin=dict(r=0, l=0, b=0, t=40),
        paper_bgcolor="black",
        font=dict(color="white")
    )

    fig.show()


if __name__ == "__main__":
    bus_data, target_data = run_simulation()
    visualize(bus_data, target_data)
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
import random

# --- Physics Constants ---
G = 9.81  # Gravity (m/s^2)
R_GAS = 287.05  # Specific gas constant for dry air (J/(kg*K))
EARTH_OMEGA = 7.2921e-5  # Earth's rotation rate (rad/s)
LATITUDE = np.radians(45.0)  # Assumed Latitude for Coriolis


class Projectile:
    def __init__(self, mass_kg, diameter_mm, c_d, muzzle_vel):
        self.mass = mass_kg
        self.area = np.pi * ((diameter_mm / 1000) / 2) ** 2
        self.cd = c_d
        self.v0 = muzzle_vel


class Environment:
    def __init__(self, wind_speed, wind_azimuth, temp_c, pressure_sl):
        self.wind_speed = wind_speed  # m/s
        self.wind_dir = np.radians(wind_azimuth)  # radians
        self.temp_k = temp_c + 273.15
        self.pressure_sl = pressure_sl  # Pascals (e.g., 101325)

        # Wind Vector (North, East, Down) -> (x, y, z)
        # Assuming X=East, Y=North for coordinate system
        self.wind_vec = np.array([
            wind_speed * np.sin(self.wind_dir),
            wind_speed * np.cos(self.wind_dir),
            0.0
        ])

    def get_density(self, altitude):
        # Standard Atmosphere Model (Isothermal approx for simplicity)
        # rho = P / (R * T)
        # P = P0 * exp(-g * h / (R * T))
        if altitude < 0: altitude = 0
        pressure = self.pressure_sl * np.exp(-G * altitude / (R_GAS * self.temp_k))
        rho = pressure / (R_GAS * self.temp_k)
        return rho


class FireControlSystem:
    def __init__(self, projectile, env):
        self.proj = projectile
        self.env = env

        # Earth rotation vector for Coriolis (North component and Vertical component)
        # Omega = [0, Omega * cos(lat), Omega * sin(lat)] in North-Up frame
        # In our X=East, Y=North, Z=Up frame:
        self.omega_vec = np.array([
            0,
            EARTH_OMEGA * np.cos(LATITUDE),
            EARTH_OMEGA * np.sin(LATITUDE)
        ])

    def derivatives(self, t, state):
        """
        Differential Equations of Motion.
        State vector: [x, y, z, vx, vy, vz]
        """
        x, y, z, vx, vy, vz = state
        v = np.array([vx, vy, vz])

        # 1. Air Density at current altitude
        rho = self.env.get_density(z)

        # 2. Relative Velocity (Airspeed)
        v_rel = v - self.env.wind_vec
        v_mag = np.linalg.norm(v_rel)

        # 3. Drag Force: Fd = -0.5 * rho * v^2 * Cd * A * (v_rel / |v_rel|)
        force_drag = -0.5 * rho * v_mag * v_rel * self.proj.cd * self.proj.area

        # 4. Coriolis Force: F_cor = -2 * m * (Omega x v)
        force_coriolis = -2 * self.proj.mass * np.cross(self.omega_vec, v)

        # 5. Gravity
        force_gravity = np.array([0, 0, -self.proj.mass * G])

        # Total Acceleration
        accel = (force_drag + force_coriolis + force_gravity) / self.proj.mass

        # Stop simulation if below ground
        if z < 0:
            return [0, 0, 0, 0, 0, 0]

        return [vx, vy, vz, accel[0], accel[1], accel[2]]

    def simulate_shot(self, azimuth, elevation, max_time=120):
        """
        Simulates a single shot given firing angles.
        Returns: Impact Position (x, y)
        """
        # Initial Velocity Vector
        az_rad = np.radians(azimuth)
        el_rad = np.radians(elevation)

        # Conversion to Cartesian (X=East, Y=North, Z=Up)
        vx0 = self.proj.v0 * np.cos(el_rad) * np.sin(az_rad)
        vy0 = self.proj.v0 * np.cos(el_rad) * np.cos(az_rad)
        vz0 = self.proj.v0 * np.sin(el_rad)

        y0 = [0, 0, 0, vx0, vy0, vz0]  # Origin at 0,0,0

        # Event to detect ground impact
        def hit_ground(t, y):
            return y[2]

        hit_ground.terminal = True
        hit_ground.direction = -1

        sol = solve_ivp(
            self.derivatives,
            [0, max_time],
            y0,
            events=hit_ground,
            rtol=1e-5
        )

        if len(sol.t_events[0]) > 0:
            impact_pos = sol.y_events[0][0][:3]
            flight_time = sol.t_events[0][0]
            return impact_pos, flight_time, sol  # Return full solution for plotting
        else:
            return None, None, None

    def calculate_firing_solution(self, target_pos, target_vel):
        """
        Iteratively finds the Azimuth and Elevation to hit a moving target.
        Target Pos: [x, y, z]
        Target Vel: [vx, vy, vz]
        """
        print(f"Calculating Firing Solution for Target at {target_pos} m...")

        # Initial guess: Point directly at target
        dx, dy, dz = target_pos
        dist_flat = np.sqrt(dx ** 2 + dy ** 2)
        az_guess = np.degrees(np.arctan2(dx, dy))
        el_guess = np.degrees(np.arctan2(dz, dist_flat)) + 5.0  # Add small arc guess

        def error_func(angles):
            # Angles = [azimuth, elevation]

            # 1. Simulate Shot
            impact, tof, _ = self.simulate_shot(angles[0], angles[1])

            if impact is None: return 1e9  # Penalty for not hitting ground

            # 2. Predict Target Position at Impact Time
            # P_target_future = P_target_now + V_target * Time_of_Flight
            predicted_target = target_pos + target_vel * tof

            # 3. Calculate Miss Distance (Error)
            error = np.linalg.norm(impact - predicted_target)
            return error

        # Optimization loop (Nelder-Mead is robust for this)
        res = minimize(error_func, [az_guess, el_guess], method='Nelder-Mead', tol=0.1)

        final_az, final_el = res.x
        impact, tof, traj = self.simulate_shot(final_az, final_el)

        return final_az, final_el, tof, traj


# --- Main Simulation Script ---

def main():
    # 1. Setup Scenario
    # 155mm Artillery Shell (M795 equivalent)
    # Mass: 46.7kg, Diameter: 155mm, Cd: ~0.3, V0: 827 m/s
    projectile = Projectile(mass_kg=46.7, diameter_mm=155, c_d=0.29, muzzle_vel=827)

    # Environment: 10 m/s wind from West (270 deg), 20C
    env = Environment(wind_speed=10, wind_azimuth=270, temp_c=20, pressure_sl=101325)

    fcs = FireControlSystem(projectile, env)

    # Target: 15km away North, moving East at 15 m/s (Tank speed)
    target_pos = np.array([5000.0, 15000.0, 0.0])
    target_vel = np.array([15.0, 0.0, 0.0])

    # 2. Get Solution
    az, el, tof, main_traj = fcs.calculate_firing_solution(target_pos, target_vel)

    print(f"\n--- FIRING SOLUTION ---")
    print(f"Azimuth:   {az:.4f} degrees")
    print(f"Elevation: {el:.4f} degrees")
    print(f"Time of Flight: {tof:.2f} s")
    print(f"Target Lead: {np.linalg.norm(target_vel * tof):.2f} m")

    # 3. Monte Carlo Simulation (Circle of Error Probability)
    print("\nRunning Monte Carlo Simulation (1000 rounds)...")

    impacts_x = []
    impacts_y = []

    # Store original values
    base_v0 = projectile.v0
    base_wind_s = env.wind_speed

    for i in range(1000):
        # Inject Perturbations (Real-world chaos)
        projectile.v0 = np.random.normal(base_v0, 1.5)  # +/- 1.5 m/s variation
        env.wind_speed = np.random.normal(base_wind_s, 2.0)  # Gusts

        # Fire!
        imp, _, _ = fcs.simulate_shot(az, el)
        if imp is not None:
            impacts_x.append(imp[0])
            impacts_y.append(imp[1])

        if i % 100 == 0: print(f"Simulated {i} rounds...")

    # Calculate actual target position at impact
    final_target_pos = target_pos + target_vel * tof

    # Calculate CEP (50th percentile of distance error)
    errors = np.sqrt((np.array(impacts_x) - final_target_pos[0]) ** 2 +
                     (np.array(impacts_y) - final_target_pos[1]) ** 2)
    cep = np.percentile(errors, 50)

    print(f"\nCEP (50%): {cep:.2f} meters")

    # 4. Visualization
    fig = plt.figure(figsize=(12, 6))

    # Plot A: Trajectory Side View
    ax1 = fig.add_subplot(1, 2, 1)
    # Extract trajectory path
    path_x = main_traj.y[0]
    path_y = main_traj.y[1]
    path_z = main_traj.y[2]
    dist = np.sqrt(path_x ** 2 + path_y ** 2)  # Ground distance

    ax1.plot(dist, path_z, 'b-', label='Ideal Trajectory')
    ax1.set_title("Ballistic Trajectory (Side View)")
    ax1.set_xlabel("Distance (m)")
    ax1.set_ylabel("Altitude (m)")
    ax1.grid(True)

    # Plot B: Impact Dispersion (Top View)
    ax2 = fig.add_subplot(1, 2, 2)
    ax2.scatter(impacts_x, impacts_y, c='blue', alpha=0.3, s=10, label='Impacts')
    ax2.plot(final_target_pos[0], final_target_pos[1], 'rX', markersize=15, label='Target Center')

    # Draw CEP Circle
    circle = plt.Circle((final_target_pos[0], final_target_pos[1]), cep, color='red', fill=False, linewidth=2,
                        label=f'CEP {cep:.1f}m')
    ax2.add_patch(circle)

    ax2.set_title(f"Target Impact Dispersion (Top View)\nTarget Speed: {np.linalg.norm(target_vel)} m/s")
    ax2.set_xlabel("East (m)")
    ax2.set_ylabel("North (m)")
    ax2.axis('equal')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
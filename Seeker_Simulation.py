import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.integrate import solve_ivp
from mpl_toolkits.mplot3d import Axes3D

# --- Configuration Constants ---
N_CONST = 4.0  # Navigation Constant (Aggressiveness)
G_ACCEL = 9.81  # Gravity (m/s^2)
MAX_G_LOAD = 30.0  # Missile Structural Limit (30G)
DT = 0.01  # Simulation Step Size (s)
MAX_TIME = 20.0  # Max flight duration
HIT_RADIUS = 5.0  # Kill radius (meters)

# Initial States
TARGET_START_POS = [4000, 3000, 2000]  # x, y, z (meters)
TARGET_VELOCITY = [-300, -10, 0]  # m/s (approx Mach 0.9)
MISSILE_START_POS = [0, 0, 0]
MISSILE_SPEED = 800.0  # m/s (approx Mach 2.3)


class EngagementSimulation:
    def __init__(self):
        self.hit_detected = False
        self.miss_distance = float('inf')
        self.intercept_time = 0.0

    def limit_g_force(self, accel_vec):
        """Clips acceleration vector to MAX_G_LOAD."""
        mag = np.linalg.norm(accel_vec)
        limit = MAX_G_LOAD * G_ACCEL
        if mag > limit:
            return (accel_vec / mag) * limit
        return accel_vec

    def dynamics(self, t, state):
        """
        Differential Equations of Motion for both Missile and Target.
        State Vector (12 vars): [Rx_t, Ry_t, Rz_t, Vx_t, Vy_t, Vz_t, Rx_m, Ry_m, Rz_m, Vx_m, Vy_m, Vz_m]
        """
        # Unpack State
        Rt = state[0:3]  # Target Pos
        Vt = state[3:6]  # Target Vel
        Rm = state[6:9]  # Missile Pos
        Vm = state[9:12]  # Missile Vel

        # 1. Relative Kinematics
        R_rel = Rt - Rm  # Relative Position Vector
        V_rel = Vt - Vm  # Relative Velocity Vector
        dist = np.linalg.norm(R_rel)

        # Stop calculation if intercept passed (improves solver efficiency)
        if dist < HIT_RADIUS:
            return np.zeros(12)

        # 2. Target Logic (Evasive Maneuver)
        # The target flies straight until missile is close (< 1.5km), then pulls 9G turn
        At = np.array([0.0, 0.0, 0.0])
        if dist < 1500:
            # Create a vector perpendicular to velocity for turning
            # Cross product with 'Up' vector roughly
            turn_vec = np.cross(Vt, np.array([0, 0, 1]))
            if np.linalg.norm(turn_vec) == 0: turn_vec = np.array([1, 0, 0])
            turn_dir = turn_vec / np.linalg.norm(turn_vec)

            # Apply 9G acceleration
            At = turn_dir * 9.0 * G_ACCEL

        # 3. Missile Logic (Proportional Navigation)
        # Formula: a_m = N * V_closing * (Omega x V_m_unit)
        # Pure ProNav applies force perpendicular to missile velocity

        # Rotation Vector (Omega) = (R_rel x V_rel) / |R_rel|^2
        # This is the rate of rotation of the Line of Sight (LOS)
        omega = np.cross(R_rel, V_rel) / (dist ** 2 + 1e-6)

        # Closing Velocity (Scalar approximation)
        # Vc = - (R_rel . V_rel) / |R_rel|
        vc = -np.dot(R_rel, V_rel) / (dist + 1e-6)

        # Missile Velocity Unit Vector
        vm_mag = np.linalg.norm(Vm)
        vm_unit = Vm / (vm_mag + 1e-6)

        # Guidance Command
        # Using Pure Proportional Navigation (PPN)
        # Acceleration is perpendicular to velocity vector to steer
        Am = N_CONST * vc * np.cross(omega, vm_unit)

        # Structural Constraints
        Am = self.limit_g_force(Am)

        # Output Derivatives [Vel_t, Acc_t, Vel_m, Acc_m]
        d_state = np.concatenate([Vt, At, Vm, Am])
        return d_state

    def run(self):
        print("Initializing Guidance Systems...")
        print(f"Target Initial Pos: {TARGET_START_POS}")
        print(f"Missile Speed: {MISSILE_SPEED} m/s")

        # Initial State Construction
        # Missile Velocity needs to point roughly at target initially
        # Calculate initial LOS vector
        los_vec = np.array(TARGET_START_POS) - np.array(MISSILE_START_POS)
        los_unit = los_vec / np.linalg.norm(los_vec)
        vm_start = los_unit * MISSILE_SPEED

        y0 = np.concatenate([TARGET_START_POS, TARGET_VELOCITY, MISSILE_START_POS, vm_start])

        # Event Detection: Impact
        def intercept_event(t, y):
            Rt = y[0:3]
            Rm = y[6:9]
            dist = np.linalg.norm(Rt - Rm)
            return dist - HIT_RADIUS

        intercept_event.terminal = True  # Stop solver when event occurs
        intercept_event.direction = -1  # Only trigger when distance is decreasing

        # Solve ODE
        t_span = (0, MAX_TIME)
        sol = solve_ivp(self.dynamics, t_span, y0,
                        events=intercept_event,
                        rtol=1e-5, atol=1e-5,
                        max_step=0.05)

        # Analysis
        final_state = sol.y[:, -1]
        final_dist = np.linalg.norm(final_state[0:3] - final_state[6:9])

        self.t_hist = sol.t
        self.Rt_hist = sol.y[0:3].T
        self.Rm_hist = sol.y[6:9].T
        self.miss_distance = final_dist
        self.intercept_time = sol.t[-1]

        if sol.status == 1:  # A termination event occurred
            self.hit_detected = True
            print(f"--- SPLASH ---")
            print(f"Target Intercepted at T={self.intercept_time:.2f}s")
            print(f"Miss Distance: {self.miss_distance:.2f} m")
        else:
            print(f"--- MISS ---")
            print(f"Missile ran out of fuel/time.")
            print(f"Closest Approach: {self.miss_distance:.2f} m")

        return sol

    def animate(self):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Set Plot Limits based on trajectory
        all_x = np.concatenate([self.Rt_hist[:, 0], self.Rm_hist[:, 0]])
        all_y = np.concatenate([self.Rt_hist[:, 1], self.Rm_hist[:, 1]])
        all_z = np.concatenate([self.Rt_hist[:, 2], self.Rm_hist[:, 2]])

        max_range = np.array(
            [all_x.max() - all_x.min(), all_y.max() - all_y.min(), all_z.max() - all_z.min()]).max() / 2.0
        mid_x = (all_x.max() + all_x.min()) * 0.5
        mid_y = (all_y.max() + all_y.min()) * 0.5
        mid_z = (all_z.max() + all_z.min()) * 0.5

        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)

        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Altitude (m)')
        ax.set_title(f"Proportional Navigation Homing (N={N_CONST})")

        # Plot Lines
        line_t, = ax.plot([], [], [], 'b--', label='Target (Fighter)')
        line_m, = ax.plot([], [], [], 'r-', linewidth=2, label='Missile (Seeker)')

        # Markers for current pos
        point_t, = ax.plot([], [], [], 'bo')
        point_m, = ax.plot([], [], [], 'ro')

        # Explosion Marker
        boom, = ax.plot([], [], [], 'k*', markersize=20, alpha=0)

        # Text Info
        txt_info = ax.text2D(0.05, 0.95, "", transform=ax.transAxes)

        frames = len(self.t_hist)
        step = max(1, frames // 400)  # Limit to ~400 frames for smooth animation

        def update(frame):
            idx = frame * step
            if idx >= frames: idx = frames - 1

            # Update Trails
            line_t.set_data(self.Rt_hist[:idx, 0], self.Rt_hist[:idx, 1])
            line_t.set_3d_properties(self.Rt_hist[:idx, 2])

            line_m.set_data(self.Rm_hist[:idx, 0], self.Rm_hist[:idx, 1])
            line_m.set_3d_properties(self.Rm_hist[:idx, 2])

            # Update Heads
            point_t.set_data([self.Rt_hist[idx, 0]], [self.Rt_hist[idx, 1]])
            point_t.set_3d_properties([self.Rt_hist[idx, 2]])

            point_m.set_data([self.Rm_hist[idx, 0]], [self.Rm_hist[idx, 1]])
            point_m.set_3d_properties([self.Rm_hist[idx, 2]])

            # Check for Boom
            if idx == frames - 1 and self.hit_detected:
                boom.set_data([self.Rm_hist[idx, 0]], [self.Rm_hist[idx, 1]])
                boom.set_3d_properties([self.Rm_hist[idx, 2]])
                boom.set_alpha(1.0)
                boom.set_color('orange')

            # Info
            current_dist = np.linalg.norm(self.Rt_hist[idx] - self.Rm_hist[idx])
            txt_info.set_text(f"Time: {self.t_hist[idx]:.2f}s\nRange: {current_dist:.1f}m")

            return line_t, line_m, point_t, point_m, boom, txt_info

        ani = FuncAnimation(fig, update, frames=frames // step, interval=20, blit=False)
        plt.legend()
        plt.show()


if __name__ == "__main__":
    sim = EngagementSimulation()
    sim.run()
    sim.animate()
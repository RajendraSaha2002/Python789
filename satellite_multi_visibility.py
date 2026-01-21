"""
Multi-Satellite Visibility (Constellation Sim)
- Walker-Delta constellation (default: 24 sats, 6 planes, Starlink-like 53° inc, 550 km alt)
- Grid of ground users every 10° lat/lon
- Coverage criterion: elevation > 10°
- Animated Matplotlib "GUI": left panel shows which users are covered; right panel shows
  global coverage % over time as it evolves.

Dependencies:
    pip install "poliastro[all]" astropy matplotlib numpy

Run:
    python constellation_sim.py
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import (
    CartesianRepresentation,
    GCRS,
    ITRS,
    EarthLocation,
)
from poliastro.bodies import Earth
from poliastro.twobody import Orbit

# -----------------------------
# Constellation builder
# -----------------------------
def walker_delta_constellation(
    total_sats=24,
    num_planes=6,
    f=1,
    inc_deg=53.0,
    alt_km=550.0,
):
    """Return a list of poliastro Orbit objects in Walker-Delta pattern.
    f is the Walker phasing factor.
    """
    sats = []
    a = Earth.R + alt_km * u.km
    ecc = 0.0 * u.one
    inc = inc_deg * u.deg
    argp = 0 * u.deg
    num_per_plane = total_sats // num_planes

    for p in range(num_planes):
        raan = (360 / num_planes * p) * u.deg
        for s in range(num_per_plane):
            # Walker phasing: M = (360/num_per_plane)*s + (360*f/total_sats)*p
            mean_anom = (360 / num_per_plane * s + 360 * f / total_sats * p) * u.deg
            # For circular orbits, true anomaly ≈ mean anomaly
            nu = mean_anom
            sat = Orbit.from_classical(Earth, a, ecc, inc, raan, argp, nu)
            sats.append(sat)
    return sats

# -----------------------------
# Ground grid
# -----------------------------
def build_user_grid(lat_step=10, lon_step=10):
    lats = np.arange(-80, 81, lat_step)  # avoid poles singularity
    lons = np.arange(-180, 181, lon_step)
    users = []
    for lat in lats:
        for lon in lons:
            loc = EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, height=0 * u.m)
            x, y, z = loc.to_geocentric()
            users.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "ecef": np.array([x.to_value(u.m), y.to_value(u.m), z.to_value(u.m)]),
                }
            )
    return users

# -----------------------------
# Geometry helpers
# -----------------------------
def ecef_from_orbit_at_time(orbit: Orbit, t: Time):
    """Get ECEF (ITRS) position vector in meters for an orbit at time t."""
    o = orbit.propagate(t - orbit.epoch)
    r = o.r  # position vector with units
    gcrs = GCRS(
        x=r[0],
        y=r[1],
        z=r[2],
        representation_type=CartesianRepresentation,
        obstime=t,
    )
    itrs = gcrs.transform_to(ITRS(obstime=t))
    return itrs.cartesian.xyz.to(u.m).value  # ndarray (3,)

def elevation_deg(user_ecef, sat_ecef):
    rho = sat_ecef - user_ecef
    rho_norm = np.linalg.norm(rho)
    zenith_unit = user_ecef / np.linalg.norm(user_ecef)
    # elevation = asin( dot(rho_unit, zenith_unit) )
    elev = np.degrees(np.arcsin(np.dot(rho, zenith_unit) / rho_norm))
    return elev

def coverage_for_time(sats, users, t, elev_mask_deg=10.0):
    covered_flags = []
    for user in users:
        user_ecef = user["ecef"]
        visible = False
        for sat in sats:
            sat_ecef = ecef_from_orbit_at_time(sat, t)
            elev = elevation_deg(user_ecef, sat_ecef)
            if elev > elev_mask_deg:
                visible = True
                break
        covered_flags.append(visible)
    covered_pct = 100 * np.mean(covered_flags)
    return covered_flags, covered_pct

# -----------------------------
# Simulation + Animation
# -----------------------------
def run_sim(
    total_sats=24,
    num_planes=6,
    f=1,
    inc_deg=53.0,
    alt_km=550.0,
    lat_step=10,
    lon_step=10,
    elev_mask_deg=10.0,
    duration_minutes=60,
    step_seconds=60,
):
    sats = walker_delta_constellation(total_sats, num_planes, f, inc_deg, alt_km)
    users = build_user_grid(lat_step, lon_step)
    start = Time.now()
    times = start + np.arange(0, duration_minutes * 60 + step_seconds, step_seconds) * u.s

    # Pre-allocate coverage history
    cov_history = []

    # Matplotlib GUI
    fig, (ax_map, ax_cov) = plt.subplots(
        1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [2, 1]}
    )
    plt.tight_layout()

    # Map scatter
    lats = [u["lat"] for u in users]
    lons = [u["lon"] for u in users]
    colors = ["red"] * len(users)
    scat = ax_map.scatter(lons, lats, c=colors, s=25, alpha=0.7)
    ax_map.set_xlim(-180, 180)
    ax_map.set_ylim(-90, 90)
    ax_map.set_xlabel("Longitude (deg)")
    ax_map.set_ylabel("Latitude (deg)")
    ax_map.set_title("User coverage (green = visible)")

    # Coverage plot
    cov_line, = ax_cov.plot([], [], lw=2)
    ax_cov.set_xlim(0, duration_minutes * 60)
    ax_cov.set_ylim(0, 100)
    ax_cov.set_xlabel("Time (s)")
    ax_cov.set_ylabel("Coverage (%)")
    ax_cov.set_title("Global coverage over time")
    cov_text = ax_cov.text(
        0.05, 0.9, "", transform=ax_cov.transAxes, fontsize=12, bbox=dict(facecolor="w")
    )

    def init():
        cov_line.set_data([], [])
        return scat, cov_line, cov_text

    def update(frame_idx):
        t = times[frame_idx]
        flags, cov_pct = coverage_for_time(sats, users, t, elev_mask_deg)
        cov_history.append(cov_pct)

        new_colors = ["green" if f else "red" for f in flags]
        scat.set_color(new_colors)

        xdata = np.arange(len(cov_history)) * step_seconds
        cov_line.set_data(xdata, cov_history)
        cov_text.set_text(f"t = {int(xdata[-1])} s\nCoverage = {cov_pct:5.1f}%")
        ax_cov.set_xlim(0, max(step_seconds, xdata[-1]))
        return scat, cov_line, cov_text

    ani = FuncAnimation(
        fig,
        update,
        frames=len(times),
        init_func=init,
        interval=200,  # ms between frames
        blit=False,
        repeat=False,
    )

    plt.show()

if __name__ == "__main__":
    run_sim()
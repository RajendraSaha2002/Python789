
import math
import time
import json
import random
import psycopg2
from datetime import datetime

# ─── Database Config ───────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "aegis_db",
    "user":     "postgres",
    "password": "varrie75"
}

# ─── Constants ─────────────────────────────────────────────
DANGER_RADIUS   = 15.0          # units — "Dangerously Close" threshold
POLL_INTERVAL   = 2.0           # seconds between engine cycles
WORLD_BOUNDS    = (0, 0, 100, 100)   # (min_x, min_y, max_x, max_y)

# Geofence polygon vertices (world units)
GEOFENCE_POLYGON = [
    (5,  5),
    (95, 5),
    (95, 95),
    (5,  95)
]


# ============================================================
#  SECTION 1 — Database Layer
# ============================================================
def get_connection():
    """Return a live psycopg2 connection."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_all_assets(conn) -> list[dict]:
    """
    Retrieve all active assets from PostgreSQL.
    Uses the native 'point' type: location field returns (x, y).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                name,
                asset_type,
                location[0]  AS x,   -- PostgreSQL point index
                location[1]  AS y
            FROM assets
            WHERE active = TRUE
            ORDER BY id;
        """)
        rows = cur.fetchall()
        return [
            {"id": r[0], "name": r[1], "type": r[2],
             "x": float(r[3]), "y": float(r[4])}
            for r in rows
        ]


def update_asset_position(conn, asset_id: int, x: float, y: float):
    """Move an asset to new coordinates using PostgreSQL point syntax."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE assets
            SET location = point(%s, %s),
                updated_at = NOW()
            WHERE id = %s;
        """, (x, y, asset_id))
    conn.commit()


def write_alert(conn, alert_type: str, message: str, asset_ids: list[int]):
    """Persist an alert to the alerts table for the JS frontend to poll."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alerts (alert_type, message, asset_ids, triggered_at)
            VALUES (%s, %s, %s, NOW());
        """, (alert_type, message, json.dumps(asset_ids)))
    conn.commit()


def clear_old_alerts(conn):
    """Remove alerts older than 10 seconds (keep dashboard fresh)."""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM alerts
            WHERE triggered_at < NOW() - INTERVAL '10 seconds';
        """)
    conn.commit()


# ============================================================
#  SECTION 2 — Kinematics Engine (Pure Math)
# ============================================================
def euclidean_distance(ax: float, ay: float, bx: float, by: float) -> float:
    """
    Pythagorean theorem:  d = √( (x₂−x₁)² + (y₂−y₁)² )
    No external libraries — pure Python math.
    """
    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)


def is_dangerously_close(a: dict, b: dict, threshold: float = DANGER_RADIUS) -> bool:
    """Returns True if two assets are within the danger radius."""
    d = euclidean_distance(a["x"], a["y"], b["x"], b["y"])
    return d < threshold


def distance_from_origin(asset: dict) -> float:
    """Distance from coordinate origin (0, 0)."""
    return euclidean_distance(0, 0, asset["x"], asset["y"])


def bearing(a: dict, b: dict) -> float:
    """
    Compass bearing from asset A to asset B (degrees, 0=North/+Y).
    Returns value in range [0, 360).
    """
    dx = b["x"] - a["x"]
    dy = b["y"] - a["y"]      # +Y = North in our coordinate system
    angle = math.degrees(math.atan2(dx, dy))
    return angle % 360


def check_proximity_pairs(assets: list[dict]) -> list[dict]:
    """
    Compare every pair of assets.
    O(n²) — acceptable for tactical-scale asset counts.
    Returns list of proximity alert dicts.
    """
    alerts = []
    n = len(assets)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = assets[i], assets[j]
            d = euclidean_distance(a["x"], a["y"], b["x"], b["y"])
            if d < DANGER_RADIUS:
                alerts.append({
                    "asset_a":   a["name"],
                    "asset_b":   b["name"],
                    "id_a":      a["id"],
                    "id_b":      b["id"],
                    "distance":  round(d, 2),
                    "bearing_ab": round(bearing(a, b), 1)
                })
    return alerts


# ============================================================
#  SECTION 3 — Geofence (Point-in-Polygon)
# ============================================================
def point_in_polygon(px: float, py: float, polygon: list[tuple]) -> bool:
    """
    Ray-casting algorithm.
    Fires a ray along +X from (px, py) and counts edge crossings.
    Odd count = inside.  Even count = outside.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        # Check if ray crosses this edge
        crosses = ((yi > py) != (yj > py))
        if crosses:
            intersect_x = (xj - xi) * (py - yi) / (yj - yi) + xi
            if px < intersect_x:
                inside = not inside
        j = i
    return inside


def check_geofence(assets: list[dict]) -> list[dict]:
    """
    Returns list of assets that have left the geofence polygon.
    """
    breaches = []
    for a in assets:
        if not point_in_polygon(a["x"], a["y"], GEOFENCE_POLYGON):
            breaches.append(a)
    return breaches


# ============================================================
#  SECTION 4 — Simulated Movement (Dev / Testing mode)
# ============================================================
# In production, real hardware/GPS pushes updates to the DB.
# In development, this function simulates asset movement.

_velocities: dict = {}   # { asset_id: (vx, vy) }

def simulate_movement(conn, assets: list[dict]):
    """
    Randomly walk each asset by a small delta per cycle.
    Bounces off WORLD_BOUNDS walls.
    """
    for a in assets:
        if a["id"] not in _velocities:
            _velocities[a["id"]] = (
                random.uniform(-1.5, 1.5),
                random.uniform(-1.5, 1.5)
            )
        vx, vy = _velocities[a["id"]]
        nx = a["x"] + vx
        ny = a["y"] + vy

        # Wall bounce
        min_x, min_y, max_x, max_y = WORLD_BOUNDS
        if nx < min_x or nx > max_x:
            vx = -vx;  nx = max(min_x, min(max_x, nx))
        if ny < min_y or ny > max_y:
            vy = -vy;  ny = max(min_y, min(max_y, ny))

        _velocities[a["id"]] = (vx, vy)
        update_asset_position(conn, a["id"], nx, ny)


# ============================================================
#  SECTION 5 — Main Engine Loop
# ============================================================
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] AEGIS ▶ {msg}")


def run_engine():
    """
    Main polling loop.
    Connects to DB → fetches assets → runs kinematics → writes alerts.
    """
    log("Kinematics Engine starting …")
    conn = get_connection()
    log("PostgreSQL connection established.")

    try:
        while True:
            # 1. Fetch current asset positions
            assets = fetch_all_assets(conn)
            if not assets:
                log("No active assets in database.")
                time.sleep(POLL_INTERVAL)
                continue

            log(f"Tracking {len(assets)} assets.")

            # 2. Simulate movement (dev mode — remove in production)
            simulate_movement(conn, assets)
            assets = fetch_all_assets(conn)   # re-fetch after move

            # 3. Proximity detection
            proximity_alerts = check_proximity_pairs(assets)
            for alert in proximity_alerts:
                msg = (f"DANGER: {alert['asset_a']} ↔ {alert['asset_b']} "
                       f"— dist={alert['distance']} units "
                       f"| bearing={alert['bearing_ab']}°")
                log(f"⚠  {msg}")
                write_alert(conn, "PROXIMITY", msg,
                            [alert["id_a"], alert["id_b"]])

            # 4. Geofence breach detection
            breaches = check_geofence(assets)
            for b in breaches:
                msg = (f"BREACH: {b['name']} is OUTSIDE geofence "
                       f"@ ({b['x']:.1f}, {b['y']:.1f})")
                log(f"🚨 {msg}")
                write_alert(conn, "GEOFENCE", msg, [b["id"]])

            # 5. Status summary
            if not proximity_alerts and not breaches:
                log("All assets SECURE — no alerts.")

            # 6. Purge stale alerts
            clear_old_alerts(conn)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        log("Engine stopped by operator.")
    finally:
        conn.close()
        log("Database connection closed.")


# ============================================================
#  Entry Point
# ============================================================
if __name__ == "__main__":
    run_engine()
import psycopg2
import math
import time
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'skyshield_db',
    'port': 5432
}

CITY_COORDS = (400, 300)  # Center of the Map (must match Java)


def calculate_threat():
    print("--- SKYSHIELD THREAT EVALUATOR ONLINE ---")

    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # 1. Fetch Live Tracks
            cur.execute("""
                        SELECT id, track_uuid, x_pos, y_pos, speed_knots, iff_status, threat_score
                        FROM tracks
                        WHERE status = 'LIVE'
                        """)
            tracks = cur.fetchall()

            for t in tracks:
                tid, uuid, x, y, speed, iff, current_score = t

                # --- FUZZY LOGIC ENGINE ---

                # Factor 1: Speed Risk (Normalized)
                # Max speed approx 2000.
                speed_risk = min(100, (speed / 1500) * 100)

                # Factor 2: Proximity/Heading Risk
                # Calculate distance to City
                dist = math.sqrt((x - CITY_COORDS[0]) ** 2 + (y - CITY_COORDS[1]) ** 2)
                # Closer = Higher Risk
                dist_risk = 0
                if dist < 300: dist_risk = 50
                if dist < 100: dist_risk = 100

                # Factor 3: IFF Status
                iff_risk = 0
                if iff == 'UNKNOWN': iff_risk = 40
                if iff == 'HOSTILE': iff_risk = 100  # Manual override persistence

                # Weighted Formula
                final_score = (speed_risk * 0.3) + (dist_risk * 0.4) + (iff_risk * 0.3)
                final_score = min(100, int(final_score))

                # Only update if score changed significantly (Optimization)
                if abs(final_score - current_score) > 2:
                    print(f"[EVAL] {uuid}: Speed:{speed} Dist:{int(dist)} -> Score: {final_score}")
                    cur.execute("UPDATE tracks SET threat_score = %s WHERE id = %s", (final_score, tid))

                # --- AUTO-ENGAGE LOGIC ---
                if final_score > 90:
                    print(f"!!! RED ALERT: AUTO-ENGAGING HOSTILE {uuid} !!!")
                    cur.execute("UPDATE tracks SET status = 'ENGAGED' WHERE id = %s", (tid,))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(0.5)  # Fast polling for real-time feel


if __name__ == "__main__":
    calculate_threat()
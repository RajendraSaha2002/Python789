import psycopg2
import time
import math
import random
from datetime import datetime

# DB CONFIG
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost"
}


class TacticalSimulator:
    def __init__(self):
        self.center_lat = 20.5937  # India roughly
        self.center_long = 78.9629
        self.tick = 0

    def calculate_position(self, asset_type, tick):
        """
        Simulate movement physics based on asset type.
        """
        # Fighters move fast in wide circles
        if asset_type == 'FIGHTER':
            radius = 2.0
            speed_factor = 0.1
            lat = self.center_lat + (radius * math.sin(tick * speed_factor))
            lon = self.center_long + (radius * math.cos(tick * speed_factor))
            heading = (math.degrees(
                math.atan2(math.cos(tick * speed_factor), -math.sin(tick * speed_factor))) + 360) % 360
            speed = 450  # knots

        # Destroyers move slow in small patrols
        elif asset_type == 'DESTROYER':
            radius = 0.5
            speed_factor = 0.02
            lat = self.center_lat - 1.5 + (radius * math.sin(tick * speed_factor))
            lon = self.center_long - 1.5 + (radius * math.cos(tick * speed_factor))
            heading = (math.degrees(
                math.atan2(math.cos(tick * speed_factor), -math.sin(tick * speed_factor))) + 360) % 360
            speed = 30  # knots

        # Tanks hold position mostly
        else:
            lat = self.center_lat + 0.5
            lon = self.center_long + 0.5
            heading = 0
            speed = 0

        return lat, lon, heading, speed

    def run(self):
        print("🔵 VANGUARD SIMULATION ONLINE. Tracking Assets...")
        try:
            conn = psycopg2.connect(**DB_CONFIG)

            # Asset IDs from SQL seed
            assets = [
                {'id': 1, 'type': 'FIGHTER'},
                {'id': 2, 'type': 'FIGHTER'},
                {'id': 3, 'type': 'DESTROYER'},
                {'id': 4, 'type': 'TANK'}
            ]

            while True:
                cur = conn.cursor()

                for asset in assets:
                    # Offset ticks for variety
                    t = self.tick + (asset['id'] * 10)
                    lat, lon, head, spd = self.calculate_position(asset['type'], t)

                    cur.execute("""
                                INSERT INTO asset_pings (asset_id, latitude, longitude, heading, speed_knots)
                                VALUES (%s, %s, %s, %s, %s)
                                """, (asset['id'], lat, lon, head, spd))

                conn.commit()
                print(f"📡 Radar Ping Sent: Tick {self.tick}")
                self.tick += 1
                time.sleep(1.0)  # 1 second update rate

        except Exception as e:
            print(f"Simulation Failed: {e}")
        finally:
            if conn: conn.close()


if __name__ == "__main__":
    sim = TacticalSimulator()
    sim.run()
import cv2
import numpy as np
import psycopg2
import time
import random

# DB CONFIG
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost"
}


class UAVDrone:
    def __init__(self, region_id):
        self.region_id = region_id
        self.lat = 34.0
        self.long = 77.0

    def connect_db(self):
        return psycopg2.connect(**DB_CONFIG)

    def log_detection(self, obj_type, threat, frame_path):
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            query = """
                    INSERT INTO uav_feeds (region_id, detected_object, threat_level, latitude, longitude, image_path)
                    VALUES (%s, %s, %s, %s, %s, %s) \
                    """
            cur.execute(query, (self.region_id, obj_type, threat, self.lat, self.long, frame_path))
            conn.commit()
            conn.close()
            print(f"🔴 ALERT LOGGED: {obj_type} [{threat}]")
        except Exception as e:
            print(f"DB Error: {e}")

    def scan_sector(self):
        print(f"🚁 UAV {self.region_id} ONLINE. Scanning Sector...")

        # Create a dummy video frame (Black background)
        width, height = 640, 480

        while True:
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Simulate "Noise" (Terrain)
            noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)

            # Random Event Generator
            roll = random.randint(1, 100)

            if roll > 95:  # 5% chance of TANK
                # Draw a rectangle (Tank)
                cv2.rectangle(frame, (200, 200), (300, 250), (0, 0, 255), 2)
                cv2.putText(frame, "TARGET: TANK", (200, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                self.log_detection("TANK", "CRITICAL", "/secure/storage/img_001.enc")

            elif roll > 80:  # 15% chance of VEHICLE
                # Draw a circle (Vehicle)
                cv2.circle(frame, (400, 300), 20, (0, 255, 255), 2)
                cv2.putText(frame, "TARGET: VEHICLE", (380, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                self.log_detection("VEHICLE", "MEDIUM", "/secure/storage/img_002.enc")

            # HUD Overlay
            cv2.putText(frame, f"REGION: {self.region_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "LIVE FEED - CLASSIFIED", (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),
                        1)

            cv2.imshow('UAV OPTICAL FEED', frame)

            # Update Coords slightly
            self.lat += 0.0001
            self.long += 0.0001

            if cv2.waitKey(100) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    # Simulate a drone in North Sector
    drone = UAVDrone("N-01")
    drone.scan_sector()
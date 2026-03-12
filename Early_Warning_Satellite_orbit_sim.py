import math
import time


# Simulates a satellite in Molniya orbit (high eccentricity)
def get_satellite_position():
    t = time.time() / 10000

    # Orbital Mechanics (Simplified)
    # Satellites move in sine waves relative to the flat map projection
    lat = 60 * math.sin(t * 50)
    lon = (t * 1000) % 360 - 180

    return {
        'id': 'SAT-EARLY-WARNING-01',
        'lat': lat,
        'lon': lon,
        'altitude_km': 35786,  # Geosynchronous
        'status': 'NOMINAL'
    }


def generate_telemetry():
    # Randomly generate an "Event" (Missile Launch or Nothing)
    import random
    if random.random() < 0.1:
        return {
            'alert_level': 'CRITICAL',
            'type': 'ICBM_SIGNATURE_DETECTED',
            'sector': 'GRID-NORTH-7'
        }
    return {
        'alert_level': 'NOMINAL',
        'type': 'HEARTBEAT',
        'sector': 'ALL_CLEAR'
    }
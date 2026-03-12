import math


# 3D Vector Mathematics for Interception
def calculate_intercept_solution(batteries, target):
    best_battery = None
    min_time_to_intercept = float('inf')

    # Target position (x, y, z)
    tx, ty, tz = target['x'], target['y'], target['alt']

    for bat in batteries:
        if bat['status'] != 'ACTIVE' or bat['total_missiles'] <= 0:
            continue

        # 1. Calculate Slant Range (3D Euclidean Distance)
        # d = sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
        dx = tx - bat['pos_x']
        dy = ty - bat['pos_y']
        dz = (tz / 1000) - (bat['pos_z'] / 1000)  # Convert meters to KM

        slant_range_km = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

        # 2. Check Radar Limits
        if slant_range_km > bat['radar_range_km']:
            continue

        # 3. Calculate Time to Intercept (Time = Distance / Speed)
        # Simplified: Assuming avg missile speed of Mach 3 (~1 km/s)
        missile_speed_km_s = 1.02
        time_to_hit = slant_range_km / missile_speed_km_s

        # Optimization: Choose the battery that can hit it FASTEST
        if time_to_hit < min_time_to_intercept:
            min_time_to_intercept = time_to_hit
            best_battery = bat
            best_battery['intercept_time'] = round(time_to_hit, 2)

    return best_battery
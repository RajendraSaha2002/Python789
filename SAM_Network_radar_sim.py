import random

threats = []


def update_radar_picture():
    # 1. Spawn new threats randomly
    if len(threats) < 2 and random.random() < 0.05:
        threats.append({
            'id': f"TGT-{random.randint(100, 999)}",
            'x': random.randint(0, 100),
            'y': 100,  # Start at top of map
            'alt': random.randint(5000, 15000),  # Meters
            'speed': 0.8,  # km per tick
            'status': 'INBOUND'
        })

    # 2. Move threats
    for t in threats:
        if t['status'] == 'INBOUND':
            t['y'] -= t['speed']  # Move south

    # 3. Remove threats that passed or were destroyed
    active_threats = [t for t in threats if t['y'] > 0 and t['status'] != 'DESTROYED']
    threats[:] = active_threats

    return threats
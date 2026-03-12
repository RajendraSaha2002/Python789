import psycopg2
from psycopg2.extras import RealDictCursor

# Update credentials
DB_CONFIG = {'dbname': 'postgres', 'user': 'postgres', 'password': 'varrie75', 'host': 'localhost', 'port': 5432}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def get_network_status():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Join batteries with their total ammo count
    query = """
        SELECT b.id, b.callsign, b.pos_x, b.pos_y, b.status, b.radar_range_km,
        SUM(m.count) as total_missiles
        FROM batteries b
        LEFT JOIN missile_inventory m ON b.id = m.battery_id
        GROUP BY b.id ORDER BY b.callsign;
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.close()
    return data

def decrement_ammo(battery_id):
    conn = get_conn()
    cur = conn.cursor()
    # Find a missile stack that has ammo and decrease it
    cur.execute("""
        UPDATE missile_inventory SET count = count - 1 
        WHERE id = (
            SELECT id FROM missile_inventory 
            WHERE battery_id = %s AND count > 0 LIMIT 1
        )
    """, (battery_id,))
    conn.commit()
    conn.close()

def log_engagement(battery_id, target_id, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO engagements (battery_id, target_id, result, notes) VALUES (%s, %s, 'INTERCEPT', %s)",
                (battery_id, target_id, note))
    conn.commit()
    conn.close()
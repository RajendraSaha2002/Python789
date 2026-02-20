import psycopg2
import time
import random
import hmac
import hashlib
from datetime import datetime

# Database Configuration
DB_CONFIG = {
    "dbname": "aetheris_db",
    "user": "postgres",
    "password": "varrie75",  # Change to your DB password
    "host": "localhost",
    "port": "5432"
}

# Secret key for simulating Digital Signatures
SECRET_KEY = b"CDS_AETHERIS_SECURE_KEY_2026"


def sign_message(message):
    """Generate a digital signature for PMO messages."""
    return hmac.new(SECRET_KEY, message.encode('utf-8'), hashlib.sha256).hexdigest()


def update_tactical_data(conn):
    """Simulate High-Speed Asset Movement (Naval/Air)"""
    cursor = conn.cursor()
    assets = [
        ("NAVY_DESTROYER_01", "SHIP", random.uniform(10.0, 15.0), random.uniform(70.0, 75.0)),
        ("AIR_FIGHTER_X9", "JET", random.uniform(12.0, 18.0), random.uniform(72.0, 78.0))
    ]

    for asset_id, a_type, lat, lon in assets:
        # Upsert data into Unlogged table
        cursor.execute("""
                       INSERT INTO schema_tactical.live_assets (asset_id, asset_type, lat, lon, status)
                       VALUES (%s, %s, %s, %s, 'ACTIVE') ON CONFLICT (asset_id) DO
                       UPDATE
                           SET lat = EXCLUDED.lat, lon = EXCLUDED.lon, last_updated = CURRENT_TIMESTAMP;
                       """, (asset_id, a_type, lat, lon))

    conn.commit()
    cursor.close()
    print(f"[{datetime.now()}] Tactical Data Updated.")


def send_pmo_flash(conn):
    """Simulate sending an encrypted Flash Message to the PMO"""
    cursor = conn.cursor()
    raw_message = f"FLASH: All clear in Sector 7. Coordinates verified at {datetime.now().strftime('%H:%M:%S')}."

    # In a real scenario, encrypt raw_message with AES-256 here.
    # For now, we simulate the encrypted text and generate a signature.
    encrypted_msg = f"[AES256-ENCRYPTED-PAYLOAD] {raw_message}"
    signature = sign_message(raw_message)

    cursor.execute("""
                   INSERT INTO schema_admin.pmo_messages (sender, encrypted_content, signature)
                   VALUES (%s, %s, %s);
                   """, ("CDS_COMMAND", encrypted_msg, signature))

    conn.commit()
    cursor.close()
    print(f"[{datetime.now()}] PMO Flash Message Dispatched.")


if __name__ == "__main__":
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        print("AETHERIS Python Engine Connected. Starting data simulation...")

        loop_count = 0
        while True:
            # Update radar data every 1 second
            update_tactical_data(connection)

            # Send a PMO secure message every 10 seconds
            if loop_count % 10 == 0:
                send_pmo_flash(connection)

            loop_count += 1
            time.sleep(1)

    except Exception as e:
        print(f"Engine Error: {e}")
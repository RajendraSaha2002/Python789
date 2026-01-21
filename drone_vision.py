import socket
import threading
import sys
import os
import psycopg2
from PIL import Image

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'drone_ops_db',
    'port': 5432
}

HOST = '0.0.0.0'
PORT = 7000


# --- 0. SELF-HEALING DB INIT ---
def init_db():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Create Log Table
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS surveillance_logs
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        drone_id
                        VARCHAR
                    (
                        10
                    ),
                        image_path TEXT,
                        analysis_result VARCHAR
                    (
                        50
                    ),
                        confidence_score DECIMAL
                    (
                        5,
                        2
                    ),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

        # Create Telemetry Table if missing (Backstop)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS drone_telemetry
                    (
                        drone_id
                        VARCHAR
                    (
                        10
                    ) PRIMARY KEY,
                        status VARCHAR
                    (
                        20
                    ) DEFAULT 'CHARGING',
                        battery_level INT DEFAULT 100,
                        current_sector VARCHAR
                    (
                        10
                    ) DEFAULT 'BASE',
                        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

        # Seed if empty
        cur.execute("SELECT count(*) FROM drone_telemetry")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO drone_telemetry (drone_id) VALUES ('DRONE-01'), ('DRONE-02'), ('DRONE-03')")

        conn.commit()
        print("[VISION] Database ready.")
    except Exception as e:
        print(f"[ERROR] DB Init Failed: {e}")
    finally:
        if conn: conn.close()


# --- 1. IMAGE PROCESSING LOGIC ---
def analyze_image(image_path):
    try:
        if not os.path.exists(image_path):
            return "ERROR: File Not Found", 0.0

        img = Image.open(image_path)
        img = img.convert("RGB")
        width, height = img.size

        red_pixel_count = 0
        total_pixels = width * height

        # Pixel Check Logic
        for x in range(width):
            for y in range(height):
                r, g, b = img.getpixel((x, y))
                # Simple logic: High Red, Low Green/Blue
                if r > 150 and g < 100 and b < 100:
                    red_pixel_count += 1

        red_ratio = red_pixel_count / total_pixels

        if red_ratio > 0.40:  # If > 40% of image is red
            return "FIRE DETECTED", red_ratio * 100
        else:
            return "SECTOR SAFE", (1 - red_ratio) * 100

    except Exception as e:
        return f"ERROR: {str(e)}", 0.0


# --- 2. SOCKET SERVER ---
def handle_client(client_socket):
    try:
        # Expecting "DRONE_ID|PATH"
        request = client_socket.recv(1024).decode('utf-8').strip()
        print(f"[REQUEST] {request}")

        if "|" in request:
            drone_id, path = request.split("|")

            # Analyze
            status, confidence = analyze_image(path)

            print(f"   -> Result: {status} ({confidence:.1f}%)")

            # Log to DB
            log_to_db(drone_id, path, status, confidence)

            # Respond to Java
            response = f"{status} (Confidence: {confidence:.1f}%)"
            client_socket.sendall(response.encode('utf-8'))

    except Exception as e:
        print(f"[ERROR] Handler: {e}")
    finally:
        client_socket.close()


def log_to_db(drone_id, path, status, conf):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO surveillance_logs (drone_id, image_path, analysis_result, confidence_score) VALUES (%s, %s, %s, %s)",
            (drone_id, path, status, conf))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB LOG ERROR] {e}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[VISION] AI Service listening on port {PORT}...")
    except OSError:
        print(f"[ERROR] Port {PORT} busy.")
        return

    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,)).start()


if __name__ == "__main__":
    init_db()
    start_server()
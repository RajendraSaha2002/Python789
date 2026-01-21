import psycopg2
import re
import time
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'sigint_db',
    'port': 5432
}

# --- NLP PATTERNS (Regular Expressions) ---
PATTERNS = {
    "COORDINATES": r"(-?\d{1,3}\.\d+),\s*(-?\d{1,3}\.\d+)",  # Matches "34.55, 69.20"
    "DATE": r"\d{4}-\d{2}-\d{2}",  # Matches YYYY-MM-DD
}

KEYWORDS = {
    "NUCLEAR": 100,
    "STRIKE": 80,
    "TARGET": 60,
    "PAYLOAD": 50,
    "SAFEHOUSE": 40
}


def init_db():
    """Automatically creates tables if they don't exist."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 1. Create Raw Intercepts Table
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS raw_intercepts
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        sender
                        VARCHAR
                    (
                        50
                    ),
                        receiver VARCHAR
                    (
                        50
                    ),
                        message_content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_processed BOOLEAN DEFAULT FALSE
                        );
                    """)

        # 2. Create Processed Intel Table
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS processed_intel
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        intercept_id
                        INT
                        REFERENCES
                        raw_intercepts
                    (
                        id
                    ),
                        entity_type VARCHAR
                    (
                        50
                    ),
                        extracted_value VARCHAR
                    (
                        255
                    ),
                        threat_score INT DEFAULT 0
                        );
                    """)

        conn.commit()
        print("[INIT] Database structure verified.")
    except Exception as e:
        print(f"[INIT ERROR] {e}")
    finally:
        if conn: conn.close()


def analyze_traffic():
    print("--- SIGINT ANALYZER ONLINE ---")

    # Initialize DB before starting loop
    init_db()

    print("Listening for unprocessed intercepts...")

    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # 1. Fetch unprocessed messages
            cur.execute("SELECT id, message_content FROM raw_intercepts WHERE is_processed = FALSE")
            rows = cur.fetchall()

            if rows:
                print(f"Processing {len(rows)} new messages...")

            for row in rows:
                msg_id = row[0]
                content = row[1]
                intel_found = False

                # 2. Extract Coordinates
                coords = re.findall(PATTERNS["COORDINATES"], content)
                for lat, lon in coords:
                    val = f"{lat}, {lon}"
                    print(f"  [+] ID {msg_id}: Found LOCATION {val}")
                    cur.execute(
                        "INSERT INTO processed_intel (intercept_id, entity_type, extracted_value, threat_score) VALUES (%s, 'LOCATION', %s, 50)",
                        (msg_id, val))
                    intel_found = True

                # 3. Extract Dates
                dates = re.findall(PATTERNS["DATE"], content)
                for date_val in dates:
                    print(f"  [+] ID {msg_id}: Found DATE {date_val}")
                    cur.execute(
                        "INSERT INTO processed_intel (intercept_id, entity_type, extracted_value, threat_score) VALUES (%s, 'DATE', %s, 20)",
                        (msg_id, date_val))
                    intel_found = True

                # 4. Keyword Analysis (Threat Scoring)
                upper_content = content.upper()
                for word, score in KEYWORDS.items():
                    if word in upper_content:
                        print(f"  [!] ID {msg_id}: Found KEYWORD '{word}' (Score: {score})")
                        cur.execute(
                            "INSERT INTO processed_intel (intercept_id, entity_type, extracted_value, threat_score) VALUES (%s, 'KEYWORD', %s, %s)",
                            (msg_id, word, score))
                        intel_found = True

                # 5. Mark as Processed
                cur.execute("UPDATE raw_intercepts SET is_processed = TRUE WHERE id = %s", (msg_id,))
                conn.commit()

            cur.close()
            conn.close()

        except Exception as e:
            # Short sleep on error to avoid log spam if DB connection drops
            print(f"Error: {e}")
            time.sleep(2)

        time.sleep(2)  # Poll every 2 seconds


if __name__ == "__main__":
    analyze_traffic()
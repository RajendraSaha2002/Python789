import psycopg2
import time
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'orbital_db',
    'port': 5432
}


def init_db():
    """Self-healing: Ensures Btree_gist extension and tables exist."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Enable Extension (Needs Superuser rights usually, or pre-installed)
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
        except psycopg2.errors.InsufficientPrivilege:
            print("[WARN] Could not enable 'btree_gist'. Ensure it is installed on DB.")
            conn.rollback()

        # Create Tables
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS satellites
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        name
                        VARCHAR
                    (
                        50
                    ) UNIQUE NOT NULL, type VARCHAR
                    (
                        20
                    )
                        );
                    """)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS requests
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        target_name
                        VARCHAR
                    (
                        100
                    ) NOT NULL,
                        priority INT NOT NULL, satellite_id INT REFERENCES satellites
                    (
                        id
                    ),
                        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        end_time TIMESTAMP WITH TIME ZONE NOT NULL,
                                               status VARCHAR (20) DEFAULT 'PENDING'
                        );
                    """)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS schedule
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        request_id
                        INT
                        REFERENCES
                        requests
                    (
                        id
                    ),
                        satellite_id INT REFERENCES satellites
                    (
                        id
                    ),
                        mission_window TSTZRANGE NOT NULL,
                        EXCLUDE USING GIST
                    (
                        satellite_id
                        WITH =,
                        mission_window
                        WITH
                        &&
                    )
                        );
                    """)

        # Seed
        cur.execute(
            "INSERT INTO satellites (name, type) VALUES ('KH-11', 'OPTICAL'), ('Lacrosse-5', 'RADAR') ON CONFLICT DO NOTHING")

        conn.commit()
        print("[INIT] Database Ready.")
    except Exception as e:
        print(f"[ERROR] Init Failed: {e}")
    finally:
        if conn: conn.close()


def run_optimizer():
    print("--- ORBITAL SCHEDULE OPTIMIZER ---")
    print("Watching for PENDING requests...")

    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # 1. Fetch PENDING requests, sorted by PRIORITY (1 first)
            cur.execute("""
                        SELECT id, target_name, priority, satellite_id, start_time, end_time
                        FROM requests
                        WHERE status = 'PENDING'
                        ORDER BY priority ASC, start_time ASC
                        """)
            requests = cur.fetchall()

            if requests:
                print(f"Processing {len(requests)} new requests...")

            for req in requests:
                req_id, target, prio, sat_id, start, end = req

                print(f" > Attempting to schedule '{target}' (Priority {prio})...")

                try:
                    # 2. Try to Insert into Schedule (Postgres Constraint enforces non-overlap)
                    # We create the TSTZRANGE string manually: '[start, end)'
                    # Note: Psycopg2 handles datetime objects, but explicit range construction is safer for logic

                    cur.execute("""
                                INSERT INTO schedule (request_id, satellite_id, mission_window)
                                VALUES (%s, %s, tstzrange(%s, %s, '[)'))
                                """, (req_id, sat_id, start, end))

                    # If success:
                    cur.execute("UPDATE requests SET status = 'SCHEDULED' WHERE id = %s", (req_id,))
                    conn.commit()
                    print(f"   [SUCCESS] Slot Secured.")

                except psycopg2.errors.ExclusionViolation:
                    # 3. Handle Conflict
                    conn.rollback()  # Must rollback the failed transaction
                    print(f"   [CONFLICT] Time slot unavailable on this satellite.")
                    cur.execute("UPDATE requests SET status = 'CONFLICT' WHERE id = %s", (req_id,))
                    conn.commit()

            cur.close()
            conn.close()

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

        time.sleep(2)


if __name__ == "__main__":
    init_db()
    run_optimizer()
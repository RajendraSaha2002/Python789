import psycopg2
from psycopg2.extras import RealDictCursor


DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'varrie75',
    'host': 'localhost',
    'port': 5432
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_system_status():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM system_status ORDER BY id DESC LIMIT 1")
    status = cur.fetchone()
    conn.close()
    return status


def get_recent_logs(limit=50):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM selinux_audit_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
    logs = cur.fetchall()

    # Format timestamps for JSON serialization
    for log in logs:
        log['timestamp'] = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

    conn.close()
    return logs


def insert_audit_log(action, scontext, tcontext, tclass, details):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO selinux_audit_logs (action, scontext, tcontext, tclass, details) VALUES (%s, %s, %s, %s, %s)",
        (action, scontext, tcontext, tclass, details)
    )
    conn.commit()
    conn.close()
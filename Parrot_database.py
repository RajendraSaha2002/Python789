# ============================================================
# database.py — PostgreSQL Connection Manager (psycopg2)
# ============================================================

import psycopg2
from psycopg2.extras import RealDictCursor
from Parrot_config import Config

def get_connection():
    """Returns a new PostgreSQL connection."""
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASS,
        cursor_factory=RealDictCursor
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally return results."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
                return [dict(row) for row in result]
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


class Parrot_database:
    pass
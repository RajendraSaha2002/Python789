# ============================================================
# db_init.py — Initialize PostgreSQL Database & Tables
# RUN THIS SCRIPT FIRST before starting the server!
# Usage: python backend/utils/db_init.py
# ============================================================

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from backend.Parrot_config import Config

def create_database():
    """Create the database if it doesn't exist."""
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname="postgres",          # connect to default db first
        user=Config.DB_USER,
        password=Config.DB_PASS
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{Config.DB_NAME}'")
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {Config.DB_NAME}")
        print(f"[+] Database '{Config.DB_NAME}' created.")
    else:
        print(f"[✓] Database '{Config.DB_NAME}' already exists.")
    cur.close()
    conn.close()

def create_tables():
    """Create all required tables."""
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASS
    )
    conn.autocommit = True
    cur = conn.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'analyst',
            created_at TIMESTAMP DEFAULT NOW(),
            last_login TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS system_stats (
            id SERIAL PRIMARY KEY,
            cpu_percent FLOAT,
            ram_percent FLOAT,
            disk_percent FLOAT,
            network_bytes_sent BIGINT,
            network_bytes_recv BIGINT,
            recorded_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS security_logs (
            id SERIAL PRIMARY KEY,
            log_type VARCHAR(100),
            severity VARCHAR(50),
            message TEXT,
            source_ip VARCHAR(50),
            timestamp TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS network_scans (
            id SERIAL PRIMARY KEY,
            target VARCHAR(255),
            open_ports TEXT,
            os_guess VARCHAR(255),
            scan_time TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            alert_type VARCHAR(100),
            message TEXT,
            severity VARCHAR(50),
            acknowledged BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    ]

    for table_sql in tables:
        cur.execute(table_sql)

    # Insert default admin user (password: admin123)
    import hashlib
    default_pass = hashlib.sha256("admin123".encode()).hexdigest()
    cur.execute("""
        INSERT INTO users (username, password_hash, role)
        VALUES ('admin', %s, 'admin')
        ON CONFLICT (username) DO NOTHING
    """, (default_pass,))

    print("[✓] All tables created successfully.")
    print("[✓] Default admin user: username='admin', password='admin123'")
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("  Parrot Dashboard — DB Initializer")
    print("=" * 50)
    create_database()
    create_tables()
    print("[✓] Database setup complete! Now run: python app.py")
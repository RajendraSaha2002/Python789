import psycopg2
import pandas as pd
from fpdf import FPDF
import time
import os
import warnings

# Use SQLAlchemy if available to silence pandas warnings, but fallback to raw connection
try:
    from sqlalchemy import create_engine

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# --- CONFIGURATION ---
# UPDATE PASSWORD HERE
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',
    'dbname': 'supply_chain_db',
    'port': 5432
}

ANOMALY_THRESHOLD_MINUTES = 5


class AuditReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SECURITY AUDIT: SUPPLY CHAIN ANOMALIES', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def init_db():
    """Self-healing: Creates table and seed data if missing."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Create Table
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS ledger_immutable
                    (
                        transaction_hash
                        VARCHAR
                    (
                        64
                    ) PRIMARY KEY,
                        item_id VARCHAR
                    (
                        50
                    ) NOT NULL,
                        item_type VARCHAR
                    (
                        20
                    ) DEFAULT 'STANDARD',
                        from_loc VARCHAR
                    (
                        50
                    ) NOT NULL,
                        to_loc VARCHAR
                    (
                        50
                    ) NOT NULL,
                        officer_id VARCHAR
                    (
                        50
                    ) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

        # Check Seed
        cur.execute("SELECT count(*) FROM ledger_immutable")
        if cur.fetchone()[0] == 0:
            print("Seeding suspicious data...")
            # Suspicious movement (Rapid transfers)
            cur.execute(
                "INSERT INTO ledger_immutable (transaction_hash, item_id, item_type, from_loc, to_loc, officer_id, timestamp) VALUES ('hash_2', 'PART-X99', 'STANDARD', 'Warehouse 1', 'Dock A', 'LT-Dan', NOW() - INTERVAL '2 minutes')")
            cur.execute(
                "INSERT INTO ledger_immutable (transaction_hash, item_id, item_type, from_loc, to_loc, officer_id, timestamp) VALUES ('hash_3', 'PART-X99', 'STANDARD', 'Dock A', 'Ship B', 'LT-Dan', NOW() - INTERVAL '1 minute')")

        conn.commit()
        print("Database initialized.")
    except Exception as e:
        print(f"DB Init Error: {e}")
    finally:
        if conn: conn.close()


def scan_for_anomalies():
    print("--- STARTING AUDIT SCAN ---")

    # 1. Initialize DB first
    init_db()

    conn = None
    try:
        # Ignore the pandas UserWarning about DBAPI2
        warnings.filterwarnings("ignore", category=UserWarning)

        conn = psycopg2.connect(**DB_CONFIG)

        # 2. Fetch All Transactions
        query = "SELECT item_id, item_type, from_loc, to_loc, timestamp, officer_id FROM ledger_immutable ORDER BY item_id, timestamp"

        # Pandas read_sql
        df = pd.read_sql(query, conn)

        if df.empty:
            print("Ledger empty. No audit required.")
            return

        anomalies = []

        # 3. Logic: Rapid Movement Detection
        df['prev_time'] = df.groupby('item_id')['timestamp'].shift(1)
        df['time_diff'] = (df['timestamp'] - df['prev_time']).dt.total_seconds() / 60.0  # Minutes

        suspicious_moves = df[df['time_diff'] < ANOMALY_THRESHOLD_MINUTES]

        if not suspicious_moves.empty:
            print(f"!!! ALERT: {len(suspicious_moves)} suspicious movements detected.")
            for _, row in suspicious_moves.iterrows():
                anomalies.append(
                    f"RAPID MOVEMENT: Item {row['item_id']} moved twice in {row['time_diff']:.1f} mins by {row['officer_id']}")

        # 4. Logic: Unauthorized Destination
        bad_locs = df[(df['item_type'] == 'SENSITIVE') & (df['to_loc'].str.contains('Public', case=False))]
        for _, row in bad_locs.iterrows():
            anomalies.append(
                f"SECURITY BREACH: Sensitive Item {row['item_id']} sent to unsecured location '{row['to_loc']}'")

        # 5. Generate PDF Report
        if anomalies:
            generate_pdf(anomalies)
        else:
            print("System Green. No anomalies detected.")

    except Exception as e:
        print(f"Audit Error: {e}")
    finally:
        if conn: conn.close()


def generate_pdf(anomalies):
    pdf = AuditReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.set_text_color(255, 0, 0)  # Red Text
    for alert in anomalies:
        pdf.multi_cell(0, 10, f"[ALERT] {alert}")
        pdf.ln(2)

    filename = f"Audit_Report_{int(time.time())}.pdf"
    pdf.output(filename)
    print(f"PDF Report Generated: {filename}")


if __name__ == "__main__":
    scan_for_anomalies()
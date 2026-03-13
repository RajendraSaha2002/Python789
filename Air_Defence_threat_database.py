
import sqlite3
import uuid
import datetime

class ThreatDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_tables()
        self._seed_demo_data()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS threats (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                unit_count INTEGER,
                sector TEXT,
                threat_level TEXT DEFAULT 'UNKNOWN',
                lat REAL,
                lng REAL,
                speed REAL,
                heading REAL,
                timestamp TEXT,
                behavior_flags TEXT
            )
        """)
        self.conn.commit()

    def _seed_demo_data(self):
        demo = [
            ("charlie-12", "Charlie-12", "DRONE_SWARM", 12, "Sector 7-G",
             "CRITICAL", 34.05, -118.25, 85.0, 270.0, "2024-01-01T11:26:26", "erratic,high_speed"),
            ("beta-3", "Beta-3", "UNKNOWN_AIRCRAFT", 3, "North Quadrant",
             "MEDIUM", 34.10, -118.30, 40.0, 180.0, "2024-01-01T11:12:34", "stealth_mode"),
            ("alpha-1", "Alpha-1", "FIXED_WING", 1, "Defence Grid Alpha",
             "HIGH", 34.08, -118.20, 200.0, 90.0, "2024-01-01T11:21:28", "jamming_detected"),
        ]
        for row in demo:
            self.conn.execute(
                "INSERT OR IGNORE INTO threats VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
        self.conn.commit()

    def get_all_threats(self):
        cur = self.conn.execute("SELECT * FROM threats")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def add_threat(self, data):
        tid = data.get("id", str(uuid.uuid4())[:8])
        now = datetime.datetime.now().isoformat()
        self.conn.execute("""
            INSERT OR REPLACE INTO threats
            (id,name,type,unit_count,sector,threat_level,lat,lng,speed,heading,timestamp,behavior_flags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            tid, data.get("name", tid), data.get("type", "UNKNOWN"),
            data.get("unit_count", 1), data.get("sector", "Unknown"),
            data.get("threat_level", "UNKNOWN"),
            data.get("lat", 0.0), data.get("lng", 0.0),
            data.get("speed", 0.0), data.get("heading", 0.0),
            now, data.get("behavior_flags", "")
        ))
        self.conn.commit()

    def update_threat_level(self, tid, level):
        self.conn.execute(
            "UPDATE threats SET threat_level=? WHERE id=?", (level, tid))
        self.conn.commit()

    def get_threat(self, tid):
        cur = self.conn.execute("SELECT * FROM threats WHERE id=?", (tid,))
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None

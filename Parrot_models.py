# ============================================================
# models.py — PostgreSQL Database Table Models
# Parrot Security OS Dashboard — Pro Edition
# Pure psycopg2 — No ORM (No SQLAlchemy)
# Used by: all routes/, services/, db_init.py
# ============================================================

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import datetime
from typing import Optional, Any
from Parrot_database import execute_query, get_connection
from utils.Parrot_helpers import (
    hash_password,
    verify_password,
    normalize_severity,
    round_percent,
    to_json_safe,
    safe_int,
    safe_float,
    safe_str,
    timestamp_now,
    format_time_ago,
    sort_by_severity,
)


# ════════════════════════════════════════════════════════════
# SECTION 1 — BASE MODEL
# ════════════════════════════════════════════════════════════

class BaseModel:
    """
    Base class for all models.
    Provides common to_dict(), __repr__(), and timestamp helpers.
    """

    TABLE_NAME: str = ''

    @classmethod
    def table(cls) -> str:
        """Return the table name for this model."""
        return cls.TABLE_NAME

    @staticmethod
    def _now() -> str:
        """Return current UTC timestamp string."""
        return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _format_row(row: Optional[dict]) -> Optional[dict]:
        """Convert any datetime values in a row dict to ISO strings."""
        if not row:
            return None
        result = {}
        for key, val in row.items():
            if isinstance(val, (datetime.datetime, datetime.date)):
                result[key] = val.isoformat()
            else:
                result[key] = val
        return result

    @staticmethod
    def _format_rows(rows: list) -> list:
        """Convert all rows in a list."""
        return [
            BaseModel._format_row(r)
            for r in rows
            if r is not None
        ]

    def to_dict(self) -> dict:
        """Convert model instance to dict (override in subclasses)."""
        return {}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict()}>"


# ════════════════════════════════════════════════════════════
# SECTION 2 — USER MODEL
# ════════════════════════════════════════════════════════════

class UserModel(BaseModel):
    """
    Model for the 'users' table.

    Table Schema:
        id           SERIAL PRIMARY KEY
        username     VARCHAR(100) UNIQUE NOT NULL
        password_hash VARCHAR(255) NOT NULL
        role         VARCHAR(50) DEFAULT 'analyst'
        created_at   TIMESTAMP DEFAULT NOW()
        last_login   TIMESTAMP
    """

    TABLE_NAME = 'users'

    def __init__(
        self,
        id:            Optional[int]  = None,
        username:      str            = '',
        password_hash: str            = '',
        role:          str            = 'analyst',
        created_at:    Optional[str]  = None,
        last_login:    Optional[str]  = None,
    ):
        self.id            = id
        self.username      = username
        self.password_hash = password_hash
        self.role          = role
        self.created_at    = created_at or self._now()
        self.last_login    = last_login

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "username":    self.username,
            "role":        self.role,
            "created_at":  self.created_at,
            "last_login":  self.last_login,
            # Never expose password_hash in to_dict
        }

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    def create(
        username: str,
        password: str,
        role:     str = 'analyst'
    ) -> dict:
        """
        Create a new user with hashed password.
        Returns: dict with success and message
        """
        try:
            hashed = hash_password(password)
            execute_query(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                """,
                (username.strip(), hashed, role.lower()),
                fetch=False
            )
            return {
                "success": True,
                "message": f"User '{username}' created successfully.",
            }
        except Exception as e:
            err = str(e)
            if 'unique' in err.lower() or 'duplicate' in err.lower():
                return {
                    "success": False,
                    "message": f"Username '{username}' already exists.",
                }
            return {"success": False, "message": err}

    @staticmethod
    def get_by_id(user_id: int) -> Optional[dict]:
        """
        Fetch a user by ID.
        Returns: user dict (without password_hash) or None
        """
        rows = execute_query(
            """
            SELECT id, username, role, created_at, last_login
            FROM users WHERE id = %s
            """,
            (safe_int(user_id),)
        )
        return BaseModel._format_row(rows[0]) if rows else None

    @staticmethod
    def get_by_username(username: str) -> Optional[dict]:
        """
        Fetch a user by username (includes password_hash for auth).
        Returns: full user dict or None
        """
        rows = execute_query(
            """
            SELECT id, username, password_hash, role, created_at, last_login
            FROM users WHERE username = %s
            """,
            (username.strip(),)
        )
        return BaseModel._format_row(rows[0]) if rows else None

    @staticmethod
    def get_all(limit: int = 100) -> list:
        """
        Fetch all users (without password_hash).
        Returns: list of user dicts
        """
        rows = execute_query(
            """
            SELECT id, username, role, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (safe_int(limit, 100),)
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[dict]:
        """
        Authenticate a user by username and password.
        Updates last_login on success.
        Returns: user dict (without password_hash) or None
        """
        user = UserModel.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.get('password_hash', '')):
            return None
        # Update last_login
        execute_query(
            "UPDATE users SET last_login = NOW() WHERE id = %s",
            (user['id'],),
            fetch=False
        )
        # Return without password_hash
        return {
            "id":         user['id'],
            "username":   user['username'],
            "role":       user['role'],
            "created_at": user['created_at'],
            "last_login": timestamp_now(),
        }

    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """
        Update a user's password.
        Returns: True on success
        """
        try:
            hashed = hash_password(new_password)
            execute_query(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed, safe_int(user_id)),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def update_role(user_id: int, new_role: str) -> bool:
        """
        Update a user's role.
        Returns: True on success
        """
        valid_roles = {'admin', 'analyst', 'viewer'}
        if new_role.lower() not in valid_roles:
            return False
        try:
            execute_query(
                "UPDATE users SET role = %s WHERE id = %s",
                (new_role.lower(), safe_int(user_id)),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def delete(user_id: int) -> bool:
        """
        Delete a user by ID (cannot delete user id=1 / root admin).
        Returns: True on success
        """
        if safe_int(user_id) <= 1:
            return False
        try:
            execute_query(
                "DELETE FROM users WHERE id = %s",
                (safe_int(user_id),),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def count() -> int:
        """Return total number of users."""
        rows = execute_query("SELECT COUNT(*) as cnt FROM users")
        return safe_int(rows[0]['cnt']) if rows else 0

    @staticmethod
    def exists(username: str) -> bool:
        """Check if a username already exists."""
        rows = execute_query(
            "SELECT 1 FROM users WHERE username = %s",
            (username.strip(),)
        )
        return bool(rows)


# ════════════════════════════════════════════════════════════
# SECTION 3 — SYSTEM STATS MODEL
# ════════════════════════════════════════════════════════════

class SystemStatModel(BaseModel):
    """
    Model for the 'system_stats' table.

    Table Schema:
        id                  SERIAL PRIMARY KEY
        cpu_percent         FLOAT
        ram_percent         FLOAT
        disk_percent        FLOAT
        network_bytes_sent  BIGINT
        network_bytes_recv  BIGINT
        recorded_at         TIMESTAMP DEFAULT NOW()
    """

    TABLE_NAME = 'system_stats'

    def __init__(
        self,
        id:                 Optional[int]   = None,
        cpu_percent:        float           = 0.0,
        ram_percent:        float           = 0.0,
        disk_percent:       float           = 0.0,
        network_bytes_sent: int             = 0,
        network_bytes_recv: int             = 0,
        recorded_at:        Optional[str]   = None,
    ):
        self.id                  = id
        self.cpu_percent         = round_percent(cpu_percent)
        self.ram_percent         = round_percent(ram_percent)
        self.disk_percent        = round_percent(disk_percent)
        self.network_bytes_sent  = safe_int(network_bytes_sent)
        self.network_bytes_recv  = safe_int(network_bytes_recv)
        self.recorded_at         = recorded_at or self._now()

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "cpu_percent":         self.cpu_percent,
            "ram_percent":         self.ram_percent,
            "disk_percent":        self.disk_percent,
            "network_bytes_sent":  self.network_bytes_sent,
            "network_bytes_recv":  self.network_bytes_recv,
            "recorded_at":         self.recorded_at,
        }

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    def record(
        cpu_percent:        float = 0.0,
        ram_percent:        float = 0.0,
        disk_percent:       float = 0.0,
        network_bytes_sent: int   = 0,
        network_bytes_recv: int   = 0,
    ) -> bool:
        """
        Insert a new system stat snapshot.
        Returns: True on success
        """
        try:
            execute_query(
                """
                INSERT INTO system_stats
                    (cpu_percent, ram_percent, disk_percent,
                     network_bytes_sent, network_bytes_recv)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    round_percent(cpu_percent),
                    round_percent(ram_percent),
                    round_percent(disk_percent),
                    safe_int(network_bytes_sent),
                    safe_int(network_bytes_recv),
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"[SystemStatModel.record] Error: {e}")
            return False

    @staticmethod
    def get_latest(limit: int = 60) -> list:
        """
        Get the most recent system stat snapshots.
        Returns: list of stat dicts ordered newest first
        """
        rows = execute_query(
            """
            SELECT * FROM system_stats
            ORDER BY recorded_at DESC
            LIMIT %s
            """,
            (safe_int(limit, 60),)
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_history(limit: int = 60) -> list:
        """
        Get system stat history ordered oldest first (for charts).
        Returns: list of stat dicts
        """
        rows = execute_query(
            """
            SELECT * FROM (
                SELECT * FROM system_stats
                ORDER BY recorded_at DESC
                LIMIT %s
            ) sub
            ORDER BY recorded_at ASC
            """,
            (safe_int(limit, 60),)
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_averages(hours: int = 24) -> dict:
        """
        Get average CPU/RAM/Disk over the last N hours.
        Returns: dict with avg_cpu, avg_ram, avg_disk
        """
        rows = execute_query(
            """
            SELECT
                ROUND(AVG(cpu_percent)::numeric,  2) AS avg_cpu,
                ROUND(AVG(ram_percent)::numeric,  2) AS avg_ram,
                ROUND(AVG(disk_percent)::numeric, 2) AS avg_disk
            FROM system_stats
            WHERE recorded_at >= NOW() - INTERVAL '%s hours'
            """,
            (safe_int(hours, 24),)
        )
        if rows:
            return {
                "avg_cpu":  safe_float(rows[0].get('avg_cpu',  0)),
                "avg_ram":  safe_float(rows[0].get('avg_ram',  0)),
                "avg_disk": safe_float(rows[0].get('avg_disk', 0)),
                "hours":    hours,
            }
        return {"avg_cpu": 0, "avg_ram": 0, "avg_disk": 0, "hours": hours}

    @staticmethod
    def get_peaks(hours: int = 24) -> dict:
        """
        Get peak (max) CPU/RAM/Disk values over the last N hours.
        Returns: dict with peak_cpu, peak_ram, peak_disk
        """
        rows = execute_query(
            """
            SELECT
                MAX(cpu_percent)  AS peak_cpu,
                MAX(ram_percent)  AS peak_ram,
                MAX(disk_percent) AS peak_disk
            FROM system_stats
            WHERE recorded_at >= NOW() - INTERVAL '%s hours'
            """,
            (safe_int(hours, 24),)
        )
        if rows:
            return {
                "peak_cpu":  safe_float(rows[0].get('peak_cpu',  0)),
                "peak_ram":  safe_float(rows[0].get('peak_ram',  0)),
                "peak_disk": safe_float(rows[0].get('peak_disk', 0)),
                "hours":     hours,
            }
        return {"peak_cpu": 0, "peak_ram": 0, "peak_disk": 0, "hours": hours}

    @staticmethod
    def purge_old(days: int = 7) -> int:
        """
        Delete system stats older than N days.
        Returns: number of rows deleted
        """
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM system_stats
                    WHERE recorded_at < NOW() - INTERVAL '%s days'
                    """,
                    (safe_int(days, 7),)
                )
                count = cur.rowcount
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            print(f"[SystemStatModel.purge_old] Error: {e}")
            return 0

    @staticmethod
    def count() -> int:
        """Return total number of system stat records."""
        rows = execute_query("SELECT COUNT(*) as cnt FROM system_stats")
        return safe_int(rows[0]['cnt']) if rows else 0


# ════════════════════════════════════════════════════════════
# SECTION 4 — SECURITY LOG MODEL
# ════════════════════════════════════════════════════════════

class SecurityLogModel(BaseModel):
    """
    Model for the 'security_logs' table.

    Table Schema:
        id          SERIAL PRIMARY KEY
        log_type    VARCHAR(100)
        severity    VARCHAR(50)
        message     TEXT
        source_ip   VARCHAR(50)
        timestamp   TIMESTAMP DEFAULT NOW()
    """

    TABLE_NAME = 'security_logs'

    VALID_SEVERITIES = {'INFO', 'WARNING', 'ERROR', 'CRITICAL'}

    def __init__(
        self,
        id:        Optional[int] = None,
        log_type:  str           = 'GENERAL',
        severity:  str           = 'INFO',
        message:   str           = '',
        source_ip: str           = '127.0.0.1',
        timestamp: Optional[str] = None,
    ):
        self.id        = id
        self.log_type  = safe_str(log_type,  'GENERAL').upper()
        self.severity  = normalize_severity(severity)
        self.message   = safe_str(message,   '')
        self.source_ip = safe_str(source_ip, '127.0.0.1')
        self.timestamp = timestamp or self._now()

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "log_type":  self.log_type,
            "severity":  self.severity,
            "message":   self.message,
            "source_ip": self.source_ip,
            "timestamp": self.timestamp,
            "time_ago":  format_time_ago(self.timestamp),
        }

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    def add(
        log_type:  str = 'GENERAL',
        message:   str = '',
        severity:  str = 'INFO',
        source_ip: str = '127.0.0.1',
    ) -> bool:
        """
        Insert a new security log entry.
        Returns: True on success
        """
        try:
            execute_query(
                """
                INSERT INTO security_logs
                    (log_type, severity, message, source_ip)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    safe_str(log_type, 'GENERAL').upper(),
                    normalize_severity(severity),
                    safe_str(message,   '')[:2000],
                    safe_str(source_ip, '127.0.0.1'),
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"[SecurityLogModel.add] Error: {e}")
            return False

    @staticmethod
    def get_all(
        limit:    int = 100,
        severity: str = '',
        log_type: str = '',
    ) -> list:
        """
        Fetch security logs with optional filters.
        Returns: list of log dicts ordered newest first
        """
        conditions = []
        params     = []

        if severity:
            conditions.append("severity = %s")
            params.append(normalize_severity(severity))
        if log_type:
            conditions.append("log_type = %s")
            params.append(safe_str(log_type).upper())

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(safe_int(limit, 100))

        rows = execute_query(
            f"""
            SELECT * FROM security_logs
            {where}
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            tuple(params)
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_by_id(log_id: int) -> Optional[dict]:
        """Fetch a single log entry by ID."""
        rows = execute_query(
            "SELECT * FROM security_logs WHERE id = %s",
            (safe_int(log_id),)
        )
        return BaseModel._format_row(rows[0]) if rows else None

    @staticmethod
    def get_by_severity(severity: str, limit: int = 100) -> list:
        """
        Fetch logs filtered by severity level.
        Returns: list of log dicts
        """
        rows = execute_query(
            """
            SELECT * FROM security_logs
            WHERE severity = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (normalize_severity(severity), safe_int(limit, 100))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_by_ip(source_ip: str, limit: int = 50) -> list:
        """
        Fetch logs filtered by source IP.
        Returns: list of log dicts
        """
        rows = execute_query(
            """
            SELECT * FROM security_logs
            WHERE source_ip = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (safe_str(source_ip), safe_int(limit, 50))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_recent(hours: int = 24, limit: int = 100) -> list:
        """
        Fetch logs from the last N hours.
        Returns: list of log dicts
        """
        rows = execute_query(
            """
            SELECT * FROM security_logs
            WHERE timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (safe_int(hours, 24), safe_int(limit, 100))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_severity_counts() -> dict:
        """
        Get count of logs grouped by severity.
        Returns: dict {severity: count}
        """
        rows = execute_query(
            """
            SELECT severity, COUNT(*) as count
            FROM security_logs
            GROUP BY severity
            ORDER BY count DESC
            """
        )
        return {
            row['severity']: safe_int(row['count'])
            for row in (rows or [])
        }

    @staticmethod
    def search(keyword: str, limit: int = 50) -> list:
        """
        Full-text search in log messages.
        Returns: list of matching log dicts
        """
        rows = execute_query(
            """
            SELECT * FROM security_logs
            WHERE message ILIKE %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (f'%{keyword}%', safe_int(limit, 50))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def delete_by_id(log_id: int) -> bool:
        """Delete a log entry by ID."""
        try:
            execute_query(
                "DELETE FROM security_logs WHERE id = %s",
                (safe_int(log_id),),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def purge_old(days: int = 30) -> int:
        """
        Delete logs older than N days.
        Returns: number of rows deleted
        """
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM security_logs
                    WHERE timestamp < NOW() - INTERVAL '%s days'
                    """,
                    (safe_int(days, 30),)
                )
                count = cur.rowcount
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            print(f"[SecurityLogModel.purge_old] Error: {e}")
            return 0

    @staticmethod
    def count() -> int:
        """Return total number of security log records."""
        rows = execute_query("SELECT COUNT(*) as cnt FROM security_logs")
        return safe_int(rows[0]['cnt']) if rows else 0


# ════════════════════════════════════════════════════════════
# SECTION 5 — NETWORK SCAN MODEL
# ════════════════════════════════════════════════════════════

class NetworkScanModel(BaseModel):
    """
    Model for the 'network_scans' table.

    Table Schema:
        id          SERIAL PRIMARY KEY
        target      VARCHAR(255)
        open_ports  TEXT
        os_guess    VARCHAR(255)
        scan_time   TIMESTAMP DEFAULT NOW()
    """

    TABLE_NAME = 'network_scans'

    def __init__(
        self,
        id:         Optional[int]  = None,
        target:     str            = '',
        open_ports: str            = '',
        os_guess:   str            = 'Unknown',
        scan_time:  Optional[str]  = None,
    ):
        self.id         = id
        self.target     = safe_str(target,     '')
        self.open_ports = safe_str(open_ports, '')
        self.os_guess   = safe_str(os_guess,   'Unknown')
        self.scan_time  = scan_time or self._now()

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "target":     self.target,
            "open_ports": self.open_ports,
            "os_guess":   self.os_guess,
            "scan_time":  self.scan_time,
            "time_ago":   format_time_ago(self.scan_time),
        }

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    def save_scan(
        target:     str,
        open_ports: list,
        os_guess:   str = 'Unknown',
    ) -> bool:
        """
        Save a completed port scan result.
        open_ports: list of dicts [{"port": 22, "service": "ssh"}, ...]
        Returns: True on success
        """
        try:
            import json
            ports_json = json.dumps(open_ports)
            execute_query(
                """
                INSERT INTO network_scans
                    (target, open_ports, os_guess)
                VALUES (%s, %s, %s)
                """,
                (
                    safe_str(target),
                    ports_json,
                    safe_str(os_guess, 'Unknown'),
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"[NetworkScanModel.save_scan] Error: {e}")
            return False

    @staticmethod
    def get_all(limit: int = 50) -> list:
        """
        Fetch all network scan records.
        Returns: list of scan dicts ordered newest first
        """
        rows = execute_query(
            """
            SELECT * FROM network_scans
            ORDER BY scan_time DESC
            LIMIT %s
            """,
            (safe_int(limit, 50),)
        )
        result = []
        for row in (rows or []):
            row = BaseModel._format_row(row)
            if row:
                try:
                    import json
                    row['open_ports'] = json.loads(
                        row.get('open_ports', '[]') or '[]'
                    )
                except Exception:
                    row['open_ports'] = []
                result.append(row)
        return result

    @staticmethod
    def get_by_target(target: str, limit: int = 10) -> list:
        """
        Fetch scan history for a specific target IP.
        Returns: list of scan dicts
        """
        rows = execute_query(
            """
            SELECT * FROM network_scans
            WHERE target = %s
            ORDER BY scan_time DESC
            LIMIT %s
            """,
            (safe_str(target), safe_int(limit, 10))
        )
        result = []
        for row in (rows or []):
            row = BaseModel._format_row(row)
            if row:
                try:
                    import json
                    row['open_ports'] = json.loads(
                        row.get('open_ports', '[]') or '[]'
                    )
                except Exception:
                    row['open_ports'] = []
                result.append(row)
        return result

    @staticmethod
    def get_latest_for_target(target: str) -> Optional[dict]:
        """
        Fetch the most recent scan for a specific target.
        Returns: scan dict or None
        """
        rows = execute_query(
            """
            SELECT * FROM network_scans
            WHERE target = %s
            ORDER BY scan_time DESC
            LIMIT 1
            """,
            (safe_str(target),)
        )
        if not rows:
            return None
        row = BaseModel._format_row(rows[0])
        if row:
            try:
                import json
                row['open_ports'] = json.loads(
                    row.get('open_ports', '[]') or '[]'
                )
            except Exception:
                row['open_ports'] = []
        return row

    @staticmethod
    def get_unique_targets() -> list:
        """
        Get list of all unique scan targets.
        Returns: list of IP strings
        """
        rows = execute_query(
            """
            SELECT DISTINCT target,
                   MAX(scan_time) as last_scan
            FROM network_scans
            GROUP BY target
            ORDER BY last_scan DESC
            """
        )
        return [
            {
                "target":    r['target'],
                "last_scan": r['last_scan'].isoformat()
                             if isinstance(r['last_scan'], datetime.datetime)
                             else str(r['last_scan'])
            }
            for r in (rows or [])
        ]

    @staticmethod
    def delete_by_id(scan_id: int) -> bool:
        """Delete a scan record by ID."""
        try:
            execute_query(
                "DELETE FROM network_scans WHERE id = %s",
                (safe_int(scan_id),),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def purge_old(days: int = 14) -> int:
        """
        Delete scan records older than N days.
        Returns: number of rows deleted
        """
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM network_scans
                    WHERE scan_time < NOW() - INTERVAL '%s days'
                    """,
                    (safe_int(days, 14),)
                )
                count = cur.rowcount
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            print(f"[NetworkScanModel.purge_old] Error: {e}")
            return 0

    @staticmethod
    def count() -> int:
        """Return total number of scan records."""
        rows = execute_query("SELECT COUNT(*) as cnt FROM network_scans")
        return safe_int(rows[0]['cnt']) if rows else 0


# ════════════════════════════════════════════════════════════
# SECTION 6 — ALERT MODEL
# ════════════════════════════════════════════════════════════

class AlertModel(BaseModel):
    """
    Model for the 'alerts' table.

    Table Schema:
        id             SERIAL PRIMARY KEY
        alert_type     VARCHAR(100)
        message        TEXT
        severity       VARCHAR(50)
        acknowledged   BOOLEAN DEFAULT FALSE
        created_at     TIMESTAMP DEFAULT NOW()
    """

    TABLE_NAME = 'alerts'

    VALID_TYPES = {
        'CPU_HIGH', 'RAM_HIGH', 'DISK_HIGH',
        'PORT_SCAN', 'LOGIN_FAIL', 'LOGIN_SUCCESS',
        'ALERT_ACK', 'NETWORK_ANOMALY', 'SYSTEM_ERROR',
        'UNAUTHORIZED', 'SERVICE_DOWN', 'INTRUSION',
        'GENERAL', 'CUSTOM',
    }

    def __init__(
        self,
        id:           Optional[int]  = None,
        alert_type:   str            = 'GENERAL',
        message:      str            = '',
        severity:     str            = 'WARNING',
        acknowledged: bool           = False,
        created_at:   Optional[str]  = None,
    ):
        self.id           = id
        self.alert_type   = safe_str(alert_type, 'GENERAL').upper()
        self.message      = safe_str(message, '')
        self.severity     = normalize_severity(severity)
        self.acknowledged = bool(acknowledged)
        self.created_at   = created_at or self._now()

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "alert_type":   self.alert_type,
            "message":      self.message,
            "severity":     self.severity,
            "acknowledged": self.acknowledged,
            "created_at":   self.created_at,
            "time_ago":     format_time_ago(self.created_at),
        }

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    def create(
        alert_type: str = 'GENERAL',
        message:    str = '',
        severity:   str = 'WARNING',
    ) -> bool:
        """
        Create a new alert.
        Returns: True on success
        """
        try:
            execute_query(
                """
                INSERT INTO alerts (alert_type, message, severity)
                VALUES (%s, %s, %s)
                """,
                (
                    safe_str(alert_type, 'GENERAL').upper(),
                    safe_str(message, '')[:2000],
                    normalize_severity(severity),
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"[AlertModel.create] Error: {e}")
            return False

    @staticmethod
    def get_all(
        limit:          int  = 50,
        acknowledged:   bool = False,
    ) -> list:
        """
        Fetch all alerts.
        acknowledged=False → only active/unacknowledged alerts
        acknowledged=True  → all alerts including acknowledged
        Returns: list of alert dicts sorted by severity
        """
        if acknowledged:
            rows = execute_query(
                """
                SELECT * FROM alerts
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (safe_int(limit, 50),)
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM alerts
                WHERE acknowledged = FALSE
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (safe_int(limit, 50),)
            )
        formatted = BaseModel._format_rows(rows)
        return sort_by_severity(formatted)

    @staticmethod
    def get_by_id(alert_id: int) -> Optional[dict]:
        """Fetch a single alert by ID."""
        rows = execute_query(
            "SELECT * FROM alerts WHERE id = %s",
            (safe_int(alert_id),)
        )
        return BaseModel._format_row(rows[0]) if rows else None

    @staticmethod
    def get_active(limit: int = 20) -> list:
        """
        Fetch only unacknowledged (active) alerts.
        Returns: list sorted by severity (CRITICAL first)
        """
        rows = execute_query(
            """
            SELECT * FROM alerts
            WHERE acknowledged = FALSE
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (safe_int(limit, 20),)
        )
        formatted = BaseModel._format_rows(rows)
        return sort_by_severity(formatted)

    @staticmethod
    def get_by_severity(severity: str, limit: int = 50) -> list:
        """
        Fetch alerts filtered by severity.
        Returns: list of alert dicts
        """
        rows = execute_query(
            """
            SELECT * FROM alerts
            WHERE severity = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (normalize_severity(severity), safe_int(limit, 50))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def get_by_type(alert_type: str, limit: int = 50) -> list:
        """
        Fetch alerts filtered by type.
        Returns: list of alert dicts
        """
        rows = execute_query(
            """
            SELECT * FROM alerts
            WHERE alert_type = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (safe_str(alert_type).upper(), safe_int(limit, 50))
        )
        return BaseModel._format_rows(rows)

    @staticmethod
    def acknowledge(alert_id: int) -> bool:
        """
        Mark a specific alert as acknowledged.
        Returns: True on success
        """
        try:
            execute_query(
                """
                UPDATE alerts
                SET acknowledged = TRUE
                WHERE id = %s
                """,
                (safe_int(alert_id),),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"[AlertModel.acknowledge] Error: {e}")
            return False

    @staticmethod
    def acknowledge_all() -> int:
        """
        Acknowledge all active alerts.
        Returns: number of rows updated
        """
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE alerts
                    SET acknowledged = TRUE
                    WHERE acknowledged = FALSE
                    """
                )
                count = cur.rowcount
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            print(f"[AlertModel.acknowledge_all] Error: {e}")
            return 0

    @staticmethod
    def get_severity_counts() -> dict:
        """
        Get count of active alerts grouped by severity.
        Returns: dict {severity: count}
        """
        rows = execute_query(
            """
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE acknowledged = FALSE
            GROUP BY severity
            ORDER BY count DESC
            """
        )
        return {
            row['severity']: safe_int(row['count'])
            for row in (rows or [])
        }

    @staticmethod
    def delete_by_id(alert_id: int) -> bool:
        """Delete an alert by ID."""
        try:
            execute_query(
                "DELETE FROM alerts WHERE id = %s",
                (safe_int(alert_id),),
                fetch=False
            )
            return True
        except Exception:
            return False

    @staticmethod
    def purge_acknowledged(days: int = 7) -> int:
        """
        Delete acknowledged alerts older than N days.
        Returns: number of rows deleted
        """
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM alerts
                    WHERE acknowledged = TRUE
                    AND created_at < NOW() - INTERVAL '%s days'
                    """,
                    (safe_int(days, 7),)
                )
                count = cur.rowcount
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            print(f"[AlertModel.purge_acknowledged] Error: {e}")
            return 0

    @staticmethod
    def count_active() -> int:
        """Return count of unacknowledged alerts."""
        rows = execute_query(
            "SELECT COUNT(*) as cnt FROM alerts WHERE acknowledged = FALSE"
        )
        return safe_int(rows[0]['cnt']) if rows else 0

    @staticmethod
    def count() -> int:
        """Return total number of alert records."""
        rows = execute_query("SELECT COUNT(*) as cnt FROM alerts")
        return safe_int(rows[0]['cnt']) if rows else 0


# ════════════════════════════════════════════════════════════
# SECTION 7 — DASHBOARD SUMMARY MODEL (Aggregated View)
# ════════════════════════════════════════════════════════════

class DashboardModel:
    """
    Aggregated dashboard summary — combines all models.
    Used by: dashboard_routes.py → /api/dashboard
    """

    @staticmethod
    def get_summary() -> dict:
        """
        Get full dashboard summary from all models.
        Returns: dict with users, stats, logs, alerts summaries
        """
        return {
            "counts": {
                "users":        UserModel.count(),
                "system_stats": SystemStatModel.count(),
                "security_logs":SecurityLogModel.count(),
                "network_scans":NetworkScanModel.count(),
                "active_alerts":AlertModel.count_active(),
                "total_alerts": AlertModel.count(),
            },
            "latest_stats":   SystemStatModel.get_latest(limit=1),
            "averages_24h":   SystemStatModel.get_averages(hours=24),
            "peaks_24h":      SystemStatModel.get_peaks(hours=24),
            "recent_logs":    SecurityLogModel.get_recent(hours=1, limit=10),
            "active_alerts":  AlertModel.get_active(limit=10),
            "log_severity":   SecurityLogModel.get_severity_counts(),
            "alert_severity": AlertModel.get_severity_counts(),
            "scan_targets":   NetworkScanModel.get_unique_targets(),
            "generated_at":   timestamp_now(),
        }

    @staticmethod
    def get_health_status() -> dict:
        """
        Get overall system health status from stored stats.
        Returns: dict with status, color, message
        """
        latest = SystemStatModel.get_latest(limit=1)
        active_alerts = AlertModel.count_active()

        if not latest:
            return {
                "status":  "UNKNOWN",
                "color":   "#7a8ba0",
                "message": "No system data available yet.",
            }

        stat = latest[0]
        cpu  = safe_float(stat.get('cpu_percent',  0))
        ram  = safe_float(stat.get('ram_percent',  0))
        disk = safe_float(stat.get('disk_percent', 0))

        if cpu >= 90 or ram >= 90 or disk >= 95 or active_alerts >= 5:
            return {
                "status":  "CRITICAL",
                "color":   "#ff3366",
                "message": "System under critical load or has active alerts!",
                "cpu":     cpu,
                "ram":     ram,
                "disk":    disk,
                "alerts":  active_alerts,
            }
        if cpu >= 70 or ram >= 80 or disk >= 85 or active_alerts >= 2:
            return {
                "status":  "WARNING",
                "color":   "#ffcc00",
                "message": "System resources elevated. Monitor closely.",
                "cpu":     cpu,
                "ram":     ram,
                "disk":    disk,
                "alerts":  active_alerts,
            }
        return {
            "status":  "HEALTHY",
            "color":   "#00ff88",
            "message": "All systems operating normally.",
            "cpu":     cpu,
            "ram":     ram,
            "disk":    disk,
            "alerts":  active_alerts,
        }


# ════════════════════════════════════════════════════════════
# SECTION 8 — SELF-TEST (run directly to verify)
# python backend/models.py
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("  🦜 Parrot OS Dashboard — models.py Self-Test")
    print("=" * 60)

    # ── Test UserModel ───────────────────────────────────────
    print("\n[1] Testing UserModel...")

    result = UserModel.create('test_user', 'TestPass123', 'analyst')
    print(f"  Create user:   {result['message']}")

    user = UserModel.get_by_username('test_user')
    assert user is not None,          "❌ get_by_username failed"
    assert user['username'] == 'test_user', "❌ Username mismatch"
    print(f"  Get by name:   ✅ Found user id={user['id']}")

    auth = UserModel.authenticate('test_user', 'TestPass123')
    assert auth is not None,          "❌ Authenticate failed"
    assert 'password_hash' not in auth,"❌ password_hash exposed!"
    print(f"  Authenticate:  ✅ Role={auth['role']}")

    auth_fail = UserModel.authenticate('test_user', 'wrongpass')
    assert auth_fail is None,         "❌ Bad auth should return None"
    print(f"  Bad password:  ✅ Correctly rejected")

    count = UserModel.count()
    print(f"  User count:    {count}")

    # ── Test SystemStatModel ─────────────────────────────────
    print("\n[2] Testing SystemStatModel...")

    ok = SystemStatModel.record(
        cpu_percent=45.5,
        ram_percent=62.3,
        disk_percent=78.1,
    )
    assert ok,                         "❌ SystemStatModel.record failed"
    print(f"  Record stat:   ✅")

    history = SystemStatModel.get_history(limit=5)
    assert isinstance(history, list),  "❌ get_history not list"
    print(f"  Get history:   ✅ {len(history)} record(s)")

    avgs = SystemStatModel.get_averages(hours=24)
    assert 'avg_cpu' in avgs,          "❌ Missing avg_cpu"
    print(f"  Averages 24h:  ✅ CPU avg={avgs['avg_cpu']}%")

    # ── Test SecurityLogModel ────────────────────────────────
    print("\n[3] Testing SecurityLogModel...")

    ok = SecurityLogModel.add(
        log_type='TEST',
        message='Self-test log entry',
        severity='INFO',
        source_ip='127.0.0.1',
    )
    assert ok,                         "❌ SecurityLogModel.add failed"
    print(f"  Add log:       ✅")

    logs = SecurityLogModel.get_all(limit=5)
    assert isinstance(logs, list),     "❌ get_all not list"
    print(f"  Get logs:      ✅ {len(logs)} log(s)")

    counts = SecurityLogModel.get_severity_counts()
    print(f"  Severity count:✅ {counts}")

    # ── Test AlertModel ──────────────────────────────────────
    print("\n[4] Testing AlertModel...")

    ok = AlertModel.create(
        alert_type='TEST',
        message='Self-test alert',
        severity='WARNING',
    )
    assert ok,                         "❌ AlertModel.create failed"
    print(f"  Create alert:  ✅")

    active = AlertModel.get_active(limit=5)
    assert isinstance(active, list),   "❌ get_active not list"
    print(f"  Active alerts: ✅ {len(active)} alert(s)")

    if active:
        alert_id = active[0]['id']
        ack_ok   = AlertModel.acknowledge(alert_id)
        assert ack_ok,                 "❌ acknowledge failed"
        print(f"  Acknowledge:   ✅ Alert #{alert_id} acknowledged")

    # ── Test NetworkScanModel ────────────────────────────────
    print("\n[5] Testing NetworkScanModel...")

    ok = NetworkScanModel.save_scan(
        target='127.0.0.1',
        open_ports=[
            {"port": 22, "service": "ssh"},
            {"port": 5000, "service": "flask"},
        ],
        os_guess='Linux'
    )
    assert ok,                         "❌ save_scan failed"
    print(f"  Save scan:     ✅")

    scans = NetworkScanModel.get_by_target('127.0.0.1')
    assert isinstance(scans, list),    "❌ get_by_target not list"
    assert len(scans) > 0,             "❌ No scans returned"
    print(f"  Get by target: ✅ {len(scans)} scan(s)")

    # ── Test DashboardModel ──────��───────────────────────────
    print("\n[6] Testing DashboardModel...")

    health = DashboardModel.get_health_status()
    assert 'status' in health,         "❌ Missing health status"
    print(f"  Health status: ✅ {health['status']}")

    summary = DashboardModel.get_summary()
    assert 'counts' in summary,        "❌ Missing counts"
    print(f"  Summary:       ✅ Users={summary['counts']['users']}")

    print()
    print("=" * 60)
    print("  ✅ ALL MODEL TESTS PASSED!")
    print("=" * 60)
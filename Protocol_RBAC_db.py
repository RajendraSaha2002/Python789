"""
db.py — PROTOCOL RBAC
All SQL queries. Wraps psycopg2 with RealDictCursor for dict results.
Permission queries delegate to get_user_permissions() / has_permission()
PostgreSQL functions defined in schema.sql.
"""
import json
import psycopg2
import psycopg2.extras
import Protocol_RBAC_config


class Database:

    def __init__(self):
        self._conn = None
        self._connect()

    # ── Connection management ──────────────────────────────────────
    def _connect(self):
        self._conn = psycopg2.connect(**Protocol_RBAC_config.DB)
        self._conn.autocommit = True

    def _ping(self):
        """Reconnect if the connection was dropped."""
        try:
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            self._connect()

    # ── Low-level query helpers ────────────────────────────────────
    def execute(self, sql: str, params=None) -> None:
        self._ping()
        with self._conn.cursor() as cur:
            cur.execute(sql, params)

    def fetchone(self, sql: str, params=None) -> dict | None:
        self._ping()
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params=None) -> list[dict]:
        self._ping()
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    # ══════════════════════════════════════════════════════════════
    # USERS
    # ══════════════════════════════════════════════════════════════
    def get_user_by_username(self, username: str) -> dict | None:
        return self.fetchone(
            "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
            (username,),
        )

    def get_user_by_id(self, uid: int) -> dict | None:
        return self.fetchone(
            """SELECT id, username, email, full_name, is_active,
                      created_at, last_login
               FROM   users WHERE id = %s""",
            (uid,),
        )

    def get_all_users(self) -> list[dict]:
        return self.fetchall(
            """
            SELECT
                u.id, u.username, u.email, u.full_name,
                u.is_active, u.created_at, u.last_login,
                COALESCE(
                    array_agg(r.name ORDER BY r.name)
                    FILTER (WHERE r.name IS NOT NULL),
                    '{}'
                ) AS roles
            FROM   users u
            LEFT   JOIN user_roles ur ON u.id  = ur.user_id
            LEFT   JOIN roles      r  ON ur.role_id = r.id
            GROUP  BY u.id
            ORDER  BY u.created_at DESC
            """
        )

    def create_user(self, username: str, pw_hash: str,
                    email: str, full_name: str) -> int:
        row = self.fetchone(
            """
            INSERT INTO users (username, password_hash, email, full_name)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (username, pw_hash, email, full_name),
        )
        return row['id']

    def update_user(self, uid: int, email: str, full_name: str,
                    is_active: bool) -> None:
        self.execute(
            """UPDATE users
               SET email = %s, full_name = %s, is_active = %s
               WHERE id = %s""",
            (email, full_name, is_active, uid),
        )

    def delete_user(self, uid: int) -> None:
        # ON DELETE CASCADE handles sessions + user_roles
        self.execute("DELETE FROM users WHERE id = %s", (uid,))

    # ══════════════════════════════════════════════════════════════
    # PERMISSIONS  — delegate to PostgreSQL recursive CTE functions
    # ══════════════════════════════════════════════════════════════
    def get_user_permissions(self, uid: int) -> list[dict]:
        """
        Full detail — permission name, module, via_role, inheritance depth.
        Powered by the WITH RECURSIVE CTE in get_user_permissions().
        """
        return self.fetchall("SELECT * FROM get_user_permissions(%s)", (uid,))

    def get_permission_names(self, uid: int) -> list[str]:
        """Flat list of permission name strings for the JS permission Set."""
        rows = self.fetchall(
            "SELECT permission_name FROM get_user_permissions(%s)", (uid,)
        )
        return [r['permission_name'] for r in rows]

    def has_permission(self, uid: int, perm: str) -> bool:
        """Single boolean check — used server-side before every sensitive op."""
        row = self.fetchone(
            "SELECT has_permission(%s, %s) AS result", (uid, perm)
        )
        return bool(row['result']) if row else False

    # ══════════════════════════════════════════════════════════════
    # ROLES
    # ══════════════════════════════════════════════════════════════
    def get_all_roles(self) -> list[dict]:
        return self.fetchall(
            """
            SELECT
                r.id, r.name, r.description, r.parent_role_id,
                pr.name   AS parent_name,
                r.created_at,
                COUNT(rp.permission_id) AS permission_count
            FROM   roles r
            LEFT   JOIN roles            pr ON r.parent_role_id = pr.id
            LEFT   JOIN role_permissions rp ON r.id = rp.role_id
            GROUP  BY r.id, pr.name
            ORDER  BY r.id
            """
        )

    def get_user_roles(self, uid: int) -> list[dict]:
        return self.fetchall(
            """
            SELECT r.id, r.name, r.description
            FROM   roles r
            INNER  JOIN user_roles ur ON r.id = ur.role_id
            WHERE  ur.user_id = %s
            """,
            (uid,),
        )

    def assign_role(self, uid: int, role_id: int, granted_by: int) -> None:
        self.execute(
            """INSERT INTO user_roles (user_id, role_id, granted_by)
               VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
            (uid, role_id, granted_by),
        )

    def revoke_role(self, uid: int, role_id: int) -> None:
        self.execute(
            "DELETE FROM user_roles WHERE user_id = %s AND role_id = %s",
            (uid, role_id),
        )

    # ══════════════════════════════════════════════════════════════
    # AUDIT LOG
    # ══════════════════════════════════════════════════════════════
    def log(self, uid: int | None, action: str,
            resource: str = None, details: dict = None,
            ip: str = None) -> None:
        self.execute(
            """
            INSERT INTO audit_log (user_id, action, resource, details, ip_address)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (uid, action, resource,
             json.dumps(details) if details else None,
             ip),
        )

    def get_audit_log(self, limit: int = 200) -> list[dict]:
        rows = self.fetchall(
            """
            SELECT al.id, al.action, al.resource, al.details,
                   al.ip_address, al.created_at,
                   u.username
            FROM   audit_log al
            LEFT   JOIN users u ON al.user_id = u.id
            ORDER  BY al.created_at DESC
            LIMIT  %s
            """,
            (limit,),
        )
        # Serialise datetimes for JSON
        for r in rows:
            if r.get('created_at'):
                r['created_at'] = r['created_at'].isoformat()
        return rows
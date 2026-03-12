#!/usr/bin/env python3
"""
setup.py — PROTOCOL RBAC
Run ONCE to:
  1. Create the database (if it doesn't exist)
  2. Apply schema.sql  (tables, functions, role/permission seeds)
  3. Hash & insert demo user accounts

Usage:
  cd backend/
  python setup.py
"""
import os
import sys
import psycopg2
import psycopg2.extensions

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from Protocol_RBAC_session import PasswordManager

_pm = PasswordManager()

# ── Demo users: (username, password, email, full_name, role_name)
DEMO_USERS = [
    ('alice',   'password123', 'alice@protocol.dev',   'Alice Chen',     'super_admin'),
    ('bob',     'password123', 'bob@protocol.dev',     'Bob Sharma',     'admin'),
    ('charlie', 'password123', 'charlie@protocol.dev', 'Charlie Nguyen', 'manager'),
    ('diana',   'password123', 'diana@protocol.dev',   'Diana Patel',    'analyst'),
    ('eve',     'password123', 'eve@protocol.dev',     'Eve Martinez',   'viewer'),
]


def _step(msg: str) -> None:
    print(f'  → {msg}')

def _ok(msg: str) -> None:
    print(f'  ✓ {msg}')

def _skip(msg: str) -> None:
    print(f'  ⊘ {msg}  (already exists)')


# ══════════════════════════════════════════════════════════════════
# STEP 1: Create database if missing
# ══════════════════════════════════════════════════════════════════
def ensure_database() -> None:
    _step(f"Checking database '{config.DB['dbname']}'…")
    # Connect to the default 'postgres' db to run CREATE DATABASE
    admin_cfg = {**config.DB, 'dbname': 'postgres'}
    conn = psycopg2.connect(**admin_cfg)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.DB['dbname'],)
        )
        if cur.fetchone():
            _skip(f"Database '{config.DB['dbname']}'")
        else:
            cur.execute(f"CREATE DATABASE {config.DB['dbname']}")
            _ok(f"Created database '{config.DB['dbname']}'")
    conn.close()


# ══════════════════════════════════════════════════════════════════
# STEP 2: Apply schema.sql
# ══════════════════════════════════════════════════════════════════
def apply_schema() -> None:
    _step(f"Applying schema from '{config.SCHEMA_FILE}'…")
    if not os.path.isfile(config.SCHEMA_FILE):
        print(f"\n  ERROR: Schema file not found: {config.SCHEMA_FILE}")
        sys.exit(1)

    with open(config.SCHEMA_FILE, encoding='utf-8') as f:
        sql = f.read()

    conn = psycopg2.connect(**config.DB)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    _ok('Schema applied (tables, functions, role seeds, permission seeds)')


# ══════════════════════════════════════════════════════════════════
# STEP 3: Seed demo users with properly hashed passwords
# ══════════════════════════════════════════════════════════════════
def seed_users() -> None:
    _step('Seeding demo users…')
    conn = psycopg2.connect(**config.DB)
    conn.autocommit = True

    with conn.cursor() as cur:
        for username, password, email, full_name, role_name in DEMO_USERS:
            # Skip if already exists
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                _skip(f"User '{username}'")
                continue

            pw_hash = _pm.hash_password(password)    # pbkdf2_hmac SHA-256

            cur.execute(
                """INSERT INTO users (username, password_hash, email, full_name)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (username, pw_hash, email, full_name),
            )
            uid = cur.fetchone()[0]

            # Assign role (role seeds already exist from schema.sql)
            cur.execute(
                """INSERT INTO user_roles (user_id, role_id)
                   SELECT %s, r.id FROM roles r WHERE r.name = %s
                   ON CONFLICT DO NOTHING""",
                (uid, role_name),
            )
            _ok(f"User '{username}' (role: {role_name})")

    conn.close()


# ══════════════════════════════════════════════════════════════════
# STEP 4: Verify recursive CTE works
# ══════════════════════════════════════════════════════════════════
def verify() -> None:
    _step('Verifying recursive CTE permission resolution…')
    conn = psycopg2.connect(**config.DB)
    conn.autocommit = True

    with conn.cursor() as cur:
        # super_admin (alice) should see ALL 19 permissions
        cur.execute(
            "SELECT array_agg(permission_name ORDER BY permission_name) "
            "FROM get_user_permissions("
            "  (SELECT id FROM users WHERE username='alice')"
            ")"
        )
        alice_perms = cur.fetchone()[0] or []

        # viewer (eve) should see only dashboard_view + system_monitor
        cur.execute(
            "SELECT array_agg(permission_name ORDER BY permission_name) "
            "FROM get_user_permissions("
            "  (SELECT id FROM users WHERE username='eve')"
            ")"
        )
        eve_perms = cur.fetchone()[0] or []

    conn.close()

    _ok(f"alice (super_admin) → {len(alice_perms)} permissions")
    _ok(f"eve   (viewer)      → {len(eve_perms)} permissions: {eve_perms}")

    if len(alice_perms) == 19 and len(eve_perms) == 2:
        _ok('Recursive CTE verified ✔')
    else:
        print('\n  WARNING: Permission counts unexpected — check schema.sql seeds.')


# ══════════════════════════════════════════════════════════════════
def main() -> None:
    print('\n  ╔══════════════════════════════════════════╗')
    print('  ║  PROTOCOL RBAC — Database Setup          ║')
    print('  ╚══════════════════════════════════════════╝\n')

    ensure_database()
    apply_schema()
    seed_users()
    verify()

    print('\n  ════════════════════════════════════════════')
    print('  Setup complete. Start the server:')
    print('    python server.py\n')
    print('  Demo accounts (all passwords: password123)')
    print('  ────────────────────────────────────────────')
    for u, pw, _, name, role in DEMO_USERS:
        print(f'  {u:<10} → {role}')
    print('  ════════════════════════════════════════════\n')


if __name__ == '__main__':
    main()
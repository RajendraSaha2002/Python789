"""
config.py — PROTOCOL RBAC
Central configuration. Edit DB credentials before running setup.py.
"""
import os

# ── PostgreSQL ────────────────────────────────────────────────────
DB = {
    'host'    : os.environ.get('PG_HOST',     'localhost'),
    'port'    : int(os.environ.get('PG_PORT', 5432)),
    'dbname'  : os.environ.get('PG_DB',       'protocol_rbac'),
    'user'    : os.environ.get('PG_USER',     'postgres'),
    'password': os.environ.get('PG_PASS',     'varrie75'),
}

# ── HTTP Server ───────────────────────────────────────────────────
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000

# ── Session ───────────────────────────────────────────────────────
SESSION_LIFETIME_HOURS = 8       # token expires after 8 hours
TOKEN_BYTES            = 32      # secrets.token_hex(32) → 64-char hex

# ── Paths (relative to backend/ directory) ────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(_BASE, '..', 'frontend')
SCHEMA_FILE  = os.path.join(_BASE, '..', 'sql', 'schema.sql')

# ── Password hashing ──────────────────────────────────────────────
PBKDF2_ITERATIONS = 100_000
PBKDF2_DIGEST     = 'sha256'
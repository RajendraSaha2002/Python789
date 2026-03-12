# ============================================================
# auth_service.py — Authentication Logic (no external lib)
# ============================================================

import hashlib
import secrets
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.Parrot_database import execute_query

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username: str, password: str) -> dict | None:
    """Verify credentials against DB."""
    hashed = hash_password(password)
    rows = execute_query(
        "SELECT id, username, role FROM users WHERE username=%s AND password_hash=%s",
        (username, hashed)
    )
    if rows:
        execute_query(
            "UPDATE users SET last_login=NOW() WHERE username=%s",
            (username,), fetch=False
        )
        return rows[0]
    return None

def create_user(username: str, password: str, role: str = "analyst") -> bool:
    """Create a new user."""
    hashed = hash_password(password)
    try:
        execute_query(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, hashed, role), fetch=False
        )
        return True
    except Exception:
        return False

def generate_session_token() -> str:
    return secrets.token_hex(32)
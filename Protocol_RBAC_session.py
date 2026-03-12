"""
session.py — PROTOCOL RBAC
SessionManager  : creates / validates / destroys DB-backed tokens.
PasswordManager : PBKDF2-HMAC password hashing (stdlib only).
"""
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import Protocol_RBAC_config


# ══════════════════════════════════════════════════════════════════
# PASSWORD MANAGER
# Stores passwords as:  <16-byte-salt-hex>:<pbkdf2-key-hex>
# Uses hmac.compare_digest for constant-time comparison (no timing attack).
# ══════════════════════════════════════════════════════════════════
class PasswordManager:

    @staticmethod
    def hash_password(plain: str) -> str:
        """Return a storable hash string for a plaintext password."""
        salt = os.urandom(16)                       # 16 random bytes
        key  = hashlib.pbkdf2_hmac(
            Protocol_RBAC_config.PBKDF2_DIGEST,
            plain.encode('utf-8'),
            salt,
            Protocol_RBAC_config.PBKDF2_ITERATIONS,
        )
        return salt.hex() + ':' + key.hex()         # "aabbcc…:ddeeff…"

    @staticmethod
    def verify_password(plain: str, stored: str) -> bool:
        """Verify plaintext against a stored hash string."""
        try:
            salt_hex, key_hex = stored.split(':', 1)
            salt     = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(key_hex)
            actual   = hashlib.pbkdf2_hmac(
                Protocol_RBAC_config.PBKDF2_DIGEST,
                plain.encode('utf-8'),
                salt,
                Protocol_RBAC_config.PBKDF2_ITERATIONS,
            )
            # Constant-time compare — prevents timing side-channel
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════
# SESSION MANAGER
# Each session is a row in the `sessions` table:
#   token      → secrets.token_hex(32)  (64-char hex string)
#   expires_at → NOW() + SESSION_LIFETIME_HOURS
#   is_active  → set to FALSE on logout / expiry cleanup
# ══════════════════════════════════════════════════════════════════
class SessionManager:

    def __init__(self, db):
        self._db = db

    # ── Create ────────────────────────────────────────────────────
    def create(self, user_id: int, ip: str = None, user_agent: str = None) -> str:
        """
        Generate a new token, persist it, update last_login, return token.
        """
        token      = secrets.token_hex(Protocol_RBAC_config.TOKEN_BYTES)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=Protocol_RBAC_config.SESSION_LIFETIME_HOURS)

        self._db.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, token, expires_at, ip, user_agent),
        )
        self._db.execute(
            "UPDATE users SET last_login = NOW() WHERE id = %s",
            (user_id,),
        )
        return token

    # ── Validate ──────────────────────────────────────────────────
    def validate(self, token: str) -> int | None:
        """
        Return user_id if the token exists, is active, and not expired.
        Returns None otherwise.
        """
        if not token or len(token) != Protocol_RBAC_config.TOKEN_BYTES * 2:
            return None
        row = self._db.fetchone(
            """
            SELECT s.user_id
            FROM   sessions s
            JOIN   users    u ON u.id = s.user_id
            WHERE  s.token      = %s
              AND  s.is_active  = TRUE
              AND  s.expires_at > NOW()
              AND  u.is_active  = TRUE
            """,
            (token,),
        )
        return row['user_id'] if row else None

    # ── Destroy (logout) ──────────────────────────────────────────
    def destroy(self, token: str) -> None:
        self._db.execute(
            "UPDATE sessions SET is_active = FALSE WHERE token = %s",
            (token,),
        )

    # ── Destroy all sessions for a user (force-logout) ────────────
    def destroy_all(self, user_id: int) -> int:
        """Returns number of sessions terminated."""
        self._db.execute(
            "UPDATE sessions SET is_active = FALSE WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
        )

    # ── Housekeeping ──────────────────────────────────────────────
    def cleanup_expired(self) -> None:
        """Mark all past-expiry sessions as inactive. Call on server start."""
        self._db.execute(
            "UPDATE sessions SET is_active = FALSE WHERE expires_at < NOW() AND is_active = TRUE"
        )

    # ── Active session list (admin use) ───────────────────────────
    def list_active(self) -> list:
        return self._db.fetchall(
            """
            SELECT s.id, s.user_id, u.username, s.created_at, s.expires_at,
                   s.ip_address, LEFT(s.token, 8) || '…' AS token_preview
            FROM   sessions s
            JOIN   users    u ON u.id = s.user_id
            WHERE  s.is_active = TRUE AND s.expires_at > NOW()
            ORDER  BY s.created_at DESC
            """
        )
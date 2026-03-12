#!/usr/bin/env python3
"""
server.py — PROTOCOL RBAC
Pure-stdlib HTTP server (http.server) + psycopg2.
Serves both the REST API (/api/*) and static frontend files.

Run:   python server.py
Visit: http://127.0.0.1:8000/
"""
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# ── resolve sibling modules ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from Protocol_RBAC_db      import Database
from Protocol_RBAC_session import PasswordManager, SessionManager

# ── module-level singletons ────────────────────────────────────────
_db = Database()
_sm = SessionManager(_db)
_pm = PasswordManager()


# ══════════════════════════════════════════════════════════════════
class ProtocolHandler(BaseHTTPRequestHandler):

    # ── silence default request log (use custom format) ───────────
    def log_message(self, fmt, *args):
        print(f"  {self.command:6s} {self.path}  [{args[1]}]")

    # ────────────────── helpers ────────────────────────────────────

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header('Content-Type',   'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control',  'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg: str, status: int = 400) -> None:
        self._json({'success': False, 'error': msg}, status)

    def _token(self) -> str | None:
        t = self.headers.get('X-Auth-Token', '').strip()
        if not t:
            t = self.headers.get('Authorization', '').replace('Bearer ', '').strip()
        return t or None

    def _uid(self) -> int | None:
        return _sm.validate(self._token())

    def _require_auth(self) -> int | None:
        uid = self._uid()
        if not uid:
            self._err('Unauthorised — invalid or expired token', 401)
        return uid

    def _require_perm(self, perm: str) -> int | None:
        uid = self._require_auth()
        if not uid:
            return None
        if not _db.has_permission(uid, perm):
            _db.log(uid, 'PERMISSION_DENIED', perm, {'required': perm}, self.client_address[0])
            self._err(f'Forbidden — missing permission: {perm}', 403)
            return None
        return uid

    def _body(self) -> dict:
        n = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def _static(self, rel_path: str) -> None:
        """Serve a file from FRONTEND_DIR safely."""
        base = os.path.realpath(config.FRONTEND_DIR)
        full = os.path.realpath(os.path.join(base, rel_path.lstrip('/')))
        if not full.startswith(base):            # path-traversal guard
            self.send_error(403); return
        if not os.path.isfile(full):
            self.send_error(404); return
        mime, _ = mimetypes.guess_type(full)
        with open(full, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type',   mime or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ────────────────── routing ────────────────────────────────────

    def do_GET(self):
        p  = urlparse(self.path)
        qs = parse_qs(p.query)
        path = p.path

        if path in ('/', '/index.html'):
            return self._static('index.html')
        if path in ('/dashboard', '/dashboard.html'):
            return self._static('dashboard.html')
        if path.startswith('/api/'):
            return self._api_get(path, qs)
        self._static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith('/api/'):
            return self._api_post(path)
        self._err('Not found', 404)

    # ────────────────── API GET ────────────────────────────────────

    def _api_get(self, path: str, qs: dict) -> None:
        routes = {
            '/api/me'          : self._me,
            '/api/permissions' : self._permissions,
            '/api/check'       : lambda: self._check(qs),
            '/api/users'       : self._get_users,
            '/api/roles'       : self._get_roles,
            '/api/audit'       : self._get_audit,
            '/api/sessions'    : self._get_sessions,
        }
        fn = routes.get(path)
        if fn:
            fn()
        else:
            self._err('Unknown API endpoint', 404)

    # ────────────────── API POST ───────────────────────────────────

    def _api_post(self, path: str) -> None:
        routes = {
            '/api/login'       : self._login,
            '/api/logout'      : self._logout,
            '/api/users'       : self._create_user,
        }
        fn = routes.get(path)
        if fn:
            fn()
        else:
            self._err('Unknown API endpoint', 404)

    # ══════════════════════════════════════════════════════════════
    # ENDPOINT IMPLEMENTATIONS
    # ══════════════════════════════════════════════════════════════

    # POST /api/login ─────────────────────────────────────────────
    def _login(self) -> None:
        b        = self._body()
        username = (b.get('username') or '').strip()
        password = b.get('password') or ''

        if not username or not password:
            return self._err('Username and password are required')

        user = _db.get_user_by_username(username)

        # Always run verify_password (even on miss) to prevent user enumeration
        stored = user['password_hash'] if user else 'x:x'
        ok     = _pm.verify_password(password, stored) and user is not None

        if not ok:
            _db.log(None, 'LOGIN_FAIL', 'auth',
                    {'username': username}, self.client_address[0])
            return self._err('Invalid username or password', 401)

        token = _sm.create(user['id'], self.client_address[0],
                           self.headers.get('User-Agent', ''))
        _db.log(user['id'], 'LOGIN_SUCCESS', 'auth', None, self.client_address[0])

        self._json({
            'success': True,
            'token'  : token,
            'user'   : {
                'id'       : user['id'],
                'username' : user['username'],
                'full_name': user['full_name'],
                'email'    : user['email'],
            },
        })

    # POST /api/logout ────────────────────────────────────────────
    def _logout(self) -> None:
        token = self._token()
        if token:
            uid = _sm.validate(token)
            _sm.destroy(token)
            if uid:
                _db.log(uid, 'LOGOUT', 'auth', None, self.client_address[0])
        self._json({'success': True})

    # GET /api/me ─────────────────────────────────────────────────
    def _me(self) -> None:
        uid = self._require_auth()
        if not uid: return
        user  = _db.get_user_by_id(uid)
        roles = _db.get_user_roles(uid)
        self._json({'user': user, 'roles': roles})

    # GET /api/permissions ────────────────────────────────────────
    def _permissions(self) -> None:
        uid = self._require_auth()
        if not uid: return
        self._json({
            'permissions': _db.get_permission_names(uid),   # flat list → JS Set
            'detailed'   : _db.get_user_permissions(uid),   # with via_role, depth
        })

    # GET /api/check?permission=xxx ───────────────────────────────
    def _check(self, qs: dict) -> None:
        uid  = self._require_auth()
        if not uid: return
        perm = (qs.get('permission') or [None])[0]
        if not perm:
            return self._err('permission query param required')
        granted = _db.has_permission(uid, perm)
        self._json({'permission': perm, 'granted': granted})

    # GET /api/users  (requires users_view) ───────────────────────
    def _get_users(self) -> None:
        uid = self._require_perm('users_view')
        if not uid: return
        rows = _db.get_all_users()
        # Convert arrays + datetimes
        for r in rows:
            if r.get('created_at'): r['created_at'] = r['created_at'].isoformat()
            if r.get('last_login'): r['last_login']  = r['last_login'].isoformat()
        self._json({'users': rows})

    # POST /api/users  (requires users_create) ────────────────────
    def _create_user(self) -> None:
        uid = self._require_perm('users_create')
        if not uid: return
        b = self._body()
        for f in ('username', 'password', 'email', 'full_name'):
            if not b.get(f):
                return self._err(f'{f} is required')
        try:
            pw_hash = _pm.hash_password(b['password'])
            new_id  = _db.create_user(b['username'], pw_hash, b['email'], b['full_name'])
            _db.log(uid, 'USER_CREATE', 'users',
                    {'new_user': b['username']}, self.client_address[0])
            self._json({'success': True, 'user_id': new_id}, 201)
        except Exception as exc:
            self._err(str(exc))

    # GET /api/roles  (requires roles_view) ───────────────────────
    def _get_roles(self) -> None:
        uid = self._require_perm('roles_view')
        if not uid: return
        rows = _db.get_all_roles()
        for r in rows:
            if r.get('created_at'): r['created_at'] = r['created_at'].isoformat()
        self._json({'roles': rows})

    # GET /api/audit  (requires audit_view) ───────────────────────
    def _get_audit(self) -> None:
        uid = self._require_perm('audit_view')
        if not uid: return
        self._json({'audit': _db.get_audit_log(300)})

    # GET /api/sessions  (requires system_admin) ──────────────────
    def _get_sessions(self) -> None:
        uid = self._require_perm('system_admin')
        if not uid: return
        rows = _db.fetchall(
            """SELECT s.id, u.username, s.ip_address,
                      s.created_at, s.expires_at,
                      LEFT(s.token,8)||'…' AS token_preview
               FROM sessions s JOIN users u ON u.id=s.user_id
               WHERE s.is_active=TRUE AND s.expires_at > NOW()
               ORDER BY s.created_at DESC"""
        )
        for r in rows:
            if r.get('created_at'): r['created_at'] = r['created_at'].isoformat()
            if r.get('expires_at'): r['expires_at']  = r['expires_at'].isoformat()
        self._json({'sessions': rows})


# ══════════════════════════════════════════════════════════════════
def main():
    _sm.cleanup_expired()
    addr = (config.SERVER_HOST, config.SERVER_PORT)
    srv  = HTTPServer(addr, ProtocolHandler)
    url  = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"
    print(f"\n  ██████╗ ██████╗  ██████╗ ████████╗ ██████╗  ██████╗ ██████╗  ██╗")
    print(f"  ██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔═══██╗██╔════╝██╔═══██╗██║")
    print(f"  ██████╔╝██████╔╝██║   ██║   ██║   ██║   ██║██║     ██║   ██║██║")
    print(f"  ██╔═══╝ ██╔══██╗██║   ██║   ██║   ██║   ██║██║     ██║   ██║██║")
    print(f"  ██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝╚██████╗╚██████╔╝███████╗")
    print(f"  ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝\n")
    print(f"  RBAC System running → {url}/")
    print(f"  Frontend directory  → {config.FRONTEND_DIR}")
    print(f"  PostgreSQL          → {config.DB['host']}:{config.DB['port']}/{config.DB['dbname']}")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n  Server stopped.')

if __name__ == '__main__':
    main()
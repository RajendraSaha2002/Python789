
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import uuid
import datetime
import psycopg2  # Used for Postgres connection

# Database connection details (replace with your local postgres creds)
DB_CONFIG = {
    "dbname": "protocol_db",  # The database where you ran schema.sql
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


class ProtocolSessionManager(BaseHTTPRequestHandler):

    # Allow CORS so the frontend can communicate if hosted on a different port
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_POST(self):
        """ Handles the Login process and creates a Session Token """
        if self.path == '/api/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            credentials = json.loads(post_data.decode('utf-8'))

            username = credentials.get('username')
            password = credentials.get('password')  # In production, verify hash!

            conn = get_db_connection()
            cur = conn.cursor()

            # Find User
            cur.execute("SELECT id FROM users WHERE username = %s AND password_hash = %s", (username, password))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                token = str(uuid.uuid4())  # Generate unique Token
                expires = datetime.datetime.now() + datetime.timedelta(hours=2)  # 2-hour session limit

                # Store Session in Postgres
                cur.execute(
                    "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                    (token, user_id, expires)
                )
                conn.commit()

                response = {"success": True, "token": token}
                self._set_headers(200)
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self._set_headers(401)
                self.wfile.write(json.dumps({"success": False, "error": "Invalid credentials"}).encode('utf-8'))

            cur.close()
            conn.close()
        else:
            self._set_headers(404)
            self.wfile.write(b'{"error": "Not Found"}')

    def do_GET(self):
        """ Handles checking permissions before routing the user on the frontend """
        if self.path == '/api/permissions':
            auth_header = self.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                self._set_headers(401)
                self.wfile.write(b'{"error": "Missing or invalid token"}')
                return

            token = auth_header.split(' ')[1]

            conn = get_db_connection()
            cur = conn.cursor()

            # Validate Session Token
            cur.execute("SELECT user_id FROM sessions WHERE token = %s AND expires_at > NOW()", (token,))
            session = cur.fetchone()

            if not session:
                self._set_headers(401)
                self.wfile.write(b'{"error": "Session expired or invalid"}')
                cur.close()
                conn.close()
                return

            user_id = session[0]

            # RECURSIVE CTE: Find all permissions, inherited and direct.
            cte_query = """
                        WITH RECURSIVE RoleHierarchy AS (SELECT r.id, r.parent_role_id \
                                                         FROM roles r \
                                                                  JOIN user_roles ur ON r.id = ur.role_id \
                                                         WHERE ur.user_id = %s \

                                                         UNION ALL \

                                                         SELECT r.id, r.parent_role_id \
                                                         FROM roles r \
                                                                  JOIN RoleHierarchy rh ON rh.parent_role_id = r.id)
                        SELECT DISTINCT p.name
                        FROM RoleHierarchy rh
                                 JOIN role_permissions rp ON rh.id = rp.role_id
                                 JOIN permissions p ON rp.permission_id = p.id; \
                        """

            cur.execute(cte_query, (user_id,))
            permissions = [row[0] for row in cur.fetchall()]

            cur.close()
            conn.close()

            self._set_headers(200)
            self.wfile.write(json.dumps({"permissions": permissions}).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(b'{"error": "Not Found"}')


def run(server_class=HTTPServer, handler_class=ProtocolSessionManager, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Protocol Backend running silently on port {port}...")
    httpd.serve_forever()


if __name__ == '__main__':
    run()
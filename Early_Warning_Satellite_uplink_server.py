from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import Early_Warning_Satellite_crypto_engine
import Early_Warning_Satellite_orbit_sim
import psycopg2

DB_CONFIG = {'dbname': 'postgres', 'user': 'postgres', 'password': 'password', 'host': 'localhost', 'port': 5432}


class SatelliteUplink(BaseHTTPRequestHandler):

    def log_telemetry_to_db(self, sat_data, packet):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                        INSERT INTO telemetry_logs (satellite_id, encrypted_payload, hash_signature, origin_sector)
                        VALUES (%s, %s, %s, %s)
                        """, (sat_data['id'], packet['payload'], packet['signature'], 'ORBIT'))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB WRITE ERROR: {e}")

    def do_POST(self):
        # MFA Login Simulation
        if self.path == '/api/auth':
            length = int(self.headers['Content-Length'])
            creds = json.loads(self.rfile.read(length))

            # Simple simulation: Code must be "DEFCON1"
            if creds['code'] == "DEFCON1":
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'token': 'SECURE-TOKEN-X99', 'clearance': 1}).encode())
            else:
                self.send_response(401)
                self.end_headers()

    def do_GET(self):
        # Secure Data Feed
        if self.path == '/api/uplink':
            # 1. Get Physical Position
            sat_pos = Early_Warning_Satellite_orbit_sim.get_satellite_position()

            # 2. Get Sensor Data
            telemetry = Early_Warning_Satellite_orbit_sim.generate_telemetry()

            # 3. Encrypt and Sign Data
            # Using 'ALPHA-ZULU-99' as the simulated ground station key
            packet = crypto_engine.SecureLink.encrypt_payload(telemetry, 'ALPHA-ZULU-99')

            response = {
                'orbit': sat_pos,
                'packet': packet  # Can be None if packet loss occurred
            }

            if packet:
                self.log_telemetry_to_db(sat_pos, packet)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        # Serve Static Files
        try:
            if self.path == '/': self.path = '/login.html'

            ctype = 'text/plain'
            if self.path.endswith('.html'):
                ctype = 'text/html'
            elif self.path.endswith('.css'):
                ctype = 'text/css'
            elif self.path.endswith('.js'):
                ctype = 'application/javascript'

            f = open(os.getcwd() + self.path, 'rb')
            self.send_response(200)
            self.send_header('Content-type', ctype)
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    print("SECURE SATELLITE UPLINK ESTABLISHED ON PORT 9000...")
    HTTPServer(('localhost', 9000), SatelliteUplink).serve_forever()
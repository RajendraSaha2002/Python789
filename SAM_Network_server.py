import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import SAM_Network_db_manager
import SAM_Network_fire_control
import SAM_Network_radar_sim


class SAMServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/sector_data':
            # 1. Get real inventory from Postgres
            batteries = SAM_Network_db_manager.get_network_status()

            # 2. Update fake radar blips
            threats = SAM_Network_radar_sim.update_radar_picture()

            # 3. Run Auto-Engagement Logic
            engagements = []
            for t in threats:
                if t['status'] == 'INBOUND':
                    # Ask the Math Engine for a solution
                    shooter = SAM_Network_fire_control.calculate_intercept_solution(batteries, t)

                    if shooter:
                        # FIRE!
                        t['status'] = 'DESTROYED'
                        SAM_Network_db_manager.decrement_ammo(shooter['id'])
                        note = f"Splash Tgt at {shooter['intercept_time']}s interval"
                        SAM_Network_db_manager.log_engagement(shooter['id'], t['id'], note)

                        engagements.append({
                            'from': {'x': shooter['pos_x'], 'y': shooter['pos_y']},
                            'to': {'x': t['x'], 'y': t['y']},
                            'shooter': shooter['callsign']
                        })

            response = {
                'batteries': batteries,
                'threats': threats,
                'engagements': engagements
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, default=str).encode())
            return

        # Serve Static Files
        try:
            if self.path == '/': self.path = '/index.html'

            # Simple mime type handling
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
    print("SAM Network Node Online on port 8080...")
    HTTPServer(('localhost', 8080), SAMServer).serve_forever()
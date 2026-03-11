import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from SELinux_database import get_system_status, get_recent_logs
from SELinux_simulator import start_simulation


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        # API Routes
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_system_status()).encode())
            return

        elif self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_recent_logs()).encode())
            return

        # Static File Routing
        if self.path == '/':
            self.path = '/index.html'

        try:
            # Handle mime types so CSS and JS load properly
            mime_types = {
                '.html': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript'
            }
            ext = os.path.splitext(self.path)[1]
            content_type = mime_types.get(ext, 'text/plain')

            # Read file from disk
            file_path = os.getcwd() + self.path
            with open(file_path, 'rb') as file:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File Not Found')


if __name__ == '__main__':
    print("Starting SELinux Kernel Simulation...")
    start_simulation()

    port = 8000
    server = HTTPServer(('localhost', port), RequestHandler)
    print(f"Server running securely on http://localhost:{port}")
    server.serve_forever()
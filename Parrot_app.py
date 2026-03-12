# ============================================================
# app.py — Flask Application Entry Point
# RUN: python app.py  (after db_init.py)
# ============================================================

from flask import Flask, send_from_directory
from flask_cors import CORS
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Parrot_config import Config
from backend.routes.Parrot_auth_routes import auth_bp
from backend.routes.Parrot_system_routes import system_bp
from backend.routes.Parrot_network_routes import network_bp
from backend.routes.Parrot_logs_routes import logs_bp
from backend.routes.Parrot_dashboard_routes import dashboard_bp

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'),
    static_url_path='/static'
)
app.secret_key = Config.SECRET_KEY
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(system_bp)
app.register_blueprint(network_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(dashboard_bp)

# Serve frontend
@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path='index.html'):
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    if path != '' and os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)
    return send_from_directory(frontend_dir, 'index.html')

if __name__ == '__main__':
    print("=" * 60)
    print("  🦜 Parrot Security OS Dashboard — Starting Server")
    print(f"  🌐 URL: http://localhost:{Config.PORT}")
    print("=" * 60)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
from flask import Flask, jsonify, send_from_directory
from BlackArch_config import get_db_connection
import os

# Point Flask to where your WebStorm frontend files will live
app = Flask(__name__, static_folder='0')


@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'BlackArch_index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# Local data route (No external APIs used)
@app.route('/get_alerts')
def get_alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, ip_address, alert_type, severity FROM security_alerts ORDER BY id DESC LIMIT 10;")
    rows = cur.fetchall()

    # Format the data for the frontend
    alerts = [{"time": row[0], "ip": row[1], "type": row[2], "severity": row[3]} for row in rows]

    cur.close()
    conn.close()
    return jsonify(alerts)


if __name__ == '__main__':
    print("[*] Starting BlackArch Dashboard Server on port 5000...")
    app.run(port=5000, debug=True)
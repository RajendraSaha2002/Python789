from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)

# Simulated Database/System State
def get_operational_data():
    return {
        "radar": {
            "range": "12 NM",
            "contacts": random.randint(1, 5),
            "bearing": f"{random.randint(0, 359)}°"
        },
        "ship_status": {
            "engine_1": f"{random.randint(80, 95)}%",
            "engine_2": f"{random.randint(80, 95)}%",
            "fuel": f"{random.randint(40, 70)}%",
            "status": "All Systems Normal"
        },
        "navigation": {
            "coords": "19°45.23'N, 72°58.17'E",
            "speed": f"{random.randint(12, 20)} kts",
            "eta": "14:30"
        },
        "threat": {
            "level": "LOW",
            "friendly": 2,
            "unknown": 1
        }
    }

@app.route('/')
def index():
    return render_template('Air_Command_index.html')

@app.route('/api/status')
def status():
    # Sending data to frontend without external APIs
    return jsonify(get_operational_data())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
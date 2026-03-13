"""
╔══════════════════════════════════════════════════════════════╗
║   Air Defense Threat Intelligence Monitoring System          ║
║   main.py — Lightweight Fast Server                         ║
║   NO flask-cors dependency — Pure Flask only                ║
╚══════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify, request, make_response
from backend.Air_Defence_threat_database import ThreatDatabase
from backend.Air_Defence_behavior_analysis import BehaviorAnalyzer
from backend.Air_Defence_alert_manager import AlertManager
from backend.Air_Defence_intelligence_report import (IntelligenceReport)
import threading
import time

app = Flask(__name__)
app.config["JSON_SORT_KEYS"]              = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.config["PROPAGATE_EXCEPTIONS"]        = False

# ── Modules ──────────────────────────────────────────────────
db        = ThreatDatabase()
analyzer  = BehaviorAnalyzer(db)
alert_mgr = AlertManager(db)
reporter  = IntelligenceReport(db)

# ── Simple Cache ─────────────────────────────────────────────
_cache     = {}
_cache_ttl = {}
CACHE_TTL  = 5


def cache_get(key):
    if key in _cache and (time.time() - _cache_ttl.get(key, 0)) < CACHE_TTL:
        return _cache[key]
    return None


def cache_set(key, val):
    _cache[key]     = val
    _cache_ttl[key] = time.time()


def cache_clear():
    _cache.clear()
    _cache_ttl.clear()


# ── CORS — manual (no flask-cors needed) ─────────────────────
def cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        r = make_response("", 204)
        return cors(r)


@app.after_request
def after(response):
    return cors(response)


# ── Background Thread ─────────────────────────────────────────
def bg_loop():
    while True:
        try:
            analyzer.run_pattern_detection()
            alert_mgr.evaluate_threats()
            cache_clear()
        except Exception as e:
            print(f"[BG] Error: {e}")
        time.sleep(10)


threading.Thread(target=bg_loop, daemon=True).start()


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})


@app.route("/api/threats")
def get_threats():
    c = cache_get("threats")
    if c: return jsonify(c)
    data = db.get_all_threats()
    cache_set("threats", data)
    return jsonify(data)


@app.route("/api/alerts")
def get_alerts():
    c = cache_get("alerts")
    if c: return jsonify(c)
    data = alert_mgr.get_active_alerts()
    cache_set("alerts", data)
    return jsonify(data)


@app.route("/api/stats")
def get_stats():
    c = cache_get("stats")
    if c: return jsonify(c)
    threats = db.get_all_threats()
    counts  = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for t in threats:
        lvl = t.get("threat_level", "UNKNOWN")
        counts[lvl] = counts.get(lvl, 0) + 1
    data = {
        "total_threats" : len(threats),
        "by_level"      : counts,
        "active_alerts" : len(alert_mgr.get_active_alerts())
    }
    cache_set("stats", data)
    return jsonify(data)


@app.route("/api/report")
def get_report():
    c = cache_get("report")
    if c: return jsonify(c)
    data = reporter.generate_summary()
    cache_set("report", data)
    return jsonify(data)


@app.route("/api/ingest", methods=["POST"])
def ingest():
    data = request.get_json(force=True, silent=True) or {}
    if not data:
        return jsonify({"error": "No data"}), 400
    db.add_threat(data)
    cache_clear()
    return jsonify({"status": "ok", "id": data.get("id")}), 201


@app.route("/api/classify", methods=["POST"])
def classify():
    data = request.get_json(force=True, silent=True) or {}
    res  = alert_mgr.manual_classify(data.get("id"), data.get("level"))
    cache_clear()
    return jsonify(res)


@app.route("/api/alerts/acknowledge", methods=["POST"])
def ack_one():
    data = request.get_json(force=True, silent=True) or {}
    res  = alert_mgr.acknowledge_alert(
        data.get("alert_id"), data.get("ack_by", "Command Staff"))
    cache_clear()
    return jsonify(res)


@app.route("/api/alerts/acknowledge_all", methods=["POST"])
def ack_all():
    res = alert_mgr.acknowledge_all()
    cache_clear()
    return jsonify(res)


@app.errorhandler(404)
def e404(_): return jsonify({"error": "not found"}), 404

@app.errorhandler(500)
def e500(_): return jsonify({"error": "server error"}), 500


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  🛡  AIR DEFENSE SYSTEM — FAST SERVER")
    print("  URL    : http://127.0.0.1:5000")
    print("  Status : Running")
    print("="*50 + "\n")
    app.run(
        host        = "127.0.0.1",
        port        = 5000,
        debug       = False,
        threaded    = True,
        use_reloader= False
    )
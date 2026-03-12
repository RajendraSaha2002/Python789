# ============================================================
# logs_routes.py
# ============================================================
from flask import Blueprint, jsonify, request
from backend.services.Parrot_log_service import get_logs, get_recent_alerts, get_system_logs_from_file, add_log

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/api/logs', methods=['GET'])
def security_logs():
    severity = request.args.get('severity')
    logs = get_logs(limit=100, severity=severity)
    return jsonify(logs)

@logs_bp.route('/api/logs/system', methods=['GET'])
def system_logs():
    return jsonify(get_system_logs_from_file())

@logs_bp.route('/api/logs/alerts', methods=['GET'])
def alerts():
    return jsonify(get_recent_alerts())

@logs_bp.route('/api/logs/add', methods=['POST'])
def add():
    data = request.get_json()
    add_log(data['type'], data['message'], data.get('severity', 'INFO'))
    return jsonify({"success": True})
# ============================================================
# dashboard_routes.py
# ============================================================
from flask import Blueprint, jsonify
from backend.services.Parrot_system_service import get_system_summary
from backend.services.Parrot_log_service import get_recent_alerts, get_logs
from backend.services.Parrot_network_service import get_local_ip

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/api/dashboard', methods=['GET'])
def dashboard():
    return jsonify({
        "system": get_system_summary(),
        "alerts": get_recent_alerts(),
        "recent_logs": get_logs(limit=10),
        "local_ip": get_local_ip()
    })
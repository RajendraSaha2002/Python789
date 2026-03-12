# ============================================================
# system_routes.py
# ============================================================
from flask import Blueprint, jsonify
from backend.services.Parrot_system_service import get_system_summary
from backend.Parrot_database import execute_query

system_bp = Blueprint('system', __name__)

@system_bp.route('/api/system', methods=['GET'])
def system_info():
    summary = get_system_summary()
    # Save snapshot to DB
    execute_query(
        """INSERT INTO system_stats (cpu_percent, ram_percent, disk_percent)
           VALUES (%s, %s, %s)""",
        (summary['cpu_percent'], summary['ram']['percent'], summary['disk']['percent']),
        fetch=False
    )
    return jsonify(summary)

@system_bp.route('/api/system/history', methods=['GET'])
def system_history():
    rows = execute_query(
        "SELECT * FROM system_stats ORDER BY recorded_at DESC LIMIT 60"
    )
    return jsonify(rows)
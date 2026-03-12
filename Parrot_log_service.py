# ============================================================
# log_service.py — Security Log Management
# ============================================================

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.Parrot_database import execute_query
from datetime import datetime

def add_log(log_type, message, severity="INFO", source_ip="127.0.0.1"):
    execute_query(
        """INSERT INTO security_logs (log_type, severity, message, source_ip)
           VALUES (%s, %s, %s, %s)""",
        (log_type, severity, message, source_ip), fetch=False
    )

def get_logs(limit=100, severity=None):
    if severity:
        return execute_query(
            "SELECT * FROM security_logs WHERE severity=%s ORDER BY timestamp DESC LIMIT %s",
            (severity, limit)
        )
    return execute_query(
        "SELECT * FROM security_logs ORDER BY timestamp DESC LIMIT %s", (limit,)
    )

def get_recent_alerts():
    return execute_query(
        "SELECT * FROM alerts WHERE acknowledged=FALSE ORDER BY created_at DESC LIMIT 20"
    )

def add_alert(alert_type, message, severity="WARNING"):
    execute_query(
        "INSERT INTO alerts (alert_type, message, severity) VALUES (%s, %s, %s)",
        (alert_type, message, severity), fetch=False
    )

def get_system_logs_from_file():
    """Read from system auth log."""
    logs = []
    try:
        log_files = ['/var/log/auth.log', '/var/log/syslog', '/var/log/kern.log']
        for lf in log_files:
            if os.path.exists(lf):
                with open(lf, 'r', errors='ignore') as f:
                    lines = f.readlines()[-50:]
                    logs.extend([{"file": lf, "line": l.strip()} for l in lines])
    except Exception as e:
        logs = [{"file": "N/A", "line": str(e)}]
    return logs
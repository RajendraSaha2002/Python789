# ============================================================
# network_routes.py
# ============================================================
from flask import Blueprint, jsonify, request
from backend.services.Parrot_network_service import scan_host, scan_network_range, get_local_ip

network_bp = Blueprint('network', __name__)

@network_bp.route('/api/network/local-ip', methods=['GET'])
def local_ip():
    return jsonify({"ip": get_local_ip()})

@network_bp.route('/api/network/scan', methods=['POST'])
def port_scan():
    data = request.get_json()
    target = data.get('target', '127.0.0.1')
    ports = scan_host(target, (1, 1024))
    return jsonify({"target": target, "open_ports": ports})

@network_bp.route('/api/network/range', methods=['POST'])
def range_scan():
    data = request.get_json()
    cidr = data.get('cidr', '192.168.1.0/24')
    hosts = scan_network_range(cidr)
    return jsonify({"hosts": hosts})
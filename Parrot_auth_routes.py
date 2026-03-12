# ============================================================
# auth_routes.py
# ============================================================
from flask import Blueprint, request, jsonify, session
from backend.services.Parrot_auth_service import verify_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = verify_user(data.get('username'), data.get('password'))
    if user:
        session['user'] = user
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@auth_bp.route('/api/me', methods=['GET'])
def me():
    user = session.get('user')
    if user:
        return jsonify({"logged_in": True, "user": user})
    return jsonify({"logged_in": False}), 401
"""User profile routes.
API endpoints for user profiles."""

from flask import Blueprint, jsonify, request

from services.profile import (
    get_user_profile, upsert_user_profile, serialize_profile, get_profile_summary
)
from utils import ValidationError, NotFoundError

profile_bp = Blueprint('profile', __name__, url_prefix='/api')


@profile_bp.post("/profile/upsert")
def api_profile_upsert():
    """Create or update a user profile."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip() or '普通用户'

    if not name:
        return jsonify({"ok": False, "message": "Name is required"}), 400

    # Check whether this is a first-time user
    existing = get_user_profile(name)
    if not existing and not email:
        return jsonify({"ok": False, "message": "Add an email address before using the system for the first time"}), 400

    try:
        profile = upsert_user_profile(name, email=email, role=role)
        return jsonify({"ok": True, "profile": serialize_profile(profile)})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400


@profile_bp.get("/profile/<name>")
def api_profile_get(name):
    """getuser profile"""
    profile = get_user_profile(name)
    if not profile:
        return jsonify({"ok": False, "message": "Profile not found"}), 404
    return jsonify({"ok": True, "profile": serialize_profile(profile)})


@profile_bp.get("/profile-summary/<name>")
def api_profile_summary(name):
    """Get a user's profile summary."""
    try:
        summary = get_profile_summary(name)
        return jsonify({"ok": True, "summary": summary})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
"""Signup routes.
API endpoints for activity registrations."""

from flask import Blueprint, jsonify, request

from services import (
    list_signups, get_signup_by_id, get_signup_name,
    create_signup, delete_signup, update_signup_review_doc,
    serialize_signup
)
from utils import NotFoundError, ValidationError, ConflictError

signup_bp = Blueprint('signup', __name__)


@signup_bp.get("/my-signups/<name>")
def api_my_signups(name):
    """List signup records for a user."""
    signups = list_signups()
    result = []

    for signup in signups:
        if get_signup_name(signup) == name:
            result.append(serialize_signup(signup))

    return jsonify({
        "ok": True,
        "signups": result,
    })


@signup_bp.post("/signup")
def api_create_signup():
    """Create a signup."""
    data = request.get_json(silent=True) or {}

    try:
        row_id = create_signup(data)
        return jsonify({"ok": True, "message": "Registration successful", "id": row_id})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ConflictError as e:
        return jsonify({"ok": False, "message": str(e)}), 409


@signup_bp.delete("/signup/<signup_id>")
def api_delete_signup(signup_id):
    """Delete a signup."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '')

    try:
        delete_signup(signup_id, name)
        return jsonify({"ok": True, "message": "Registration cancelled"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@signup_bp.post("/signup/<signup_id>/review-doc")
def api_submit_review_doc(signup_id):
    """Submit a review document."""
    data = request.get_json(silent=True) or {}
    review_doc_url = data.get('review_doc_url', '')
    reviewer_name = data.get('reviewer_name', '')

    try:
        update_signup_review_doc(signup_id, review_doc_url, reviewer_name)
        return jsonify({"ok": True, "message": "Review document submitted"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
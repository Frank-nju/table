"""Activity routes.
API endpoints for activity operations."""

from flask import Blueprint, jsonify, request

from services import (
    list_activities, get_activity_by_id, get_activity_details,
    create_activity, update_activity, delete_activity, close_activity,
    get_activity_signups, get_signup_stats, activity_is_closed
)
from utils import NotFoundError, ValidationError

activity_bp = Blueprint('activity', __name__)


@activity_bp.get("/activities")
def api_list_activities():
    """Return a list of all activities."""
    activities = list_activities()
    result = []

    for activity in activities:
        # Skip closed activities
        if activity_is_closed(activity):
            continue
        activity_id = activity.get('_id')
        details = get_activity_details(activity)
        stats = get_signup_stats(activity_id)
        result.append({
            **details,
            **stats,
        })

    return jsonify({
        "ok": True,
        "activities": result,
    })


@activity_bp.get("/activity/<activity_id>")
def api_get_activity(activity_id):
    """Get an activity by ID."""
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("Activity not found")

    details = get_activity_details(activity)
    stats = get_signup_stats(activity_id)
    signups = get_activity_signups(activity_id)

    return jsonify({
        "ok": True,
        "activity": {
            **details,
            **stats,
            "signups": [serialize_signup_simple(s) for s in signups],
        }
    })


@activity_bp.post("/activity")
def api_create_activity():
    """Create an activity."""
    data = request.get_json(silent=True) or {}

    try:
        row_id = create_activity({
            'date': data.get('date', ''),
            'time': data.get('time', ''),
            'speakers': data.get('speakers', ''),
            'topic': data.get('topic', ''),
            'creator_name': data.get('creator_name', ''),
            'creator_email': data.get('creator_email', ''),
            'classroom': data.get('classroom', ''),
            'videourl': data.get('videourl', ''),
            'activity_type': data.get('activity_type', 'normal'),
            'group_id': data.get('group_id', ''),
            'group_name': data.get('group_name', ''),
            'expected_attendance': data.get('expected_attendance', 0),
        })
        return jsonify({"ok": True, "message": "Activity created", "id": row_id})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400


@activity_bp.put("/activity/<activity_id>")
def api_update_activity(activity_id):
    """Update an activity."""
    data = request.get_json(silent=True) or {}
    creator_name = data.get('creator_name', '')

    try:
        update_activity(activity_id, data, creator_name)
        return jsonify({"ok": True, "message": "Activity updated"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@activity_bp.delete("/activity/<activity_id>")
def api_delete_activity(activity_id):
    """Delete an activity."""
    data = request.get_json(silent=True) or {}
    creator_name = data.get('creator_name', '')

    try:
        delete_activity(activity_id, creator_name)
        return jsonify({"ok": True, "message": "Activity deleted"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@activity_bp.post("/activity/<activity_id>/close")
def api_close_activity(activity_id):
    """Close an activity."""
    data = request.get_json(silent=True) or {}
    closer_name = data.get('creator_name', '')

    try:
        close_activity(activity_id, closer_name)
        return jsonify({"ok": True, "message": "Activity closed"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400


def serialize_signup_simple(signup):
    """Serialize a signup record."""
    return {
        'id': signup.get('_id'),
        'name': signup.get('姓名', ''),
        'role': signup.get('角色', ''),
        'phone': signup.get('联系电话', ''),
        'email': signup.get('邮箱', ''),
        'review_content': signup.get('评议内容', ''),
    }
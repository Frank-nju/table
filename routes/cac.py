"""CAC administration routes.
API endpoints for CAC administrators and room availability."""

from flask import Blueprint, jsonify, request

from services.cac_admin import (
    list_cac_admins, is_cac_admin, add_cac_admin, remove_cac_admin,
    list_cac_room_slots, add_cac_room_slot, remove_cac_room_slot
)
from utils import ValidationError, NotFoundError, AuthError

cac_bp = Blueprint('cac', __name__, url_prefix='/api')


# ===== Administrator routes =====

@cac_bp.get("/cac-admins")
def api_list_cac_admins():
    """List CAC administrators."""
    admins = list_cac_admins()
    return jsonify({"ok": True, "admins": admins})


@cac_bp.post("/cac-admin")
def api_add_cac_admin():
    """Add a CAC administrator."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    requester_name = data.get("requester_name", "").strip()

    try:
        add_cac_admin(name, requester_name)
        return jsonify({"ok": True, "message": f"Added {name} as an administrator"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@cac_bp.delete("/cac-admin/<name>")
def api_delete_cac_admin(name):
    """Remove a CAC administrator."""
    data = request.get_json(silent=True) or {}
    requester_name = data.get("requester_name", "").strip()

    try:
        remove_cac_admin(name, requester_name)
        return jsonify({"ok": True, "message": f"Removed administrator access for {name}"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404


# ===== Room time-slot routes =====

@cac_bp.get("/cac-room-slots")
def api_list_cac_room_slots():
    """getCAC room slotlist"""
    date = request.args.get("date", "").strip()
    time_slot = request.args.get("time_slot", "").strip()

    result = list_cac_room_slots(date=date or None, time_slot=time_slot or None)
    return jsonify({"ok": True, "slots": result})


@cac_bp.post("/cac-room-slot")
def api_add_cac_room_slot():
    """addroomtime slot"""
    data = request.get_json(silent=True) or {}
    date = data.get("date", "").strip()
    time_slot = data.get("time_slot", "").strip()
    classroom = data.get("classroom", "").strip()
    requester_name = data.get("requester_name", "").strip()

    try:
        row_id = add_cac_room_slot(date, time_slot, classroom, requester_name)
        return jsonify({"ok": True, "message": "Room slot added", "id": row_id})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@cac_bp.delete("/cac-room-slot/<slot_id>")
def api_delete_cac_room_slot(slot_id):
    """Delete a room time slot."""
    data = request.get_json(silent=True) or {}
    requester_name = data.get("requester_name", "").strip()

    try:
        remove_cac_room_slot(slot_id, requester_name)
        return jsonify({"ok": True, "message": "Room slot deleted"})
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
"""
CAC 管理路由模块

CAC 管理员和教室时间槽相关的 API 路由
"""

from flask import Blueprint, jsonify, request

from services.cac_admin import (
    list_cac_admins, is_cac_admin, add_cac_admin, remove_cac_admin,
    list_cac_room_slots, add_cac_room_slot, remove_cac_room_slot
)
from utils import ValidationError, NotFoundError, AuthError

cac_bp = Blueprint('cac', __name__, url_prefix='/api')


# ===== 管理员路由 =====

@cac_bp.get("/cac-admins")
def api_list_cac_admins():
    """获取CAC管理员列表"""
    admins = list_cac_admins()
    return jsonify({"ok": True, "admins": admins})


@cac_bp.post("/cac-admin")
def api_add_cac_admin():
    """添加CAC管理员"""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    requester_name = data.get("requester_name", "").strip()

    try:
        add_cac_admin(name, requester_name)
        return jsonify({"ok": True, "message": f"已添加 {name} 为管理员"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@cac_bp.delete("/cac-admin/<name>")
def api_delete_cac_admin(name):
    """删除CAC管理员"""
    data = request.get_json(silent=True) or {}
    requester_name = data.get("requester_name", "").strip()

    try:
        remove_cac_admin(name, requester_name)
        return jsonify({"ok": True, "message": f"已移除 {name} 的管理员权限"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404


# ===== 教室时间槽路由 =====

@cac_bp.get("/cac-room-slots")
def api_list_cac_room_slots():
    """获取CAC教室时间槽列表"""
    date = request.args.get("date", "").strip()
    time_slot = request.args.get("time_slot", "").strip()

    result = list_cac_room_slots(date=date or None, time_slot=time_slot or None)
    return jsonify({"ok": True, "slots": result})


@cac_bp.post("/cac-room-slot")
def api_add_cac_room_slot():
    """添加教室时间槽"""
    data = request.get_json(silent=True) or {}
    date = data.get("date", "").strip()
    time_slot = data.get("time_slot", "").strip()
    classroom = data.get("classroom", "").strip()
    requester_name = data.get("requester_name", "").strip()

    try:
        row_id = add_cac_room_slot(date, time_slot, classroom, requester_name)
        return jsonify({"ok": True, "message": "时间槽添加成功", "id": row_id})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@cac_bp.delete("/cac-room-slot/<slot_id>")
def api_delete_cac_room_slot(slot_id):
    """删除教室时间槽"""
    data = request.get_json(silent=True) or {}
    requester_name = data.get("requester_name", "").strip()

    try:
        remove_cac_room_slot(slot_id, requester_name)
        return jsonify({"ok": True, "message": "时间槽删除成功"})
    except AuthError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
"""
兴趣组路由模块

兴趣组相关的 API 路由
"""

from flask import Blueprint, jsonify, request

from services.group import (
    list_interest_groups, get_interest_group_by_id, serialize_interest_group,
    get_group_ids_for_member, create_group, join_group, leave_group
)
from utils import ValidationError, NotFoundError

group_bp = Blueprint('group', __name__, url_prefix='/api')


@group_bp.get("/groups")
def api_list_groups():
    """获取所有兴趣组列表"""
    groups = list_interest_groups()
    result = [serialize_interest_group(g) for g in groups if g]
    return jsonify({"ok": True, "groups": result})


@group_bp.get("/group/<group_id>")
def api_get_group(group_id):
    """获取单个兴趣组详情"""
    group = get_interest_group_by_id(group_id)
    if not group:
        raise NotFoundError("兴趣组不存在")
    return jsonify({"ok": True, "group": serialize_interest_group(group)})


@group_bp.get("/my-groups/<name>")
def api_my_groups(name):
    """获取某人的兴趣组列表"""
    group_ids = get_group_ids_for_member(name)
    result = []
    seen = set()
    for gid in group_ids:
        if gid and gid not in seen:
            group = get_interest_group_by_id(gid)
            if group:
                result.append(serialize_interest_group(group))
                seen.add(gid)
    return jsonify({"ok": True, "groups": result})


@group_bp.post("/group")
def api_create_group():
    """创建兴趣组"""
    data = request.get_json(silent=True) or {}

    try:
        group = create_group(data)
        return jsonify({"ok": True, "group": group, "message": "兴趣组创建成功"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400


@group_bp.post("/group/<group_id>/join")
def api_join_group(group_id):
    """加入兴趣组"""
    data = request.get_json(silent=True) or {}
    member_name = data.get('member_name', '').strip()
    member_email = data.get('member_email', '').strip()

    if not member_name:
        return jsonify({"ok": False, "message": "请填写姓名"}), 400

    try:
        group = join_group(group_id, member_name, member_email)
        return jsonify({"ok": True, "group": group, "message": "加入成功"})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404


@group_bp.post("/group/<group_id>/leave")
def api_leave_group(group_id):
    """退出兴趣组"""
    data = request.get_json(silent=True) or {}
    member_name = data.get('member_name', '').strip()

    if not member_name:
        return jsonify({"ok": False, "message": "请填写姓名"}), 400

    try:
        leave_group(group_id, member_name)
        return jsonify({"ok": True, "message": "已退出兴趣组"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
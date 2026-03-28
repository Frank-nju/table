"""
用户档案路由模块

用户档案相关的 API 路由
"""

from flask import Blueprint, jsonify, request

from services.profile import (
    get_user_profile, upsert_user_profile, serialize_profile, get_profile_summary
)
from utils import ValidationError, NotFoundError

profile_bp = Blueprint('profile', __name__, url_prefix='/api')


@profile_bp.post("/profile/upsert")
def api_profile_upsert():
    """创建或更新用户档案"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip() or '普通用户'

    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    # 首次使用检查
    existing = get_user_profile(name)
    if not existing and not email:
        return jsonify({"ok": False, "message": "首次使用必须填写邮箱"}), 400

    try:
        profile = upsert_user_profile(name, email=email, role=role)
        return jsonify({"ok": True, "profile": serialize_profile(profile)})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400


@profile_bp.get("/profile/<name>")
def api_profile_get(name):
    """获取用户档案"""
    profile = get_user_profile(name)
    if not profile:
        return jsonify({"ok": False, "message": "用户档案不存在"}), 404
    return jsonify({"ok": True, "profile": serialize_profile(profile)})


@profile_bp.get("/profile-summary/<name>")
def api_profile_summary(name):
    """获取用户档案摘要"""
    try:
        summary = get_profile_summary(name)
        return jsonify({"ok": True, "summary": summary})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
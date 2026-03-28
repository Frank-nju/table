"""
评议邀请路由模块

评议邀请相关的 API 路由
"""

from flask import Blueprint, jsonify, request

from services.invite import (
    list_review_invites, get_invites_by_activity, get_invites_for_user,
    create_review_invite, update_invite_status, serialize_review_invite
)
from utils import ValidationError, NotFoundError

invite_bp = Blueprint('invite', __name__, url_prefix='/api')


@invite_bp.post("/invite-reviewer")
def api_invite_reviewer():
    """邀请评议员"""
    data = request.get_json(silent=True) or {}
    activity_id = data.get('activity_id', '').strip()
    inviter_name = data.get('inviter_name', '').strip()
    invitee_name = data.get('invitee_name', '').strip()
    invitee_email = data.get('invitee_email', '').strip()
    source_type = data.get('source_type', '').strip() or '分享者指定'

    try:
        invite = create_review_invite(activity_id, inviter_name, invitee_name, invitee_email, source_type)
        return jsonify({"ok": True, "message": "评议邀请已发送", "invite": invite})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404


@invite_bp.get("/activity/<activity_id>/invites")
def api_activity_invites(activity_id):
    """获取活动的邀请列表"""
    invites = get_invites_by_activity(activity_id)
    result = [serialize_review_invite(i) for i in invites]
    result.sort(key=lambda x: (x.get('created_at', ''), x.get('invitee_name', '')))
    return jsonify({"ok": True, "invites": result})


@invite_bp.get("/my-invites/<name>")
def api_my_invites(name):
    """获取用户的邀请列表"""
    name = name.strip()
    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    invites = get_invites_for_user(name)
    result = [serialize_review_invite(i) for i in invites]
    result.sort(key=lambda x: (x.get('created_at', ''), x.get('activity_topic', '')))
    return jsonify({"ok": True, "invites": result})


@invite_bp.post("/invite/<invite_id>/status")
def api_update_invite_status(invite_id):
    """更新邀请状态"""
    data = request.get_json(silent=True) or {}
    status = data.get('status', '').strip()
    updater_name = data.get('updater_name', '').strip()

    if not status:
        return jsonify({"ok": False, "message": "状态不能为空"}), 400

    try:
        invite = update_invite_status(invite_id, status, updater_name)
        return jsonify({"ok": True, "message": "状态更新成功", "invite": invite})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
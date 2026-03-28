"""
报名路由模块

报名相关的 API 路由
"""

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
    """获取某人的报名记录"""
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
    """创建报名"""
    data = request.get_json(silent=True) or {}

    try:
        row_id = create_signup(data)
        return jsonify({"ok": True, "message": "报名成功", "id": row_id})
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ConflictError as e:
        return jsonify({"ok": False, "message": str(e)}), 409


@signup_bp.delete("/signup/<signup_id>")
def api_delete_signup(signup_id):
    """删除报名"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '')

    try:
        delete_signup(signup_id, name)
        return jsonify({"ok": True, "message": "取消报名成功"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403


@signup_bp.post("/signup/<signup_id>/review-doc")
def api_submit_review_doc(signup_id):
    """提交评议文档"""
    data = request.get_json(silent=True) or {}
    review_doc_url = data.get('review_doc_url', '')
    reviewer_name = data.get('reviewer_name', '')

    try:
        update_signup_review_doc(signup_id, review_doc_url, reviewer_name)
        return jsonify({"ok": True, "message": "评议文档提交成功"})
    except NotFoundError as e:
        return jsonify({"ok": False, "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"ok": False, "message": str(e)}), 403
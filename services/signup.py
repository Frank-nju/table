"""
报名服务模块

封装报名相关的业务逻辑
"""

import json
from datetime import datetime

from config import (
    SIGNUP_TABLE_NAME, ACTIVITY_TABLE_NAME,
    SIGNUP_COL_NAME, SIGNUP_COL_ACTIVITY_ID, SIGNUP_COL_ROLE,
    SIGNUP_COL_PHONE, SIGNUP_COL_EMAIL, SIGNUP_COL_REVIEW_DOC_URL,
    SIGNUP_COL_REVIEW_SUBMITTED_AT, SIGNUP_COL_LAST_REVIEW_REMINDER_AT,
    SIGNUP_COL_REVIEW_CONTENT,
    ACTIVITY_COL_TYPE, ACTIVITY_COL_CREATOR_NAME, ACTIVITY_COL_CREATOR_EMAIL,
    REVIEWER_LIMIT, TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError, ConflictError, safe_text
from services.activity import get_activity_by_id, get_activity_creator_name, get_activity_creator_email, get_activity_details
from services.email import send_email_async
from utils.versioned_cache import cached_build, touch_version


def list_signups():
    """获取所有报名记录（带版本缓存）"""
    return cached_build(
        'signups',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(SIGNUP_TABLE_NAME) or [],
    )


def get_signup_by_id(signup_id):
    """根据ID获取报名记录"""
    if not signup_id:
        return None
    signups = list_signups()
    for signup in signups:
        if signup.get('_id') == signup_id:
            return signup
    return None


def get_signup_name(signup):
    """获取报名者姓名"""
    return safe_text(signup.get(SIGNUP_COL_NAME, ''))


def get_signup_email(signup):
    """获取报名者邮箱"""
    return safe_text(signup.get(SIGNUP_COL_EMAIL, ''))


def get_signup_role(signup):
    """获取报名角色"""
    return safe_text(signup.get(SIGNUP_COL_ROLE, ''))


def get_signup_review_doc_url(signup):
    """获取评议文档链接"""
    return safe_text(signup.get(SIGNUP_COL_REVIEW_DOC_URL, ''))


def get_signups_by_activity(activity_id, role=None):
    """获取活动的报名列表"""
    signups = list_signups()
    result = []
    for signup in signups:
        if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')) == activity_id:
            if role is None or signup.get(SIGNUP_COL_ROLE) == role:
                result.append(signup)
    return result


def count_signups_by_activity(activity_id, role=None):
    """统计活动的报名人数"""
    return len(get_signups_by_activity(activity_id, role))


def serialize_signup(signup):
    """序列化报名记录"""
    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = get_activity_by_id(activity_id)
    activity_details = get_activity_details(activity) if activity else {}

    return {
        'id': signup.get('_id'),
        'name': get_signup_name(signup),
        'activity_id': activity_id,
        'role': get_signup_role(signup),
        'phone': safe_text(signup.get(SIGNUP_COL_PHONE, '')),
        'email': get_signup_email(signup),
        'review_content': safe_text(signup.get(SIGNUP_COL_REVIEW_CONTENT, '')),
        'review_doc_url': safe_text(signup.get(SIGNUP_COL_REVIEW_DOC_URL, '')),
        'review_submitted_at': signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''),
        'activity': activity_details,
    }


def create_signup(data):
    """创建报名"""
    name = safe_text(data.get('name', ''))
    activity_id = safe_text(data.get('activity_id', ''))
    role = safe_text(data.get('role', ''))
    phone = safe_text(data.get('phone', ''))
    email = safe_text(data.get('email', ''))
    review_content = safe_text(data.get('review_content', ''))

    # 验证必填字段
    if not name or not activity_id or not role:
        raise ValidationError("请完整填写姓名、活动和角色")

    # 验证角色
    if role not in ['评议员', '旁听']:
        raise ValidationError("角色必须为'评议员'或'旁听'")

    # 评议员必填评议内容
    if role == '评议员' and not review_content:
        raise ValidationError("评议员请填写评议内容")

    # 验证活动是否存在
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("活动不存在")

    # 检查评议员是否已满
    if role == '评议员':
        reviewer_count = count_signups_by_activity(activity_id, '评议员')
        if reviewer_count >= REVIEWER_LIMIT:
            raise ConflictError(f"评议员已满 {REVIEWER_LIMIT} 人，无法报名")

    # 检查是否已报名
    existing_signups = get_signups_by_activity(activity_id)
    for signup in existing_signups:
        if get_signup_name(signup) == name:
            raise ConflictError("您已经报名过该活动，不能重复提交")

    # 创建报名记录
    row_data = {
        SIGNUP_COL_NAME: name,
        SIGNUP_COL_ACTIVITY_ID: activity_id,
        SIGNUP_COL_ROLE: role,
        SIGNUP_COL_PHONE: phone,
        SIGNUP_COL_EMAIL: email,
        SIGNUP_COL_REVIEW_CONTENT: review_content if role == '评议员' else '',
    }

    result = db.append_row(SIGNUP_TABLE_NAME, row_data)
    touch_version()

    # 发送通知邮件
    creator_email = get_activity_creator_email(activity)
    if creator_email:
        topic = activity.get('活动主题', '')
        send_email_async(
            creator_email,
            f"【报名通知】{name} 报名了 {topic}",
            f"{name} 以「{role}」身份报名了您的活动「{topic}」\n" +
            (f"评议内容：{review_content}\n" if review_content else "")
        )

    return str(result.get('_id', ''))


def delete_signup(signup_id, name=None):
    """删除报名"""
    signup = get_signup_by_id(signup_id)
    if not signup:
        raise NotFoundError("报名记录不存在")

    if name and get_signup_name(signup) != name:
        raise ValidationError("只能取消自己的报名")

    result = db.delete_row(SIGNUP_TABLE_NAME, signup_id)
    if result:
        touch_version()
    return result


def update_signup_review_doc(signup_id, review_doc_url, reviewer_name=None):
    """更新评议文档链接"""
    signup = get_signup_by_id(signup_id)
    if not signup:
        raise NotFoundError("报名记录不存在")

    if reviewer_name and get_signup_name(signup) != reviewer_name:
        raise ValidationError("只能更新自己的评议")

    update_data = {
        **signup,
        SIGNUP_COL_REVIEW_DOC_URL: review_doc_url,
        SIGNUP_COL_REVIEW_SUBMITTED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    result = db.update_row(SIGNUP_TABLE_NAME, signup_id, update_data)
    touch_version()
    return result


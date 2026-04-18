"""
评议邀请服务模块

封装评议邀请相关的业务逻辑
"""

from datetime import datetime

from config import (
    REVIEW_INVITE_TABLE_NAME,
    INVITE_COL_ACTIVITY_ID, INVITE_COL_ACTIVITY_TOPIC,
    INVITE_COL_INVITER_NAME, INVITE_COL_INVITEE_NAME, INVITE_COL_INVITEE_EMAIL,
    INVITE_COL_SOURCE_TYPE, INVITE_COL_STATUS, INVITE_COL_CREATED_AT,
    INVITE_COL_UPDATED_AT, INVITE_COL_UPDATED_BY,
    TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError, safe_text
from services.activity import get_activity_by_id
from services.profile import get_user_email, upsert_user_profile
from services.email import send_email_async
from utils.versioned_cache import cached_build, touch_version


def list_review_invites():
    """获取所有评议邀请（带版本缓存）"""
    return cached_build(
        'review_invites',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(REVIEW_INVITE_TABLE_NAME) or [],
    )


def get_invite_by_id(invite_id):
    """根据ID获取邀请"""
    if not invite_id:
        return None
    invites = list_review_invites()
    for invite in invites:
        if str(invite.get('_id')) == invite_id:
            return invite
    return None


def get_invites_by_activity(activity_id):
    """获取活动的邀请列表"""
    invites = list_review_invites()
    return [i for i in invites if str(i.get(INVITE_COL_ACTIVITY_ID, '')) == str(activity_id)]


def get_invites_for_user(name):
    """获取用户的邀请列表"""
    invites = list_review_invites()
    return [i for i in invites if str(i.get(INVITE_COL_INVITEE_NAME, '')).strip() == name]


def serialize_review_invite(invite):
    """序列化评议邀请"""
    if not invite:
        return None
    return {
        'id': str(invite.get('_id', '')),
        'activity_id': str(invite.get(INVITE_COL_ACTIVITY_ID, '')),
        'activity_topic': str(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')).strip(),
        'inviter_name': str(invite.get(INVITE_COL_INVITER_NAME, '')).strip(),
        'invitee_name': str(invite.get(INVITE_COL_INVITEE_NAME, '')).strip(),
        'invitee_email': str(invite.get(INVITE_COL_INVITEE_EMAIL, '')).strip(),
        'source_type': str(invite.get(INVITE_COL_SOURCE_TYPE, '')).strip(),
        'status': str(invite.get(INVITE_COL_STATUS, '')).strip(),
        'created_at': invite.get(INVITE_COL_CREATED_AT, ''),
        'updated_at': invite.get(INVITE_COL_UPDATED_AT, ''),
        'updated_by': str(invite.get(INVITE_COL_UPDATED_BY, '')).strip(),
    }


def create_review_invite(activity_id, inviter_name, invitee_name, invitee_email='', source_type='分享者指定'):
    """创建评议邀请"""
    if not activity_id or not inviter_name or not invitee_name:
        raise ValidationError("请完整填写活动、邀请人和被邀请人")

    if source_type not in {'开放报名', '分享者指定', 'CAC特邀'}:
        raise ValidationError("邀请来源必须为 开放报名、分享者指定 或 CAC特邀")

    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("活动不存在")

    topic = str(activity.get('活动主题', '')).strip()

    # 确保用户档案存在
    upsert_user_profile(invitee_name, email=invitee_email, role='普通用户')
    final_email = get_user_email(invitee_name)

    row_data = {
        INVITE_COL_ACTIVITY_ID: activity_id,
        INVITE_COL_ACTIVITY_TOPIC: topic,
        INVITE_COL_INVITER_NAME: inviter_name,
        INVITE_COL_INVITEE_NAME: invitee_name,
        INVITE_COL_INVITEE_EMAIL: final_email,
        INVITE_COL_SOURCE_TYPE: source_type,
        INVITE_COL_STATUS: '已发送',
        INVITE_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        INVITE_COL_UPDATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        INVITE_COL_UPDATED_BY: inviter_name,
    }

    result = db.append_row(REVIEW_INVITE_TABLE_NAME, row_data)
    touch_version()

    # 发送邮件通知
    if final_email:
        subject = f"[CAC 分享会] 评议邀请：{topic}"
        body = (
            f"{invitee_name}，您好：\n\n"
            f"{inviter_name} 通过\"{source_type}\"邀请您参与活动《{topic}》评议。\n"
            "请登录系统确认并报名。"
        )
        send_email_async(final_email, subject, body)

    return serialize_review_invite(result)


def update_invite_status(invite_id, status, updater_name):
    """更新邀请状态"""
    invite = get_invite_by_id(invite_id)
    if not invite:
        raise NotFoundError("邀请不存在")

    if status not in {'已发送', '已接受', '已拒绝', '已取消'}:
        raise ValidationError("状态必须为 已发送、已接受、已拒绝 或 已取消")

    update_data = {
        **invite,
        INVITE_COL_STATUS: status,
        INVITE_COL_UPDATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        INVITE_COL_UPDATED_BY: updater_name,
    }

    db.update_row(REVIEW_INVITE_TABLE_NAME, invite_id, update_data)
    touch_version()
    return serialize_review_invite(get_invite_by_id(invite_id))


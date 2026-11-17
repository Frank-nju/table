"""Review invitation service.
Encapsulates review invitation business logic."""

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
    """List all review invitations using the versioned cache."""
    return cached_build(
        'review_invites',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(REVIEW_INVITE_TABLE_NAME) or [],
    )


def get_invite_by_id(invite_id):
    """Get an invitation by ID."""
    if not invite_id:
        return None
    invites = list_review_invites()
    for invite in invites:
        if str(invite.get('_id')) == invite_id:
            return invite
    return None


def get_invites_by_activity(activity_id):
    """List invitations for an activity."""
    invites = list_review_invites()
    return [i for i in invites if str(i.get(INVITE_COL_ACTIVITY_ID, '')) == str(activity_id)]


def get_invites_for_user(name):
    """List invitations for a user."""
    invites = list_review_invites()
    return [i for i in invites if str(i.get(INVITE_COL_INVITEE_NAME, '')).strip() == name]


def serialize_review_invite(invite):
    """Serialize a review invitation."""
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
    """Create a review invitation."""
    if not activity_id or not inviter_name or not invitee_name:
        raise ValidationError("Provide the activity, inviter, and invitee")

    if source_type not in {'开放报名', '分享者指定', 'CAC特邀'}:
        raise ValidationError("Invitation source must be Open signup, Organizer-selected, or CAC invitation")

    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("Activity not found")

    topic = str(activity.get('活动主题', '')).strip()

    # Ensure the user has a profile.
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

    # Send an email notification.
    if final_email:
        source_label = {'开放报名': 'open signup', '分享者指定': 'organizer-selected', 'CAC特邀': 'CAC invitation'}.get(source_type, source_type)
        subject = f"[CAC Share Sessions] Review invitation: {topic}"
        body = (
            f"Hello, {invitee_name},\n\n"
            f"{inviter_name} invited you to review “{topic}” through {source_label}.\n"
            "Sign in to respond to the invitation and register."
        )
        send_email_async(final_email, subject, body)

    return serialize_review_invite(result)


def update_invite_status(invite_id, status, updater_name):
    """Update an invitation's status."""
    invite = get_invite_by_id(invite_id)
    if not invite:
        raise NotFoundError("Invitation not found")

    if status not in {'已发送', '已接受', '已拒绝', '已取消'}:
        raise ValidationError("Status must be Pending, Accepted, Declined, or Cancelled")

    update_data = {
        **invite,
        INVITE_COL_STATUS: status,
        INVITE_COL_UPDATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        INVITE_COL_UPDATED_BY: updater_name,
    }

    db.update_row(REVIEW_INVITE_TABLE_NAME, invite_id, update_data)
    touch_version()
    return serialize_review_invite(get_invite_by_id(invite_id))


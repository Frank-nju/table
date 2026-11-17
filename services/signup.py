"""Signup service.
Encapsulates registration business logic."""

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
    """List all signup records using the versioned cache."""
    return cached_build(
        'signups',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(SIGNUP_TABLE_NAME) or [],
    )


def get_signup_by_id(signup_id):
    """Get a signup record by ID."""
    if not signup_id:
        return None
    signups = list_signups()
    for signup in signups:
        if signup.get('_id') == signup_id:
            return signup
    return None


def get_signup_name(signup):
    """Get the signup participant's name."""
    return safe_text(signup.get(SIGNUP_COL_NAME, ''))


def get_signup_email(signup):
    """Get the signup participant's email address."""
    return safe_text(signup.get(SIGNUP_COL_EMAIL, ''))


def get_signup_role(signup):
    """Get the signup role."""
    return safe_text(signup.get(SIGNUP_COL_ROLE, ''))


def get_signup_review_doc_url(signup):
    """Get the review document URL."""
    return safe_text(signup.get(SIGNUP_COL_REVIEW_DOC_URL, ''))


def get_signups_by_activity(activity_id, role=None):
    """List signups for an activity."""
    signups = list_signups()
    result = []
    for signup in signups:
        if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')) == activity_id:
            if role is None or signup.get(SIGNUP_COL_ROLE) == role:
                result.append(signup)
    return result


def count_signups_by_activity(activity_id, role=None):
    """Count signups for an activity."""
    return len(get_signups_by_activity(activity_id, role))


def serialize_signup(signup):
    """Serialize a signup record."""
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
    """Create a signup."""
    name = safe_text(data.get('name', ''))
    activity_id = safe_text(data.get('activity_id', ''))
    role = safe_text(data.get('role', ''))
    phone = safe_text(data.get('phone', ''))
    email = safe_text(data.get('email', ''))
    review_content = safe_text(data.get('review_content', ''))

    # Validate required fields.
    if not name or not activity_id or not role:
        raise ValidationError("Provide a name, activity, and role")

    # Validate the role
    if role not in ['评议员', '旁听']:
        raise ValidationError("Role must be Reviewer or Observer")

    # Reviewers must provide review content
    if role == '评议员' and not review_content:
        raise ValidationError("Reviewers must provide a review topic")

    # Check that the activity exists.
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("Activity not found")

    # Check whether the reviewer limit has been reached.
    if role == '评议员':
        reviewer_count = count_signups_by_activity(activity_id, '评议员')
        if reviewer_count >= REVIEWER_LIMIT:
            raise ConflictError(f"Reviewer capacity reached ({REVIEWER_LIMIT}); registration is unavailable")

    # Check whether the user has already signed up
    existing_signups = get_signups_by_activity(activity_id)
    for signup in existing_signups:
        if get_signup_name(signup) == name:
            raise ConflictError("You are already registered for this activity")

    # Create the signup record.
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

    # Send a notification email
    creator_email = get_activity_creator_email(activity)
    if creator_email:
        topic = activity.get('活动主题', '')
        send_email_async(
            creator_email,
            f"[CAC Share Sessions] New signup: {name} registered for {topic}",
            f"{name} registered for your activity “{topic}” as {'Reviewer' if role == '评议员' else 'Observer'}.\n" +
            (f"Review topic: {review_content}\n" if review_content else "")
        )

    return str(result.get('_id', ''))


def delete_signup(signup_id, name=None):
    """Delete a signup."""
    signup = get_signup_by_id(signup_id)
    if not signup:
        raise NotFoundError("Registration not found")

    if name and get_signup_name(signup) != name:
        raise ValidationError("You can only cancel your own registration")

    result = db.delete_row(SIGNUP_TABLE_NAME, signup_id)
    if result:
        touch_version()
    return result


def update_signup_review_doc(signup_id, review_doc_url, reviewer_name=None):
    """Update the review document URL."""
    signup = get_signup_by_id(signup_id)
    if not signup:
        raise NotFoundError("Registration not found")

    if reviewer_name and get_signup_name(signup) != reviewer_name:
        raise ValidationError("You can only update your own review")

    update_data = {
        **signup,
        SIGNUP_COL_REVIEW_DOC_URL: review_doc_url,
        SIGNUP_COL_REVIEW_SUBMITTED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    result = db.update_row(SIGNUP_TABLE_NAME, signup_id, update_data)
    touch_version()
    return result


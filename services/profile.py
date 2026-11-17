"""User profile service.
Encapsulates user profile business logic."""

from datetime import datetime

from config import (
    USER_PROFILE_TABLE_NAME,
    USER_COL_NAME, USER_COL_EMAIL, USER_COL_ROLE, USER_COL_FIRST_SEEN_AT,
    TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError, safe_text
from utils.versioned_cache import cached_build, touch_version


def list_user_profiles():
    """List all user profiles using the versioned cache."""
    return cached_build(
        'user_profiles',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(USER_PROFILE_TABLE_NAME) or [],
    )


def get_user_profile(name):
    """Get a user profile by name."""
    if not name:
        return None
    profiles = list_user_profiles()
    for profile in profiles:
        if str(profile.get(USER_COL_NAME, '')).strip() == name:
            return profile
    return None


def get_user_email(name):
    """Get a user's email address."""
    profile = get_user_profile(name)
    if profile:
        return str(profile.get(USER_COL_EMAIL, '')).strip()
    return ''


def upsert_user_profile(name, email='', role='普通用户'):
    """Create or update a user profile."""
    if not name:
        raise ValidationError("Name is required")

    profile = get_user_profile(name)

    if profile:
        # Update the existing profile
        update_data = {**profile}
        if email:
            update_data[USER_COL_EMAIL] = email
        if role:
            update_data[USER_COL_ROLE] = role
        db.update_row(USER_PROFILE_TABLE_NAME, profile.get('_id'), update_data)
        touch_version()
        return get_user_profile(name)
    else:
        # Create a new profile
        if not email:
            raise ValidationError("Add an email address before using the system for the first time")

        row_data = {
            USER_COL_NAME: name,
            USER_COL_EMAIL: email,
            USER_COL_ROLE: role,
            USER_COL_FIRST_SEEN_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        result = db.append_row(USER_PROFILE_TABLE_NAME, row_data)
        touch_version()
        return result


def serialize_profile(profile):
    """Serialize a user profile."""
    if not profile:
        return None
    return {
        'id': str(profile.get('_id', '')),
        'name': str(profile.get(USER_COL_NAME, '')).strip(),
        'email': str(profile.get(USER_COL_EMAIL, '')).strip(),
        'role': str(profile.get(USER_COL_ROLE, '')).strip(),
        'first_seen_at': profile.get(USER_COL_FIRST_SEEN_AT, ''),
    }


def get_profile_summary(name):
    """Get a profile summary, including activity participation statistics."""
    profile = get_user_profile(name)
    if not profile:
        raise NotFoundError("Profile not found")

    # Count activities the user participated in
    from services.signup import list_signups, get_signup_name

    signups = list_signups()
    user_signups = [s for s in signups if get_signup_name(s) == name]

    # Count signups by role
    roles = {}
    for s in user_signups:
        role = str(s.get('角色', '')).strip()
        roles[role] = roles.get(role, 0) + 1

    return {
        **serialize_profile(profile),
        'stats': {
            'total_signups': len(user_signups),
            'roles': roles,
        }
    }


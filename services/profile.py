"""
用户档案服务模块

封装用户档案相关的业务逻辑
"""

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
    """获取所有用户档案（带版本缓存）"""
    return cached_build(
        'user_profiles',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(USER_PROFILE_TABLE_NAME) or [],
    )


def get_user_profile(name):
    """根据姓名获取用户档案"""
    if not name:
        return None
    profiles = list_user_profiles()
    for profile in profiles:
        if str(profile.get(USER_COL_NAME, '')).strip() == name:
            return profile
    return None


def get_user_email(name):
    """获取用户邮箱"""
    profile = get_user_profile(name)
    if profile:
        return str(profile.get(USER_COL_EMAIL, '')).strip()
    return ''


def upsert_user_profile(name, email='', role='普通用户'):
    """创建或更新用户档案"""
    if not name:
        raise ValidationError("姓名不能为空")

    profile = get_user_profile(name)

    if profile:
        # 更新现有档案
        update_data = {**profile}
        if email:
            update_data[USER_COL_EMAIL] = email
        if role:
            update_data[USER_COL_ROLE] = role
        db.update_row(USER_PROFILE_TABLE_NAME, profile.get('_id'), update_data)
        touch_version()
        return get_user_profile(name)
    else:
        # 创建新档案
        if not email:
            raise ValidationError("首次使用必须填写邮箱")

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
    """序列化用户档案"""
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
    """获取用户档案摘要（包含活动参与统计）"""
    profile = get_user_profile(name)
    if not profile:
        raise NotFoundError("用户档案不存在")

    # 统计参与的活动
    from services.signup import list_signups, get_signup_name

    signups = list_signups()
    user_signups = [s for s in signups if get_signup_name(s) == name]

    # 统计角色分布
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


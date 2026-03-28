"""
活动服务模块

封装活动相关的业务逻辑
"""

import json
from datetime import datetime, timedelta
from collections import Counter

from config import (
    ACTIVITY_TABLE_NAME, SIGNUP_TABLE_NAME,
    ACTIVITY_COL_DATE, ACTIVITY_COL_TIME, ACTIVITY_COL_SPEAKERS, ACTIVITY_COL_TOPIC,
    ACTIVITY_COL_CLASSROOM, ACTIVITY_COL_VIDEOURL, ACTIVITY_COL_CREATOR_NAME,
    ACTIVITY_COL_CREATOR_EMAIL, ACTIVITY_COL_STATUS, ACTIVITY_COL_CLOSED_AT,
    ACTIVITY_COL_ON_TIME, ACTIVITY_COL_CLOSER_NAME, ACTIVITY_COL_TYPE,
    ACTIVITY_COL_GROUP_ID, ACTIVITY_COL_GROUP_NAME, ACTIVITY_COL_EXPECTED_ATTENDANCE,
    SIGNUP_COL_ACTIVITY_ID, SIGNUP_COL_ROLE,
    REVIEWER_LIMIT, ACTIVITY_CLOSE_GRACE_MINUTES
)
from models import db
from utils import NotFoundError, ValidationError


def list_activities():
    """获取所有活动列表"""
    return db.list_rows(ACTIVITY_TABLE_NAME)


def get_activity_by_id(activity_id):
    """根据ID获取活动"""
    if not activity_id:
        return None
    activities = list_activities()
    for activity in activities:
        if activity.get('_id') == activity_id:
            return activity
    return None


def get_activity_details(activity):
    """获取活动详情"""
    if not activity:
        return {}
    return {
        'id': activity.get('_id'),
        'date': _safe_text(activity.get(ACTIVITY_COL_DATE, '')),
        'time': _safe_text(activity.get(ACTIVITY_COL_TIME, '')),
        'speakers': _safe_text(activity.get(ACTIVITY_COL_SPEAKERS, '')),
        'topic': _safe_text(activity.get(ACTIVITY_COL_TOPIC, '')),
        'classroom': _safe_text(activity.get(ACTIVITY_COL_CLASSROOM, '')),
        'videourl': _safe_text(activity.get(ACTIVITY_COL_VIDEOURL, '')),
        'creator_name': _safe_text(activity.get(ACTIVITY_COL_CREATOR_NAME, '')),
        'creator_email': _safe_text(activity.get(ACTIVITY_COL_CREATOR_EMAIL, '')),
        'status': _safe_text(activity.get(ACTIVITY_COL_STATUS, '进行中')),
        'closed_at': _safe_text(activity.get(ACTIVITY_COL_CLOSED_AT, '')),
        'closer_name': _safe_text(activity.get(ACTIVITY_COL_CLOSER_NAME, '')),
        'on_time': activity.get(ACTIVITY_COL_ON_TIME),
        'activity_type': _safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal',
        'group_id': _safe_text(activity.get(ACTIVITY_COL_GROUP_ID, '')),
        'group_name': _safe_text(activity.get(ACTIVITY_COL_GROUP_NAME, '')),
        'expected_attendance': activity.get(ACTIVITY_COL_EXPECTED_ATTENDANCE, 0),
    }


def get_activity_creator_name(activity):
    """获取活动创建者姓名"""
    return _safe_text(activity.get(ACTIVITY_COL_CREATOR_NAME, ''))


def get_activity_creator_email(activity):
    """获取活动创建者邮箱"""
    return _safe_text(activity.get(ACTIVITY_COL_CREATOR_EMAIL, ''))


def activity_is_closed(activity):
    """检查活动是否已结项"""
    return _safe_bool(activity.get(ACTIVITY_COL_ON_TIME)) or \
           _safe_text(activity.get(ACTIVITY_COL_STATUS, '')) == '已结项' or \
           bool(get_activity_closed_at(activity))


def get_activity_closed_at(activity):
    """获取活动结项时间"""
    return _parse_datetime(activity.get(ACTIVITY_COL_CLOSED_AT, ''))


def get_activity_state(activity):
    """获取活动状态"""
    if not activity:
        return "未开始"
    if activity_is_closed(activity):
        return "已结项"
    end_at = get_activity_end_datetime(activity)
    if end_at and _now() > end_at:
        return "待结项"
    return "进行中"


def get_activity_end_datetime(activity):
    """获取活动结束时间"""
    date_str = _safe_text(activity.get(ACTIVITY_COL_DATE, ''))
    time_str = _safe_text(activity.get(ACTIVITY_COL_TIME, ''))
    if not date_str or not time_str:
        return None
    try:
        # 解析时间范围如 "14:00-15:00"
        time_parts = time_str.split('-')
        if len(time_parts) >= 2:
            end_time = time_parts[-1].strip()
            return datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")
    except (ValueError, IndexError):
        pass
    return None


def get_activity_signups(activity_id, role=None):
    """获取活动的报名列表"""
    signups = db.list_rows(SIGNUP_TABLE_NAME)
    result = []
    for signup in signups:
        if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')) == activity_id:
            if role is None or signup.get(SIGNUP_COL_ROLE) == role:
                result.append(signup)
    return result


def count_signups_by_activity(activity_id, role=None):
    """统计活动的报名人数"""
    return len(get_activity_signups(activity_id, role))


def get_signup_stats(activity_id):
    """获取活动报名统计"""
    signups = get_activity_signups(activity_id)
    reviewers = [s for s in signups if s.get(SIGNUP_COL_ROLE) == '评议员']
    listeners = [s for s in signups if s.get(SIGNUP_COL_ROLE) == '旁听']

    return {
        'reviewers': len(reviewers),
        'listeners': len(listeners),
        'reviewer_limit': REVIEWER_LIMIT,
        'reviewer_remaining': max(0, REVIEWER_LIMIT - len(reviewers)),
        'reviewer_full': len(reviewers) >= REVIEWER_LIMIT,
    }


def create_activity(data):
    """创建活动"""
    required_fields = ['date', 'time', 'speakers', 'topic', 'creator_name']
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"{field} 不能为空")

    row_data = {
        ACTIVITY_COL_DATE: data['date'],
        ACTIVITY_COL_TIME: data['time'],
        ACTIVITY_COL_SPEAKERS: data['speakers'],
        ACTIVITY_COL_TOPIC: data['topic'],
        ACTIVITY_COL_CREATOR_NAME: data['creator_name'],
        ACTIVITY_COL_CREATOR_EMAIL: data.get('creator_email', ''),
        ACTIVITY_COL_CLASSROOM: data.get('classroom', ''),
        ACTIVITY_COL_VIDEOURL: data.get('videourl', ''),
        ACTIVITY_COL_TYPE: data.get('activity_type', 'normal'),
        ACTIVITY_COL_GROUP_ID: data.get('group_id', ''),
        ACTIVITY_COL_GROUP_NAME: data.get('group_name', ''),
        ACTIVITY_COL_STATUS: '进行中',
        ACTIVITY_COL_EXPECTED_ATTENDANCE: data.get('expected_attendance', 0),
    }

    row_id = db.append_row(ACTIVITY_TABLE_NAME, row_data)
    return row_id


def update_activity(activity_id, data, creator_name=None):
    """更新活动"""
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("活动不存在")

    if creator_name and get_activity_creator_name(activity) != creator_name:
        raise ValidationError("只有活动创建者才能修改")

    update_data = {}
    for key, env_key in [
        ('date', ACTIVITY_COL_DATE),
        ('time', ACTIVITY_COL_TIME),
        ('speakers', ACTIVITY_COL_SPEAKERS),
        ('topic', ACTIVITY_COL_TOPIC),
        ('classroom', ACTIVITY_COL_CLASSROOM),
        ('videourl', ACTIVITY_COL_VIDEOURL),
        ('group_id', ACTIVITY_COL_GROUP_ID),
        ('group_name', ACTIVITY_COL_GROUP_NAME),
        ('expected_attendance', ACTIVITY_COL_EXPECTED_ATTENDANCE),
    ]:
        if key in data:
            update_data[env_key] = data[key]

    if update_data:
        db.update_row(ACTIVITY_TABLE_NAME, activity_id, {**activity, **update_data})
    return True


def delete_activity(activity_id, creator_name=None):
    """删除活动"""
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("活动不存在")

    if creator_name and get_activity_creator_name(activity) != creator_name:
        raise ValidationError("只有活动创建者才能删除")

    # 检查是否有报名
    signup_count = count_signups_by_activity(activity_id)
    if signup_count > 0:
        # 删除所有报名
        signups = get_activity_signups(activity_id)
        for signup in signups:
            db.delete_row(SIGNUP_TABLE_NAME, signup.get('_id'))

    return db.delete_row(ACTIVITY_TABLE_NAME, activity_id)


def close_activity(activity_id, closer_name):
    """结项活动"""
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise NotFoundError("活动不存在")

    if activity_is_closed(activity):
        raise ValidationError("活动已经结项")

    closed_at = datetime.now()
    end_at = get_activity_end_datetime(activity)
    on_time = end_at and closed_at <= end_at + timedelta(minutes=ACTIVITY_CLOSE_GRACE_MINUTES)

    update_data = {
        ACTIVITY_COL_STATUS: '已结项',
        ACTIVITY_COL_CLOSED_AT: closed_at.strftime('%Y-%m-%d %H:%M:%S'),
        ACTIVITY_COL_ON_TIME: 'true' if on_time else 'false',
        ACTIVITY_COL_CLOSER_NAME: closer_name,
    }

    return db.update_row(ACTIVITY_TABLE_NAME, activity_id, {**activity, **update_data})


# ===== 辅助函数 =====

def _safe_text(value):
    """安全获取文本"""
    if value is None:
        return ''
    return str(value).strip()


def _safe_bool(value):
    """安全获取布尔值"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes')


def _parse_datetime(dt_str):
    """解析日期时间"""
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d')
        except ValueError:
            return None


def _now():
    """获取当前时间"""
    return datetime.now()
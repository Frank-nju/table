"""
兴趣组服务模块

封装兴趣组相关的业务逻辑
"""

import uuid
from datetime import datetime

from config import (
    INTEREST_GROUP_TABLE_NAME, GROUP_MEMBER_TABLE_NAME,
    GROUP_COL_NAME, GROUP_COL_LEADER_NAME, GROUP_COL_TOPIC_GOAL,
    GROUP_COL_TIME_BOUNDARY, GROUP_COL_EXECUTION_PLAN, GROUP_COL_DESCRIPTION,
    GROUP_COL_STATUS, GROUP_COL_CREATED_AT,
    GROUP_MEMBER_COL_GROUP_ID, GROUP_MEMBER_COL_GROUP_NAME,
    GROUP_MEMBER_COL_MEMBER_NAME, GROUP_MEMBER_COL_MEMBER_EMAIL,
    GROUP_MEMBER_COL_MEMBER_ROLE, GROUP_MEMBER_COL_JOINED_AT
)
from models import db
from utils import ValidationError, NotFoundError


def list_interest_groups():
    """获取所有兴趣组"""
    return db.list_rows(INTEREST_GROUP_TABLE_NAME)


def get_interest_group_by_id(group_id):
    """根据ID获取兴趣组"""
    if not group_id:
        return None
    groups = list_interest_groups()
    for group in groups:
        if str(group.get('_id')) == group_id:
            return group
    return None


def list_group_members():
    """获取所有兴趣组成员"""
    return db.list_rows(GROUP_MEMBER_TABLE_NAME)


def get_group_members(group_id):
    """获取指定兴趣组的成员列表"""
    members = list_group_members()
    return [m for m in members if str(m.get(GROUP_MEMBER_COL_GROUP_ID, '')) == group_id]


def serialize_interest_group(group):
    """序列化兴趣组"""
    if not group:
        return None
    group_id = str(group.get('_id', ''))
    members = get_group_members(group_id)

    return {
        'id': group_id,
        'name': _safe_text(group.get(GROUP_COL_NAME, '')),
        'leader_name': _safe_text(group.get(GROUP_COL_LEADER_NAME, '')),
        'topic_goal': _safe_text(group.get(GROUP_COL_TOPIC_GOAL, '')),
        'time_boundary': _safe_text(group.get(GROUP_COL_TIME_BOUNDARY, '')),
        'execution_plan': _safe_text(group.get(GROUP_COL_EXECUTION_PLAN, '')),
        'description': _safe_text(group.get(GROUP_COL_DESCRIPTION, '')),
        'status': _safe_text(group.get(GROUP_COL_STATUS, '活跃')),
        'created_at': group.get(GROUP_COL_CREATED_AT, ''),
        'members': [{
            'name': _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')),
            'email': _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_EMAIL, '')),
            'role': _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_ROLE, '组员')),
            'joined_at': m.get(GROUP_MEMBER_COL_JOINED_AT, ''),
        } for m in members],
    }


def get_group_ids_for_member(name):
    """获取用户加入的兴趣组ID列表"""
    members = list_group_members()
    return [m.get(GROUP_MEMBER_COL_GROUP_ID, '') for m in members
            if _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == name]


def create_group(data):
    """创建兴趣组"""
    group_name = _safe_text(data.get('name', ''))
    leader_name = _safe_text(data.get('leader_name', ''))
    leader_email = _safe_text(data.get('leader_email', ''))
    topic_goal = _safe_text(data.get('topic_goal', ''))
    time_boundary = _safe_text(data.get('time_boundary', ''))
    execution_plan = _safe_text(data.get('execution_plan', ''))
    description = _safe_text(data.get('description', ''))
    member_names = data.get('member_names', []) or []

    # 兼容前端传 members 字符串的情况
    members_str = _safe_text(data.get('members', ''))
    if members_str and not member_names:
        member_names = [m.strip() for m in members_str.replace('，', ',').split(',') if m.strip()]

    if not group_name or not leader_name or not topic_goal or not time_boundary or not execution_plan:
        raise ValidationError("请完整填写组名、组长、主题目标、时间边界、执行方案")

    # 规范化成员列表
    normalized_members = []
    for item in member_names:
        member_name = _safe_text(item)
        if member_name:
            normalized_members.append(member_name)
    if leader_name not in normalized_members:
        normalized_members.append(leader_name)
    normalized_members = sorted(set(normalized_members))

    if len(normalized_members) < 2:
        raise ValidationError("兴趣组创建条件至少 2 人（含组长）")

    # 创建兴趣组
    row_data = {
        GROUP_COL_NAME: group_name,
        GROUP_COL_LEADER_NAME: leader_name,
        GROUP_COL_TOPIC_GOAL: topic_goal,
        GROUP_COL_TIME_BOUNDARY: time_boundary,
        GROUP_COL_EXECUTION_PLAN: execution_plan,
        GROUP_COL_DESCRIPTION: description,
        GROUP_COL_STATUS: '活跃',
        GROUP_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    group = db.append_row(INTEREST_GROUP_TABLE_NAME, row_data)
    group_id = str(group.get('_id', ''))

    # 添加成员
    for member_name in normalized_members:
        role = '组长' if member_name == leader_name else '组员'
        db.append_row(GROUP_MEMBER_TABLE_NAME, {
            GROUP_MEMBER_COL_GROUP_ID: group_id,
            GROUP_MEMBER_COL_GROUP_NAME: group_name,
            GROUP_MEMBER_COL_MEMBER_NAME: member_name,
            GROUP_MEMBER_COL_MEMBER_EMAIL: '',
            GROUP_MEMBER_COL_MEMBER_ROLE: role,
            GROUP_MEMBER_COL_JOINED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

    return serialize_interest_group(get_interest_group_by_id(group_id))


def join_group(group_id, member_name, member_email=''):
    """加入兴趣组"""
    group = get_interest_group_by_id(group_id)
    if not group:
        raise NotFoundError("兴趣组不存在")

    # 检查是否已加入
    members = get_group_members(group_id)
    for m in members:
        if _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            raise ValidationError("您已加入该兴趣组")

    db.append_row(GROUP_MEMBER_TABLE_NAME, {
        GROUP_MEMBER_COL_GROUP_ID: group_id,
        GROUP_MEMBER_COL_GROUP_NAME: _safe_text(group.get(GROUP_COL_NAME, '')),
        GROUP_MEMBER_COL_MEMBER_NAME: member_name,
        GROUP_MEMBER_COL_MEMBER_EMAIL: member_email,
        GROUP_MEMBER_COL_MEMBER_ROLE: '组员',
        GROUP_MEMBER_COL_JOINED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })

    return serialize_interest_group(get_interest_group_by_id(group_id))


def leave_group(group_id, member_name):
    """退出兴趣组"""
    group = get_interest_group_by_id(group_id)
    if not group:
        raise NotFoundError("兴趣组不存在")

    members = get_group_members(group_id)
    for m in members:
        if _safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            db.delete_row(GROUP_MEMBER_TABLE_NAME, m.get('_id'))
            return True

    raise NotFoundError("您未加入该兴趣组")


# ===== 辅助函数 =====

def _safe_text(value):
    """安全获取文本"""
    if value is None:
        return ''
    return str(value).strip()
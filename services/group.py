"""Interest group service.
Encapsulates interest group business logic."""

import uuid
from datetime import datetime

from config import (
    INTEREST_GROUP_TABLE_NAME, GROUP_MEMBER_TABLE_NAME,
    GROUP_COL_NAME, GROUP_COL_LEADER_NAME, GROUP_COL_TOPIC_GOAL,
    GROUP_COL_TIME_BOUNDARY, GROUP_COL_EXECUTION_PLAN, GROUP_COL_DESCRIPTION,
    GROUP_COL_STATUS, GROUP_COL_CREATED_AT,
    GROUP_MEMBER_COL_GROUP_ID, GROUP_MEMBER_COL_GROUP_NAME,
    GROUP_MEMBER_COL_MEMBER_NAME, GROUP_MEMBER_COL_MEMBER_EMAIL,
    GROUP_MEMBER_COL_MEMBER_ROLE, GROUP_MEMBER_COL_JOINED_AT,
    TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError, safe_text
from utils.versioned_cache import cached_build, touch_version


def list_interest_groups():
    """List all interest groups using the versioned cache."""
    return cached_build(
        'interest_groups',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(INTEREST_GROUP_TABLE_NAME) or [],
    )


def get_interest_group_by_id(group_id):
    """Get an interest group by ID."""
    if not group_id:
        return None
    groups = list_interest_groups()
    for group in groups:
        if str(group.get('_id')) == group_id:
            return group
    return None


def list_group_members():
    """List all interest group members using the versioned cache."""
    return cached_build(
        'group_members',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(GROUP_MEMBER_TABLE_NAME) or [],
    )


def get_group_members(group_id):
    """List members of a specific interest group."""
    members = list_group_members()
    return [m for m in members if str(m.get(GROUP_MEMBER_COL_GROUP_ID, '')) == group_id]


def serialize_interest_group(group):
    """Serialize an interest group."""
    if not group:
        return None
    group_id = str(group.get('_id', ''))
    members = get_group_members(group_id)

    return {
        'id': group_id,
        'name': safe_text(group.get(GROUP_COL_NAME, '')),
        'leader_name': safe_text(group.get(GROUP_COL_LEADER_NAME, '')),
        'topic_goal': safe_text(group.get(GROUP_COL_TOPIC_GOAL, '')),
        'time_boundary': safe_text(group.get(GROUP_COL_TIME_BOUNDARY, '')),
        'execution_plan': safe_text(group.get(GROUP_COL_EXECUTION_PLAN, '')),
        'description': safe_text(group.get(GROUP_COL_DESCRIPTION, '')),
        'status': safe_text(group.get(GROUP_COL_STATUS, '活跃')),
        'created_at': group.get(GROUP_COL_CREATED_AT, ''),
        'members': [{
            'name': safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')),
            'email': safe_text(m.get(GROUP_MEMBER_COL_MEMBER_EMAIL, '')),
            'role': safe_text(m.get(GROUP_MEMBER_COL_MEMBER_ROLE, '组员')),
            'joined_at': m.get(GROUP_MEMBER_COL_JOINED_AT, ''),
        } for m in members],
    }


def get_group_ids_for_member(name):
    """List the interest group IDs for a user."""
    members = list_group_members()
    return [m.get(GROUP_MEMBER_COL_GROUP_ID, '') for m in members
            if safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == name]


def create_group(data):
    """Create an interest group."""
    group_name = safe_text(data.get('name', ''))
    leader_name = safe_text(data.get('leader_name', ''))
    leader_email = safe_text(data.get('leader_email', ''))
    topic_goal = safe_text(data.get('topic_goal', ''))
    time_boundary = safe_text(data.get('time_boundary', ''))
    execution_plan = safe_text(data.get('execution_plan', ''))
    description = safe_text(data.get('description', ''))
    member_names = data.get('member_names', []) or []

    # Accept a members string from the frontend for compatibility
    members_str = safe_text(data.get('members', ''))
    if members_str and not member_names:
        member_names = [m.strip() for m in members_str.replace('，', ',').split(',') if m.strip()]

    if not group_name or not leader_name or not topic_goal or not time_boundary or not execution_plan:
        raise ValidationError("Complete the group name, leader, goal, time boundaries, and execution plan")

    # Normalize the member list
    normalized_members = []
    for item in member_names:
        member_name = safe_text(item)
        if member_name:
            normalized_members.append(member_name)
    if leader_name not in normalized_members:
        normalized_members.append(leader_name)
    normalized_members = sorted(set(normalized_members))

    if len(normalized_members) < 2:
        raise ValidationError("An interest group must have at least two members, including its leader")

    # Create the interest group.
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

    # Add the member to the group.
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

    touch_version()
    return serialize_interest_group(get_interest_group_by_id(group_id))


def join_group(group_id, member_name, member_email=''):
    """Join an interest group."""
    group = get_interest_group_by_id(group_id)
    if not group:
        raise NotFoundError("Interest group not found")

    # Check whether the user has already joined.
    members = get_group_members(group_id)
    for m in members:
        if safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            raise ValidationError("You have already joined this interest group")

    db.append_row(GROUP_MEMBER_TABLE_NAME, {
        GROUP_MEMBER_COL_GROUP_ID: group_id,
        GROUP_MEMBER_COL_GROUP_NAME: safe_text(group.get(GROUP_COL_NAME, '')),
        GROUP_MEMBER_COL_MEMBER_NAME: member_name,
        GROUP_MEMBER_COL_MEMBER_EMAIL: member_email,
        GROUP_MEMBER_COL_MEMBER_ROLE: '组员',
        GROUP_MEMBER_COL_JOINED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    touch_version()

    return serialize_interest_group(get_interest_group_by_id(group_id))


def leave_group(group_id, member_name):
    """Leave an interest group."""
    group = get_interest_group_by_id(group_id)
    if not group:
        raise NotFoundError("Interest group not found")

    members = get_group_members(group_id)
    for m in members:
        if safe_text(m.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            db.delete_row(GROUP_MEMBER_TABLE_NAME, m.get('_id'))
            touch_version()
            return True

    raise NotFoundError("You are not a member of this interest group")


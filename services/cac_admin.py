"""
CAC 管理服务模块

封装 CAC 管理员和教室时间槽相关的业务逻辑
"""

import uuid
from datetime import datetime

from config import (
    CAC_ADMINS_TABLE_NAME, CAC_ROOM_SLOTS_TABLE_NAME,
    CAC_ADMIN_COL_NAME, CAC_ADMIN_COL_CREATED_AT,
    CAC_SLOT_COL_DATE, CAC_SLOT_COL_TIME_SLOT, CAC_SLOT_COL_CLASSROOM,
    CAC_SLOT_COL_STATUS, CAC_SLOT_COL_ACTIVITY_ID, CAC_SLOT_COL_CREATED_BY,
    CAC_SLOT_COL_CREATED_AT, CAC_NAME
)
from models import db
from utils import ValidationError, NotFoundError, AuthError


# ===== 管理员服务 =====

def list_cac_admins():
    """获取CAC管理员列表"""
    rows = db.list_rows(CAC_ADMINS_TABLE_NAME)
    return [{'name': str(row.get(CAC_ADMIN_COL_NAME, '')).strip()} for row in rows]


def is_cac_admin(name):
    """检查是否是CAC管理员"""
    admins = list_cac_admins()
    return any(a['name'] == name for a in admins)


def is_cac_user(name):
    """检查是否是CAC系统用户"""
    text = str(name).strip().lower() if name else ''
    return text == str(CAC_NAME).strip().lower() or text == "cac"


def add_cac_admin(name, requester_name=None):
    """添加CAC管理员"""
    if not name:
        raise ValidationError("姓名不能为空")

    # 检查权限：已有管理员或首次初始化
    existing_admins = list_cac_admins()
    if existing_admins and requester_name and not is_cac_admin(requester_name):
        raise AuthError("只有管理员才能添加新管理员")

    # 检查是否已存在
    if is_cac_admin(name):
        raise ValidationError("该用户已是管理员")

    row_id = db.append_row(CAC_ADMINS_TABLE_NAME, {
        CAC_ADMIN_COL_NAME: name,
        CAC_ADMIN_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    return row_id


def remove_cac_admin(name, requester_name):
    """删除CAC管理员"""
    if not requester_name:
        raise ValidationError("缺少请求者姓名")

    if not is_cac_admin(requester_name):
        raise AuthError("只有管理员才能删除管理员")

    rows = db.list_rows(CAC_ADMINS_TABLE_NAME)
    for row in rows:
        if str(row.get(CAC_ADMIN_COL_NAME, '')).strip() == name:
            db.delete_row(CAC_ADMINS_TABLE_NAME, row.get('_id'))
            return True

    raise NotFoundError("该用户不是管理员")


# ===== 教室时间槽服务 =====

def list_cac_room_slots(date=None, time_slot=None):
    """获取CAC教室时间槽列表

    time_slot 可以是单个时间段如 '14:00-14:30' 或合并后的如 '14:00-15:30'
    当是合并后的时间段时，返回在该时间段内所有半小时槽都可用的教室
    """
    rows = db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME)

    # 解析需要的半小时槽列表
    required_slots = []
    if time_slot:
        for ts in time_slot.split(','):
            ts = ts.strip()
            if not ts:
                continue
            parts = ts.split('-')
            if len(parts) != 2:
                continue
            start, end = parts[0], parts[1]
            start_parts = start.split(':')
            end_parts = end.split(':')
            if len(start_parts) != 2 or len(end_parts) != 2:
                continue
            start_h, start_m = int(start_parts[0]), int(start_parts[1])
            end_h, end_m = int(end_parts[0]), int(end_parts[1])
            current_h, current_m = start_h, start_m
            while current_h * 60 + current_m < end_h * 60 + end_m:
                next_h, next_m = current_h, current_m + 30
                if next_m >= 60:
                    next_h += 1
                    next_m -= 60
                required_slots.append(f"{current_h:02d}:{current_m:02d}-{next_h:02d}:{next_m:02d}")
                current_h, current_m = next_h, next_m

    result = []
    for row in rows:
        slot_date = str(row.get(CAC_SLOT_COL_DATE, '')).strip()
        slot_time = str(row.get(CAC_SLOT_COL_TIME_SLOT, '')).strip()
        slot_classroom = str(row.get(CAC_SLOT_COL_CLASSROOM, '')).strip()
        slot_status = str(row.get(CAC_SLOT_COL_STATUS, 'available')).strip()

        # 日期过滤
        if date and slot_date != date:
            continue

        # 时间段过滤
        if required_slots and slot_time not in required_slots:
            continue

        # 状态过滤（只返回可用的）
        if slot_status != 'available':
            continue

        result.append({
            'id': row.get('_id'),
            'date': slot_date,
            'time_slot': slot_time,
            'classroom': slot_classroom,
            'status': slot_status,
        })

    # 如果需要合并时间段，按教室分组
    if time_slot and required_slots:
        # 找出在所有需要的时间槽都可用的教室
        classroom_slots = {}
        for slot in result:
            classroom = slot['classroom']
            if classroom not in classroom_slots:
                classroom_slots[classroom] = []
            classroom_slots[classroom].append(slot['time_slot'])

        # 检查每个教室是否覆盖所有需要的时间槽
        available_classrooms = []
        for classroom, slots in classroom_slots.items():
            if all(req in slots for req in required_slots):
                available_classrooms.append(classroom)

        return list(set(available_classrooms))

    return result


def add_cac_room_slot(date, time_slot, classroom, requester_name):
    """添加教室时间槽"""
    if not date or not time_slot or not classroom:
        raise ValidationError("日期、时间段和教室不能为空")

    if not is_cac_admin(requester_name):
        raise AuthError("只有管理员才能添加教室时间槽")

    # 检查是否已存在相同的时间槽
    rows = db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if (str(row.get(CAC_SLOT_COL_DATE, '')).strip() == date and
            str(row.get(CAC_SLOT_COL_TIME_SLOT, '')).strip() == time_slot and
            str(row.get(CAC_SLOT_COL_CLASSROOM, '')).strip() == classroom):
            raise ValidationError("该时间槽已存在")

    row_id = db.append_row(CAC_ROOM_SLOTS_TABLE_NAME, {
        CAC_SLOT_COL_DATE: date,
        CAC_SLOT_COL_TIME_SLOT: time_slot,
        CAC_SLOT_COL_CLASSROOM: classroom,
        CAC_SLOT_COL_STATUS: 'available',
        CAC_SLOT_COL_ACTIVITY_ID: '',
        CAC_SLOT_COL_CREATED_BY: requester_name,
        CAC_SLOT_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    return row_id


def remove_cac_room_slot(slot_id, requester_name):
    """删除教室时间槽"""
    if not is_cac_admin(requester_name):
        raise AuthError("只有管理员才能删除教室时间槽")

    rows = db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if row.get('_id') == slot_id:
            db.delete_row(CAC_ROOM_SLOTS_TABLE_NAME, slot_id)
            return True

    raise NotFoundError("时间槽不存在")
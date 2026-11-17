"""CAC administration service.
Encapsulates CAC administration and room-slot logic."""

import uuid
from datetime import datetime

from config import (
    CAC_ADMINS_TABLE_NAME, CAC_ROOM_SLOTS_TABLE_NAME,
    CAC_ADMIN_COL_NAME, CAC_ADMIN_COL_CREATED_AT,
    CAC_SLOT_COL_DATE, CAC_SLOT_COL_TIME_SLOT, CAC_SLOT_COL_CLASSROOM,
    CAC_SLOT_COL_STATUS, CAC_SLOT_COL_ACTIVITY_ID, CAC_SLOT_COL_CREATED_BY,
    CAC_SLOT_COL_CREATED_AT, CAC_NAME,
    TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError, AuthError
from utils.versioned_cache import cached_build, touch_version


# ===== Administrator service =====

def list_cac_admins():
    """List CAC administrators using the versioned cache."""
    return cached_build(
        'cac_admins',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(CAC_ADMINS_TABLE_NAME) or [],
    )


def is_cac_admin(name):
    """Check whether a user is a CAC administrator."""
    admins = list_cac_admins()
    return any(a['name'] == name for a in admins)


def is_cac_user(name):
    """Check whether a user is a CAC system user."""
    text = str(name).strip().lower() if name else ''
    return text == str(CAC_NAME).strip().lower() or text == "cac"


def add_cac_admin(name, requester_name=None):
    """Add a CAC administrator."""
    if not name:
        raise ValidationError("Name is required")

    # Allow existing administrators or the initial setup user.
    existing_admins = list_cac_admins()
    if existing_admins and requester_name and not is_cac_admin(requester_name):
        raise AuthError("Only an administrator can add another administrator")

    # Check whether the record already exists.
    if is_cac_admin(name):
        raise ValidationError("This user is already an administrator")

    result = db.append_row(CAC_ADMINS_TABLE_NAME, {
        CAC_ADMIN_COL_NAME: name,
        CAC_ADMIN_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    touch_version()
    return str(result.get('_id', ''))


def remove_cac_admin(name, requester_name):
    """Remove a CAC administrator."""
    if not requester_name:
        raise ValidationError("The requester's name is required")

    if not is_cac_admin(requester_name):
        raise AuthError("Only an administrator can remove an administrator")

    rows = db.list_rows(CAC_ADMINS_TABLE_NAME)
    for row in rows:
        if str(row.get(CAC_ADMIN_COL_NAME, '')).strip() == name:
            db.delete_row(CAC_ADMINS_TABLE_NAME, row.get('_id'))
            touch_version()
            return True

    raise NotFoundError("This user is not an administrator")


# ===== Room time-slot service =====

def list_cac_room_slots(date=None, time_slot=None):
    """List CAC room slots.
A time_slot may be a single interval such as '14:00-14:30' or a merged interval such as '14:00-15:30'.
For merged intervals, return rooms available for every 30-minute slot in the range."""
    rows = cached_build(
        'cac_room_slots',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME) or [],
    )

    # Parse the required 30-minute time slots
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

        # Filter by date
        if date and slot_date != date:
            continue

        # time rangefilter
        if required_slots and slot_time not in required_slots:
            continue

        # Filter by status; return available slots only
        if slot_status != 'available':
            continue

        result.append({
            'id': row.get('_id'),
            'date': slot_date,
            'time_slot': slot_time,
            'classroom': slot_classroom,
            'status': slot_status,
        })

    # When merging time ranges, group slots by room
    if time_slot and required_slots:
        # Find rooms available for every required time slot
        classroom_slots = {}
        for slot in result:
            classroom = slot['classroom']
            if classroom not in classroom_slots:
                classroom_slots[classroom] = []
            classroom_slots[classroom].append(slot['time_slot'])

        # Check that each room covers every required time slot
        available_classrooms = []
        for classroom, slots in classroom_slots.items():
            if all(req in slots for req in required_slots):
                available_classrooms.append(classroom)

        return list(set(available_classrooms))

    return result


def add_cac_room_slot(date, time_slot, classroom, requester_name):
    """addroomtime slot"""
    if not date or not time_slot or not classroom:
        raise ValidationError("Date, time slot, and room are required")

    if not is_cac_admin(requester_name):
        raise AuthError("Only an administrator can add room slots")

    # Check whether this time slot already exists
    rows = db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if (str(row.get(CAC_SLOT_COL_DATE, '')).strip() == date and
            str(row.get(CAC_SLOT_COL_TIME_SLOT, '')).strip() == time_slot and
            str(row.get(CAC_SLOT_COL_CLASSROOM, '')).strip() == classroom):
            raise ValidationError("This room slot already exists")

    result = db.append_row(CAC_ROOM_SLOTS_TABLE_NAME, {
        CAC_SLOT_COL_DATE: date,
        CAC_SLOT_COL_TIME_SLOT: time_slot,
        CAC_SLOT_COL_CLASSROOM: classroom,
        CAC_SLOT_COL_STATUS: 'available',
        CAC_SLOT_COL_ACTIVITY_ID: '',
        CAC_SLOT_COL_CREATED_BY: requester_name,
        CAC_SLOT_COL_CREATED_AT: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    touch_version()
    return str(result.get('_id', ''))


def remove_cac_room_slot(slot_id, requester_name):
    """Delete a room time slot."""
    if not is_cac_admin(requester_name):
        raise AuthError("Only an administrator can delete room slots")

    rows = db.list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if row.get('_id') == slot_id:
            db.delete_row(CAC_ROOM_SLOTS_TABLE_NAME, slot_id)
            touch_version()
            return True

    raise NotFoundError("Room slot not found")
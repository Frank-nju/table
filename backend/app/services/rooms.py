"""Rooms, their bookable time slots and availability lookups."""

from __future__ import annotations

from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import BadRequest, Conflict, NotFound
from app.models import Activity, ActivityKind, Room, RoomSlot, User
from app.scheduling import Window, is_covered, on_grid, overlaps
from app.schemas import RoomAvailability, RoomIn, RoomOut, RoomSlotIn, UserBrief


def get(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise NotFound("Room not found.", code="room_not_found")
    return room


def list_rooms(db: Session, include_inactive: bool = False) -> list[Room]:
    stmt = select(Room).order_by(Room.name)
    if not include_inactive:
        stmt = stmt.where(Room.is_active)
    return list(db.scalars(stmt))


def _check_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    other = db.scalar(select(Room).where(func.lower(Room.name) == name.lower()))
    if other is not None and other.id != exclude_id:
        raise Conflict("A room with this name already exists.", code="room_name_taken")


def create(db: Session, data: RoomIn) -> Room:
    _check_name(db, data.name)
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    return room


def update(db: Session, room_id: int, data: RoomIn) -> Room:
    room = get(db, room_id)
    _check_name(db, data.name, exclude_id=room.id)
    for field, value in data.model_dump().items():
        setattr(room, field, value)
    db.commit()
    return room


def delete(db: Session, room_id: int) -> None:
    room = get(db, room_id)
    in_use = db.scalar(select(func.count()).where(Activity.room_id == room.id))
    if in_use:
        # Keep history intact; retire the room instead.
        room.is_active = False
    else:
        db.delete(room)
    try:
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - defensive
        db.rollback()
        raise Conflict("This room is still in use.", code="room_in_use") from exc


def list_slots(db: Session, date_from: date, date_to: date, room_id: int | None = None) -> list[RoomSlot]:
    stmt = (
        select(RoomSlot)
        .where(RoomSlot.date >= date_from, RoomSlot.date <= date_to)
        .order_by(RoomSlot.date, RoomSlot.start_time)
    )
    if room_id:
        stmt = stmt.where(RoomSlot.room_id == room_id)
    return list(db.scalars(stmt))


def add_slots(db: Session, actor: User, data: RoomSlotIn) -> list[RoomSlot]:
    room = get(db, data.room_id)
    if data.start_time >= data.end_time:
        raise BadRequest("The end time must be after the start time.", code="time_order")
    if not (on_grid(data.start_time) and on_grid(data.end_time)):
        raise BadRequest("Slot times must be on the time grid.", code="time_off_grid")
    created: list[RoomSlot] = []
    for week in range(data.repeat_weeks):
        d = data.date + timedelta(weeks=week)
        existing = db.scalars(select(RoomSlot).where(RoomSlot.room_id == room.id, RoomSlot.date == d)).all()
        if any(overlaps(data.start_time, data.end_time, s.start_time, s.end_time) for s in existing):
            continue  # already open at (part of) this time; skip rather than duplicate
        slot = RoomSlot(
            room_id=room.id, date=d, start_time=data.start_time, end_time=data.end_time, created_by_id=actor.id
        )
        db.add(slot)
        created.append(slot)
    if not created:
        raise Conflict("These slots already exist.", code="slot_exists")
    db.commit()
    return created


def delete_slot(db: Session, slot_id: int) -> None:
    slot = db.get(RoomSlot, slot_id)
    if slot is None:
        raise NotFound("Slot not found.", code="slot_not_found")
    db.delete(slot)
    db.commit()


def availability(
    db: Session, d: date, start: time, end: time, kind: ActivityKind, exclude_activity_id: int | None = None
) -> list[RoomAvailability]:
    rooms = list_rooms(db)
    slots: dict[int, list[Window]] = {}
    for s in db.scalars(select(RoomSlot).where(RoomSlot.date == d)):
        slots.setdefault(s.room_id, []).append(Window(s.start_time, s.end_time))
    bookings = [
        a
        for a in db.scalars(select(Activity).where(Activity.date == d, Activity.room_id.is_not(None)))
        if a.id != exclude_activity_id and overlaps(start, end, a.start_time, a.end_time)
    ]
    result = []
    for room in rooms:
        entry = RoomAvailability(room=RoomOut.model_validate(room), available=True)
        if not is_covered(start, end, slots.get(room.id, [])):
            entry.available, entry.reason = False, "no_slot"
        else:
            booking = next((b for b in bookings if b.room_id == room.id), None)
            if booking is not None:
                entry.available = booking.kind != kind
                entry.reason = "booked" if booking.kind == kind else "shared"
                entry.booked_by = UserBrief(id=booking.organizer.id, name=booking.organizer.name)
                entry.booked_activity_title = booking.title
        result.append(entry)
    result.sort(key=lambda r: (not r.available, r.reason or "", r.room.name))
    return result

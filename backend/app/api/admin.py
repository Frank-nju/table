"""Administrator-only endpoints."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DB, AdminUser
from app.errors import BadRequest, NotFound
from app.models import Activity, Contribution, Signup
from app.scheduling import local_today
from app.schemas import (
    AdminDashboard,
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    ContributionIn,
    ContributionOut,
    RoomIn,
    RoomOut,
    RoomSlotIn,
    RoomSlotOut,
    UserBrief,
)
from app.services import activities as activity_service
from app.services import rooms as room_service
from app.services import stats
from app.services import users as user_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboard)
def dashboard(
    db: DB, _: AdminUser, month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None
) -> AdminDashboard:
    today = local_today()
    year, mon = (int(month[:4]), int(month[5:])) if month else (today.year, today.month)
    if not 1 <= mon <= 12:
        raise BadRequest("Invalid month.", code="invalid_month")
    return stats.admin_dashboard(db, year, mon)


# ----- Users -----


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: DB, _: AdminUser, q: str = "") -> list[AdminUserOut]:
    return [AdminUserOut.model_validate(u) for u in user_service.admin_list(db, q)]


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(data: AdminUserCreate, db: DB, _: AdminUser) -> AdminUserOut:
    return AdminUserOut.model_validate(user_service.admin_create(db, data))


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, data: AdminUserUpdate, db: DB, admin: AdminUser) -> AdminUserOut:
    user = user_service.get_user(db, user_id, active_only=False)
    return AdminUserOut.model_validate(user_service.admin_update(db, admin, user, data))


@router.post("/users/{user_id}/password-link")
def password_link(user_id: int, db: DB, _: AdminUser) -> dict[str, str]:
    """A one-off link the admin can pass on to someone who has no email on file."""
    return {"link": user_service.password_link(user_service.get_user(db, user_id))}


# ----- Rooms -----


@router.get("/rooms", response_model=list[RoomOut])
def all_rooms(db: DB, _: AdminUser) -> list[RoomOut]:
    return [RoomOut.model_validate(r) for r in room_service.list_rooms(db, include_inactive=True)]


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(data: RoomIn, db: DB, _: AdminUser) -> RoomOut:
    return RoomOut.model_validate(room_service.create(db, data))


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, data: RoomIn, db: DB, _: AdminUser) -> RoomOut:
    return RoomOut.model_validate(room_service.update(db, room_id, data))


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: DB, _: AdminUser) -> Response:
    room_service.delete(db, room_id)
    return Response(status_code=204)


@router.post("/room-slots", response_model=list[RoomSlotOut], status_code=201)
def add_slots(data: RoomSlotIn, db: DB, admin: AdminUser) -> list[RoomSlotOut]:
    return [RoomSlotOut.model_validate(s) for s in room_service.add_slots(db, admin, data)]


@router.delete("/room-slots/{slot_id}", status_code=204)
def delete_slot(slot_id: int, db: DB, _: AdminUser) -> Response:
    room_service.delete_slot(db, slot_id)
    return Response(status_code=204)


# ----- Contributions -----


def _contribution_out(c: Contribution) -> ContributionOut:
    return ContributionOut(
        id=c.id,
        user=UserBrief(id=c.user.id, name=c.user.name),
        kind=c.kind,
        date=c.date,
        note=c.note,
        created_at=c.created_at,
    )


@router.get("/contributions", response_model=list[ContributionOut])
def list_contributions(db: DB, _: AdminUser, limit: Annotated[int, Query(le=500)] = 100) -> list[ContributionOut]:
    rows = db.scalars(select(Contribution).order_by(Contribution.date.desc(), Contribution.id.desc()).limit(limit))
    return [_contribution_out(c) for c in rows]


@router.post("/contributions", response_model=ContributionOut, status_code=201)
def add_contribution(data: ContributionIn, db: DB, admin: AdminUser) -> ContributionOut:
    user = user_service.get_user(db, data.user_id)
    c = Contribution(user_id=user.id, kind=data.kind, date=data.date, note=data.note, created_by_id=admin.id)
    db.add(c)
    db.commit()
    return _contribution_out(c)


@router.delete("/contributions/{contribution_id}", status_code=204)
def delete_contribution(contribution_id: int, db: DB, _: AdminUser) -> Response:
    c = db.get(Contribution, contribution_id)
    if c is None:
        raise NotFound("Contribution not found.")
    db.delete(c)
    db.commit()
    return Response(status_code=204)


# ----- Exports -----


def _csv(rows: list[list[object]], filename: str) -> Response:
    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel opens UTF-8 (Chinese names) correctly
    csv.writer(buf).writerows(rows)
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/activities.csv")
def export_activities(db: DB, _: AdminUser, date_from: date | None = None, date_to: date | None = None) -> Response:
    stmt = select(Activity).options(*activity_service.LOAD).order_by(Activity.date, Activity.start_time)
    if date_from:
        stmt = stmt.where(Activity.date >= date_from)
    if date_to:
        stmt = stmt.where(Activity.date <= date_to)
    rows: list[list[object]] = [
        [
            "id",
            "title",
            "kind",
            "date",
            "start",
            "end",
            "room",
            "location",
            "group",
            "organizer",
            "speakers",
            "reviewers",
            "observers",
            "participants",
            "state",
            "closed_at",
            "closed_on_time",
        ]
    ]
    for a in db.scalars(stmt):
        out = activity_service.to_out(a)
        rows.append(
            [
                a.id,
                a.title,
                a.kind.value,
                a.date.isoformat(),
                a.start_time.strftime("%H:%M"),
                a.end_time.strftime("%H:%M"),
                a.room.name if a.room else "",
                a.location,
                a.group.name if a.group else "",
                a.organizer.name,
                ", ".join(s.user.name for s in a.speakers),
                out.counts.reviewers,
                out.counts.observers,
                out.counts.participants,
                out.state.value,
                a.closed_at.isoformat() if a.closed_at else "",
                "" if a.closed_on_time is None else ("yes" if a.closed_on_time else "no"),
            ]
        )
    return _csv(rows, "activities.csv")


@router.get("/export/signups.csv")
def export_signups(db: DB, _: AdminUser, date_from: date | None = None, date_to: date | None = None) -> Response:
    stmt = (
        select(Signup)
        .join(Activity)
        .options(selectinload(Signup.ratings), selectinload(Signup.activity))
        .order_by(Activity.date, Signup.created_at)
    )
    if date_from:
        stmt = stmt.where(Activity.date >= date_from)
    if date_to:
        stmt = stmt.where(Activity.date <= date_to)
    rows: list[list[object]] = [
        [
            "signup_id",
            "activity_id",
            "activity",
            "date",
            "name",
            "email",
            "role",
            "review_topic",
            "review_doc_url",
            "review_submitted_at",
            "average_score",
            "rating_count",
        ]
    ]
    for s in db.scalars(stmt):
        avg = activity_service.weighted_average(s)
        rows.append(
            [
                s.id,
                s.activity_id,
                s.activity.title,
                s.activity.date.isoformat(),
                s.user.name,
                s.user.email or "",
                s.role.value,
                s.review_topic,
                s.review_doc_url,
                s.review_submitted_at.isoformat() if s.review_submitted_at else "",
                "" if avg is None else avg,
                len(s.ratings),
            ]
        )
    return _csv(rows, "signups.csv")

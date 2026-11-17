"""Groups, rooms, people, invitations, leaderboards and the personal dashboard."""

from __future__ import annotations

from datetime import date, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.deps import DB, CurrentUser, OptionalUser
from app.errors import BadRequest
from app.models import ActivityKind
from app.scheduling import local_today
from app.schemas import (
    GroupDetail,
    GroupIn,
    GroupOut,
    GroupUpdate,
    InviteOut,
    InviteStatusIn,
    Leaderboards,
    MeDashboard,
    Overview,
    PublicProfile,
    RoomAvailability,
    RoomOut,
    RoomSlotOut,
    TransferLeadershipIn,
    UserBrief,
)
from app.services import groups as group_service
from app.services import invites as invite_service
from app.services import rooms as room_service
from app.services import stats
from app.services import users as user_service

router = APIRouter()


# ----- Groups -----


@router.get("/groups", response_model=list[GroupOut], tags=["groups"])
def list_groups(db: DB, viewer: OptionalUser, include_archived: bool = False) -> list[GroupOut]:
    return group_service.list_groups(db, viewer, include_archived)


@router.post("/groups", response_model=GroupDetail, status_code=201, tags=["groups"])
def create_group(data: GroupIn, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.create(db, user, data), user)


@router.get("/groups/{group_id}", response_model=GroupDetail, tags=["groups"])
def get_group(group_id: int, db: DB, viewer: OptionalUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.get(db, group_id), viewer)


@router.patch("/groups/{group_id}", response_model=GroupDetail, tags=["groups"])
def update_group(group_id: int, data: GroupUpdate, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.update(db, user, group_id, data), user)


@router.post("/groups/{group_id}/join", response_model=GroupDetail, tags=["groups"])
def join_group(group_id: int, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.join(db, user, group_id), user)


@router.post("/groups/{group_id}/leave", response_model=GroupDetail, tags=["groups"])
def leave_group(group_id: int, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.leave(db, user, group_id), user)


@router.post("/groups/{group_id}/transfer", response_model=GroupDetail, tags=["groups"])
def transfer_group(group_id: int, data: TransferLeadershipIn, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.transfer(db, user, group_id, data.user_id), user)


@router.delete("/groups/{group_id}/members/{user_id}", response_model=GroupDetail, tags=["groups"])
def remove_member(group_id: int, user_id: int, db: DB, user: CurrentUser) -> GroupDetail:
    return group_service.to_detail(db, group_service.remove_member(db, user, group_id, user_id), user)


# ----- Rooms (read-only for members; administration lives in admin.py) -----


@router.get("/rooms", response_model=list[RoomOut], tags=["rooms"])
def list_rooms(db: DB) -> list[RoomOut]:
    return [RoomOut.model_validate(r) for r in room_service.list_rooms(db)]


@router.get("/rooms/availability", response_model=list[RoomAvailability], tags=["rooms"])
def room_availability(
    db: DB,
    _: CurrentUser,
    date: date,
    start_time: time,
    end_time: time,
    kind: ActivityKind = ActivityKind.REGULAR,
    exclude_activity_id: int | None = None,
) -> list[RoomAvailability]:
    if start_time >= end_time:
        raise BadRequest("The end time must be after the start time.", code="time_order")
    return room_service.availability(db, date, start_time, end_time, kind, exclude_activity_id)


@router.get("/rooms/slots", response_model=list[RoomSlotOut], tags=["rooms"])
def room_slots(
    db: DB, date_from: date | None = None, date_to: date | None = None, room_id: int | None = None
) -> list[RoomSlotOut]:
    start = date_from or local_today()
    end = date_to or start + timedelta(days=13)
    if (end - start).days > 92:
        raise BadRequest("Please request at most three months at a time.", code="range_too_large")
    return [RoomSlotOut.model_validate(s) for s in room_service.list_slots(db, start, end, room_id)]


# ----- People -----


@router.get("/users", response_model=list[UserBrief], tags=["users"])
def search_users(
    db: DB, _: CurrentUser, q: Annotated[str, Query(max_length=64)] = "", limit: Annotated[int, Query(le=50)] = 20
) -> list[UserBrief]:
    return [UserBrief(id=u.id, name=u.name) for u in user_service.search(db, q, limit)]


@router.get("/users/{user_id}", response_model=PublicProfile, tags=["users"])
def user_profile(user_id: int, db: DB, viewer: CurrentUser) -> PublicProfile:
    return stats.public_profile(db, user_service.get_user(db, user_id), viewer)


# ----- Me -----


@router.get("/me/dashboard", response_model=MeDashboard, tags=["me"])
def my_dashboard(db: DB, user: CurrentUser) -> MeDashboard:
    return stats.me_dashboard(db, user)


@router.get("/me/invites", response_model=list[InviteOut], tags=["me"])
def my_invites(db: DB, user: CurrentUser) -> list[InviteOut]:
    return [invite_service.to_out(i) for i in invite_service.for_user(db, user)]


@router.get("/me/summary", tags=["me"])
def my_summary(db: DB, user: CurrentUser) -> dict[str, int]:
    """Small payload for the navigation badge."""
    return {"pending_invites": stats.pending_invite_count(db, user)}


@router.post("/invites/{invite_id}/status", response_model=InviteOut, tags=["invites"])
def set_invite_status(invite_id: int, data: InviteStatusIn, db: DB, user: CurrentUser) -> InviteOut:
    return invite_service.to_out(invite_service.set_status(db, user, invite_id, data.status))


# ----- Stats -----


@router.get("/stats/overview", response_model=Overview, tags=["stats"])
def overview(db: DB, response: Response) -> Overview:
    response.headers["Cache-Control"] = "public, max-age=60"
    return stats.overview(db)


@router.get("/stats/leaderboards", response_model=Leaderboards, tags=["stats"])
def leaderboards(db: DB, days: Annotated[int | None, Query(ge=1, le=3650)] = None) -> Leaderboards:
    since = local_today() - timedelta(days=days) if days else None
    return stats.leaderboards(db, since)

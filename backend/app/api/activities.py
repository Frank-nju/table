from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from app.deps import DB, CurrentUser, OptionalUser
from app.errors import Forbidden
from app.ics import activity_calendar
from app.models import ActivityKind
from app.scheduling import ActivityState
from app.schemas import (
    ActivityDetail,
    ActivityIn,
    ActivityPage,
    ActivityUpdate,
    CloseResult,
    InviteIn,
    InviteOut,
    RatingIn,
    ReviewDocIn,
    ReviewToRate,
    ScheduleCheck,
    SignupIn,
    SignupOut,
)
from app.services import activities as service
from app.services import invites as invite_service
from app.services import signups as signup_service

router = APIRouter(tags=["activities"])


@router.get("/activities", response_model=ActivityPage)
def list_activities(
    db: DB,
    viewer: OptionalUser,
    state: Annotated[list[ActivityState] | None, Query()] = None,
    kind: ActivityKind | None = None,
    group_id: int | None = None,
    q: Annotated[str, Query(max_length=100)] = "",
    date_from: date | None = None,
    date_to: date | None = None,
    mine: bool = False,
    order: Literal["asc", "desc"] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ActivityPage:
    involving = None
    if mine:
        if viewer is None:
            raise Forbidden("Sign in to see your activities.", code="not_authenticated")
        involving = viewer.id
    return service.list_activities(
        db,
        viewer,
        states=state,
        kind=kind,
        group_id=group_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        involving=involving,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.post("/activities/check", response_model=ScheduleCheck)
def check_schedule(data: ActivityIn, db: DB, user: CurrentUser, exclude_id: int | None = None) -> ScheduleCheck:
    """Dry-run the scheduling rules so the form can show problems before submitting."""
    if exclude_id is not None:
        service.require_manager(user, service.get_activity(db, exclude_id))
    return service.preview(db, user, data, exclude_id=exclude_id)


@router.post("/activities", response_model=ActivityDetail, status_code=201)
def create_activity(data: ActivityIn, db: DB, user: CurrentUser) -> ActivityDetail:
    return service.to_detail(service.create(db, user, data), user)


@router.get("/activities/{activity_id}", response_model=ActivityDetail)
def get_activity(activity_id: int, db: DB, viewer: OptionalUser) -> ActivityDetail:
    return service.to_detail(service.get_activity(db, activity_id), viewer)


@router.patch("/activities/{activity_id}", response_model=ActivityDetail)
def update_activity(activity_id: int, data: ActivityUpdate, db: DB, user: CurrentUser) -> ActivityDetail:
    return service.to_detail(service.update(db, user, activity_id, data), user)


@router.delete("/activities/{activity_id}", status_code=204)
def delete_activity(activity_id: int, db: DB, user: CurrentUser) -> Response:
    service.delete(db, user, activity_id)
    return Response(status_code=204)


@router.post("/activities/{activity_id}/close", response_model=CloseResult)
def close_activity(activity_id: int, db: DB, user: CurrentUser) -> CloseResult:
    activity, on_time, reminders = service.close(db, user, activity_id)
    return CloseResult(activity=service.to_out(activity, user), on_time=on_time, reminders_sent=reminders)


@router.get("/activities/{activity_id}/calendar.ics")
def activity_ics(activity_id: int, db: DB) -> Response:
    activity = service.get_activity(db, activity_id)
    return Response(
        activity_calendar(activity),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="activity-{activity.id}.ics"'},
    )


# ----- Signups & reviews -----


@router.post("/activities/{activity_id}/signups", response_model=SignupOut, status_code=201)
def sign_up(activity_id: int, data: SignupIn, db: DB, user: CurrentUser, response: Response) -> SignupOut:
    signup, accepted = signup_service.create(db, user, activity_id, data)
    if accepted:
        response.headers["X-Invites-Accepted"] = str(accepted)
    return service.signup_out(signup, user, manager=False)


@router.delete("/signups/{signup_id}", status_code=204)
def cancel_signup(signup_id: int, db: DB, user: CurrentUser) -> Response:
    signup_service.cancel(db, user, signup_id)
    return Response(status_code=204)


@router.put("/signups/{signup_id}/review", response_model=SignupOut)
def submit_review(signup_id: int, data: ReviewDocIn, db: DB, user: CurrentUser) -> SignupOut:
    signup = signup_service.submit_review(db, user, signup_id, data.review_doc_url)
    return service.signup_out(signup, user, manager=False)


@router.put("/signups/{signup_id}/rating", response_model=SignupOut)
def rate_review(signup_id: int, data: RatingIn, db: DB, user: CurrentUser) -> SignupOut:
    signup_service.rate(db, user, signup_id, data.score, data.comment)
    db.expire_all()
    signup = signup_service.get_signup(db, signup_id)
    return service.signup_out(signup, user, manager=service.can_manage(user, signup.activity))


@router.get("/reviews/to-rate", response_model=list[ReviewToRate])
def reviews_to_rate(db: DB, user: CurrentUser) -> list[ReviewToRate]:
    return signup_service.reviews_to_rate(db, user)


# ----- Invitations -----


@router.get("/activities/{activity_id}/invites", response_model=list[InviteOut])
def activity_invites(activity_id: int, db: DB, user: CurrentUser) -> list[InviteOut]:
    return [invite_service.to_out(i) for i in invite_service.for_activity(db, user, activity_id)]


@router.post("/activities/{activity_id}/invites", response_model=InviteOut, status_code=201)
def invite(activity_id: int, data: InviteIn, db: DB, user: CurrentUser) -> InviteOut:
    return invite_service.to_out(invite_service.create(db, user, activity_id, data))

"""Activities: creating, scheduling, listing, closing and serialising share sessions."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.config import get_settings
from app.db import utcnow
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    Activity,
    ActivityKind,
    ActivitySpeaker,
    Group,
    GroupMembership,
    GroupStatus,
    Invite,
    InviteStatus,
    Room,
    RoomSlot,
    Signup,
    SignupRole,
    User,
    UserRole,
)
from app.scheduling import (
    WEEKDAY_NAMES,
    ActivityState,
    Window,
    activity_state,
    closed_on_time,
    is_covered,
    local_datetime,
    overlaps,
    validate_meetup_window,
    validate_time_range,
)
from app.schemas import (
    ActivityDetail,
    ActivityIn,
    ActivityOut,
    ActivityPage,
    ActivityUpdate,
    Issue,
    RoomOut,
    ScheduleCheck,
    SignupCounts,
    SignupOut,
    UserBrief,
    ViewerContext,
)
from app.services import mail, users

LOAD = (
    selectinload(Activity.speakers),
    selectinload(Activity.signups).selectinload(Signup.ratings),
    selectinload(Activity.invites),
)

ERROR_MESSAGES = {
    "time_order": "The end time must be after the start time.",
    "time_off_grid": "Times must fall on {slot}-minute boundaries.",
    "time_outside_day": "Activities must take place between {day_start} and {day_end}.",
    "meetup_wrong_day": "CAC Meetups can only be held on {weekday}s.",
    "meetup_outside_window": "CAC Meetups must take place between {window_start} and {window_end}.",
    "date_in_past": "The activity must start in the future.",
    "room_not_found": "The selected room does not exist or is no longer in use.",
    "room_unavailable": "{room} is not open for booking at this time.",
    "room_conflict": "{room} is already booked for “{title}” at this time.",
    "group_not_member": "You can only file an activity under a group you belong to.",
    "group_archived": "This interest group is archived.",
    "group_required": "You belong to several interest groups. Choose which one this activity is for.",
}

WARNING_MESSAGES = {
    "room_shared": "{room} is also booked for “{title}” (a {kind}) at this time.",
    "time_overlap": "Overlaps with “{title}” on the same day.",
    "meetup_overlap": "Overlaps with the CAC Meetup “{title}”. Consider choosing another time.",
}


# ----- Lookups & permissions -----


def lock_activity(db: Session, activity_id: int) -> None:
    """Take a row lock on the activity until the transaction ends (a no-op on SQLite, which
    serialises writers anyway). Only the primary key is selected: FOR UPDATE can't be combined
    with the eager outer joins used when loading the full entity."""
    if db.scalar(select(Activity.id).where(Activity.id == activity_id).with_for_update()) is None:
        raise NotFound("Activity not found.", code="activity_not_found")


def get_activity(db: Session, activity_id: int, *, lock: bool = False) -> Activity:
    if lock:
        lock_activity(db, activity_id)
    activity = db.scalar(select(Activity).where(Activity.id == activity_id).options(*LOAD))
    if activity is None:
        raise NotFound("Activity not found.", code="activity_not_found")
    return activity


def can_manage(user: User | None, activity: Activity) -> bool:
    return user is not None and (user.is_admin or user.id == activity.organizer_id)


def require_manager(user: User, activity: Activity) -> None:
    if not can_manage(user, activity):
        raise Forbidden("Only the organiser or an administrator can do this.", code="not_organizer")


def state_of(activity: Activity, now: datetime | None = None) -> ActivityState:
    return activity_state(activity.date, activity.start_time, activity.end_time, activity.closed_at, now)


def state_filter(states: list[ActivityState], now: datetime | None = None) -> ColumnElement[bool]:
    """Translate computed states into SQL so filtering and pagination happen in the database."""
    settings = get_settings()
    local_now = (now or utcnow()).astimezone(settings.tz)
    today, now_t = local_now.date(), local_now.time().replace(tzinfo=None)
    open_ = Activity.closed_at.is_(None)
    clauses = {
        ActivityState.CLOSED: Activity.closed_at.is_not(None),
        ActivityState.UPCOMING: and_(
            open_, or_(Activity.date > today, and_(Activity.date == today, Activity.start_time > now_t))
        ),
        ActivityState.LIVE: and_(
            open_, Activity.date == today, Activity.start_time <= now_t, Activity.end_time > now_t
        ),
        ActivityState.AWAITING_CLOSE: and_(
            open_, or_(Activity.date < today, and_(Activity.date == today, Activity.end_time <= now_t))
        ),
    }
    return or_(*(clauses[s] for s in states))


# ----- Serialisation -----


def brief(user: User | None) -> UserBrief | None:
    return UserBrief(id=user.id, name=user.name) if user else None


def counts_of(activity: Activity) -> SignupCounts:
    by_role = {role: 0 for role in SignupRole}
    for signup in activity.signups:
        by_role[signup.role] += 1
    limit = None if activity.kind == ActivityKind.MEETUP else get_settings().reviewer_limit
    return SignupCounts(
        reviewers=by_role[SignupRole.REVIEWER],
        observers=by_role[SignupRole.OBSERVER],
        participants=by_role[SignupRole.PARTICIPANT],
        reviewer_limit=limit,
        reviewer_spots_left=None if limit is None else max(0, limit - by_role[SignupRole.REVIEWER]),
    )


def to_out(activity: Activity, viewer: User | None = None, now: datetime | None = None) -> ActivityOut:
    ctx = ViewerContext(can_manage=can_manage(viewer, activity))
    if viewer is not None:
        mine = next((s for s in activity.signups if s.user_id == viewer.id), None)
        if mine is not None:
            ctx.signup_id, ctx.signup_role = mine.id, mine.role
        invite = next(
            (i for i in activity.invites if i.invitee_id == viewer.id and i.status == InviteStatus.PENDING), None
        )
        ctx.pending_invite_id = invite.id if invite else None
    return ActivityOut(
        id=activity.id,
        title=activity.title,
        description=activity.description,
        kind=activity.kind,
        date=activity.date,
        start_time=activity.start_time,
        end_time=activity.end_time,
        state=state_of(activity, now),
        room=RoomOut.model_validate(activity.room) if activity.room else None,
        location=activity.location,
        video_url=activity.video_url,
        group=UserBrief(id=activity.group.id, name=activity.group.name) if activity.group else None,
        organizer=UserBrief(id=activity.organizer.id, name=activity.organizer.name),
        speakers=[UserBrief(id=s.user.id, name=s.user.name) for s in activity.speakers],
        counts=counts_of(activity),
        closed_at=activity.closed_at,
        closed_on_time=activity.closed_on_time,
        created_at=activity.created_at,
        viewer=ctx,
    )


def weighted_average(signup: Signup) -> float | None:
    total_weight = sum(r.weight for r in signup.ratings)
    if not total_weight:
        return None
    return round(sum(r.score * r.weight for r in signup.ratings) / total_weight, 2)


def signup_out(signup: Signup, viewer: User | None, manager: bool) -> SignupOut:
    from app.schemas import RatingOut

    is_self = viewer is not None and viewer.id == signup.user_id
    my_rating = next((r for r in signup.ratings if viewer and r.rater_id == viewer.id), None)
    out = SignupOut(
        id=signup.id,
        user=UserBrief(id=signup.user.id, name=signup.user.name),
        role=signup.role,
        review_topic=signup.review_topic,
        review_doc_url=signup.review_doc_url,
        review_submitted_at=signup.review_submitted_at,
        created_at=signup.created_at,
        average_score=weighted_average(signup),
        rating_count=len(signup.ratings),
        my_score=my_rating.score if my_rating else None,
    )
    if manager or is_self:
        out.email = signup.user.email
        out.phone = signup.user.phone
        out.ratings = [
            RatingOut(
                id=r.id,
                rater=UserBrief(id=r.rater.id, name=r.rater.name),
                score=r.score,
                weight=r.weight,
                comment=r.comment,
                updated_at=r.updated_at,
            )
            for r in sorted(signup.ratings, key=lambda r: r.updated_at, reverse=True)
        ]
    return out


def to_detail(activity: Activity, viewer: User | None) -> ActivityDetail:
    base = to_out(activity, viewer)
    manager = can_manage(viewer, activity)
    signups = [signup_out(s, viewer, manager) for s in activity.signups] if viewer else []
    return ActivityDetail(**base.model_dump(), signups=signups)


# ----- Listing -----


def list_activities(
    db: Session,
    viewer: User | None,
    *,
    states: list[ActivityState] | None = None,
    kind: ActivityKind | None = None,
    group_id: int | None = None,
    q: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    involving: int | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> ActivityPage:
    conditions: list[ColumnElement[bool]] = []
    if states:
        conditions.append(state_filter(states))
    if kind:
        conditions.append(Activity.kind == kind)
    if group_id:
        conditions.append(Activity.group_id == group_id)
    if date_from:
        conditions.append(Activity.date >= date_from)
    if date_to:
        conditions.append(Activity.date <= date_to)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        speaker_match = exists().where(
            ActivitySpeaker.activity_id == Activity.id,
            ActivitySpeaker.user_id == User.id,
            func.lower(User.name).like(like),
        )
        conditions.append(or_(func.lower(Activity.title).like(like), speaker_match))
    if involving:
        conditions.append(
            or_(
                Activity.organizer_id == involving,
                exists().where(ActivitySpeaker.activity_id == Activity.id, ActivitySpeaker.user_id == involving),
                exists().where(Signup.activity_id == Activity.id, Signup.user_id == involving),
            )
        )
    total = db.scalar(select(func.count()).select_from(Activity).where(*conditions)) or 0
    ordering = (
        (Activity.date.desc(), Activity.start_time.desc())
        if order == "desc"
        else (Activity.date.asc(), Activity.start_time.asc())
    )
    rows = db.scalars(
        select(Activity)
        .where(*conditions)
        .options(*LOAD)
        .order_by(*ordering, Activity.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    now = utcnow()
    return ActivityPage(items=[to_out(a, viewer, now) for a in rows], total=total, page=page, page_size=page_size)


# ----- Scheduling checks -----


def _fmt(template: str, **ctx: object) -> str:
    s = get_settings()
    base = {
        "slot": s.slot_minutes,
        "day_start": s.day_start.strftime("%H:%M"),
        "day_end": s.day_end.strftime("%H:%M"),
        "weekday": WEEKDAY_NAMES[s.meetup_weekday],
        "window_start": s.meetup_window_start.strftime("%H:%M"),
        "window_end": s.meetup_window_end.strftime("%H:%M"),
    }
    return template.format(**{**base, **ctx})


def _error(code: str, **ctx: object) -> Issue:
    return Issue(code=code, message=_fmt(ERROR_MESSAGES[code], **ctx))


def _warning(code: str, other: Activity, **ctx: object) -> Issue:
    return Issue(
        code=code,
        message=_fmt(WARNING_MESSAGES[code], title=other.title, **ctx),
        activity_id=other.id,
        activity_title=other.title,
    )


class Plan:
    """The proposed schedule of an activity being created or edited."""

    def __init__(
        self,
        kind: ActivityKind,
        d: date,
        start: time,
        end: time,
        room_id: int | None,
        group_id: int | None,
        group_given: bool,
    ):
        self.kind, self.date, self.start, self.end = kind, d, start, end
        self.room_id, self.group_id, self.group_given = room_id, group_id, group_given


def check_schedule(
    db: Session,
    actor: User,
    plan: Plan,
    *,
    exclude_id: int | None = None,
    check_future: bool = True,
    lock_room: bool = False,
) -> tuple[ScheduleCheck, Group | None]:
    """Validate a proposed schedule. Errors block saving; warnings need the organiser's confirmation."""
    errors: list[Issue] = []
    warnings: list[Issue] = []

    code = validate_time_range(plan.start, plan.end)
    if code:
        errors.append(_error(code))
    if plan.kind == ActivityKind.MEETUP:
        code = validate_meetup_window(plan.date, plan.start, plan.end)
        if code:
            errors.append(_error(code))
    if check_future and local_datetime(plan.date, plan.start) <= utcnow():
        errors.append(_error("date_in_past"))

    # Group attribution (regular activities only)
    group: Group | None = None
    if plan.kind == ActivityKind.REGULAR:
        if plan.group_id:
            group = db.get(Group, plan.group_id)
            if group is None:
                raise NotFound("Interest group not found.", code="group_not_found")
            if group.status == GroupStatus.ARCHIVED:
                errors.append(_error("group_archived"))
            is_member = db.get(GroupMembership, (group.id, actor.id)) is not None
            if not is_member and not actor.is_admin:
                errors.append(_error("group_not_member"))
        elif not plan.group_given:
            my_groups = db.scalars(
                select(Group)
                .join(GroupMembership)
                .where(GroupMembership.user_id == actor.id, Group.status == GroupStatus.ACTIVE)
            ).all()
            if len(my_groups) == 1:
                group = my_groups[0]
            elif len(my_groups) > 1:
                errors.append(_error("group_required"))

    # Room availability & bookings
    room: Room | None = None
    if plan.room_id:
        stmt = select(Room).where(Room.id == plan.room_id)
        if lock_room:
            stmt = stmt.with_for_update()  # serialises concurrent bookings of the same room
        room = db.scalar(stmt)
        if room is None or not room.is_active:
            errors.append(_error("room_not_found"))
            room = None
        else:
            slots = db.scalars(select(RoomSlot).where(RoomSlot.room_id == room.id, RoomSlot.date == plan.date))
            if not is_covered(plan.start, plan.end, [Window(s.start_time, s.end_time) for s in slots]):
                errors.append(_error("room_unavailable", room=room.name))

    same_day = db.scalars(select(Activity).where(Activity.date == plan.date, Activity.id != (exclude_id or 0))).all()
    for other in same_day:
        if not overlaps(plan.start, plan.end, other.start_time, other.end_time):
            continue
        if room is not None and other.room_id == room.id:
            if other.kind == plan.kind:
                errors.append(
                    Issue(
                        code="room_conflict",
                        message=_fmt(ERROR_MESSAGES["room_conflict"], room=room.name, title=other.title),
                        activity_id=other.id,
                        activity_title=other.title,
                    )
                )
            else:
                kind_label = "CAC Meetup" if other.kind == ActivityKind.MEETUP else "regular session"
                warnings.append(_warning("room_shared", other, room=room.name, kind=kind_label))
            continue
        if other.is_closed:
            continue
        if ActivityKind.MEETUP in (other.kind, plan.kind) and other.kind != plan.kind:
            warnings.append(_warning("meetup_overlap", other))
        else:
            warnings.append(_warning("time_overlap", other))

    return ScheduleCheck(errors=errors, warnings=warnings), group


def _raise_on_problems(result: ScheduleCheck, acknowledged: bool) -> None:
    if result.errors:
        first = result.errors[0]
        payload = {
            "errors": [e.model_dump() for e in result.errors],
            "warnings": [w.model_dump() for w in result.warnings],
        }
        status_cls = Conflict if first.code == "room_conflict" else BadRequest
        raise status_cls(first.message, code=first.code, details=payload)
    if result.warnings and not acknowledged:
        raise Conflict(
            "This schedule has warnings that need your confirmation.",
            code="confirmation_required",
            details={"errors": [], "warnings": [w.model_dump() for w in result.warnings]},
        )


# ----- Mutations -----


def _set_speakers(activity: Activity, speakers: list[User]) -> None:
    activity.speakers = [ActivitySpeaker(user_id=u.id, position=i) for i, u in enumerate(speakers)]


def preview(db: Session, actor: User, data: ActivityIn, exclude_id: int | None = None) -> ScheduleCheck:
    plan = Plan(
        data.kind,
        data.date,
        data.start_time,
        data.end_time,
        data.room_id,
        data.group_id,
        group_given=data.group_id is not None,
    )
    result, _ = check_schedule(db, actor, plan, exclude_id=exclude_id)
    return result


def create(db: Session, actor: User, data: ActivityIn) -> Activity:
    plan = Plan(
        data.kind,
        data.date,
        data.start_time,
        data.end_time,
        data.room_id,
        data.group_id,
        group_given=data.group_id is not None,
    )
    speakers = users.get_users(db, data.speaker_ids) or [actor]
    result, group = check_schedule(db, actor, plan, lock_room=True)
    _raise_on_problems(result, data.acknowledge_warnings)

    activity = Activity(
        title=data.title,
        description=data.description,
        kind=data.kind,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        room_id=data.room_id,
        location=data.location,
        video_url=data.video_url,
        group_id=group.id if group else None,
        organizer_id=actor.id,
    )
    db.add(activity)
    _set_speakers(activity, speakers)
    db.flush()
    if activity.kind == ActivityKind.MEETUP:
        _announce_meetup(db, actor, activity)
    db.commit()
    return get_activity(db, activity.id)


def _announce_meetup(db: Session, actor: User, activity: Activity) -> None:
    """Let CAC administrators know a Meetup was proposed so they can plan around it."""
    ctx = {
        "organizer": actor.name,
        "title": activity.title,
        "when": mail.when(activity.date, activity.start_time, activity.end_time),
        "link": mail.link(f"/activities/{activity.id}"),
    }
    for admin in db.scalars(select(User).where(User.role == UserRole.ADMIN, User.is_active, User.id != actor.id)):
        mail.notify(db, admin, "meetup_proposed", **ctx)
    report_to = get_settings().participation_report_email
    if report_to:
        mail.notify_address(db, report_to, "meetup_proposed", **ctx)


def update(db: Session, actor: User, activity_id: int, data: ActivityUpdate) -> Activity:
    activity = get_activity(db, activity_id)
    require_manager(actor, activity)
    if activity.is_closed:
        raise BadRequest("Closed activities can't be edited.", code="activity_closed")
    changes = data.model_dump(exclude_unset=True, exclude={"acknowledge_warnings", "speaker_ids"})
    speakers = None
    if data.speaker_ids is not None:
        speakers = users.get_users(db, data.speaker_ids) or [activity.organizer]

    new_kind = changes.get("kind", activity.kind)
    schedule_fields = {"kind", "date", "start_time", "end_time", "room_id", "group_id"}
    rescheduled = any(
        changes.get(f, getattr(activity, f)) != getattr(activity, f)
        for f in ("date", "start_time", "end_time", "room_id")
    )
    if schedule_fields & changes.keys():
        plan = Plan(
            new_kind,
            changes.get("date", activity.date),
            changes.get("start_time", activity.start_time),
            changes.get("end_time", activity.end_time),
            changes.get("room_id", activity.room_id),
            changes.get("group_id", activity.group_id),
            group_given=True,
        )
        time_changed = any(
            changes.get(f, getattr(activity, f)) != getattr(activity, f) for f in ("date", "start_time", "end_time")
        )
        result, group = check_schedule(
            db, actor, plan, exclude_id=activity.id, check_future=time_changed, lock_room=True
        )
        _raise_on_problems(result, data.acknowledge_warnings)
        if new_kind == ActivityKind.REGULAR:
            reviewers = sum(1 for s in activity.signups if s.role == SignupRole.REVIEWER)
            if reviewers > get_settings().reviewer_limit:
                raise BadRequest(
                    "This activity already has more reviewers than a regular session allows.",
                    code="too_many_reviewers",
                )
            if any(s.role == SignupRole.PARTICIPANT for s in activity.signups):
                raise BadRequest(
                    "Meetup participants are signed up; remove them before changing the type.",
                    code="has_participants",
                )
        changes["group_id"] = group.id if (group and new_kind == ActivityKind.REGULAR) else None

    for field, value in changes.items():
        setattr(activity, field, value)
    if speakers is not None:
        _set_speakers(activity, speakers)

    if rescheduled:
        db.flush()
        db.refresh(activity)
        where = f", {activity.room.name}" if activity.room else (f", {activity.location}" if activity.location else "")
        for signup in activity.signups:
            mail.notify(
                db,
                signup.user,
                "activity_rescheduled",
                title=activity.title,
                when=mail.activity_when(activity),
                where=where,
                link=mail.link(f"/activities/{activity.id}"),
            )
    db.commit()
    db.expire_all()
    return get_activity(db, activity.id)


def delete(db: Session, actor: User, activity_id: int) -> None:
    activity = get_activity(db, activity_id)
    require_manager(actor, activity)
    if activity.is_closed and not actor.is_admin:
        raise BadRequest("Closed activities are part of the record and can't be deleted.", code="activity_closed")
    if state_of(activity) != ActivityState.CLOSED:
        for signup in activity.signups:
            mail.notify(
                db,
                signup.user,
                "activity_cancelled",
                title=activity.title,
                when=mail.activity_when(activity),
                organizer=actor.name,
            )
    db.delete(activity)
    db.commit()


def close(db: Session, actor: User, activity_id: int) -> tuple[Activity, bool, int]:
    activity = get_activity(db, activity_id, lock=True)
    require_manager(actor, activity)
    state = state_of(activity)
    if state == ActivityState.CLOSED:
        raise Conflict("This activity has already been closed.", code="already_closed")
    if state == ActivityState.UPCOMING:
        raise BadRequest("An activity can only be closed once it has started.", code="not_started")
    now = utcnow()
    activity.closed_at = now
    activity.closed_by_id = actor.id
    activity.closed_on_time = closed_on_time(activity.date, activity.end_time, now)
    reminders = 0
    if activity.kind == ActivityKind.REGULAR:
        hours = get_settings().review_reminder_interval_hours
        for signup in activity.signups:
            if signup.role == SignupRole.REVIEWER and not signup.review_doc_url:
                if mail.notify(
                    db,
                    signup.user,
                    "review_reminder",
                    title=activity.title,
                    hours=hours,
                    link=mail.link(f"/activities/{activity.id}"),
                ):
                    reminders += 1
                signup.last_reminder_at = now
    db.commit()
    return get_activity(db, activity.id), bool(activity.closed_on_time), reminders


def pending_invites_for(db: Session, activity_id: int, user_id: int) -> list[Invite]:
    return list(
        db.scalars(
            select(Invite).where(
                Invite.activity_id == activity_id, Invite.invitee_id == user_id, Invite.status == InviteStatus.PENDING
            )
        )
    )

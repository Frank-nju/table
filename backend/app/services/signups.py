"""Signing up for activities, submitting reviews and rating them."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import utcnow
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    Activity,
    ActivityKind,
    ActivitySpeaker,
    InviteStatus,
    ReviewRating,
    Signup,
    SignupRole,
    User,
)
from app.scheduling import ActivityState
from app.schemas import ReviewToRate, SignupIn, UserBrief
from app.services import activities as activity_service
from app.services import mail


def get_signup(db: Session, signup_id: int) -> Signup:
    signup = db.scalar(
        select(Signup)
        .where(Signup.id == signup_id)
        .options(selectinload(Signup.ratings), selectinload(Signup.activity))
    )
    if signup is None:
        raise NotFound("Signup not found.", code="signup_not_found")
    return signup


def create(db: Session, actor: User, activity_id: int, data: SignupIn) -> tuple[Signup, int]:
    # Lock the activity row so concurrent reviewer signups can't exceed the limit.
    activity = activity_service.get_activity(db, activity_id, lock=True)
    if activity.is_closed:
        raise BadRequest("This activity is closed.", code="activity_closed")
    if data.role == SignupRole.PARTICIPANT and activity.kind != ActivityKind.MEETUP:
        raise BadRequest("The participant role is only available for CAC Meetups.", code="invalid_role")
    if data.role == SignupRole.REVIEWER and not data.review_topic:
        raise BadRequest("Reviewers need to describe what they plan to review.", code="review_topic_required")
    if any(s.user_id == actor.id for s in activity.speakers):
        raise BadRequest("Speakers can't sign up for their own session.", code="speaker_cannot_signup")
    if any(s.user_id == actor.id for s in activity.signups):
        raise Conflict("You're already signed up for this activity.", code="already_signed_up")
    if data.role == SignupRole.REVIEWER and activity.kind == ActivityKind.REGULAR:
        limit = get_settings().reviewer_limit
        reviewers = db.scalar(
            select(func.count()).where(Signup.activity_id == activity.id, Signup.role == SignupRole.REVIEWER)
        )
        if (reviewers or 0) >= limit:
            raise Conflict(
                f"All {limit} reviewer spots are taken. You can still join as an observer.", code="reviewers_full"
            )

    if data.phone is not None:
        actor.phone = data.phone or None
    signup = Signup(
        activity_id=activity.id,
        user_id=actor.id,
        role=data.role,
        review_topic=data.review_topic if data.role == SignupRole.REVIEWER else "",
    )
    db.add(signup)
    accepted = 0
    for invite in activity_service.pending_invites_for(db, activity.id, actor.id):
        invite.status = InviteStatus.ACCEPTED
        invite.updated_by_id = actor.id
        accepted += 1
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise Conflict("You're already signed up for this activity.", code="already_signed_up") from exc

    link = mail.link(f"/activities/{activity.id}")
    when = mail.activity_when(activity)
    from app.emails import role_label

    mail.notify(
        db,
        actor,
        "signup_confirmed",
        title=activity.title,
        when=when,
        link=link,
        role=role_label(data.role.value, actor.locale),
    )
    organizer = activity.organizer
    if organizer.id != actor.id:
        topic = ""
        if signup.review_topic:
            topic = f"\n\n{'评议方向' if organizer.locale == 'zh' else 'Review focus'}: {signup.review_topic}"
        mail.notify(
            db,
            organizer,
            "organizer_new_signup",
            participant=actor.name,
            title=activity.title,
            when=when,
            link=link,
            topic=topic,
            role=role_label(data.role.value, organizer.locale),
        )
    db.commit()
    return get_signup(db, signup.id), accepted


def cancel(db: Session, actor: User, signup_id: int) -> None:
    signup = get_signup(db, signup_id)
    activity = signup.activity
    is_self = signup.user_id == actor.id
    manager = activity_service.can_manage(actor, activity)
    if not (is_self or manager):
        raise Forbidden("You can only cancel your own signup.", code="not_your_signup")
    if not manager and activity_service.state_of(activity) != ActivityState.UPCOMING:
        raise BadRequest("Signups can't be cancelled after the activity has started.", code="activity_started")
    mail.notify(db, signup.user, "signup_cancelled", title=activity.title, when=mail.activity_when(activity))
    db.delete(signup)
    db.commit()


def submit_review(db: Session, actor: User, signup_id: int, url: str) -> Signup:
    signup = get_signup(db, signup_id)
    if signup.user_id != actor.id:
        raise Forbidden("You can only submit your own review.", code="not_your_signup")
    if signup.role != SignupRole.REVIEWER:
        raise BadRequest("Only reviewers submit review documents.", code="not_reviewer")
    signup.review_doc_url = url
    signup.review_submitted_at = utcnow()
    db.commit()
    return get_signup(db, signup.id)


def rating_weight(db: Session, activity_id: int, rater_id: int) -> int:
    observer = db.scalar(
        select(Signup.id).where(
            Signup.activity_id == activity_id, Signup.user_id == rater_id, Signup.role == SignupRole.OBSERVER
        )
    )
    return get_settings().observer_rating_weight if observer else 1


def rate(db: Session, actor: User, signup_id: int, score: int, comment: str) -> ReviewRating:
    signup = get_signup(db, signup_id)
    if signup.role != SignupRole.REVIEWER:
        raise BadRequest("Only reviews can be rated.", code="not_reviewer")
    if signup.user_id == actor.id:
        raise BadRequest("You can't rate your own review.", code="cannot_rate_self")
    if not signup.review_doc_url:
        raise Conflict("This review hasn't been submitted yet.", code="review_not_submitted")
    rating = db.scalar(
        select(ReviewRating).where(ReviewRating.signup_id == signup.id, ReviewRating.rater_id == actor.id)
    )
    weight = rating_weight(db, signup.activity_id, actor.id)
    if rating is None:
        rating = ReviewRating(signup_id=signup.id, rater_id=actor.id, score=score, weight=weight, comment=comment)
        db.add(rating)
    else:
        rating.score, rating.weight, rating.comment = score, weight, comment
    db.commit()
    return rating


def reviews_to_rate(db: Session, actor: User, limit: int = 50) -> list[ReviewToRate]:
    rated = select(ReviewRating.signup_id).where(ReviewRating.rater_id == actor.id)
    spoke = select(ActivitySpeaker.activity_id).where(ActivitySpeaker.user_id == actor.id)
    attended = select(Signup.activity_id).where(Signup.user_id == actor.id)
    rows = db.execute(
        select(Signup, Activity)
        .join(Activity, Activity.id == Signup.activity_id)
        .where(
            Signup.role == SignupRole.REVIEWER,
            Signup.review_doc_url != "",
            Signup.user_id != actor.id,
            Signup.id.not_in(rated),
            Activity.closed_at.is_not(None),
        )
        .order_by(
            # Sessions you attended or spoke at come first: you're best placed to judge those reviews.
            (Activity.id.in_(attended) | Activity.id.in_(spoke)).desc(),
            Activity.date.desc(),
        )
        .limit(limit)
    ).all()
    observer_of = set(
        db.scalars(select(Signup.activity_id).where(Signup.user_id == actor.id, Signup.role == SignupRole.OBSERVER))
    )
    weight = get_settings().observer_rating_weight
    return [
        ReviewToRate(
            signup_id=signup.id,
            reviewer=UserBrief(id=signup.user.id, name=signup.user.name),
            review_doc_url=signup.review_doc_url,
            review_topic=signup.review_topic,
            activity=UserBrief(id=activity.id, name=activity.title),
            activity_date=activity.date,
            weight=weight if activity.id in observer_of else 1,
        )
        for signup, activity in rows
    ]


def my_signups(db: Session, user: User, *, include_closed: bool) -> list[Signup]:
    stmt = (
        select(Signup)
        .join(Activity)
        .where(Signup.user_id == user.id)
        .options(selectinload(Signup.ratings), selectinload(Signup.activity).options(*activity_service.LOAD))
        .order_by(Activity.date, Activity.start_time)
    )
    if not include_closed:
        stmt = stmt.where(Activity.closed_at.is_(None))
    return list(db.scalars(stmt))

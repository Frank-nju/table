"""Review invitations: an organiser asks a specific member to review their session."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.emails import status_label
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.models import Activity, Invite, InviteSource, InviteStatus, User
from app.schemas import InviteIn, InviteOut, UserBrief
from app.services import activities as activity_service
from app.services import mail, users


def to_out(invite: Invite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        activity=UserBrief(id=invite.activity.id, name=invite.activity.title),
        activity_date=invite.activity.date,
        activity_start_time=invite.activity.start_time,
        inviter=UserBrief(id=invite.inviter.id, name=invite.inviter.name) if invite.inviter else None,
        invitee=UserBrief(id=invite.invitee.id, name=invite.invitee.name),
        source=invite.source,
        status=invite.status,
        message=invite.message,
        created_at=invite.created_at,
        updated_at=invite.updated_at,
    )


def _can_invite(actor: User, activity: Activity) -> bool:
    return activity_service.can_manage(actor, activity) or any(s.user_id == actor.id for s in activity.speakers)


def create(db: Session, actor: User, activity_id: int, data: InviteIn) -> Invite:
    activity = activity_service.get_activity(db, activity_id)
    if not _can_invite(actor, activity):
        raise Forbidden("Only the organiser or a speaker can invite reviewers.", code="not_organizer")
    if data.source == InviteSource.CAC and not actor.is_admin:
        raise Forbidden("Only administrators can send CAC invitations.", code="admin_required")
    if activity.is_closed:
        raise BadRequest("This activity is closed.", code="activity_closed")
    invitee = users.get_user(db, data.invitee_id)
    if invitee.id == actor.id:
        raise BadRequest("You can't invite yourself.", code="cannot_invite_self")
    if any(s.user_id == invitee.id for s in activity.speakers):
        raise BadRequest("Speakers can't review their own session.", code="speaker_cannot_signup")
    if any(s.user_id == invitee.id for s in activity.signups):
        raise Conflict(f"{invitee.name} is already signed up.", code="already_signed_up")
    if any(
        i.invitee_id == invitee.id and i.status in (InviteStatus.PENDING, InviteStatus.ACCEPTED)
        for i in activity.invites
    ):
        raise Conflict(f"{invitee.name} has already been invited.", code="already_invited")
    invite = Invite(
        activity_id=activity.id,
        inviter_id=actor.id,
        invitee_id=invitee.id,
        source=data.source,
        message=data.message,
        updated_by_id=actor.id,
    )
    db.add(invite)
    db.flush()
    message = f"\n\n“{data.message}”" if data.message else ""
    mail.notify(
        db,
        invitee,
        "invite_received",
        inviter=actor.name,
        title=activity.title,
        when=mail.activity_when(activity),
        message=message,
        link=mail.link(f"/activities/{activity.id}"),
    )
    db.commit()
    return get(db, invite.id)


def get(db: Session, invite_id: int) -> Invite:
    invite = db.get(Invite, invite_id)
    if invite is None:
        raise NotFound("Invitation not found.", code="invite_not_found")
    return invite


def set_status(db: Session, actor: User, invite_id: int, status: InviteStatus) -> Invite:
    invite = get(db, invite_id)
    if invite.status == status:
        return invite
    activity = invite.activity
    is_invitee = actor.id == invite.invitee_id
    is_sender = actor.id == invite.inviter_id or activity_service.can_manage(actor, activity)

    if actor.is_admin:
        pass  # administrators may correct any invitation
    elif (
        is_invitee
        and invite.status == InviteStatus.PENDING
        and status
        in (
            InviteStatus.ACCEPTED,
            InviteStatus.DECLINED,
        )
    ) or (is_sender and invite.status == InviteStatus.PENDING and status == InviteStatus.WITHDRAWN):
        pass
    elif is_invitee or is_sender:
        raise Conflict(
            f"An invitation can't go from {invite.status.value} to {status.value}.", code="invalid_transition"
        )
    else:
        raise Forbidden("You can't change this invitation.", code="forbidden")

    invite.status = status
    invite.updated_by_id = actor.id
    link = mail.link(f"/activities/{activity.id}")
    recipient = invite.inviter if is_invitee else invite.invitee
    if recipient is not None and recipient.id != actor.id:
        mail.notify(
            db,
            recipient,
            "invite_updated",
            title=activity.title,
            actor=actor.name,
            link=link,
            status=status_label(status.value, recipient.locale),
        )
    db.commit()
    return invite


def for_activity(db: Session, actor: User, activity_id: int) -> list[Invite]:
    activity = activity_service.get_activity(db, activity_id)
    if not _can_invite(actor, activity):
        raise Forbidden("Only the organiser or a speaker can see invitations.", code="not_organizer")
    return sorted(activity.invites, key=lambda i: i.created_at, reverse=True)


def for_user(db: Session, user: User, *, pending_only: bool = False) -> list[Invite]:
    stmt = select(Invite).where(Invite.invitee_id == user.id).order_by(Invite.created_at.desc())
    if pending_only:
        stmt = stmt.where(Invite.status == InviteStatus.PENDING)
    return list(db.scalars(stmt))

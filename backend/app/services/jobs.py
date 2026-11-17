"""Periodic jobs. Each is idempotent, so running the worker on several machines is harmless."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import utcnow
from app.models import Activity, ActivityKind, JobRun, Signup, SignupRole, User, UserRole
from app.services import mail, stats

log = logging.getLogger(__name__)


def send_review_reminders(db: Session, now: datetime | None = None) -> int:
    """Remind reviewers of closed sessions who still haven't linked their review document."""
    settings = get_settings()
    now = now or utcnow()
    cutoff = now - timedelta(hours=settings.review_reminder_interval_hours)
    rows = db.scalars(
        select(Signup)
        .join(Activity)
        .where(
            Signup.role == SignupRole.REVIEWER,
            Signup.review_doc_url == "",
            Activity.closed_at.is_not(None),
            Activity.kind == ActivityKind.REGULAR,
            (Signup.last_reminder_at.is_(None)) | (Signup.last_reminder_at <= cutoff),
        )
    ).all()
    sent = 0
    for signup in rows:
        if mail.notify(
            db,
            signup.user,
            "review_reminder",
            title=signup.activity.title,
            hours=settings.review_reminder_interval_hours,
            link=mail.link(f"/activities/{signup.activity_id}"),
        ):
            sent += 1
        signup.last_reminder_at = now
    db.commit()
    return sent


def _claim(db: Session, key: str) -> bool:
    """Record that `key` ran. Returns False if another run already claimed it."""
    db.add(JobRun(key=key))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def participation_report_key(now: datetime | None = None) -> str | None:
    """The key for this week's report, or None if it isn't time to send it yet."""
    settings = get_settings()
    local = (now or utcnow()).astimezone(settings.tz)
    if local.weekday() != settings.participation_report_weekday or local.hour < settings.participation_report_hour:
        return None
    return f"participation-report:{local.date().isoformat()}"


def send_participation_report(db: Session, now: datetime | None = None) -> int:
    key = participation_report_key(now)
    if key is None or not _claim(db, key):
        return 0
    settings = get_settings()
    watch = stats.participation_watch(db)
    if not watch.inactive:
        return 0
    names = "\n".join(f"• {u.name}" for u in watch.inactive)
    recipients: list[tuple[str, str]] = []
    if settings.participation_report_email:
        recipients.append((settings.participation_report_email, "en"))
    for admin in db.scalars(select(User).where(User.role == UserRole.ADMIN, User.is_active)):
        if admin.email and admin.email != settings.participation_report_email:
            recipients.append((admin.email, admin.locale))
    for address, locale in recipients:
        mail.notify_address(
            db,
            address,
            "participation_report",
            locale=locale,
            count=len(watch.inactive),
            days=watch.lookback_days,
            tracked=watch.tracked_count,
            names=names,
        )
    inactive_ids = [u.id for u in watch.inactive]
    for user in db.scalars(select(User).where(User.id.in_(inactive_ids))):
        mail.notify(db, user, "participation_reminder", days=watch.lookback_days, link=mail.link("/"))
    db.commit()
    return len(watch.inactive)


def run_all(db: Session) -> dict[str, int]:
    results = {}
    for name, job in (
        ("review_reminders", send_review_reminders),
        ("participation_report", send_participation_report),
        ("emails", mail.deliver_pending),
    ):
        try:
            results[name] = job(db)
        except Exception:
            db.rollback()
            log.exception("Job %s failed", name)
            results[name] = -1
    return results

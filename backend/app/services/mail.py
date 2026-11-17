"""Queueing and delivering email through the outbox table."""

from __future__ import annotations

import logging
import smtplib
from datetime import date, time
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import utcnow
from app.emails import render
from app.models import Activity, OutboxEmail, User

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


def link(path: str) -> str:
    return get_settings().public_base_url.rstrip("/") + path


def when(d: date, start: time, end: time) -> str:
    return f"{d.isoformat()} {start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def activity_when(activity: Activity) -> str:
    return when(activity.date, activity.start_time, activity.end_time)


def queue(db: Session, to_address: str | None, subject: str, body: str) -> OutboxEmail | None:
    if not to_address:
        return None
    email = OutboxEmail(to_address=to_address, subject=subject, body=body)
    db.add(email)
    return email


def notify(db: Session, user: User | None, template: str, **context: Any) -> OutboxEmail | None:
    """Render `template` in the user's language and queue it. Silently skips users without email."""
    if user is None or not user.email or not user.is_active:
        return None
    settings = get_settings()
    subject, body = render(template, user.locale, settings.app_name, name=user.name, **context)
    return queue(db, user.email, subject, body)


def notify_address(db: Session, address: str, template: str, locale: str = "en", **context: Any) -> None:
    settings = get_settings()
    subject, body = render(template, locale, settings.app_name, **context)
    queue(db, address, subject, body)


def _send(settings: Settings, email: OutboxEmail) -> None:
    msg = EmailMessage()
    msg["Subject"] = email.subject
    msg["From"] = formataddr((settings.mail_from_name, settings.mail_from))
    msg["To"] = email.to_address
    msg.set_content(email.body)
    smtp_cls = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
    with smtp_cls(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)


def deliver_pending(db: Session, limit: int = 50) -> int:
    """Send queued emails. Without SMTP configured, emails are written to the log instead."""
    settings = get_settings()
    pending = db.scalars(
        select(OutboxEmail)
        .where(OutboxEmail.sent_at.is_(None), OutboxEmail.attempts < MAX_ATTEMPTS)
        .order_by(OutboxEmail.id)
        .limit(limit)
    ).all()
    sent = 0
    for email in pending:
        email.attempts += 1
        try:
            if settings.mail_enabled:
                _send(settings, email)
            else:
                log.info(
                    "Email (SMTP not configured) to=%s subject=%s\n%s", email.to_address, email.subject, email.body
                )
            email.sent_at = utcnow()
            email.last_error = ""
            sent += 1
        except Exception as exc:  # network errors, auth errors, ...
            email.last_error = str(exc)[:2000]
            log.warning("Email to %s failed (attempt %s): %s", email.to_address, email.attempts, exc)
        db.commit()
    return sent

"""Minimal RFC 5545 calendar export so members can add a session to their calendar."""

from __future__ import annotations

from datetime import UTC

from app.config import get_settings
from app.db import utcnow
from app.models import Activity
from app.scheduling import local_datetime


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 octets must be folded."""
    out, current = [], b""
    for ch in line:
        encoded = ch.encode()
        if len(current) + len(encoded) > 73:
            out.append(current.decode())
            current = b" "
        current += encoded
    out.append(current.decode())
    return "\r\n".join(out)


def _utc(dt) -> str:  # type: ignore[no-untyped-def]
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def activity_calendar(activity: Activity) -> str:
    settings = get_settings()
    start = local_datetime(activity.date, activity.start_time)
    end = local_datetime(activity.date, activity.end_time)
    location = activity.room.name if activity.room else activity.location
    speakers = ", ".join(s.user.name for s in activity.speakers)
    description = "\n".join(
        part for part in (f"Speakers: {speakers}" if speakers else "", activity.description, activity.video_url) if part
    )
    url = settings.public_base_url.rstrip("/") + f"/activities/{activity.id}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CAC Share Sessions//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:activity-{activity.id}@cac-share-sessions",
        f"DTSTAMP:{_utc(utcnow())}",
        f"DTSTART:{_utc(start)}",
        f"DTEND:{_utc(end)}",
        f"SUMMARY:{_escape(activity.title)}",
        f"DESCRIPTION:{_escape(description)}",
        f"URL:{url}",
    ]
    if location:
        lines.append(f"LOCATION:{_escape(location)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"

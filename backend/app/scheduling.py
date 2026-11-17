"""Pure time and scheduling helpers. Nothing here touches the database."""

from __future__ import annotations

import enum
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.config import Settings, get_settings
from app.db import utcnow


class ActivityState(enum.StrEnum):
    UPCOMING = "upcoming"
    LIVE = "live"
    AWAITING_CLOSE = "awaiting_close"
    CLOSED = "closed"


def minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def from_minutes(total: int) -> time:
    return time(total // 60, total % 60)


def time_grid(settings: Settings | None = None) -> list[str]:
    """Every selectable boundary between DAY_START and DAY_END, e.g. ['09:00', '09:30', ...]."""
    s = settings or get_settings()
    step = s.slot_minutes
    return [from_minutes(m).strftime("%H:%M") for m in range(minutes(s.day_start), minutes(s.day_end) + 1, step)]


def on_grid(t: time, settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return t.second == 0 and t.microsecond == 0 and minutes(t) % s.slot_minutes == 0


def local_datetime(d: date, t: time, settings: Settings | None = None) -> datetime:
    s = settings or get_settings()
    return datetime.combine(d, t, tzinfo=s.tz)


def local_today(settings: Settings | None = None) -> date:
    s = settings or get_settings()
    return utcnow().astimezone(s.tz).date()


def activity_state(
    d: date, start: time, end: time, closed_at: datetime | None, now: datetime | None = None
) -> ActivityState:
    if closed_at is not None:
        return ActivityState.CLOSED
    now = now or utcnow()
    if now < local_datetime(d, start):
        return ActivityState.UPCOMING
    if now < local_datetime(d, end):
        return ActivityState.LIVE
    return ActivityState.AWAITING_CLOSE


def closed_on_time(d: date, end: time, closed_at: datetime, settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return closed_at <= local_datetime(d, end, s) + timedelta(minutes=s.close_grace_minutes)


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """Half-open interval overlap: touching end points (10:00-11:00 and 11:00-12:00) do not overlap."""
    return a_start < b_end and b_start < a_end


@dataclass(frozen=True)
class Window:
    start: time
    end: time


def merge_windows(windows: Iterable[Window]) -> list[Window]:
    merged: list[Window] = []
    for w in sorted(windows, key=lambda w: (w.start, w.end)):
        if merged and w.start <= merged[-1].end:
            last = merged[-1]
            merged[-1] = Window(last.start, max(last.end, w.end))
        else:
            merged.append(w)
    return merged


def is_covered(start: time, end: time, windows: Iterable[Window]) -> bool:
    """True when [start, end) lies entirely inside the union of `windows`."""
    return any(w.start <= start and end <= w.end for w in merge_windows(windows))


def validate_time_range(start: time, end: time, settings: Settings | None = None) -> str | None:
    """Returns an error code, or None if the range is acceptable for a regular activity."""
    s = settings or get_settings()
    if start >= end:
        return "time_order"
    if not (on_grid(start, s) and on_grid(end, s)):
        return "time_off_grid"
    if start < s.day_start or end > s.day_end:
        return "time_outside_day"
    return None


def validate_meetup_window(d: date, start: time, end: time, settings: Settings | None = None) -> str | None:
    s = settings or get_settings()
    if d.weekday() != s.meetup_weekday:
        return "meetup_wrong_day"
    if start < s.meetup_window_start or end > s.meetup_window_end:
        return "meetup_outside_window"
    return None


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

from datetime import UTC, date, datetime, time

from app.scheduling import (
    ActivityState,
    Window,
    activity_state,
    closed_on_time,
    is_covered,
    merge_windows,
    overlaps,
    time_grid,
    validate_meetup_window,
    validate_time_range,
)

from .conftest import NEXT_SUNDAY, TOMORROW, TZ


def t(s: str) -> time:
    return time.fromisoformat(s)


def test_time_grid_runs_from_day_start_to_end_in_slots():
    grid = time_grid()
    assert grid[0] == "09:00" and grid[-1] == "22:00"
    assert grid[1] == "09:30"
    assert len(grid) == 27


def test_overlap_is_half_open():
    assert overlaps(t("10:00"), t("11:00"), t("10:30"), t("11:30"))
    assert not overlaps(t("10:00"), t("11:00"), t("11:00"), t("12:00"))
    assert overlaps(t("10:00"), t("12:00"), t("10:30"), t("11:00"))


def test_windows_merge_and_cover_adjacent_slots():
    slots = [Window(t("14:00"), t("14:30")), Window(t("14:30"), t("15:00")), Window(t("16:00"), t("17:00"))]
    assert merge_windows(slots) == [Window(t("14:00"), t("15:00")), Window(t("16:00"), t("17:00"))]
    assert is_covered(t("14:00"), t("15:00"), slots)
    assert not is_covered(t("14:30"), t("16:30"), slots)  # gap from 15:00 to 16:00
    assert not is_covered(t("14:00"), t("15:00"), [])


def test_time_range_validation():
    assert validate_time_range(t("14:00"), t("15:30")) is None
    assert validate_time_range(t("15:00"), t("14:00")) == "time_order"
    assert validate_time_range(t("14:15"), t("15:00")) == "time_off_grid"
    assert validate_time_range(t("08:00"), t("09:00")) == "time_outside_day"
    assert validate_time_range(t("21:30"), t("22:30")) == "time_outside_day"


def test_meetup_window_validation():
    assert validate_meetup_window(NEXT_SUNDAY, t("14:00"), t("15:00")) is None
    assert validate_meetup_window(NEXT_SUNDAY, t("17:30"), t("18:00")) is None
    assert validate_meetup_window(TOMORROW, t("14:00"), t("15:00")) == "meetup_wrong_day"
    assert validate_meetup_window(NEXT_SUNDAY, t("17:30"), t("18:30")) == "meetup_outside_window"


def test_activity_state_uses_local_time():
    d = date(2026, 11, 16)
    at = lambda h, m=0: datetime(2026, 11, 16, h, m, tzinfo=TZ).astimezone(UTC)  # noqa: E731
    assert activity_state(d, t("14:00"), t("15:00"), None, at(13, 59)) == ActivityState.UPCOMING
    assert activity_state(d, t("14:00"), t("15:00"), None, at(14)) == ActivityState.LIVE
    assert activity_state(d, t("14:00"), t("15:00"), None, at(15)) == ActivityState.AWAITING_CLOSE
    assert activity_state(d, t("14:00"), t("15:00"), at(15), at(16)) == ActivityState.CLOSED


def test_on_time_closure_respects_grace_period():
    d = date(2026, 11, 16)
    end = t("15:00")
    within = datetime(2026, 11, 17, 14, 59, tzinfo=TZ)
    late = datetime(2026, 11, 17, 15, 1, tzinfo=TZ)
    assert closed_on_time(d, end, within)
    assert not closed_on_time(d, end, late)

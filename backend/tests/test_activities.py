from datetime import datetime, timedelta

from .conftest import NEXT_SUNDAY, NOW, TOMORROW, TZ, activity_payload, error_code, outbox, set_now


def test_create_activity_defaults_speaker_to_organizer(as_user, create_activity):
    alice = as_user("Alice")
    a = create_activity(alice)
    assert a["organizer"]["name"] == "Alice"
    assert [s["name"] for s in a["speakers"]] == ["Alice"]
    assert a["state"] == "upcoming"
    assert a["counts"] == {
        "reviewers": 0,
        "observers": 0,
        "participants": 0,
        "reviewer_limit": 3,
        "reviewer_spots_left": 3,
    }
    assert a["viewer"]["can_manage"] is True
    assert a["start_time"] == "14:00"


def test_create_requires_login(anon):
    r = anon.post("/api/activities", json=activity_payload())
    assert r.status_code == 401


def test_speakers_can_be_other_members(as_user, make_user, create_activity):
    alice = as_user("Alice")
    bob, carol = make_user("Bob"), make_user("Carol")
    a = create_activity(alice, speaker_ids=[bob.id, carol.id])
    assert [s["name"] for s in a["speakers"]] == ["Bob", "Carol"]
    r = alice.post("/api/activities", json=activity_payload(speaker_ids=[99999]))
    assert r.status_code == 400 and error_code(r) == "user_not_found"


def test_time_rules(as_user):
    alice = as_user("Alice")
    cases = {
        "time_order": {"start_time": "15:00", "end_time": "14:00"},
        "time_off_grid": {"start_time": "14:10", "end_time": "15:00"},
        "time_outside_day": {"start_time": "21:30", "end_time": "22:30"},
        "date_in_past": {"date": (NOW.date() - timedelta(days=1)).isoformat()},
    }
    for code, override in cases.items():
        r = alice.post("/api/activities", json=activity_payload(**override))
        assert r.status_code == 400, (code, r.text)
        assert error_code(r) == code


def test_same_day_but_already_started_is_in_the_past(as_user):
    alice = as_user("Alice")
    r = alice.post("/api/activities", json=activity_payload(date=NOW.date().isoformat(), start_time="09:00"))
    assert error_code(r) == "date_in_past"
    r = alice.post("/api/activities", json=activity_payload(date=NOW.date().isoformat(), start_time="10:00"))
    assert r.status_code == 201


def test_meetup_rules(as_user, create_activity):
    alice = as_user("Alice")
    r = alice.post("/api/activities", json=activity_payload(kind="meetup"))  # a Tuesday
    assert error_code(r) == "meetup_wrong_day"
    r = alice.post(
        "/api/activities",
        json=activity_payload(kind="meetup", date=NEXT_SUNDAY.isoformat(), start_time="17:00", end_time="19:00"),
    )
    assert error_code(r) == "meetup_outside_window"
    a = create_activity(alice, kind="meetup", date=NEXT_SUNDAY.isoformat(), start_time="14:00", end_time="15:30")
    assert a["counts"]["reviewer_limit"] is None


def test_meetup_notifies_admins(as_user, make_user, create_activity, db):
    admin = make_user("Admin", admin=True)
    alice = as_user("Alice")
    create_activity(alice, kind="meetup", date=NEXT_SUNDAY.isoformat(), start_time="14:00", end_time="15:00")
    assert any("CAC Meetup" in m.subject for m in outbox(db, admin.email))


def test_room_must_be_open(as_user, room, open_room, create_activity):
    alice = as_user("Alice")
    r = alice.post("/api/activities", json=activity_payload(room_id=room.id))
    assert r.status_code == 400 and error_code(r) == "room_unavailable"
    open_room(TOMORROW, "13:00", "14:30")
    open_room(TOMORROW, "14:30", "16:00")  # adjacent slots combine
    a = create_activity(alice, room_id=room.id)
    assert a["room"]["name"] == "CAC-101"


def test_same_room_same_kind_is_blocked(as_user, room, open_room, create_activity):
    open_room(TOMORROW)
    alice, bob = as_user("Alice"), as_user("Bob")
    first = create_activity(alice, room_id=room.id)
    r = bob.post("/api/activities", json=activity_payload(room_id=room.id, start_time="14:30", end_time="15:30"))
    assert r.status_code == 409 and error_code(r) == "room_conflict"
    assert r.json()["error"]["details"]["errors"][0]["activity_id"] == first["id"]
    # Back-to-back bookings are fine.
    create_activity(bob, room_id=room.id, start_time="15:00", end_time="16:00")


def test_same_room_different_kind_needs_confirmation(as_user, room, open_room, create_activity):
    open_room(NEXT_SUNDAY)
    alice, bob = as_user("Alice"), as_user("Bob")
    create_activity(alice, kind="meetup", date=NEXT_SUNDAY.isoformat(), room_id=room.id)
    payload = activity_payload(date=NEXT_SUNDAY.isoformat(), room_id=room.id)
    r = bob.post("/api/activities", json=payload)
    assert r.status_code == 409 and error_code(r) == "confirmation_required"
    assert r.json()["error"]["details"]["warnings"][0]["code"] == "room_shared"
    r = bob.post("/api/activities", json={**payload, "acknowledge_warnings": True})
    assert r.status_code == 201


def test_time_overlap_without_room_is_a_warning(as_user, create_activity):
    alice, bob = as_user("Alice"), as_user("Bob")
    create_activity(alice)
    check = bob.post("/api/activities/check", json=activity_payload(start_time="14:30", end_time="16:00")).json()
    assert check["errors"] == []
    assert [w["code"] for w in check["warnings"]] == ["time_overlap"]
    create_activity(bob, expect=409, start_time="14:30", end_time="16:00")
    create_activity(bob, start_time="14:30", end_time="16:00", acknowledge_warnings=True)


def test_room_availability_endpoint(as_user, room, open_room, db, create_activity):
    from app.models import Room

    other = Room(name="CAC-202")
    db.add(other)
    db.commit()
    open_room(TOMORROW)
    alice = as_user("Alice")
    create_activity(alice, room_id=room.id)
    rows = alice.get(
        "/api/rooms/availability",
        params={"date": TOMORROW.isoformat(), "start_time": "14:30", "end_time": "15:30"},
    ).json()
    by_name = {r["room"]["name"]: r for r in rows}
    assert by_name["CAC-101"]["available"] is False and by_name["CAC-101"]["reason"] == "booked"
    assert by_name["CAC-101"]["booked_activity_title"] == "Intro to Rust"
    assert by_name["CAC-202"]["available"] is False and by_name["CAC-202"]["reason"] == "no_slot"


def test_group_attribution(as_user, make_user, create_activity):
    alice = as_user("Alice")
    bob = make_user("Bob")
    g1 = alice.post(
        "/api/groups",
        json={"name": "Systems", "goal": "OS", "time_boundary": "Term", "plan": "Weekly", "member_ids": [bob.id]},
    ).json()
    a = create_activity(alice)
    assert a["group"]["name"] == "Systems"  # auto-filed under the only group
    alice.post(
        "/api/groups",
        json={"name": "ML", "goal": "Models", "time_boundary": "Term", "plan": "Biweekly", "member_ids": [bob.id]},
    )
    r = alice.post("/api/activities", json=activity_payload(start_time="16:00", end_time="17:00"))
    assert error_code(r) == "group_required"
    a = create_activity(alice, start_time="16:00", end_time="17:00", group_id=g1["id"])
    assert a["group"]["id"] == g1["id"]
    stranger = as_user("Stranger")
    r = stranger.post("/api/activities", json=activity_payload(group_id=g1["id"], start_time="18:00", end_time="19:00"))
    assert error_code(r) == "group_not_member"


def test_only_organizer_or_admin_can_edit_or_delete(as_user, create_activity):
    alice, bob, admin = as_user("Alice"), as_user("Bob"), as_user("Admin", admin=True)
    a = create_activity(alice)
    assert bob.patch(f"/api/activities/{a['id']}", json={"title": "Hijacked"}).status_code == 403
    assert bob.delete(f"/api/activities/{a['id']}").status_code == 403
    r = admin.patch(f"/api/activities/{a['id']}", json={"title": "Fixed typo"})
    assert r.status_code == 200 and r.json()["title"] == "Fixed typo"
    assert alice.delete(f"/api/activities/{a['id']}").status_code == 204
    assert alice.get(f"/api/activities/{a['id']}").status_code == 404


def test_reschedule_rechecks_rules_and_notifies(as_user, create_activity, db):
    alice, bob = as_user("Alice"), as_user("Bob")
    a = create_activity(alice)
    bob.post(f"/api/activities/{a['id']}/signups", json={"role": "observer"})
    r = alice.patch(f"/api/activities/{a['id']}", json={"start_time": "14:15"})
    assert error_code(r) == "time_off_grid"
    r = alice.patch(f"/api/activities/{a['id']}", json={"start_time": "16:00", "end_time": "17:00"})
    assert r.status_code == 200 and r.json()["start_time"] == "16:00"
    assert any(m.subject.endswith("Updated: Intro to Rust") for m in outbox(db, bob.user.email))
    # Editing only the title of an activity that has started does not trip the "in the past" check.
    set_now(datetime(2026, 11, 17, 16, 30, tzinfo=TZ))
    assert alice.patch(f"/api/activities/{a['id']}", json={"title": "Rust, live"}).status_code == 200


def test_delete_notifies_signups(as_user, create_activity, db):
    alice, bob = as_user("Alice"), as_user("Bob")
    a = create_activity(alice)
    bob.post(f"/api/activities/{a['id']}/signups", json={"role": "observer"})
    alice.delete(f"/api/activities/{a['id']}")
    assert any("Cancelled" in m.subject for m in outbox(db, bob.user.email))


def test_close_lifecycle(as_user, create_activity, db):
    alice, rev = as_user("Alice"), as_user("Reviewer")
    a = create_activity(alice)
    rev.post(f"/api/activities/{a['id']}/signups", json={"role": "reviewer", "review_topic": "Lifetimes"})
    r = alice.post(f"/api/activities/{a['id']}/close")
    assert r.status_code == 400 and error_code(r) == "not_started"

    set_now(datetime(2026, 11, 17, 15, 30, tzinfo=TZ))
    assert alice.get(f"/api/activities/{a['id']}").json()["state"] == "awaiting_close"
    assert rev.post(f"/api/activities/{a['id']}/close").status_code == 403
    r = alice.post(f"/api/activities/{a['id']}/close")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["on_time"] is True and body["reminders_sent"] == 1
    assert body["activity"]["state"] == "closed"
    assert any("Please submit your review" in m.subject for m in outbox(db, rev.user.email))
    assert error_code(alice.post(f"/api/activities/{a['id']}/close")) == "already_closed"
    assert error_code(alice.patch(f"/api/activities/{a['id']}", json={"title": "x"})) == "activity_closed"
    assert error_code(alice.delete(f"/api/activities/{a['id']}")) == "activity_closed"


def test_late_close_is_recorded(as_user, create_activity):
    alice = as_user("Alice")
    a = create_activity(alice)
    set_now(datetime(2026, 11, 19, 9, 0, tzinfo=TZ))  # well past the 24-hour grace period
    assert alice.post(f"/api/activities/{a['id']}/close").json()["on_time"] is False


def test_listing_filters_and_pagination(as_user, create_activity):
    alice = as_user("Alice")
    rust = create_activity(alice, title="Rust", start_time="10:00", end_time="11:00")
    create_activity(alice, title="Go", start_time="11:00", end_time="12:00")
    create_activity(alice, title="Meetup", kind="meetup", date=NEXT_SUNDAY.isoformat())

    page = alice.get("/api/activities", params={"state": ["upcoming"], "page_size": 2}).json()
    assert page["total"] == 3 and [i["title"] for i in page["items"]] == ["Rust", "Go"]
    assert alice.get("/api/activities", params={"kind": "meetup"}).json()["total"] == 1
    assert alice.get("/api/activities", params={"q": "rus"}).json()["items"][0]["id"] == rust["id"]
    assert alice.get("/api/activities", params={"q": "alice"}).json()["total"] == 3  # matches speaker names

    set_now(datetime(2026, 11, 17, 10, 30, tzinfo=TZ))
    live = alice.get("/api/activities", params={"state": ["live"]}).json()
    assert [i["title"] for i in live["items"]] == ["Rust"]
    open_ = alice.get("/api/activities", params={"state": ["upcoming", "live"]}).json()
    assert open_["total"] == 3
    set_now(datetime(2026, 11, 17, 12, 0, tzinfo=TZ))
    waiting = alice.get("/api/activities", params={"state": ["awaiting_close"]}).json()
    assert {i["title"] for i in waiting["items"]} == {"Rust", "Go"}


def test_mine_filter(as_user, create_activity):
    alice, bob = as_user("Alice"), as_user("Bob")
    a = create_activity(alice)
    create_activity(alice, start_time="16:00", end_time="17:00")
    bob.post(f"/api/activities/{a['id']}/signups", json={"role": "observer"})
    assert bob.get("/api/activities", params={"mine": True}).json()["total"] == 1
    assert alice.get("/api/activities", params={"mine": True}).json()["total"] == 2


def test_calendar_export(anon, as_user, create_activity):
    a = create_activity(as_user("Alice"), title="Ownership, borrowing; and more")
    r = anon.get(f"/api/activities/{a['id']}/calendar.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert "DTSTART:20261117T060000Z" in body  # 14:00 in Asia/Shanghai
    assert "SUMMARY:Ownership\\, borrowing\\; and more" in body


def test_contact_details_are_private(as_user, anon, create_activity):
    alice, bob, carol = as_user("Alice"), as_user("Bob"), as_user("Carol")
    a = create_activity(alice)
    bob.post(f"/api/activities/{a['id']}/signups", json={"role": "observer", "phone": "13800000000"})
    as_organizer = alice.get(f"/api/activities/{a['id']}").json()["signups"][0]
    assert as_organizer["email"] == bob.user.email and as_organizer["phone"] == "13800000000"
    as_peer = carol.get(f"/api/activities/{a['id']}").json()["signups"][0]
    assert as_peer["email"] is None and as_peer["phone"] is None and as_peer["user"]["name"] == "Bob"
    assert anon.get(f"/api/activities/{a['id']}").json()["signups"] == []


def test_today_is_computed_in_configured_timezone(as_user, create_activity):
    # 23:30 UTC on the 16th is already 07:30 on the 17th in Nanjing.
    from datetime import UTC

    alice = as_user("Alice")
    set_now(datetime(2026, 11, 16, 23, 30, tzinfo=UTC))
    a = create_activity(alice, date="2026-11-17", start_time="09:00", end_time="10:00")
    assert a["state"] == "upcoming"

from datetime import UTC, date, datetime, timedelta

import pytest

from app.models import Contribution, JobRun, OutboxEmail, User
from app.services import jobs, mail

from .conftest import TZ, error_code, outbox, set_now


@pytest.fixture
def history(as_user, make_user, create_activity, db):
    """Alice speaks; Bob reviews (rated by observer Carol); then time moves on and Alice closes."""
    alice, bob, carol = as_user("Alice"), as_user("Bob"), as_user("Carol")
    a = create_activity(alice)
    s = bob.post(f"/api/activities/{a['id']}/signups", json={"role": "reviewer", "review_topic": "x"}).json()
    carol.post(f"/api/activities/{a['id']}/signups", json={"role": "observer"})
    set_now(datetime(2026, 11, 17, 15, 30, tzinfo=TZ))
    alice.post(f"/api/activities/{a['id']}/close")
    bob.put(f"/api/signups/{s['id']}/review", json={"review_doc_url": "https://doc"})
    carol.put(f"/api/signups/{s['id']}/rating", json={"score": 8})
    # Backdate accounts so they're past the new-member grace period.
    for u in db.query(User).all():
        u.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    db.commit()
    return alice, bob, carol, a


def test_leaderboards(history, anon):
    boards = anon.get("/api/stats/leaderboards").json()
    assert [(e["user"]["name"], e["count"]) for e in boards["sharing"]] == [("Alice", 1)]
    assert {e["user"]["name"] for e in boards["participation"]} == {"Bob", "Carol"}
    assert boards["review_quality"][0]["user"]["name"] == "Bob" and boards["review_quality"][0]["score"] == 8
    assert boards["punctuality"][0] == {
        "user": {"id": history[0].user.id, "name": "Alice"},
        "closed_count": 1,
        "on_time_count": 1,
        "on_time_rate": 1.0,
    }


def test_untracked_users_are_hidden_from_leaderboards(history, anon, db):
    alice = history[0]
    db.get(User, alice.user.id).participation_tracked = False
    db.commit()
    assert anon.get("/api/stats/leaderboards").json()["sharing"] == []


def test_future_sessions_do_not_count_yet(as_user, create_activity, anon):
    create_activity(as_user("Alice"))
    assert anon.get("/api/stats/leaderboards").json()["sharing"] == []


def test_participation_watch(history, make_user, db, as_user):
    idle = make_user("Idle", created_at=datetime(2026, 1, 1, tzinfo=UTC))
    make_user("Newcomer")  # joined today: not flagged yet
    admin = as_user("Admin", admin=True, created_at=datetime(2026, 1, 1, tzinfo=UTC))
    dash = admin.get("/api/admin/dashboard").json()
    names = {u["name"] for u in dash["participation"]["inactive"]}
    # Carol only observed, which isn't an output; Alice spoke and Bob reviewed.
    assert names == {"Carol", "Idle", "Admin"}
    # A recorded contribution counts as an output.
    db.add(Contribution(user_id=idle.id, kind="sharing", date=date(2026, 11, 10)))
    db.commit()
    dash = admin.get("/api/admin/dashboard").json()
    assert "Idle" not in {u["name"] for u in dash["participation"]["inactive"]}


def test_admin_dashboard_reports(history, as_user, make_user, create_activity):
    admin = as_user("Admin", admin=True)
    dash = admin.get("/api/admin/dashboard", params={"month": "2026-11"}).json()
    m = dash["monthly"]
    assert m["activity_count"] == 1 and m["signup_count"] == 2 and m["closed_count"] == 1
    assert m["on_time_close_rate"] == 1.0
    reviewers = {e["user"]["name"]: e for e in dash["reviewers"]}
    assert reviewers["Bob"]["status"] == "needs_feedback" or reviewers["Bob"]["rating_count"] == 1
    assert admin.get("/api/admin/dashboard", params={"month": "2026-13"}).status_code == 400
    member = as_user("Member")
    assert member.get("/api/admin/dashboard").status_code == 403


def test_conflict_report(as_user, create_activity):
    alice, bob = as_user("Alice"), as_user("Bob")
    create_activity(alice, title="A")
    create_activity(bob, title="B", start_time="14:30", end_time="15:30", acknowledge_warnings=True)
    create_activity(bob, title="C", start_time="16:00", end_time="17:00")
    admin = as_user("Admin", admin=True)
    conflicts = admin.get("/api/admin/dashboard").json()["conflicts"]
    assert len(conflicts) == 1
    assert [a["title"] for a in conflicts[0]["activities"]] == ["A", "B"]


def test_group_health(as_user, make_user, create_activity):
    alice = as_user("Alice")
    bob = make_user("Bob")
    alice.post(
        "/api/groups",
        json={"name": "G", "goal": "g", "time_boundary": "t", "plan": "p", "member_ids": [bob.id]},
    )
    create_activity(alice)
    admin = as_user("Admin", admin=True)
    health = admin.get("/api/admin/dashboard").json()["groups"][0]
    assert health["recent_activity_count"] == 1 and health["member_count"] == 2
    assert health["status"] in ("healthy", "at_risk", "inactive")


def test_me_dashboard_tasks_and_recommendations(history, as_user, create_activity):
    _alice, bob, carol, _ = history
    future = create_activity(as_user("Dave"), title="Future talk", date="2026-11-20")
    carol_dash = carol.get("/api/me/dashboard").json()
    kinds = {t["kind"] for t in carol_dash["tasks"]}
    assert "inactive" in kinds and "join_group" in kinds
    rec = carol_dash["recommendations"][0]
    assert rec["activity"]["id"] == future["id"] and rec["suggested_role"] == "reviewer"

    bob_dash = bob.get("/api/me/dashboard").json()
    assert "inactive" not in {t["kind"] for t in bob_dash["tasks"]}
    assert bob_dash["metrics"]["review_score"] == 8
    assert bob_dash["metrics"]["ranks"]["review_quality"] == 1


def test_review_and_close_tasks(as_user, create_activity):
    alice, bob = as_user("Alice"), as_user("Bob")
    a = create_activity(alice)
    bob.post(f"/api/activities/{a['id']}/signups", json={"role": "reviewer", "review_topic": "x"})
    set_now(datetime(2026, 11, 17, 16, 0, tzinfo=TZ))
    assert "close_activity" in {t["kind"] for t in alice.get("/api/me/dashboard").json()["tasks"]}
    alice.post(f"/api/activities/{a['id']}/close")
    assert "submit_review" in {t["kind"] for t in bob.get("/api/me/dashboard").json()["tasks"]}


def test_public_profile(history):
    alice, _bob, carol, _a = history
    profile = carol.get(f"/api/users/{alice.user.id}").json()
    assert profile["user"]["name"] == "Alice"
    assert profile["history"][0]["kind"] == "spoke"
    assert profile["metrics"]["share_count"] == 1


def test_overview(history, anon):
    o = anon.get("/api/stats/overview").json()
    assert o["members"] == 3 and o["activities_this_month"] == 1


# ----- Jobs -----


def test_review_reminders_repeat_every_interval(history, as_user, create_activity, db):
    alice = history[0]
    late = as_user("Late")
    a = create_activity(alice, title="Second", date="2026-11-18")
    late.post(f"/api/activities/{a['id']}/signups", json={"role": "reviewer", "review_topic": "x"})
    set_now(datetime(2026, 11, 18, 16, 0, tzinfo=TZ))
    alice.post(f"/api/activities/{a['id']}/close")  # sends the first reminder immediately
    assert len([m for m in outbox(db, late.user.email) if "Please submit" in m.subject]) == 1
    assert jobs.send_review_reminders(db) == 0  # too soon
    set_now(datetime(2026, 11, 19, 16, 1, tzinfo=TZ))
    assert jobs.send_review_reminders(db) == 1
    assert jobs.send_review_reminders(db) == 0


def test_weekly_participation_report_runs_once(history, make_user, db, monkeypatch):
    monkeypatch.setenv("PARTICIPATION_REPORT_EMAIL", "cac@example.edu")
    from app.config import get_settings

    get_settings.cache_clear()
    make_user("Admin", admin=True)
    set_now(datetime(2026, 11, 22, 21, 0, tzinfo=TZ))  # Sunday, before 22:00
    assert jobs.send_participation_report(db) == 0
    set_now(datetime(2026, 11, 22, 22, 5, tzinfo=TZ))
    assert jobs.send_participation_report(db) >= 1
    assert jobs.send_participation_report(db) == 0  # already ran this week
    assert db.query(JobRun).count() == 1
    report = outbox(db, "cac@example.edu")
    assert len(report) == 1 and "Carol" in report[0].body
    assert any("We miss you" in m.subject for m in outbox(db, history[2].user.email))


def test_outbox_delivery_logs_without_smtp_and_retries_on_failure(db, monkeypatch):
    mail.queue(db, "a@example.edu", "Hello", "Body")
    db.commit()
    assert mail.deliver_pending(db) == 1
    assert db.query(OutboxEmail).one().sent_at is not None

    monkeypatch.setenv("SMTP_HOST", "smtp.invalid")
    monkeypatch.setenv("MAIL_FROM", "noreply@example.edu")
    from app.config import get_settings

    get_settings.cache_clear()

    def boom(*_):
        raise OSError("connection refused")

    monkeypatch.setattr(mail, "_send", boom)
    mail.queue(db, "b@example.edu", "Hi", "Body")
    db.commit()
    assert mail.deliver_pending(db) == 0
    failed = db.query(OutboxEmail).filter_by(to_address="b@example.edu").one()
    assert failed.attempts == 1 and "refused" in failed.last_error


def test_run_all_isolates_failures(db, monkeypatch):
    monkeypatch.setattr(jobs, "send_review_reminders", lambda _db: 1 / 0)
    results = jobs.run_all(db)
    assert results["review_reminders"] == -1 and results["emails"] == 0


# ----- Admin -----


def test_admin_user_management(as_user, db, anon):
    admin = as_user("Admin", admin=True)
    r = admin.post("/api/admin/users", json={"name": "New Person", "email": "New@Example.edu"})
    assert r.status_code == 201 and r.json()["is_claimed"] is False
    assert any("Your account is ready" in m.subject for m in outbox(db, "new@example.edu"))
    users = admin.get("/api/admin/users", params={"q": "new"}).json()
    assert [u["name"] for u in users] == ["New Person"]
    uid = users[0]["id"]
    link = admin.post(f"/api/admin/users/{uid}/password-link").json()["link"]
    token = link.split("token=")[1]
    assert (
        anon.post("/api/auth/password/reset", json={"token": token, "password": "my new password"}).status_code == 200
    )
    r = admin.patch(f"/api/admin/users/{uid}", json={"role": "admin", "participation_tracked": False})
    assert r.json()["role"] == "admin" and r.json()["participation_tracked"] is False


def test_rooms_and_slots_admin(as_user):
    admin, member = as_user("Admin", admin=True), as_user("Member")
    assert member.post("/api/admin/rooms", json={"name": "X"}).status_code == 403
    room = admin.post("/api/admin/rooms", json={"name": "CAC-301", "capacity": 30}).json()
    assert error_code(admin.post("/api/admin/rooms", json={"name": "cac-301"})) == "room_name_taken"
    r = admin.post(
        "/api/admin/room-slots",
        json={
            "room_id": room["id"],
            "date": "2026-11-17",
            "start_time": "14:00",
            "end_time": "18:00",
            "repeat_weeks": 3,
        },
    )
    assert r.status_code == 201 and [s["date"] for s in r.json()] == ["2026-11-17", "2026-11-24", "2026-12-01"]
    dup = admin.post(
        "/api/admin/room-slots",
        json={"room_id": room["id"], "date": "2026-11-17", "start_time": "15:00", "end_time": "16:00"},
    )
    assert error_code(dup) == "slot_exists"
    slots = member.get("/api/rooms/slots", params={"date_from": "2026-11-17", "date_to": "2026-12-31"}).json()
    assert len(slots) == 3 and slots[0]["start_time"] == "14:00"
    assert admin.delete(f"/api/admin/room-slots/{slots[0]['id']}").status_code == 204
    assert admin.delete(f"/api/admin/rooms/{room['id']}").status_code == 204
    assert member.get("/api/rooms").json() == []


def test_room_in_use_is_retired_not_deleted(as_user, room, open_room, create_activity):
    from .conftest import TOMORROW

    open_room(TOMORROW)
    admin = as_user("Admin", admin=True)
    a = create_activity(admin, room_id=room.id)
    admin.delete(f"/api/admin/rooms/{room.id}")
    assert admin.get(f"/api/activities/{a['id']}").json()["room"]["name"] == "CAC-101"
    assert [r["is_active"] for r in admin.get("/api/admin/rooms").json()] == [False]


def test_contributions_and_exports(history, as_user):
    admin = as_user("Admin", admin=True)
    carol = history[2]
    r = admin.post(
        "/api/admin/contributions",
        json={"user_id": carol.user.id, "kind": "meetup", "date": "2026-11-15", "note": "Hosted"},
    )
    assert r.status_code == 201
    assert admin.get("/api/admin/contributions").json()[0]["user"]["name"] == "Carol"
    csv = admin.get("/api/admin/export/activities.csv")
    assert csv.status_code == 200 and "Intro to Rust" in csv.text and csv.text.startswith("﻿")
    signups = admin.get("/api/admin/export/signups.csv").text
    assert "Bob" in signups and "https://doc" in signups
    assert carol.get("/api/admin/export/signups.csv").status_code == 403
    assert admin.delete(f"/api/admin/contributions/{r.json()['id']}").status_code == 204


def test_leaderboard_window(history, anon):
    boards = anon.get("/api/stats/leaderboards", params={"days": 30}).json()
    assert boards["since"] == (date(2026, 11, 17) - timedelta(days=30)).isoformat()
    assert boards["sharing"][0]["count"] == 1

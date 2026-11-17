from datetime import datetime

import pytest

from .conftest import NEXT_SUNDAY, TZ, error_code, outbox, set_now


@pytest.fixture
def session(as_user, create_activity):
    organizer = as_user("Organizer")
    activity = create_activity(organizer)
    return organizer, activity


def signup(client, activity, role="observer", **extra):
    return client.post(f"/api/activities/{activity['id']}/signups", json={"role": role, **extra})


def test_observer_signup_and_emails(session, as_user, db):
    organizer, activity = session
    bob = as_user("Bob")
    r = signup(bob, activity)
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "observer"
    detail = bob.get(f"/api/activities/{activity['id']}").json()
    assert detail["counts"]["observers"] == 1
    assert detail["viewer"]["signup_role"] == "observer"
    assert any("You're signed up" in m.subject for m in outbox(db, bob.user.email))
    assert any("New observer" in m.subject for m in outbox(db, organizer.user.email))


def test_emails_respect_recipient_language(session, as_user, db):
    _, activity = session
    zh = as_user("Li", locale="zh")
    signup(zh, activity)
    assert any("报名成功" in m.subject for m in outbox(db, zh.user.email))


def test_reviewer_needs_topic(session, as_user):
    _, activity = session
    r = signup(as_user("Bob"), activity, role="reviewer")
    assert r.status_code == 400 and error_code(r) == "review_topic_required"


def test_reviewer_limit(session, as_user):
    _, activity = session
    for i in range(3):
        assert signup(as_user(f"R{i}"), activity, role="reviewer", review_topic="Testing").status_code == 201
    r = signup(as_user("Late"), activity, role="reviewer", review_topic="Testing")
    assert r.status_code == 409 and error_code(r) == "reviewers_full"
    assert signup(as_user("Observer"), activity).status_code == 201  # observers are unlimited


def test_meetups_have_no_reviewer_limit_and_allow_participants(as_user, create_activity):
    host = as_user("Host")
    meetup = create_activity(host, kind="meetup", date=NEXT_SUNDAY.isoformat())
    for i in range(4):
        assert signup(as_user(f"R{i}"), meetup, role="reviewer", review_topic="x").status_code == 201
    assert signup(as_user("P"), meetup, role="participant").status_code == 201


def test_participant_role_only_for_meetups(session, as_user):
    _, activity = session
    r = signup(as_user("Bob"), activity, role="participant")
    assert error_code(r) == "invalid_role"


def test_no_double_signup_and_speakers_cannot_sign_up(session, as_user):
    organizer, activity = session
    bob = as_user("Bob")
    signup(bob, activity)
    r = signup(bob, activity, role="reviewer", review_topic="x")
    assert r.status_code == 409 and error_code(r) == "already_signed_up"
    assert error_code(signup(organizer, activity)) == "speaker_cannot_signup"


def test_cancel_rules(session, as_user):
    organizer, activity = session
    bob, carol = as_user("Bob"), as_user("Carol")
    s = signup(bob, activity).json()
    assert carol.delete(f"/api/signups/{s['id']}").status_code == 403
    assert bob.delete(f"/api/signups/{s['id']}").status_code == 204
    s = signup(bob, activity).json()
    set_now(datetime(2026, 11, 17, 14, 30, tzinfo=TZ))
    r = bob.delete(f"/api/signups/{s['id']}")
    assert r.status_code == 400 and error_code(r) == "activity_started"
    assert organizer.delete(f"/api/signups/{s['id']}").status_code == 204  # organisers can still tidy up


def test_closed_activities_refuse_signups(session, as_user):
    organizer, activity = session
    set_now(datetime(2026, 11, 17, 16, 0, tzinfo=TZ))
    organizer.post(f"/api/activities/{activity['id']}/close")
    assert error_code(signup(as_user("Bob"), activity)) == "activity_closed"


def test_review_submission_and_weighted_ratings(session, as_user):
    _organizer, activity = session
    reviewer, observer, passerby = as_user("Reviewer"), as_user("Observer"), as_user("Passerby")
    s = signup(reviewer, activity, role="reviewer", review_topic="Error handling").json()
    signup(observer, activity)

    r = observer.put(f"/api/signups/{s['id']}/rating", json={"score": 8})
    assert r.status_code == 409 and error_code(r) == "review_not_submitted"
    assert observer.put(f"/api/signups/{s['id']}/review", json={"review_doc_url": "https://x.y/z"}).status_code == 403
    bad = reviewer.put(f"/api/signups/{s['id']}/review", json={"review_doc_url": "javascript:alert(1)"})
    assert bad.status_code == 422
    ok = reviewer.put(f"/api/signups/{s['id']}/review", json={"review_doc_url": "https://www.yuque.com/doc/1"})
    assert ok.status_code == 200 and ok.json()["review_submitted_at"]

    assert error_code(reviewer.put(f"/api/signups/{s['id']}/rating", json={"score": 10})) == "cannot_rate_self"
    assert observer.put(f"/api/signups/{s['id']}/rating", json={"score": 11}).status_code == 422
    # Observers of the session carry ten times the weight of other raters.
    r = observer.put(f"/api/signups/{s['id']}/rating", json={"score": 9, "comment": "Thorough"})
    assert r.status_code == 200 and r.json()["my_score"] == 9
    r = passerby.put(f"/api/signups/{s['id']}/rating", json={"score": 3})
    assert r.json()["average_score"] == pytest.approx((9 * 10 + 3 * 1) / 11, abs=0.01)
    # Re-rating replaces the earlier score instead of adding a second one.
    r = passerby.put(f"/api/signups/{s['id']}/rating", json={"score": 9})
    assert r.json()["rating_count"] == 2 and r.json()["average_score"] == 9

    reviewer_view = next(
        x for x in reviewer.get(f"/api/activities/{activity['id']}").json()["signups"] if x["id"] == s["id"]
    )
    assert {r["rater"]["name"]: r["weight"] for r in reviewer_view["ratings"]} == {"Observer": 10, "Passerby": 1}
    peer_view = next(
        x for x in passerby.get(f"/api/activities/{activity['id']}").json()["signups"] if x["id"] == s["id"]
    )
    assert peer_view["ratings"] is None and peer_view["my_score"] == 9


def test_reviews_to_rate_queue(session, as_user):
    organizer, activity = session
    reviewer, observer = as_user("Reviewer"), as_user("Observer")
    s = signup(reviewer, activity, role="reviewer", review_topic="x").json()
    signup(observer, activity)
    reviewer.put(f"/api/signups/{s['id']}/review", json={"review_doc_url": "https://doc"})
    assert observer.get("/api/reviews/to-rate").json() == []  # only closed sessions
    set_now(datetime(2026, 11, 17, 16, 0, tzinfo=TZ))
    organizer.post(f"/api/activities/{activity['id']}/close")
    queue = observer.get("/api/reviews/to-rate").json()
    assert len(queue) == 1 and queue[0]["weight"] == 10 and queue[0]["reviewer"]["name"] == "Reviewer"
    observer.put(f"/api/signups/{s['id']}/rating", json={"score": 7})
    assert observer.get("/api/reviews/to-rate").json() == []
    assert reviewer.get("/api/reviews/to-rate").json() == []  # never your own


# ----- Invitations -----


def test_invite_flow_and_auto_accept_on_signup(session, as_user, make_user, db):
    organizer, activity = session
    guest = as_user("Guest")
    r = organizer.post(
        f"/api/activities/{activity['id']}/invites", json={"invitee_id": guest.user.id, "message": "You'd be great"}
    )
    assert r.status_code == 201, r.text
    invite = r.json()
    assert invite["status"] == "pending"
    assert any("Review invitation" in m.subject for m in outbox(db, guest.user.email))
    again = organizer.post(f"/api/activities/{activity['id']}/invites", json={"invitee_id": guest.user.id})
    assert error_code(again) == "already_invited"

    detail = guest.get(f"/api/activities/{activity['id']}").json()
    assert detail["viewer"]["pending_invite_id"] == invite["id"]
    assert guest.get("/api/me/summary").json() == {"pending_invites": 1}

    r = signup(guest, activity, role="reviewer", review_topic="Benchmarks")
    assert r.headers["X-Invites-Accepted"] == "1"
    mine = guest.get("/api/me/invites").json()
    assert mine[0]["status"] == "accepted"


def test_invite_permissions_and_transitions(session, as_user):
    organizer, activity = session
    guest, stranger = as_user("Guest"), as_user("Stranger")
    assert (
        stranger.post(f"/api/activities/{activity['id']}/invites", json={"invitee_id": guest.user.id}).status_code
        == 403
    )
    assert (
        error_code(
            organizer.post(
                f"/api/activities/{activity['id']}/invites", json={"invitee_id": guest.user.id, "source": "cac"}
            )
        )
        == "admin_required"
    )
    invite = organizer.post(f"/api/activities/{activity['id']}/invites", json={"invitee_id": guest.user.id}).json()

    assert stranger.post(f"/api/invites/{invite['id']}/status", json={"status": "declined"}).status_code == 403
    assert (
        error_code(guest.post(f"/api/invites/{invite['id']}/status", json={"status": "withdrawn"}))
        == "invalid_transition"
    )
    r = guest.post(f"/api/invites/{invite['id']}/status", json={"status": "declined"})
    assert r.status_code == 200 and r.json()["status"] == "declined"
    # Final states can't be reopened by members...
    r = guest.post(f"/api/invites/{invite['id']}/status", json={"status": "accepted"})
    assert error_code(r) == "invalid_transition"
    # ...but administrators can correct mistakes.
    admin = as_user("Admin", admin=True)
    assert admin.post(f"/api/invites/{invite['id']}/status", json={"status": "pending"}).json()["status"] == "pending"
    # The organiser can withdraw a pending invitation.
    assert (
        organizer.post(f"/api/invites/{invite['id']}/status", json={"status": "withdrawn"}).json()["status"]
        == "withdrawn"
    )
    listing = organizer.get(f"/api/activities/{activity['id']}/invites")
    assert listing.status_code == 200 and len(listing.json()) == 1
    assert stranger.get(f"/api/activities/{activity['id']}/invites").status_code == 403


def test_cannot_invite_speakers_or_existing_participants(session, as_user):
    organizer, activity = session
    bob = as_user("Bob")
    signup(bob, activity)
    r = organizer.post(f"/api/activities/{activity['id']}/invites", json={"invitee_id": bob.user.id})
    assert error_code(r) == "already_signed_up"
    r = organizer.post(f"/api/activities/{activity['id']}/invites", json={"invitee_id": organizer.user.id})
    assert error_code(r) == "cannot_invite_self"

from .conftest import error_code, outbox


def group_payload(**overrides):
    payload = {
        "name": "Systems Reading Group",
        "goal": "Read one OS paper a week",
        "time_boundary": "Autumn term 2026",
        "plan": "Thursdays, one presenter, two reviewers",
        "description": "",
        "member_ids": [],
    }
    payload.update(overrides)
    return payload


def test_group_needs_two_members(as_user, make_user):
    alice = as_user("Alice")
    r = alice.post("/api/groups", json=group_payload())
    assert r.status_code == 400 and error_code(r) == "group_too_small"
    bob = make_user("Bob")
    r = alice.post("/api/groups", json=group_payload(member_ids=[bob.id, alice.user.id]))
    assert r.status_code == 201
    g = r.json()
    assert g["leader"]["name"] == "Alice" and g["member_count"] == 2 and g["is_member"]
    assert [m["role"] for m in g["members"]] == ["leader", "member"]


def test_group_names_are_unique(as_user, make_user):
    alice = as_user("Alice")
    bob = make_user("Bob")
    alice.post("/api/groups", json=group_payload(member_ids=[bob.id]))
    r = alice.post("/api/groups", json=group_payload(name="systems reading group", member_ids=[bob.id]))
    assert error_code(r) == "group_name_taken"


def test_join_leave_transfer(as_user, make_user, db):
    alice = as_user("Alice")
    bob = make_user("Bob")
    g = alice.post("/api/groups", json=group_payload(member_ids=[bob.id])).json()
    carol = as_user("Carol")
    r = carol.post(f"/api/groups/{g['id']}/join")
    assert r.status_code == 200 and r.json()["member_count"] == 3
    assert any("Carol joined" in m.subject for m in outbox(db, alice.user.email))
    assert error_code(carol.post(f"/api/groups/{g['id']}/join")) == "already_member"

    assert error_code(alice.post(f"/api/groups/{g['id']}/leave")) == "leader_cannot_leave"
    assert carol.post(f"/api/groups/{g['id']}/transfer", json={"user_id": carol.user.id}).status_code == 403
    r = alice.post(f"/api/groups/{g['id']}/transfer", json={"user_id": carol.user.id})
    assert r.json()["leader"]["name"] == "Carol"
    assert alice.post(f"/api/groups/{g['id']}/leave").status_code == 200
    r = carol.delete(f"/api/groups/{g['id']}/members/{bob.id}")
    assert r.status_code == 200 and r.json()["member_count"] == 1


def test_update_and_archive(as_user, make_user):
    alice = as_user("Alice")
    bob = make_user("Bob")
    g = alice.post("/api/groups", json=group_payload(member_ids=[bob.id])).json()
    stranger = as_user("Stranger")
    assert stranger.patch(f"/api/groups/{g['id']}", json={"goal": "x"}).status_code == 403
    r = alice.patch(f"/api/groups/{g['id']}", json={"status": "archived"})
    assert r.json()["status"] == "archived"
    assert alice.get("/api/groups").json() == []
    assert len(alice.get("/api/groups", params={"include_archived": True}).json()) == 1
    assert error_code(stranger.post(f"/api/groups/{g['id']}/join")) == "group_archived"


def test_group_detail_lists_recent_activities(as_user, make_user, create_activity, anon):
    alice = as_user("Alice")
    bob = make_user("Bob")
    g = alice.post("/api/groups", json=group_payload(member_ids=[bob.id])).json()
    create_activity(alice)
    detail = anon.get(f"/api/groups/{g['id']}").json()
    assert detail["recent_activities"][0]["title"] == "Intro to Rust"
    assert detail["is_member"] is False

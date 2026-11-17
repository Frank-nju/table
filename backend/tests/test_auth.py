from app.security import SESSION_COOKIE

from .conftest import PASSWORD, error_code, outbox


def register(client, **overrides):
    payload = {"name": "Lin Yue", "email": "lin@example.edu", "password": PASSWORD, "locale": "zh"}
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def test_register_signs_in_and_me_returns_profile(anon):
    r = register(anon)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "lin@example.edu"
    assert r.json()["role"] == "member"
    me = anon.get("/api/auth/me").json()
    assert me["name"] == "Lin Yue" and me["locale"] == "zh"


def test_session_cookie_is_http_only(anon):
    r = register(anon)
    cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_email_is_case_insensitive_and_unique(anon):
    assert register(anon).status_code == 201
    r = register(anon, email="LIN@Example.edu")
    assert r.status_code == 409 and error_code(r) == "email_taken"


def test_password_must_be_long_enough(anon):
    r = register(anon, password="short")
    assert r.status_code == 422
    assert "password" in r.json()["error"]["details"]["fields"]


def test_login_logout_flow(anon, make_user):
    user = make_user("Zhou")
    assert anon.get("/api/auth/me").json() is None
    bad = anon.post("/api/auth/login", json={"email": user.email, "password": "wrong password"})
    assert bad.status_code == 401 and error_code(bad) == "invalid_credentials"
    ok = anon.post("/api/auth/login", json={"email": user.email.upper(), "password": PASSWORD})
    assert ok.status_code == 200
    assert anon.get("/api/auth/me").json()["id"] == user.id
    anon.post("/api/auth/logout")
    assert anon.get("/api/auth/me").json() is None


def test_login_is_rate_limited(anon, make_user):
    user = make_user()
    for _ in range(10):
        anon.post("/api/auth/login", json={"email": user.email, "password": "nope nope"})
    r = anon.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 429


def test_mutations_require_csrf_header(app, make_user):
    from fastapi.testclient import TestClient

    plain = TestClient(app)
    r = plain.post("/api/auth/login", json={"email": "a@b.c", "password": "x"})
    assert r.status_code == 403 and error_code(r) == "csrf_failed"


def test_protected_endpoints_require_login(anon):
    r = anon.post("/api/activities", json={})
    assert r.status_code in (401, 422)
    assert anon.get("/api/me/dashboard").status_code == 401


def test_bootstrap_admin(anon, monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAILS", "boss@example.edu, other@example.edu")
    from app.config import get_settings

    get_settings.cache_clear()
    r = register(anon, email="boss@example.edu")
    assert r.json()["role"] == "admin"


def test_registration_domain_allowlist(anon, monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "smail.nju.edu.cn")
    from app.config import get_settings

    get_settings.cache_clear()
    r = register(anon, email="someone@gmail.com")
    assert r.status_code == 400 and error_code(r) == "email_domain_not_allowed"
    assert register(anon, email="someone@smail.nju.edu.cn").status_code == 201


def test_password_reset_flow_invalidates_old_sessions(anon, make_user, login, db):
    user = make_user("Reset Me")
    old_session = login(user)
    assert old_session.get("/api/auth/me").json()["id"] == user.id

    assert anon.post("/api/auth/password/forgot", json={"email": user.email}).status_code == 202
    # Unknown emails get the same response, so accounts can't be probed.
    assert anon.post("/api/auth/password/forgot", json={"email": "ghost@example.edu"}).status_code == 202
    mails = outbox(db, user.email)
    assert len(mails) == 1
    token = mails[0].body.split("token=")[1].split()[0]

    r = anon.post("/api/auth/password/reset", json={"token": token, "password": "a brand new password"})
    assert r.status_code == 200
    # The link is single-use and older sessions are revoked.
    again = anon.post("/api/auth/password/reset", json={"token": token, "password": "another password!"})
    assert again.status_code == 400 and error_code(again) == "invalid_token"
    assert old_session.get("/api/auth/me").json() is None
    login_new = anon.post("/api/auth/login", json={"email": user.email, "password": "a brand new password"})
    assert login_new.status_code == 200


def test_unclaimed_account_cannot_be_registered_over(anon, db):
    from app.models import User

    db.add(User(name="Imported", email="imported@example.edu"))
    db.commit()
    r = register(anon, email="imported@example.edu")
    assert r.status_code == 409 and error_code(r) == "account_unclaimed"
    # ...and can't log in until a password is set.
    bad = anon.post("/api/auth/login", json={"email": "imported@example.edu", "password": PASSWORD})
    assert bad.status_code == 401


def test_change_password_and_profile_update(as_user):
    c = as_user("Wang")
    r = c.patch("/api/auth/me", json={"name": "Wang Fang", "locale": "zh", "phone": "138", "bio": "Hi"})
    assert r.status_code == 200 and r.json()["name"] == "Wang Fang" and r.json()["phone"] == "138"
    r = c.patch("/api/auth/me", json={"phone": ""})
    assert r.json()["phone"] is None
    bad = c.post("/api/auth/password/change", json={"current_password": "nope", "new_password": "something long"})
    assert bad.status_code == 400
    ok = c.post("/api/auth/password/change", json={"current_password": PASSWORD, "new_password": "something long"})
    assert ok.status_code == 200
    assert c.get("/api/auth/me").json() is not None  # current session survives


def test_deactivated_user_is_signed_out(as_user, login, make_user):
    admin = as_user("Admin", admin=True)
    member = make_user("Member")
    session = login(member)
    r = admin.patch(f"/api/admin/users/{member.id}", json={"is_active": False})
    assert r.status_code == 200
    assert session.get("/api/auth/me").json() is None


def test_admin_cannot_demote_self(as_user):
    admin = as_user("Admin", admin=True)
    r = admin.patch(f"/api/admin/users/{admin.user.id}", json={"role": "member"})
    assert r.status_code == 400 and error_code(r) == "cannot_demote_self"


def test_public_config(anon):
    cfg = anon.get("/api/config").json()
    assert cfg["reviewer_limit"] == 3
    assert cfg["meetup_window"] == ["14:00", "18:00"]
    assert cfg["time_grid"][0] == "09:00"


def test_unknown_api_route_is_json_404(anon):
    r = anon.get("/api/nope")
    assert r.status_code == 404 and error_code(r) == "not_found"

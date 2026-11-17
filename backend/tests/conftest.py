"""Shared fixtures.

Tests run against SQLite by default. Set TEST_DATABASE_URL to run the same suite against MySQL or
PostgreSQL, e.g. TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost/cac_test pytest
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PUBLIC_BASE_URL", "https://cac.example.edu")
os.environ.setdefault("FRONTEND_DIST", "/nonexistent")
os.environ.setdefault("RUN_SCHEDULER", "false")

from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session

from app import db as db_module
from app.config import get_settings
from app.db import Base, configure_engine, freeze_time, make_engine
from app.main import create_app
from app.models import OutboxEmail, Room, RoomSlot, User, UserRole
from app.security import auth_limiter, hash_password

TZ = ZoneInfo("Asia/Shanghai")
# Monday 16 November 2026, 09:00 in Nanjing. Sunday 22 November is the next CAC Meetup day.
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=TZ)
TOMORROW = date(2026, 11, 17)
NEXT_SUNDAY = date(2026, 11, 22)
PASSWORD = "correct horse battery"


@pytest.fixture(scope="session")
def engine():
    url = os.environ["DATABASE_URL"]
    if url == "sqlite:///:memory:":
        eng = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        from sqlalchemy import event

        @event.listens_for(eng, "connect")
        def _fk(conn, _):  # type: ignore[no-untyped-def]
            conn.execute("PRAGMA foreign_keys=ON")
    else:
        eng = make_engine(url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    configure_engine(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(autouse=True)
def clean(engine) -> Iterator[None]:
    get_settings.cache_clear()
    auth_limiter.reset()
    freeze_time(NOW.astimezone(UTC))
    yield
    freeze_time(None)
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db(engine) -> Iterator[Session]:
    session = db_module.SessionLocal()
    yield session
    session.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def anon(app) -> TestClient:
    return TestClient(app, headers={"X-Requested-With": "test"})


def set_now(moment: datetime) -> None:
    freeze_time(moment.astimezone(UTC))


def advance(**delta: float) -> None:
    current = db_module.utcnow()
    freeze_time(current + timedelta(**delta))


class Client(TestClient):
    user: User


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    counter = {"n": 0}

    def _make(name: str | None = None, *, admin: bool = False, email: str | None = None, **fields) -> User:  # type: ignore[no-untyped-def]
        counter["n"] += 1
        name = name or f"User {counter['n']}"
        user = User(
            name=name,
            email=email or f"{name.lower().replace(' ', '.')}@example.edu",
            password_hash=hash_password(PASSWORD),
            role=UserRole.ADMIN if admin else UserRole.MEMBER,
            **fields,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def login(app) -> Callable[[User], Client]:
    def _login(user: User) -> Client:
        client = Client(app, headers={"X-Requested-With": "test"})
        r = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        client.user = user
        return client

    return _login


@pytest.fixture
def as_user(make_user, login) -> Callable[..., Client]:
    def _as(name: str | None = None, **kwargs) -> Client:  # type: ignore[no-untyped-def]
        return login(make_user(name, **kwargs))

    return _as


@pytest.fixture
def room(db: Session) -> Room:
    r = Room(name="CAC-101", capacity=40)
    db.add(r)
    db.commit()
    return r


@pytest.fixture
def open_room(db: Session, room: Room) -> Callable[..., RoomSlot]:
    def _open(d: date, start: str = "09:00", end: str = "22:00", target: Room | None = None) -> RoomSlot:
        from datetime import time

        slot = RoomSlot(
            room_id=(target or room).id, date=d, start_time=time.fromisoformat(start), end_time=time.fromisoformat(end)
        )
        db.add(slot)
        db.commit()
        return slot

    return _open


def activity_payload(**overrides) -> dict:  # type: ignore[no-untyped-def,type-arg]
    payload = {
        "title": "Intro to Rust",
        "description": "Ownership and borrowing in 45 minutes.",
        "date": TOMORROW.isoformat(),
        "start_time": "14:00",
        "end_time": "15:00",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def create_activity() -> Callable[..., dict]:  # type: ignore[type-arg]
    def _create(client: TestClient, expect: int = 201, **overrides) -> dict:  # type: ignore[no-untyped-def,type-arg]
        r = client.post("/api/activities", json=activity_payload(**overrides))
        assert r.status_code == expect, r.text
        return r.json()

    return _create


def outbox(db: Session, to: str | None = None) -> list[OutboxEmail]:
    db.expire_all()
    rows = db.query(OutboxEmail).order_by(OutboxEmail.id).all()
    return [r for r in rows if to is None or r.to_address == to]


def error_code(response) -> str:  # type: ignore[no-untyped-def]
    return response.json()["error"]["code"]

"""Database engine, session factory and shared column types."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


class UTCDateTime(TypeDecorator[datetime]):
    """Stores timestamps as naive UTC and always returns timezone-aware UTC datetimes.

    This behaves the same on SQLite, MySQL and PostgreSQL, which handle time zones differently.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; use utcnow()")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


_frozen_now: datetime | None = None


def utcnow() -> datetime:
    """The current time in UTC. Every 'now' in the app goes through here so tests can control time."""
    return _frozen_now if _frozen_now is not None else datetime.now(UTC)


def freeze_time(moment: datetime | None) -> None:
    """Pin utcnow() to `moment` (an aware datetime), or pass None to return to the real clock."""
    global _frozen_now
    if moment is not None and moment.tzinfo is None:
        raise ValueError("freeze_time needs an aware datetime")
    _frozen_now = moment


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        path = url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    else:
        kwargs["pool_recycle"] = 1800
    engine = create_engine(url, **kwargs)  # type: ignore[arg-type]
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def configure_engine(engine: Engine) -> None:
    """Point the application at a specific engine (used by tests and scripts)."""
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

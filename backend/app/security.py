"""Password hashing, signed tokens and a small in-memory rate limiter."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings
from app.db import utcnow
from app.errors import TooManyRequests

SESSION_COOKIE = "cac_session"
_hasher = PasswordHasher()
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_token(user_id: int, token_version: int, purpose: str, ttl: timedelta) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=_ALGORITHM)


def decode_token(token: str, purpose: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[_ALGORITHM],
            options={"verify_exp": False, "require": ["exp", "sub", "purpose"]},
        )
    except jwt.PyJWTError:
        return None
    # Expiry is checked against the app clock (utcnow) rather than the system clock, so it agrees
    # with every other time-based rule in the app.
    if payload.get("purpose") != purpose or int(payload["exp"]) <= int(utcnow().timestamp()):
        return None
    return payload


def create_session_token(user_id: int, token_version: int) -> str:
    return create_token(user_id, token_version, "session", timedelta(hours=get_settings().session_ttl_hours))


def create_password_token(user_id: int, token_version: int) -> str:
    ttl = timedelta(minutes=get_settings().password_reset_ttl_minutes)
    return create_token(user_id, token_version, "password", ttl)


class RateLimiter:
    """Sliding-window limiter keyed by an arbitrary string (e.g. client IP + action).

    It is per-process, which is enough to blunt password guessing; put a proxy-level limit in
    front for anything stricter.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise TooManyRequests("Too many attempts. Please wait a few minutes and try again.")
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_limiter = RateLimiter(limit=10, window_seconds=300)

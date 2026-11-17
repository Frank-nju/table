"""FastAPI dependencies shared by the routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import Forbidden, Unauthorized
from app.models import User
from app.security import SESSION_COOKIE, decode_token

DB = Annotated[Session, Depends(get_db)]


def get_optional_user(request: Request, db: DB) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    payload = decode_token(token, "session")
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active or user.token_version != payload.get("tv"):
        return None
    return user


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise Unauthorized("Please sign in to continue.")
    return user


def get_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise Forbidden("Only administrators can do this.", code="admin_required")
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin)]

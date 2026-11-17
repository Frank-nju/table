"""Accounts: registration, sign-in, password resets and administration."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import utcnow
from app.errors import BadRequest, Conflict, Forbidden, NotFound, Unauthorized
from app.models import User, UserRole
from app.schemas import AdminUserCreate, AdminUserUpdate, MeUpdate, RegisterIn
from app.security import (
    create_password_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.services import mail


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user(db: Session, user_id: int, *, active_only: bool = True) -> User:
    user = db.get(User, user_id)
    if user is None or (active_only and not user.is_active):
        raise NotFound("User not found.", code="user_not_found")
    return user


def get_users(db: Session, ids: list[int]) -> list[User]:
    """Fetch active users, preserving order and failing if any id is unknown."""
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        return []
    found = {u.id: u for u in db.scalars(select(User).where(User.id.in_(unique_ids), User.is_active))}
    missing = [i for i in unique_ids if i not in found]
    if missing:
        raise BadRequest("Some selected people could not be found.", code="user_not_found", details={"ids": missing})
    return [found[i] for i in unique_ids]


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def _check_domain(email: str) -> None:
    domains = get_settings().allowed_email_domains
    if domains and email.rsplit("@", 1)[-1] not in domains:
        raise BadRequest(
            "Please use your organisation email address.",
            code="email_domain_not_allowed",
            details={"domains": domains},
        )


def _maybe_promote(user: User) -> None:
    if user.email and user.email in get_settings().bootstrap_admin_emails:
        user.role = UserRole.ADMIN


def register(db: Session, data: RegisterIn) -> User:
    settings = get_settings()
    if not settings.allow_registration:
        raise Forbidden("Registration is closed. Ask an administrator for an account.", code="registration_closed")
    email = normalize_email(data.email)
    _check_domain(email)
    existing = find_by_email(db, email)
    if existing is not None:
        if existing.is_claimed:
            raise Conflict("An account with this email already exists.", code="email_taken")
        # An imported or admin-created account: let the person claim it by email verification only.
        raise Conflict(
            "An account already exists for this email. Use “Forgot password” to activate it.",
            code="account_unclaimed",
        )
    user = User(name=data.name, email=email, password_hash=hash_password(data.password), locale=data.locale)
    _maybe_promote(user)
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = find_by_email(db, email)
    if user is None or not verify_password(user.password_hash, password):
        raise Unauthorized("Incorrect email or password.", code="invalid_credentials")
    if not user.is_active:
        raise Forbidden("This account has been deactivated.", code="account_inactive")
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    _maybe_promote(user)
    user.last_login_at = utcnow()
    db.commit()
    return user


def password_link(user: User) -> str:
    token = create_password_token(user.id, user.token_version)
    return mail.link(f"/reset-password?token={token}")


def request_password_reset(db: Session, email: str) -> None:
    """Always succeeds from the caller's point of view, so it can't be used to probe for accounts."""
    user = find_by_email(db, email)
    if user is None or not user.is_active:
        return
    mail.notify(db, user, "password_reset", link=password_link(user), ttl=get_settings().password_reset_ttl_minutes)
    db.commit()


def reset_password(db: Session, token: str, password: str) -> User:
    payload = decode_token(token, "password")
    user = db.get(User, int(payload["sub"])) if payload else None
    if user is None or payload is None or user.token_version != payload.get("tv") or not user.is_active:
        raise BadRequest("This link is invalid or has expired. Request a new one.", code="invalid_token")
    user.password_hash = hash_password(password)
    user.token_version += 1  # invalidates the link and every existing session
    user.last_login_at = utcnow()
    db.commit()
    return user


def change_password(db: Session, user: User, current: str, new: str) -> User:
    if not verify_password(user.password_hash, current):
        raise BadRequest("Your current password is incorrect.", code="invalid_credentials")
    user.password_hash = hash_password(new)
    user.token_version += 1
    db.commit()
    return user


def update_me(db: Session, user: User, data: MeUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        if field in ("phone", "bio"):
            setattr(user, field, value or None)  # empty string clears the field
        elif value is not None:
            setattr(user, field, value)
    db.commit()
    return user


def search(db: Session, q: str, limit: int = 20) -> list[User]:
    stmt = select(User).where(User.is_active).order_by(User.name).limit(limit)
    q = q.strip()
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    return list(db.scalars(stmt))


# ----- Administration -----


def admin_list(db: Session, q: str = "") -> list[User]:
    stmt = select(User).order_by(User.is_active.desc(), User.name)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    return list(db.scalars(stmt))


def admin_create(db: Session, data: AdminUserCreate) -> User:
    email = normalize_email(data.email) if data.email else None
    if email and find_by_email(db, email):
        raise Conflict("An account with this email already exists.", code="email_taken")
    user = User(name=data.name, email=email)
    db.add(user)
    db.flush()
    if email:
        mail.notify(db, user, "account_invite", link=password_link(user), ttl=get_settings().password_reset_ttl_minutes)
    db.commit()
    return user


def admin_update(db: Session, actor: User, user: User, data: AdminUserUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    if user.id == actor.id and (changes.get("role") == UserRole.MEMBER or changes.get("is_active") is False):
        raise BadRequest("You can't remove your own administrator access.", code="cannot_demote_self")
    if changes.get("email"):
        email = normalize_email(changes["email"])
        other = find_by_email(db, email)
        if other is not None and other.id != user.id:
            raise Conflict("An account with this email already exists.", code="email_taken")
        changes["email"] = email
    for field, value in changes.items():
        if value is not None:
            setattr(user, field, value)
    if changes.get("is_active") is False:
        user.token_version += 1  # sign them out everywhere
    db.commit()
    return user

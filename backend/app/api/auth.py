from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.config import get_settings
from app.deps import DB, CurrentUser, OptionalUser
from app.models import User
from app.schemas import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    Me,
    MeUpdate,
    RegisterIn,
    ResetPasswordIn,
)
from app.security import SESSION_COOKIE, auth_limiter, create_session_token
from app.services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _start_session(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id, user.token_version),
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=Me, status_code=201)
def register(data: RegisterIn, request: Request, response: Response, db: DB) -> User:
    auth_limiter.hit(f"register:{_client(request)}")
    user = user_service.register(db, data)
    _start_session(response, user)
    return user


@router.post("/login", response_model=Me)
def login(data: LoginIn, request: Request, response: Response, db: DB) -> User:
    auth_limiter.hit(f"login:{_client(request)}:{data.email.lower()}")
    user = user_service.authenticate(db, data.email, data.password)
    _start_session(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=Me | None)
def me(user: OptionalUser) -> User | None:
    return user


@router.patch("/me", response_model=Me)
def update_me(data: MeUpdate, user: CurrentUser, db: DB) -> User:
    return user_service.update_me(db, user, data)


@router.post("/password/forgot", status_code=202)
def forgot_password(data: ForgotPasswordIn, request: Request, db: DB) -> dict[str, bool]:
    auth_limiter.hit(f"forgot:{_client(request)}")
    user_service.request_password_reset(db, data.email)
    return {"ok": True}


@router.post("/password/reset", response_model=Me)
def reset_password(data: ResetPasswordIn, request: Request, response: Response, db: DB) -> User:
    auth_limiter.hit(f"reset:{_client(request)}")
    user = user_service.reset_password(db, data.token, data.password)
    _start_session(response, user)
    return user


@router.post("/password/change", response_model=Me)
def change_password(data: ChangePasswordIn, response: Response, user: CurrentUser, db: DB) -> User:
    user = user_service.change_password(db, user, data.current_password, data.new_password)
    _start_session(response, user)  # other sessions are signed out; keep this one
    return user

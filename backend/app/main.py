"""Application factory."""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import activities, admin, auth, community
from app.config import get_settings
from app.db import SessionLocal, get_engine
from app.errors import AppError
from app.scheduling import time_grid
from app.schemas import PublicConfig

log = logging.getLogger("app")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _error(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:  # type: ignore[type-arg]
    body: dict[str, object] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details  # type: ignore[index]
    return JSONResponse(body, status_code=status)


def _scheduler_loop(stop: threading.Event) -> None:
    from app.services.jobs import run_all

    interval = get_settings().scheduler_interval_seconds
    while not stop.wait(interval):
        with SessionLocal() as db:
            run_all(db)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    stop = threading.Event()
    if settings.run_scheduler:
        threading.Thread(target=_scheduler_loop, args=(stop,), daemon=True, name="scheduler").start()
        log.info("Embedded scheduler started")
    yield
    stop.set()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            fields[".".join(loc) or "_"] = err["msg"].removeprefix("Value error, ")
        return _error(422, "validation_error", "Some fields need attention.", {"fields": fields})

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error", exc_info=exc)
        return _error(500, "internal_error", "Something went wrong on our side. Please try again.")

    @app.middleware("http")
    async def guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        # CSRF protection: browsers can't attach custom headers to cross-site form posts, and
        # cross-origin fetches with custom headers require a CORS preflight we never approve.
        if (
            request.method in UNSAFE_METHODS
            and request.url.path.startswith("/api/")
            and "x-requested-with" not in request.headers
        ):
            return _error(403, "csrf_failed", "Missing X-Requested-With header.")
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/api/") and request.url.path != "/api/docs":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    api = APIRouter(prefix="/api")
    api.include_router(auth.router)
    api.include_router(activities.router)
    api.include_router(community.router)
    api.include_router(admin.router)

    @api.get("/config", response_model=PublicConfig, tags=["meta"])
    def public_config() -> PublicConfig:
        return PublicConfig(
            app_name=settings.app_name,
            timezone=settings.timezone,
            time_grid=time_grid(settings),
            slot_minutes=settings.slot_minutes,
            reviewer_limit=settings.reviewer_limit,
            meetup_weekday=settings.meetup_weekday,
            meetup_window=(
                settings.meetup_window_start.strftime("%H:%M"),
                settings.meetup_window_end.strftime("%H:%M"),
            ),
            close_grace_minutes=settings.close_grace_minutes,
            observer_rating_weight=settings.observer_rating_weight,
            participation_lookback_days=settings.participation_lookback_days,
            allow_registration=settings.allow_registration,
            allowed_email_domains=settings.allowed_email_domains,
            mail_enabled=settings.mail_enabled,
        )

    @api.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_not_found(path: str) -> JSONResponse:
        return _error(404, "not_found", f"No API endpoint at /api/{path}")

    app.include_router(api)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> JSONResponse:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"})

    _mount_frontend(app, Path(settings.frontend_dist))
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built single-page app, falling back to index.html for client-side routes."""
    if not dist.is_absolute():
        dist = (Path(__file__).resolve().parent.parent / dist).resolve()
    index = dist / "index.html"
    if not index.exists():
        log.info("Frontend build not found at %s; serving the API only", dist)
        return
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    csp = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Content-Security-Policy": csp, "Cache-Control": "no-cache"})

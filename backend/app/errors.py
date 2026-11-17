"""Domain errors. Every error carries a stable `code` that clients can translate."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    default_code = "bad_request"

    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}


class BadRequest(AppError):
    status_code = 400
    default_code = "bad_request"


class Unauthorized(AppError):
    status_code = 401
    default_code = "not_authenticated"


class Forbidden(AppError):
    status_code = 403
    default_code = "forbidden"


class NotFound(AppError):
    status_code = 404
    default_code = "not_found"


class Conflict(AppError):
    status_code = 409
    default_code = "conflict"


class TooManyRequests(AppError):
    status_code = 429
    default_code = "rate_limited"

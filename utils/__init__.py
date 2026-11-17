"""Exception handling utilities.
Centralizes application exception types and handling behavior."""

import logging

logger = logging.getLogger(__name__)

# ===== Custom exception classes =====

class AppError(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseError(AppError):
    """Exception raised when a database operation fails."""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, code="DATABASE_ERROR", status_code=500)


class ValidationError(AppError):
    """Data validation exception."""
    def __init__(self, message: str = "Data validation failed"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class NotFoundError(AppError):
    """Exception raised when a resource cannot be found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class AuthError(AppError):
    """Exception raised when permission validation fails."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTH_ERROR", status_code=403)


class ConflictError(AppError):
    """Exception raised when a resource conflicts with the current state."""
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, code="CONFLICT", status_code=409)


# ===== Exception handling helpers =====

def safe_execute(default=None, log_error=True):
    """Safely run a function, catch exceptions, and return a default value.

Usage:
    @safe_execute(default=set())
    def get_columns(table_name):
        ..."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if log_error:
                    logger.error("%s: %s", func.__name__, exc)
                return default() if callable(default) else default
        return wrapper
    return decorator


def handle_db_error(func):
    """
    databaseoperationexceptionhandledecorator
    Convert pymysql exceptioninto DatabaseError
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # catch pymysql exception
            error_msg = str(exc)
            logger.error("[DB_ERROR] %s: %s", func.__name__, error_msg)
            raise DatabaseError(f"Database operation failed: {error_msg}")
    return wrapper


# ===== Response helpers =====

def success_response(data=None, message="Operation completed successfully"):
    """Build a successful JSON response."""
    response = {"ok": True, "message": message}
    if data is not None:
        response.update(data)
    return response


def error_response(message: str, code: str = "ERROR", status_code: int = 400):
    """Build an error JSON response."""
    return {"ok": False, "message": message, "code": code}, status_code


# ===== Common helpers =====

from utils.helpers import safe_text, safe_bool

__all__ = [
    "AppError", "DatabaseError", "ValidationError", "NotFoundError",
    "AuthError", "ConflictError",
    "safe_execute", "handle_db_error",
    "success_response", "error_response",
    "safe_text", "safe_bool",
]
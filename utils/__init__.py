"""
异常处理工具模块

统一管理应用中的异常类型和处理方式
"""

import logging

logger = logging.getLogger(__name__)

# ===== 自定义异常类 =====

class AppError(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseError(AppError):
    """数据库操作异常"""
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, code="DATABASE_ERROR", status_code=500)


class ValidationError(AppError):
    """数据验证异常"""
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class NotFoundError(AppError):
    """资源不存在异常"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class AuthError(AppError):
    """权限验证异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code="AUTH_ERROR", status_code=403)


class ConflictError(AppError):
    """资源冲突异常"""
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, code="CONFLICT", status_code=409)


# ===== 异常处理工具函数 =====

def safe_execute(default=None, log_error=True):
    """
    安全执行装饰器，捕获异常并返回默认值

    用法：
        @safe_execute(default=set())
        def get_columns(table_name):
            ...
    """
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
    数据库操作异常处理装饰器
    将 pymysql 异常转换为 DatabaseError
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # 捕获 pymysql 异常
            error_msg = str(exc)
            logger.error("[DB_ERROR] %s: %s", func.__name__, error_msg)
            raise DatabaseError(f"数据库操作失败: {error_msg}")
    return wrapper


# ===== 响应构建工具 =====

def success_response(data=None, message="操作成功"):
    """构建成功响应"""
    response = {"ok": True, "message": message}
    if data is not None:
        response.update(data)
    return response


def error_response(message: str, code: str = "ERROR", status_code: int = 400):
    """构建错误响应"""
    return {"ok": False, "message": message, "code": code}, status_code


# ===== 通用辅助函数 =====

from utils.helpers import safe_text, safe_bool

__all__ = [
    "AppError", "DatabaseError", "ValidationError", "NotFoundError",
    "AuthError", "ConflictError",
    "safe_execute", "handle_db_error",
    "success_response", "error_response",
    "safe_text", "safe_bool",
]
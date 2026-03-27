"""
路由模块

按功能分组管理 API 路由
"""

from routes.activity import activity_bp
from routes.signup import signup_bp

__all__ = ["activity_bp", "signup_bp"]
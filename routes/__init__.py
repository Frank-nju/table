"""
路由模块

按功能分组管理 API 路由
"""

from routes.activity import activity_bp
from routes.signup import signup_bp
from routes.cac import cac_bp
from routes.group import group_bp
from routes.profile import profile_bp
from routes.invite import invite_bp
from routes.stats import stats_bp

__all__ = ["activity_bp", "signup_bp", "cac_bp", "group_bp", "profile_bp", "invite_bp", "stats_bp"]
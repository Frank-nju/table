"""
统计路由模块

统计和排行榜相关的 API 路由
"""

from flask import Blueprint, jsonify

from services.stats import (
    build_review_quality_stats, build_share_leaderboard,
    build_participation_leaderboard, build_punctuality_leaderboard,
    build_boundary_stats
)
from utils.cache import cached_build

stats_bp = Blueprint('stats', __name__, url_prefix='/api')


@stats_bp.get("/leaderboards")
def api_leaderboards():
    """获取各类榜单与边界预警"""
    _, review_quality_ranking = build_review_quality_stats()
    boundary_stats = build_boundary_stats()
    return jsonify({
        "ok": True,
        "leaderboards": {
            "sharing": build_share_leaderboard(),
            "participation": build_participation_leaderboard(),
            "review_quality": review_quality_ranking,
            "punctuality": build_punctuality_leaderboard(),
        },
        "boundary_watch": boundary_stats,
    })


@stats_bp.get("/stats")
def api_stats():
    """获取统计数据"""
    from services.activity import list_activities, count_signups_by_activity
    from services.signup import list_signups
    from services.group import list_interest_groups

    activities = list_activities()
    signups = list_signups()
    groups = list_interest_groups()

    return jsonify({
        "ok": True,
        "stats": {
            "total_activities": len(activities),
            "total_signups": len(signups),
            "total_groups": len(groups),
        }
    })
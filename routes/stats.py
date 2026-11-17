"""Statistics routes.
API endpoints for statistics and leaderboards."""

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
    """Get leaderboards and participation-threshold alerts."""
    def build_payload():
        _, review_quality_ranking = build_review_quality_stats()
        boundary_stats = build_boundary_stats()
        return {
            "ok": True,
            "leaderboards": {
                "sharing": build_share_leaderboard(),
                "participation": build_participation_leaderboard(),
                "review_quality": review_quality_ranking,
                "punctuality": build_punctuality_leaderboard(),
            },
            "boundary_watch": boundary_stats,
        }
    return jsonify(cached_build("api_leaderboards_payload", 30, build_payload))


@stats_bp.get("/stats")
def api_stats():
    """Get statistics."""
    from services.activity import list_activities
    from services.stats import build_boundary_stats

    # TODO: Migrate more helper functions to complete this interface.
    activities = list_activities()
    boundary_watch = build_boundary_stats()

    return jsonify({
        "ok": True,
        "total_activities": len(activities),
        "boundary_watch": boundary_watch,
    })

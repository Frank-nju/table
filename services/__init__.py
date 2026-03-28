"""
服务模块

导出各种业务服务
"""

from services.email import EmailService, send_email, send_email_async
from services.activity import (
    list_activities, get_activity_by_id, get_activity_details,
    create_activity, update_activity, delete_activity, close_activity,
    get_activity_signups, count_signups_by_activity, get_signup_stats,
    activity_is_closed, get_activity_state
)
from services.signup import (
    list_signups, get_signup_by_id, get_signup_name, get_signup_email,
    get_signups_by_activity, count_signups_by_activity as count_signups,
    serialize_signup, create_signup, delete_signup, update_signup_review_doc
)
from services.cac_admin import (
    list_cac_admins, is_cac_admin, is_cac_user, add_cac_admin, remove_cac_admin,
    list_cac_room_slots, add_cac_room_slot, remove_cac_room_slot
)
from services.group import (
    list_interest_groups, get_interest_group_by_id, serialize_interest_group,
    get_group_ids_for_member, create_group, join_group, leave_group
)
from services.profile import (
    list_user_profiles, get_user_profile, get_user_email, upsert_user_profile,
    serialize_profile, get_profile_summary
)
from services.invite import (
    list_review_invites, get_invites_by_activity, get_invites_for_user,
    create_review_invite, update_invite_status, serialize_review_invite
)
from services.rating import (
    list_review_ratings, get_rating_by_id, get_ratings_by_signup,
    serialize_rating, create_review_rating
)
from services.stats import (
    build_review_quality_stats, build_share_leaderboard,
    build_participation_leaderboard, build_punctuality_leaderboard,
    build_boundary_stats
)

__all__ = [
    # 邮件服务
    "EmailService", "send_email", "send_email_async",
    # 活动服务
    "list_activities", "get_activity_by_id", "get_activity_details",
    "create_activity", "update_activity", "delete_activity", "close_activity",
    "get_activity_signups", "count_signups_by_activity", "get_signup_stats",
    "activity_is_closed", "get_activity_state",
    # 报名服务
    "list_signups", "get_signup_by_id", "get_signup_name", "get_signup_email",
    "get_signups_by_activity", "count_signups",
    "serialize_signup", "create_signup", "delete_signup", "update_signup_review_doc",
    # CAC 管理服务
    "list_cac_admins", "is_cac_admin", "is_cac_user", "add_cac_admin", "remove_cac_admin",
    "list_cac_room_slots", "add_cac_room_slot", "remove_cac_room_slot",
    # 兴趣组服务
    "list_interest_groups", "get_interest_group_by_id", "serialize_interest_group",
    "get_group_ids_for_member", "create_group", "join_group", "leave_group",
    # 用户档案服务
    "list_user_profiles", "get_user_profile", "get_user_email", "upsert_user_profile",
    "serialize_profile", "get_profile_summary",
    # 评议邀请服务
    "list_review_invites", "get_invites_by_activity", "get_invites_for_user",
    "create_review_invite", "update_invite_status", "serialize_review_invite",
    # 评议评分服务
    "list_review_ratings", "get_rating_by_id", "get_ratings_by_signup",
    "serialize_rating", "create_review_rating",
    # 统计服务
    "build_review_quality_stats", "build_share_leaderboard",
    "build_participation_leaderboard", "build_punctuality_leaderboard",
    "build_boundary_stats",
]
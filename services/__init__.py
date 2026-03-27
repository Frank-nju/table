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
]
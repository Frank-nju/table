import logging

import os
import re
import json
import smtplib
import threading
import time
import tempfile
import uuid
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from email.message import EmailMessage

# Custom exception handling
from utils import (
    AppError, DatabaseError, ValidationError, NotFoundError, AuthError, ConflictError,
    success_response, error_response, safe_text, safe_bool
)
from utils.versioned_cache import cached_build, touch_version, clear_all as clear_versioned_cache

# Route blueprints
from routes import (
    activity_bp, signup_bp, cac_bp, group_bp,
    profile_bp, invite_bp, stats_bp
)

# fcntl is only available on Unix/Linux
import platform
if platform.system() != 'Windows':
    import fcntl
else:
    fcntl = None

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
try:
    from seatable_api import Base
except Exception:
    Base = None
try:
    from seatable_api.constants import ColumnTypes
except Exception:
    ColumnTypes = None

# Import configuration from config.py; do not duplicate settings in app.py.
from config import (
    DB_BACKEND, SERVER_URL, API_TOKEN,
    TABLE_ROWS_CACHE_TTL_SECONDS,
    ACTIVITY_TABLE_NAME, SIGNUP_TABLE_NAME, REVIEW_RATING_TABLE_NAME,
    OUTPUT_RECORD_TABLE_NAME, USER_PROFILE_TABLE_NAME, INTEREST_GROUP_TABLE_NAME,
    GROUP_MEMBER_TABLE_NAME, REVIEW_INVITE_TABLE_NAME, CAC_ADMINS_TABLE_NAME,
    CAC_ROOM_SLOTS_TABLE_NAME,
    ACTIVITY_COL_DATE, ACTIVITY_COL_TIME, ACTIVITY_COL_SPEAKERS, ACTIVITY_COL_TOPIC,
    ACTIVITY_COL_CLASSROOM, ACTIVITY_COL_VIDEOURL, ACTIVITY_COL_CREATOR_NAME,
    ACTIVITY_COL_CREATOR_EMAIL, ACTIVITY_COL_STATUS, ACTIVITY_COL_CLOSED_AT,
    ACTIVITY_COL_ON_TIME, ACTIVITY_COL_CLOSER_NAME, ACTIVITY_COL_TYPE,
    ACTIVITY_COL_GROUP_ID, ACTIVITY_COL_GROUP_NAME, ACTIVITY_COL_EXPECTED_ATTENDANCE,
    LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID,
    SIGNUP_COL_NAME, SIGNUP_COL_ACTIVITY_ID, SIGNUP_COL_ROLE,
    SIGNUP_COL_PHONE, SIGNUP_COL_EMAIL, SIGNUP_COL_REVIEW_DOC_URL,
    SIGNUP_COL_REVIEW_SUBMITTED_AT, SIGNUP_COL_LAST_REVIEW_REMINDER_AT,
    SIGNUP_COL_REVIEW_CONTENT, LEGACY_SIGNUP_COL_STUDENT_ID,
    REVIEW_RATING_COL_SIGNUP_ID, REVIEW_RATING_COL_ACTIVITY_ID,
    REVIEW_RATING_COL_REVIEWER_NAME, REVIEW_RATING_COL_RATER_NAME,
    REVIEW_RATING_COL_SCORE, REVIEW_RATING_COL_WEIGHT, REVIEW_RATING_COL_COMMENT,
    OUTPUT_RECORD_COL_NAME, OUTPUT_RECORD_COL_TYPE, OUTPUT_RECORD_COL_DATE,
    OUTPUT_RECORD_COL_NOTE,
    USER_COL_NAME, USER_COL_EMAIL, USER_COL_ROLE, USER_COL_FIRST_SEEN_AT,
    GROUP_COL_NAME, GROUP_COL_LEADER_NAME, GROUP_COL_TOPIC_GOAL,
    GROUP_COL_TIME_BOUNDARY, GROUP_COL_EXECUTION_PLAN, GROUP_COL_DESCRIPTION,
    GROUP_COL_STATUS, GROUP_COL_CREATED_AT,
    GROUP_MEMBER_COL_GROUP_ID, GROUP_MEMBER_COL_GROUP_NAME,
    GROUP_MEMBER_COL_MEMBER_NAME, GROUP_MEMBER_COL_MEMBER_EMAIL,
    GROUP_MEMBER_COL_MEMBER_ROLE, GROUP_MEMBER_COL_JOINED_AT,
    INVITE_COL_ACTIVITY_ID, INVITE_COL_ACTIVITY_TOPIC,
    INVITE_COL_INVITER_NAME, INVITE_COL_INVITEE_NAME, INVITE_COL_INVITEE_EMAIL,
    INVITE_COL_SOURCE_TYPE, INVITE_COL_STATUS, INVITE_COL_CREATED_AT,
    INVITE_COL_UPDATED_AT, INVITE_COL_UPDATED_BY,
    CAC_ADMIN_COL_NAME, CAC_ADMIN_COL_CREATED_AT,
    CAC_SLOT_COL_CLASSROOM, CAC_SLOT_COL_DATE, CAC_SLOT_COL_TIME_SLOT,
    CAC_SLOT_COL_STATUS, CAC_SLOT_COL_ACTIVITY_ID, CAC_SLOT_COL_CREATED_BY,
    CAC_SLOT_COL_CREATED_AT,
    AUTO_REGISTER_COLUMNS,
    REVIEWER_LIMIT, LISTENER_UNLIMITED, TIME_SLOTS,
    CAC_FIXED_WEEKDAY, CAC_FIXED_TIME,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_SSL,
    SENDER_EMAIL, SENDER_NAME,
    BOUNDARY_REPORT_EMAIL, BOUNDARY_LOOKBACK_DAYS,
    BOUNDARY_FIRST_REPORT_AT, BOUNDARY_WEEKLY_REPORT_WEEKDAY,
    BOUNDARY_WEEKLY_REPORT_HOUR, BOUNDARY_WEEKLY_REPORT_MINUTE,
    ACTIVITY_CLOSE_GRACE_MINUTES, REVIEW_REMINDER_INTERVAL_HOURS,
    BACKGROUND_SCAN_INTERVAL_SECONDS, MEMBER_ROSTER_FILE,
    TASK_LOCK_FILE, PROFILE_EXPLORE_DEFAULT_PAGE_SIZE,
    PROFILE_EXPLORE_MAX_PAGE_SIZE, PROFILE_CACHE_TTL_SECONDS,
    PROFILE_FEED_DEFAULT_LIMIT, CAC_NAME, CAC_EMAIL,
)

load_dotenv()

from models import db

# Import service-layer functions to avoid duplicating business logic in app.py
from services.activity import (
    list_activities, get_activity_by_id, get_activity_details,
    get_activity_creator_name, get_activity_creator_email,
    get_activity_closed_at, get_activity_end_datetime,
    get_activity_signups, count_signups_by_activity, get_signup_stats,
    activity_is_closed, get_activity_state,
)
from services.signup import (
    list_signups, get_signup_by_id, serialize_signup,
    get_signup_review_doc_url, get_signup_review_submitted_at,
    get_signup_last_review_reminder_at, get_signup_name,
    auto_accept_invites_after_signup,
)
from services.rating import list_review_ratings, serialize_rating
from services.profile import list_user_profiles, get_user_profile, get_user_email, upsert_user_profile
from services.group import (
    list_interest_groups, list_group_members, get_interest_group_by_id,
    serialize_interest_group, get_group_ids_for_member,
)
from services.invite import (
    list_review_invites, get_invite_by_id, serialize_review_invite,
)
from services.cac_admin import (
    is_cac_admin, is_cac_user, list_cac_admins, list_cac_room_slots,
)

logger = logging.getLogger(__name__)

# Initialize the backend. MySQL mode uses the db singleton from models/database.py.
# SeaTable mode requires an adapter layer; leave it unchanged for now.
if DB_BACKEND == "seatable":
    if Base is None:
        raise RuntimeError("seatable-api is not installed; the SeaTable backend is unavailable")
    if not API_TOKEN:
        raise RuntimeError("SEATABLE_API_TOKEN is required when DB_BACKEND=seatable")
    base = Base(API_TOKEN, SERVER_URL)
    try:
        base.auth()
    except Exception as exc:
        raise RuntimeError(
            "SeaTable authentication failed. Make sure you are using the Base API token, not an account token,"
            "and that the token has read and write access to the target table."
        ) from exc
else:
    base = db  # In MySQL mode, use the shared db instance from models.database

# Column registration is handled by Database.__init__ in models/database.py.

app = Flask(__name__)

# ===== Register route blueprints =====
app.register_blueprint(activity_bp)
app.register_blueprint(signup_bp)
app.register_blueprint(cac_bp)
app.register_blueprint(group_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(invite_bp)
app.register_blueprint(stats_bp)

# ===== Global exception handlers =====
@app.errorhandler(AppError)
def handle_app_error(error):
    """Handle custom exceptions consistently."""
    return jsonify({"ok": False, "message": error.message, "code": error.code}), error.status_code

@app.errorhandler(404)
def handle_404(error):
    return jsonify({"ok": False, "message": "Resource not found", "code": "NOT_FOUND"}), 404

@app.errorhandler(500)
def handle_500(error):
    return jsonify({"ok": False, "message": "Internal server error", "code": "INTERNAL_ERROR"}), 500

# Protect check+insert in single-process deployment to reduce race conditions.
submit_lock = threading.Lock()


def _now():
    return datetime.now()


def _now_iso():
    return _now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_date(date_str):
    try:
        return datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
    except Exception:
        return None


def _parse_datetime(dt_str):
    text = str(dt_str or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _should_track_member_name(name):
    text = safe_text(name)
    if not text:
        return False
    if re.fullmatch(r"[A-Za-z]{1,4}\d{4,}", text):
        return False
    return True


def _list_rows(table_name):
    def load_rows():
        try:
            rows = base.list_rows(table_name)
            return rows or []
        except Exception as exc:
            logger.error("Error listing rows from %s: %s", table_name, exc)
            return []

    return cached_build(
        'table_rows',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        load_rows,
        table_name,
    )


def _split_names(raw_value):
    text = str(raw_value or "").strip()
    if not text:
        return []
    normalized = text.replace("，", ",").replace("、", ",")
    return [name.strip() for name in normalized.split(",") if _should_track_member_name(name.strip())]


def _load_member_roster():
    members = []
    try:
        with open(ROSTER_FILE_PATH, "r", encoding="utf-8") as file:
            for line in file:
                name = line.strip()
                if name:
                    members.append(name)
    except FileNotFoundError:
        pass
    return members


def _collect_known_member_names():
    names = set(_load_member_roster())
    for activity in list_activities():
        names.update(_split_names(activity.get(ACTIVITY_COL_SPEAKERS, "")))
        creator_name = _get_activity_creator_name_legacy(activity)
        if _should_track_member_name(creator_name):
            names.add(creator_name)
    for signup in list_signups():
        signup_name = _get_signup_name(signup)
        if _should_track_member_name(signup_name):
            names.add(signup_name)
    for record in _list_output_records():
        name = safe_text(record.get(OUTPUT_RECORD_COL_NAME, ""))
        if _should_track_member_name(name):
            names.add(name)
    for rating in list_review_ratings():
        reviewer_name = safe_text(rating.get(REVIEW_RATING_COL_REVIEWER_NAME, ""))
        rater_name = safe_text(rating.get(REVIEW_RATING_COL_RATER_NAME, ""))
        if _should_track_member_name(reviewer_name):
            names.add(reviewer_name)
        if _should_track_member_name(rater_name):
            names.add(rater_name)
    return sorted(names)


def _get_activity_end_datetime(activity):
    date_value = str(activity.get(ACTIVITY_COL_DATE, "")).strip()
    time_value = str(activity.get(ACTIVITY_COL_TIME, "")).strip()
    if not date_value or not time_value:
        return None
    time_range = _parse_time_range(time_value)
    if not time_range:
        return None
    date_obj = _parse_date(date_value)
    if not date_obj:
        return None
    end_minutes = time_range[1]
    return datetime.combine(date_obj.date(), datetime.min.time()) + timedelta(minutes=end_minutes)


def _compute_activity_on_time(activity, closed_at=None):
    closed_at = closed_at or get_activity_closed_at(activity)
    end_at = _get_activity_end_datetime(activity)
    if not closed_at or not end_at:
        return None
    return closed_at <= end_at + timedelta(minutes=ACTIVITY_CLOSE_GRACE_MINUTES)


def _task_lock():
    lock = open(TASK_LOCK_FILE, "a+", encoding="utf-8")
    if fcntl is not None:  # Unix/Linux
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    return lock


def _read_state_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return ""


def _write_state_file(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def _get_first_nonempty(row, *column_names):
    for column_name in column_names:
        if not column_name:
            continue
        value = row.get(column_name)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        return value
    return ""


def _get_table_columns(table_name):
    try:
        columns = base.list_columns(table_name)
        return {column.get('name') for column in (columns or [])}
    except Exception as exc:
        logger.error("Error listing columns for %s: %s", table_name, exc)
        return set()


PHASE1_SCHEMA_SPEC = {
    USER_PROFILE_TABLE_NAME: [
        USER_COL_NAME,
        USER_COL_EMAIL,
        USER_COL_ROLE,
        USER_COL_FIRST_SEEN_AT,
    ],
    INTEREST_GROUP_TABLE_NAME: [
        GROUP_COL_NAME,
        GROUP_COL_LEADER_NAME,
        GROUP_COL_TOPIC_GOAL,
        GROUP_COL_TIME_BOUNDARY,
        GROUP_COL_EXECUTION_PLAN,
        GROUP_COL_DESCRIPTION,
        GROUP_COL_STATUS,
        GROUP_COL_CREATED_AT,
    ],
    GROUP_MEMBER_TABLE_NAME: [
        GROUP_MEMBER_COL_GROUP_ID,
        GROUP_MEMBER_COL_GROUP_NAME,
        GROUP_MEMBER_COL_MEMBER_NAME,
        GROUP_MEMBER_COL_MEMBER_EMAIL,
        GROUP_MEMBER_COL_MEMBER_ROLE,
        GROUP_MEMBER_COL_JOINED_AT,
    ],
    REVIEW_INVITE_TABLE_NAME: [
        INVITE_COL_ACTIVITY_ID,
        INVITE_COL_ACTIVITY_TOPIC,
        INVITE_COL_INVITER_NAME,
        INVITE_COL_INVITEE_NAME,
        INVITE_COL_INVITEE_EMAIL,
        INVITE_COL_SOURCE_TYPE,
        INVITE_COL_STATUS,
        INVITE_COL_CREATED_AT,
        INVITE_COL_UPDATED_AT,
        INVITE_COL_UPDATED_BY,
    ],
}


def _add_table_best_effort(table_name):
    attempts = [
        (table_name,),
        (table_name, "zh-cn"),
        (table_name, "en"),
    ]
    last_error = None
    for args in attempts:
        try:
            base.add_table(*args)
            return True, "created"
        except TypeError as exc:
            last_error = str(exc)
            continue
        except Exception as exc:
            msg = str(exc)
            if "exist" in msg.lower() or "已存在" in msg:
                return True, "exists"
            last_error = msg
    return False, last_error or "add_table failed"


def _insert_text_column_best_effort(table_name, column_name):
    text_type = ColumnTypes.TEXT if ColumnTypes else "text"
    attempts = [
        (table_name, column_name, text_type),
        (table_name, column_name, text_type, None),
        (table_name, column_name, "text"),
    ]
    last_error = None
    for args in attempts:
        try:
            base.insert_column(*args)
            return True, "created"
        except TypeError as exc:
            last_error = str(exc)
            continue
        except Exception as exc:
            msg = str(exc)
            if "exist" in msg.lower() or "已存在" in msg:
                return True, "exists"
            last_error = msg
    return False, last_error or "insert_column failed"


def _ensure_single_table_schema(table_name, expected_columns):
    result = {
        "table": table_name,
        "table_ready": False,
        "table_action": "none",
        "columns_created": [],
        "missing_columns": [],
        "errors": [],
    }

    existing_columns = _get_table_columns(table_name)
    if not existing_columns:
        ok, action_or_error = _add_table_best_effort(table_name)
        if not ok:
            result["errors"].append(f"Failed to create table: {action_or_error}")
            return result
        result["table_action"] = action_or_error
        existing_columns = _get_table_columns(table_name)

    if not existing_columns:
        result["errors"].append("Could not read column metadata. Check that the token has access to the table.")
        return result

    result["table_ready"] = True
    for column_name in expected_columns:
        if column_name in existing_columns:
            continue
        ok, action_or_error = _insert_text_column_best_effort(table_name, column_name)
        if ok:
            result["columns_created"].append(column_name)
        else:
            result["missing_columns"].append(column_name)
            result["errors"].append(f"Failed to add column {column_name}: {action_or_error}")
    return result


def _ensure_phase1_schema():
    report = []
    for table_name, expected_columns in PHASE1_SCHEMA_SPEC.items():
        report.append(_ensure_single_table_schema(table_name, expected_columns))
    ok = all(not item["errors"] for item in report)
    return {
        "ok": ok,
        "report": report,
    }


def _filter_append_row_data(table_name, row_data):
    allowed_columns = _get_table_columns(table_name)
    if not allowed_columns:
        allowed_columns = set((row_data or {}).keys())
    filtered = {}
    for key, value in row_data.items():
        if key not in allowed_columns:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        filtered[key] = value
    return filtered


def _filter_update_row_data(table_name, row_data):
    allowed_columns = _get_table_columns(table_name)
    if not allowed_columns:
        allowed_columns = set((row_data or {}).keys())
    filtered = {}
    for key, value in row_data.items():
        if key not in allowed_columns:
            continue
        if isinstance(value, str):
            value = value.strip()
        filtered[key] = value
    return filtered


def _append_row(table_name, row_data):
    filtered = _filter_append_row_data(table_name, row_data)
    if not filtered:
        raise RuntimeError(f"{table_name} is missing writable fields. Check the table schema configuration.")
    return base.append_row(table_name, filtered)


def _update_row(table_name, row_id, row_data):
    filtered = _filter_update_row_data(table_name, row_data)
    if not filtered:
        raise RuntimeError(f"{table_name} is missing updatable fields. Check the table schema configuration.")
    return base.update_row(table_name, row_id, filtered)


def _get_activity_creator_name_legacy(activity):
    value = _get_first_nonempty(
        activity,
        ACTIVITY_COL_CREATOR_NAME,
        LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID,
    )
    return safe_text(value)


def _get_signup_email(signup):
    value = _get_first_nonempty(signup, SIGNUP_COL_EMAIL)
    return safe_text(value)


def _get_signup_name(signup):
    value = _get_first_nonempty(signup, SIGNUP_COL_NAME, LEGACY_SIGNUP_COL_STUDENT_ID)
    return safe_text(value)


def _mail_configured():
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and EMAIL_FROM)


def _send_email(recipient, subject, body):
    recipient = str(recipient or "").strip()
    if not recipient or not _mail_configured():
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = recipient
    msg.set_content(body)

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    return True


def _send_email_async(recipient, subject, body):
    if not recipient or not _mail_configured():
        return

    def worker():
        try:
            _send_email(recipient, subject, body)
        except Exception as exc:
            logger.error("Send email failed to %s: %s", recipient, exc)

    threading.Thread(target=worker, daemon=True).start()


def _english_label(value):
    labels = {
        '评议员': 'Reviewer',
        '旁听': 'Observer',
        '参与者': 'Participant',
        '普通活动': 'regular activity',
        '组长': 'Group lead',
        '组员': 'Member',
        '普通用户': 'Member',
        'CAC管理员': 'CAC administrator',
        'CAC有约': 'CAC Meetup',
        'CAC特邀': 'CAC invitation',
        'normal': 'regular activity',
        '进行中': 'In progress',
        '待结项': 'Pending closure',
        '已结项': 'Closed',
        '已发送': 'Pending',
        '已接受': 'Accepted',
        '已拒绝': 'Declined',
        '已撤回': 'Withdrawn',
        '已取消': 'Cancelled',
        '报名': 'registration',
        '已报名': 'registered',
        '已更新': 'updated',
        '已删除': 'deleted',
        '创建': 'created',
        '更新': 'updated',
        '删除': 'deleted',
        '取消': 'cancelled',
        '加入': 'joined',
        '退出': 'left',
    }
    return labels.get(safe_text(value), safe_text(value))


def _notify_signup_change(activity, signup_name, role, recipient_email, action):
    if not recipient_email:
        return
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or 'Untitled activity'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or 'Date to be confirmed'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or 'Time to be confirmed'
    subject = f"[CAC Share Sessions] {_english_label(action)} reminder"
    body = (
        f"Hello, {signup_name},\n\n"
        f"Your registration as an {_english_label(role)} for “{topic}” has been processed.\n"
        f"Activity time: {date} {time}\n\n"
        "Please refer to the latest information in the app if anything changes."
    )
    _send_email_async(recipient_email, subject, body)


def _notify_organizer_signup(activity, signup_name, role, review_content=''):
    organizer_email = get_activity_creator_email(activity)
    if not organizer_email:
        return
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or 'Untitled activity'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or 'Date to be confirmed'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or 'Time to be confirmed'
    subject = f"[CAC Share Sessions] New {_english_label(role)} signup"
    body = (
        f"Hello, a new signup has been submitted for your activity “{topic}”.\n\n"
        f"Participant: {signup_name}\n"
        f"Role: {_english_label(role)}\n"
        f"Activity time: {date} {time}\n"
    )
    if review_content:
        body += f"Review topic: {review_content}\n"
    _send_email_async(organizer_email, subject, body)


def _notify_activity_change(activity_email, creator_name, topic, action, extra_lines=None):
    if not activity_email:
        return
    extra_text = "\n".join(extra_lines or [])
    if extra_text:
        extra_text = f"\n{extra_text}"
    subject = f"[CAC Share Sessions] Activity {_english_label(action)}"
    body = (
        f"Hello, {creator_name},\n\n"
        f"Your activity “{topic or 'Untitled activity'}” has been {_english_label(action)}."
        f"{extra_text}\n\n"
        "To make further changes, return to the admin page."
    )
    _send_email_async(activity_email, subject, body)


def _notify_review_doc_reminder(signup, activity):
    recipient_email = _get_signup_email(signup)
    if not recipient_email:
        return
    signup_name = _get_signup_name(signup)
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or 'Untitled activity'
    subject = f"[CAC Share Sessions] Please submit your review for “{topic}”"
    body = (
        f"Hello, {signup_name},\n\n"
        f"Activity “{topic}” has closed. Please submit your review document link as soon as possible.\n"
        "If you have already submitted it, please ignore this reminder. Otherwise, you will continue to receive daily reminders."
    )
    _send_email_async(recipient_email, subject, body)


def _notify_boundary_report(non_compliant_names, stats):
    if not _mail_configured() or not non_compliant_names:
        return
    summary_recipient = BOUNDARY_REPORT_EMAIL or CAC_EMAIL
    subject = f"[CAC Share Sessions] Two-week participation reminder ({len(non_compliant_names)} members)"
    body = (
        f"The following members have not taken part in an output activity during the past {BOUNDARY_LOOKBACK_DAYS} days:\n\n"
        + "\n".join(non_compliant_names)
        + f"\n\nMembers included in this report: {stats.get('tracked_member_count', 0)}"
    )
    if summary_recipient:
        _send_email_async(summary_recipient, subject, body)

    member_email_map = _build_member_email_map()
    for member_name in non_compliant_names:
        recipient_email = member_email_map.get(member_name)
        if not recipient_email:
            continue
        member_body = (
            f"Hello, {member_name},\n\n"
            f"You have not yet taken part in an output activity (sharing, reviewing, or a CAC-hosted session) during the past {BOUNDARY_LOOKBACK_DAYS} days.\n"
            "Please schedule and complete an output activity soon to avoid further participation follow-up."
        )
        _send_email_async(recipient_email, "[CAC Share Sessions] Participation reminder", member_body)


def _build_member_email_map():
    result = {}
    for signup in list_signups():
        name = _get_signup_name(signup)
        email = _get_signup_email(signup)
        if _should_track_member_name(name) and email:
            result[name] = email
    for activity in list_activities():
        name = _get_activity_creator_name_legacy(activity)
        email = get_activity_creator_email(activity)
        if _should_track_member_name(name) and email:
            result[name] = email
    if CAC_EMAIL:
        result[safe_text(CAC_NAME)] = CAC_EMAIL
    return result


def _get_current_boundary_schedule_key(now=None):
    now = now or _now()
    first_report = _parse_datetime(BOUNDARY_FIRST_REPORT_AT)
    if not first_report:
        first_report = datetime(2026, 3, 22, 22, 0, 0)
    if now < first_report:
        return None
    if now.date() == first_report.date() and now >= first_report:
        return first_report.strftime("%Y-%m-%d %H:%M:%S")

    if now.weekday() != BOUNDARY_WEEKLY_REPORT_WEEKDAY:
        return None
    scheduled = datetime(now.year, now.month, now.day, BOUNDARY_WEEKLY_REPORT_HOUR, BOUNDARY_WEEKLY_REPORT_MINUTE, 0)
    if now < scheduled:
        return None
    return scheduled.strftime("%Y-%m-%d %H:%M:%S")



def _list_output_records():
    return _list_rows(OUTPUT_RECORD_TABLE_NAME)


def _get_memberships_by_name(name):
    target = safe_text(name)
    if not target:
        return []
    return [
        member for member in list_group_members()
        if safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == target
    ]


def _get_group_ids_for_member(name):
    return [str(member.get(GROUP_MEMBER_COL_GROUP_ID, '')) for member in _get_memberships_by_name(name)]


def _notify_group_membership_change(group, member_name, member_email, action):
    group_name = safe_text(group.get(GROUP_COL_NAME, ''))
    leader_name = safe_text(group.get(GROUP_COL_LEADER_NAME, ''))
    leader_email = get_user_email(leader_name)
    subject = f"[CAC Interest Group] Membership {_english_label(action)}"
    body = f"Membership in “{group_name}” has changed: {member_name} {_english_label(action)}."

    if leader_email:
        _send_email_async(leader_email, subject, body)
    if member_email:
        _send_email_async(member_email, subject, body)


def _notify_cac_activity_created(activity_type, topic, creator_name):
    if activity_type != 'cac有约':
        return
    recipient = CAC_EMAIL or BOUNDARY_REPORT_EMAIL
    if not recipient:
        return
    subject = "[CAC Share Sessions] New CAC-hosted session"
    body = (
        f"{creator_name} has proposed a CAC-hosted session.\n"
        f"Topic: {topic}\n"
        "Please confirm whether there are other plans. CAC will be included automatically by default."
    )
    _send_email_async(recipient, subject, body)


def _list_pending_invites_for_user(activity_id, invitee_name):
    result = []
    target_activity_id = str(activity_id).strip()
    target_name = safe_text(invitee_name)
    for invite in list_review_invites():
        if safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')) != target_activity_id:
            continue
        if safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target_name:
            continue
        if safe_text(invite.get(INVITE_COL_STATUS, '')) != '已发送':
            continue
        result.append(invite)
    return result


def _auto_accept_invites_after_signup(activity_id, signup_name):
    accepted_count = 0
    for invite in _list_pending_invites_for_user(activity_id, signup_name):
        try:
            _update_row(REVIEW_INVITE_TABLE_NAME, invite.get('_id'), {
                INVITE_COL_STATUS: '已接受',
                INVITE_COL_UPDATED_AT: _now_iso(),
                INVITE_COL_UPDATED_BY: signup_name,
            })
            accepted_count += 1
        except Exception as exc:
            logger.error("Update invite status failed: %s", exc)
    return accepted_count


def _is_invite_transition_allowed(old_status, new_status, is_cac_operator=False):
    old_status = safe_text(old_status)
    new_status = safe_text(new_status)
    if old_status == new_status:
        return True
    if is_cac_operator:
        return True
    allowed_map = {
        '已发送': {'已接受', '已拒绝', '已撤回'},
        '已接受': set(),
        '已拒绝': set(),
        '已撤回': set(),
    }
    return new_status in allowed_map.get(old_status, set())


def _get_signups_grouped_by_activity():
    def build_groups():
        grouped = defaultdict(list)
        for signup in list_signups():
            activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
            if not activity_id:
                continue
            grouped[activity_id].append(signup)
        return dict(grouped)

    return cached_build('signups_grouped_activity', PROFILE_CACHE_TTL_SECONDS, build_groups)


def _get_signup_role(signup):
    return str(signup.get(SIGNUP_COL_ROLE, '')).strip()


def _build_review_quality_stats():
    def build_stats():
        per_signup = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'ratings': []})
        per_reviewer = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'review_count': 0})

        for rating in list_review_ratings():
            item = serialize_rating(rating)
            signup_id = item['signup_id']
            if not signup_id:
                continue
            per_signup[signup_id]['weighted_score'] += item['score'] * item['weight']
            per_signup[signup_id]['total_weight'] += item['weight']
            per_signup[signup_id]['rating_count'] += 1
            per_signup[signup_id]['ratings'].append(item)

        for signup in list_signups():
            if _get_signup_role(signup) != '评议员':
                continue
            signup_id = str(signup.get('_id'))
            signup_name = _get_signup_name(signup)
            stats = per_signup[signup_id]
            if stats['total_weight'] <= 0:
                continue
            per_reviewer[signup_name]['weighted_score'] += stats['weighted_score']
            per_reviewer[signup_name]['total_weight'] += stats['total_weight']
            per_reviewer[signup_name]['rating_count'] += stats['rating_count']
            per_reviewer[signup_name]['review_count'] += 1

        ranking = []
        for reviewer_name, stats in per_reviewer.items():
            ranking.append({
                'name': reviewer_name,
                'score': round(stats['weighted_score'] / stats['total_weight'], 2) if stats['total_weight'] > 0 else 0,
                'rating_count': stats['rating_count'],
                'review_count': stats['review_count'],
            })

        ranking.sort(key=lambda item: (-item['score'], -item['rating_count'], item['name']))
        return dict(per_signup), ranking

    return cached_build('review_quality_stats', PROFILE_CACHE_TTL_SECONDS, build_stats)


def _serialize_review_task(signup):
    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = get_activity_by_id(activity_id)
    activity_details = get_activity_details(activity) if activity else {}
    per_signup_stats, _ = _build_review_quality_stats()
    signup_stats = per_signup_stats.get(str(signup.get('_id')), {})
    average_score = 0
    if signup_stats.get('total_weight', 0) > 0:
        average_score = round(signup_stats['weighted_score'] / signup_stats['total_weight'], 2)
    return {
        **serialize_signup(signup),
        'review_doc_url': get_signup_review_doc_url(signup),
        'review_submitted_at': signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''),
        'average_score': average_score,
        'rating_count': signup_stats.get('rating_count', 0),
        'activity_state': get_activity_state(activity),
        'activity': activity_details,
    }


def _get_activity_review_documents(activity_id, include_pending=False):
    per_signup_stats, _ = _build_review_quality_stats()
    documents = []
    for signup in get_activity_signups(activity_id, role='评议员'):
        review_doc_url = get_signup_review_doc_url(signup)
        if not include_pending and not review_doc_url:
            continue
        signup_id = str(signup.get('_id'))
        signup_stats = per_signup_stats.get(signup_id, {})
        average_score = 0
        if signup_stats.get('total_weight', 0) > 0:
            average_score = round(signup_stats['weighted_score'] / signup_stats['total_weight'], 2)
        documents.append({
            'signup_id': signup_id,
            'reviewer_name': _get_signup_name(signup),
            'review_doc_url': review_doc_url,
            'review_submitted_at': signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''),
            'average_score': average_score,
            'rating_count': signup_stats.get('rating_count', 0),
            'ratings': signup_stats.get('ratings', []),
        })
    return documents


def _build_share_leaderboard():
    counter = Counter()
    for activity in list_activities():
        for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
            if is_cac_user(speaker):
                continue
            counter[speaker] += 1
    ranking = [{'name': name, 'count': count} for name, count in counter.most_common()]
    return ranking


def _build_participation_leaderboard():
    counter = Counter()
    for signup in list_signups():
        if _get_signup_role(signup) in {'评议员', '旁听'}:
            signup_name = _get_signup_name(signup)
            if is_cac_user(signup_name):
                continue
            counter[signup_name] += 1
    ranking = [{'name': name, 'count': count} for name, count in counter.most_common()]
    return ranking


def _build_punctuality_leaderboard():
    stats = defaultdict(lambda: {'on_time': 0, 'closed': 0})
    for activity in list_activities():
        if not activity_is_closed(activity):
            continue
        creator_name = _get_activity_creator_name_legacy(activity)
        if not creator_name:
            continue
        if is_cac_user(creator_name):
            continue
        stats[creator_name]['closed'] += 1
        if _compute_activity_on_time(activity):
            stats[creator_name]['on_time'] += 1
    ranking = []
    for name, item in stats.items():
        closed = item['closed']
        ranking.append({
            'name': name,
            'closed_count': closed,
            'on_time_count': item['on_time'],
            'on_time_rate': round(item['on_time'] / closed, 4) if closed else 0,
        })
    ranking.sort(key=lambda item: (-item['on_time_rate'], -item['closed_count'], item['name']))
    return ranking


def _within_lookback(date_value, lookback_days=BOUNDARY_LOOKBACK_DAYS):
    target = _parse_date(date_value)
    if not target:
        return False
    return target.date() >= (_now().date() - timedelta(days=lookback_days))


def _build_output_counts(lookback_days=BOUNDARY_LOOKBACK_DAYS):
    output_counter = Counter()

    for activity in list_activities():
        if _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
            for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
                output_counter[speaker] += 1

    for signup in list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if activity and _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
            output_counter[_get_signup_name(signup)] += 1

    for record in _list_output_records():
        if not _within_lookback(record.get(OUTPUT_RECORD_COL_DATE, ''), lookback_days=lookback_days):
            continue
        record_type = str(record.get(OUTPUT_RECORD_COL_TYPE, '')).strip()
        if record_type in {'分享', '评议', 'CAC有约'}:
            name = str(record.get(OUTPUT_RECORD_COL_NAME, '')).strip()
            if name:
                output_counter[name] += 1

    return output_counter


def _build_boundary_stats():
    known_members = set(_collect_known_member_names())
    known_members = {name for name in known_members if not is_cac_user(name)}
    output_counter = _build_output_counts(lookback_days=BOUNDARY_LOOKBACK_DAYS)

    non_compliant = sorted(name for name in known_members if output_counter.get(name, 0) < 1)
    return {
        'lookback_days': BOUNDARY_LOOKBACK_DAYS,
        'tracked_member_count': len(known_members),
        'non_compliant_count': len(non_compliant),
        'non_compliant_names': non_compliant,
        'output_counts': dict(output_counter),
    }


def _build_monthly_report(now=None):
    now = now or _now()
    year = now.year
    month = now.month

    monthly_activities = []
    for activity in list_activities():
        activity_date = _parse_date(activity.get(ACTIVITY_COL_DATE, ''))
        if not activity_date or activity_date.year != year or activity_date.month != month:
            continue
        monthly_activities.append(activity)

    monthly_activity_ids = {str(activity.get('_id')) for activity in monthly_activities}
    monthly_signups = [signup for signup in list_signups() if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip() in monthly_activity_ids]
    monthly_outputs = []
    for record in _list_output_records():
        output_date = _parse_date(record.get(OUTPUT_RECORD_COL_DATE, ''))
        if output_date and output_date.year == year and output_date.month == month:
            monthly_outputs.append(record)

    closed_activities = [activity for activity in monthly_activities if activity_is_closed(activity)]
    on_time_closed = [activity for activity in closed_activities if _compute_activity_on_time(activity)]
    type_counter = Counter((safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal') for activity in monthly_activities)
    creator_names = {name for name in (_get_activity_creator_name_legacy(activity) for activity in monthly_activities) if name}
    participant_names = {name for name in (_get_signup_name(signup) for signup in monthly_signups) if name}

    return {
        'year_month': f"{year:04d}-{month:02d}",
        'activity_count': len(monthly_activities),
        'signup_count': len(monthly_signups),
        'output_record_count': len(monthly_outputs),
        'active_creator_count': len(creator_names),
        'active_participant_count': len(participant_names),
        'closed_count': len(closed_activities),
        'pending_close_count': len([activity for activity in monthly_activities if get_activity_state(activity) == '待结项']),
        'on_time_close_rate': round((len(on_time_closed) / len(closed_activities)), 4) if closed_activities else 0,
        'activity_type_breakdown': {
            'normal': int(type_counter.get('normal', 0)),
            'cac有约': int(type_counter.get('cac有约', 0)),
        },
    }


def _build_group_health_report(lookback_days=30):
    recent_output_counts = _build_output_counts(lookback_days=lookback_days)
    report = []
    for group in list_interest_groups():
        group_id = str(group.get('_id'))
        group_name = safe_text(group.get(GROUP_COL_NAME, ''))
        members = [member for member in list_group_members() if str(member.get(GROUP_MEMBER_COL_GROUP_ID, '')) == group_id]
        member_names = {safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) for member in members if safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, ''))}
        related_activities = []
        for activity in list_activities():
            if safe_text(activity.get(ACTIVITY_COL_GROUP_ID, '')) != group_id:
                continue
            if not _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
                continue
            related_activities.append(activity)

        recent_activity_count = len(related_activities)
        pending_close_count = len([activity for activity in related_activities if get_activity_state(activity) == '待结项'])
        active_member_count = len([name for name in member_names if recent_output_counts.get(name, 0) > 0])
        score = 35 + min(30, recent_activity_count * 15) + min(25, active_member_count * 5) - (pending_close_count * 12)
        score = max(0, min(100, score))
        if score >= 75:
            status = 'healthy'
        elif score >= 45:
            status = 'at_risk'
        else:
            status = 'inactive'

        report.append({
            'id': group_id,
            'name': group_name,
            'leader_name': safe_text(group.get(GROUP_COL_LEADER_NAME, '')),
            'member_count': len(member_names),
            'active_member_count': active_member_count,
            'recent_activity_count': recent_activity_count,
            'pending_close_count': pending_close_count,
            'health_score': score,
            'status': status,
        })

    report.sort(key=lambda item: (item.get('health_score', 0), item.get('recent_activity_count', 0), item.get('name', '')))
    return report


def _build_reviewer_watch():
    _, ranking = _build_review_quality_stats()
    score_map = {item.get('name'): item for item in ranking}
    pending_docs = Counter()
    for signup in list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        if get_signup_review_doc_url(signup):
            continue
        activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if activity and activity_is_closed(activity):
            pending_docs[_get_signup_name(signup)] += 1

    names = set(score_map.keys()) | set(pending_docs.keys())
    watch = []
    for name in names:
        item = score_map.get(name, {})
        score = float(item.get('score', 0) or 0)
        rating_count = int(item.get('rating_count', 0) or 0)
        review_count = int(item.get('review_count', 0) or 0)
        pending_doc_count = int(pending_docs.get(name, 0) or 0)
        if pending_doc_count > 0:
            status = 'pending_docs'
        elif rating_count >= 2 and score < 7:
            status = 'low_score'
        elif review_count > 0 and rating_count == 0:
            status = 'not_enough_feedback'
        else:
            status = 'ok'
        watch.append({
            'name': name,
            'score': score,
            'rating_count': rating_count,
            'review_count': review_count,
            'pending_doc_count': pending_doc_count,
            'status': status,
        })

    watch.sort(key=lambda item: (-item.get('pending_doc_count', 0), item.get('score', 10), item.get('name', '')))
    return watch


def _build_time_conflict_report():
    """Detect time conflicts between open activities on the same day, including the Friday 18:00 CAC-hosted session."""
    slot_map = defaultdict(list)
    for activity in list_activities():
        if activity_is_closed(activity):
            continue
        parsed = _parse_date(activity.get(ACTIVITY_COL_DATE, ''))
        if not parsed:
            continue
        date_str = parsed.strftime('%Y-%m-%d')
        time_slot = safe_text(activity.get(ACTIVITY_COL_TIME, ''))
        if not time_slot:
            continue
        slot_map[(date_str, time_slot)].append(activity)

    conflicts = []
    for (date_str, time_slot), activities in slot_map.items():
        if len(activities) < 2:
            continue
        is_cac_slot = False
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            if dt.weekday() == 4 and '18' in time_slot:
                is_cac_slot = True
        except Exception:
            pass
        conflicts.append({
            'date': date_str,
            'time_slot': time_slot,
            'count': len(activities),
            'is_cac_slot': is_cac_slot,
            'activities': [
                {
                    'id': str(a.get('_id', '')),
                    'topic': safe_text(a.get(ACTIVITY_COL_TOPIC, '')),
                    'speakers': safe_text(a.get(ACTIVITY_COL_SPEAKERS, '')),
                    'type': safe_text(a.get(ACTIVITY_COL_TYPE, '')),
                    'status': get_activity_state(a),
                }
                for a in activities
            ],
        })
    conflicts.sort(key=lambda x: x['date'])
    return {
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
    }


def _find_rank_by_name(items, name):
    target = safe_text(name)
    if not target:
        return None
    for index, item in enumerate(items or [], start=1):
        if safe_text(item.get('name', '')) == target:
            return index
    return None


def _build_person_profile_summary(name):
    target = safe_text(name)
    if not target:
        return None

    share_ranking = _build_share_leaderboard()
    participation_ranking = _build_participation_leaderboard()
    punctuality_ranking = _build_punctuality_leaderboard()
    _, review_quality_ranking = _build_review_quality_stats()
    boundary_stats = _build_boundary_stats()

    share_count = next((item.get('count', 0) for item in share_ranking if safe_text(item.get('name', '')) == target), 0)
    participation_count = next((item.get('count', 0) for item in participation_ranking if safe_text(item.get('name', '')) == target), 0)
    review_quality_item = next((item for item in review_quality_ranking if safe_text(item.get('name', '')) == target), None)
    punctuality_item = next((item for item in punctuality_ranking if safe_text(item.get('name', '')) == target), None)

    my_groups = []
    for member in _get_memberships_by_name(target):
        group = get_interest_group_by_id(member.get(GROUP_MEMBER_COL_GROUP_ID, ''))
        if group:
            my_groups.append({
                'id': str(group.get('_id')),
                'name': safe_text(group.get(GROUP_COL_NAME, '')),
                'member_role': safe_text(member.get(GROUP_MEMBER_COL_MEMBER_ROLE, '')),
            })

    my_signups = []
    for signup in list_signups():
        if _get_signup_name(signup) == target:
            my_signups.append(_serialize_review_task(signup))
    my_signups.sort(key=lambda item: (item.get('activity', {}).get('date', ''), item.get('activity', {}).get('time', '')), reverse=True)

    my_invites = []
    for invite in list_review_invites():
        if safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) == target:
            my_invites.append(serialize_review_invite(invite))
    my_invites.sort(key=lambda item: item.get('created_at', ''), reverse=True)

    output_count_recent = int(boundary_stats.get('output_counts', {}).get(target, 0))
    boundary_ok = output_count_recent >= 1 or is_cac_user(target)

    return {
        'name': target,
        'is_cac': is_cac_user(target),
        'profile': {
            'email': get_user_email(target),
            'groups': my_groups,
        },
        'metrics': {
            'share_count': int(share_count or 0),
            'participation_count': int(participation_count or 0),
            'review_quality_score': float((review_quality_item or {}).get('score', 0) or 0),
            'review_quality_rating_count': int((review_quality_item or {}).get('rating_count', 0) or 0),
            'punctuality_rate': float((punctuality_item or {}).get('on_time_rate', 0) or 0),
            'punctuality_closed_count': int((punctuality_item or {}).get('closed_count', 0) or 0),
            'output_count_recent': output_count_recent,
            'boundary_ok': boundary_ok,
            'boundary_lookback_days': int(boundary_stats.get('lookback_days', BOUNDARY_LOOKBACK_DAYS)),
        },
        'ranks': {
            'sharing': _find_rank_by_name(share_ranking, target),
            'participation': _find_rank_by_name(participation_ranking, target),
            'review_quality': _find_rank_by_name(review_quality_ranking, target),
            'punctuality': _find_rank_by_name(punctuality_ranking, target),
        },
        'recent_signups': my_signups[:8],
        'recent_invites': my_invites[:8],
    }


def _build_profile_feed(name, limit=30, type_filter='', keyword=''):
    target = safe_text(name)
    if not target:
        return []

    events = []

    for signup in list_signups():
        if _get_signup_name(signup) != target:
            continue
        activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        activity_details = get_activity_details(activity) if activity else {}
        events.append({
            'type': 'signup',
            'ts': safe_text(signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, '')) or safe_text(activity_details.get('date', '')),
            'title': f"Registered for: {safe_text(activity_details.get('topic', 'Untitled activity'))}",
            'detail': f"Role: {_english_label(signup.get(SIGNUP_COL_ROLE, '')) or '-'}",
            'meta': {
                'activity_id': safe_text(activity_details.get('id', '')),
                'activity_topic': safe_text(activity_details.get('topic', '')),
                'activity_type': safe_text(activity_details.get('activity_type', 'normal')),
                'group_name': safe_text(activity_details.get('group_name', '')),
            },
        })

    for invite in list_review_invites():
        if safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target:
            continue
        events.append({
            'type': 'invite',
            'ts': safe_text(invite.get(INVITE_COL_UPDATED_AT, '')) or safe_text(invite.get(INVITE_COL_CREATED_AT, '')),
            'title': f"Invitation received: {safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, 'Untitled activity'))}",
            'detail': f"Status: {_english_label(invite.get(INVITE_COL_STATUS, '已发送'))} · Source: {_english_label(invite.get(INVITE_COL_SOURCE_TYPE, '-'))}",
            'meta': {
                'invite_id': str(invite.get('_id')),
                'activity_id': safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')),
                'activity_topic': safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')),
                'invite_status': safe_text(invite.get(INVITE_COL_STATUS, '已发送')),
            },
        })

    for activity in list_activities():
        if _get_activity_creator_name_legacy(activity) != target:
            continue
        details = get_activity_details(activity)
        events.append({
            'type': 'created_activity',
            'ts': safe_text(details.get('date', '')),
            'title': f"Created activity: {safe_text(details.get('topic', 'Untitled activity'))}",
            'detail': f"Type: {_english_label(details.get('activity_type', 'normal'))} · Status: {_english_label(details.get('status', '-'))}",
            'meta': {
                'activity_id': safe_text(details.get('id', '')),
                'group_name': safe_text(details.get('group_name', '')),
                'activity_topic': safe_text(details.get('topic', '')),
                'activity_type': safe_text(details.get('activity_type', 'normal')),
                'state': safe_text(details.get('status', '')),
            },
        })

    normalized_type_filter = safe_text(type_filter)
    normalized_keyword = safe_text(keyword).lower()
    if normalized_type_filter:
        events = [event for event in events if safe_text(event.get('type', '')) == normalized_type_filter]
    if normalized_keyword:
        events = [
            event for event in events
            if normalized_keyword in safe_text(event.get('title', '')).lower()
            or normalized_keyword in safe_text(event.get('detail', '')).lower()
            or normalized_keyword in safe_text((event.get('meta') or {}).get('activity_topic', '')).lower()
        ]

    events.sort(key=lambda item: (safe_text(item.get('ts', '')), safe_text(item.get('title', ''))), reverse=True)
    return events[:max(1, min(limit, 100))]


def _build_profile_tasks(name):
    target = safe_text(name)
    if not target:
        return []

    tasks = []
    boundary_stats = _build_boundary_stats()
    output_count_recent = int(boundary_stats.get('output_counts', {}).get(target, 0))
    if not is_cac_user(target) and output_count_recent < 1:
        tasks.append({
            'type': 'boundary_warning',
            'priority': 100,
            'title': 'Log a recent output activity',
            'detail': f"No output activity has been recorded in the past {BOUNDARY_LOOKBACK_DAYS} days.",
            'action': 'browse_activities',
            'action_label': 'Browse activities',
        })

    if not get_user_email(target):
        tasks.append({
            'type': 'missing_email',
            'priority': 95,
            'title': 'Add an email address to receive reminders',
            'detail': 'Your profile has no email address, so invitations, signup notices, and participation reminders may not reach you.',
            'action': 'open_account',
            'action_label': 'Update email',
        })

    if not _get_memberships_by_name(target) and not is_cac_user(target):
        tasks.append({
            'type': 'join_group',
            'priority': 70,
            'title': 'Join an interest group',
            'detail': 'Joining an interest group improves activity attribution and recommendations.',
            'action': 'open_groups',
            'action_label': 'Browse interest groups',
        })

    for invite in list_review_invites():
        if safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target:
            continue
        if safe_text(invite.get(INVITE_COL_STATUS, '已发送')) != '已发送':
            continue
        tasks.append({
            'type': 'pending_invite',
            'priority': 90,
            'title': f"Invitation awaiting a response: {safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, 'Untitled activity'))}",
            'detail': f"Source: {_english_label(invite.get(INVITE_COL_SOURCE_TYPE, '-'))} · Invited by: {safe_text(invite.get(INVITE_COL_INVITER_NAME, '-'))}",
            'activity_id': safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')),
            'activity_topic': safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')),
            'invite_id': str(invite.get('_id')),
            'action': 'respond_invite',
            'action_label': 'Respond to invitation',
        })

    for signup in list_signups():
        if _get_signup_name(signup) != target:
            continue
        if _get_signup_role(signup) != '评议员':
            continue
        if get_signup_review_doc_url(signup):
            continue
        activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if not activity or not activity_is_closed(activity):
            continue
        details = get_activity_details(activity)
        tasks.append({
            'type': 'review_doc',
            'priority': 88,
            'title': f"Review needed: {safe_text(details.get('topic', 'Untitled activity'))}",
            'detail': 'The activity has closed. Please submit your review document link.',
            'signup_id': str(signup.get('_id')),
            'activity_id': safe_text(details.get('id', '')),
            'activity_topic': safe_text(details.get('topic', '')),
            'activity_type': safe_text(details.get('activity_type', 'normal')),
            'state': safe_text(details.get('status', '')),
            'action': 'jump_activity',
            'action_label': 'View activity',
        })

    for activity in list_activities():
        if _get_activity_creator_name_legacy(activity) != target:
            continue
        if get_activity_state(activity) != '待结项':
            continue
        details = get_activity_details(activity)
        tasks.append({
            'type': 'close_activity',
            'priority': 85,
            'title': f"Activity awaiting closure: {safe_text(details.get('topic', 'Untitled activity'))}",
            'detail': 'The activity time has passed. Close the activity to start the review workflow.',
            'activity_id': safe_text(details.get('id', '')),
            'activity_topic': safe_text(details.get('topic', '')),
            'activity_type': safe_text(details.get('activity_type', 'normal')),
            'state': safe_text(details.get('status', '')),
            'action': 'jump_activity',
            'action_label': 'Close activity',
        })

    tasks.sort(key=lambda item: (-int(item.get('priority', 0)), safe_text(item.get('title', ''))))
    return tasks[:12]


def _build_profile_recommendations(name, limit=6):
    target = safe_text(name)
    if not target:
        return []

    joined_group_ids = set(_get_group_ids_for_member(target))
    signed_activity_ids = {
        str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
        for signup in list_signups()
        if _get_signup_name(signup) == target
    }

    recommendations = []
    for activity in list_activities():
        details = get_activity_details(activity)
        activity_id = safe_text(details.get('id', ''))
        if not activity_id or activity_id in signed_activity_ids:
            continue
        if _get_activity_creator_name_legacy(activity) == target:
            continue
        if safe_text(details.get('status', '')) == '已结项':
            continue

        score = 0
        reasons = []
        group_id = safe_text(details.get('group_id', ''))
        activity_type = safe_text(details.get('activity_type', 'normal'))
        state = safe_text(details.get('status', ''))
        reviewer_remaining = int(_get_signup_stats_local(activity_id).get('reviewer_remaining', 0) or 0)

        if group_id and group_id in joined_group_ids:
            score += 5
            reasons.append('From one of your interest groups')
        if state == '进行中':
            score += 3
            reasons.append('Open for participation')
        elif state == '待结项':
            score += 1
            reasons.append('Recently ended; you can still add an observer or participation record')
        if activity_type == 'cac有约':
            score += 2
            reasons.append('A good fit for direct participation and discussion')
        elif reviewer_remaining > 0:
            score += 2
            reasons.append(f'{reviewer_remaining} reviewer spot(s) available')
        else:
            score += 1
            reasons.append('Join as an observer to increase your recent participation')

        recommended_role = '参与者' if activity_type == 'cac有约' else ('评议员' if reviewer_remaining > 0 else '旁听')
        recommendations.append({
            'activity_id': activity_id,
            'topic': safe_text(details.get('topic', 'Untitled activity')),
            'date': safe_text(details.get('date', '')),
            'time': safe_text(details.get('time', '')),
            'speakers': safe_text(details.get('speakers', '')),
            'group_name': safe_text(details.get('group_name', '')),
            'activity_type': activity_type,
            'state': state,
            'recommended_role': recommended_role,
            'score': score,
            'reasons': reasons[:3],
        })

    recommendations.sort(key=lambda item: (-int(item.get('score', 0)), safe_text(item.get('date', '')), safe_text(item.get('topic', ''))), reverse=False)
    return recommendations[:max(1, min(limit, 20))]


def _run_review_reminder_scan():
    with _task_lock():
        reminder_cutoff = _now() - timedelta(hours=REVIEW_REMINDER_INTERVAL_HOURS)
        for signup in list_signups():
            if _get_signup_role(signup) != '评议员':
                continue
            if get_signup_review_doc_url(signup):
                continue
            activity = get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
            if not activity or not activity_is_closed(activity):
                continue
            if (safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal') == 'cac有约':
                continue
            last_reminder = get_signup_last_review_reminder_at(signup)
            if last_reminder and last_reminder > reminder_cutoff:
                continue
            _notify_review_doc_reminder(signup, activity)
            try:
                _update_row(SIGNUP_TABLE_NAME, signup.get('_id'), {
                    SIGNUP_COL_LAST_REVIEW_REMINDER_AT: _now_iso(),
                })
            except Exception as exc:
                logger.error("Update review reminder timestamp failed: %s", exc)


def _run_boundary_report_scan():
    with _task_lock():
        schedule_key = _get_current_boundary_schedule_key()
        if not schedule_key:
            return
        if _read_state_file(BOUNDARY_REPORT_STATE_FILE) == schedule_key:
            return
        stats = _build_boundary_stats()
        non_compliant_names = stats.get('non_compliant_names', [])
        if non_compliant_names:
            _notify_boundary_report(non_compliant_names, stats)
        _write_state_file(BOUNDARY_REPORT_STATE_FILE, schedule_key)


def _background_maintenance_loop():
    while not _shutdown_event.is_set():
        try:
            _run_review_reminder_scan()
            _run_boundary_report_scan()
        except Exception as exc:
            logger.error("Background maintenance error: %s", exc)
        _shutdown_event.wait(timeout=max(300, BACKGROUND_SCAN_INTERVAL_SECONDS))


# ===== Internal activity and signup statistics =====
# Note: list_activities, get_activity_by_id, and get_activity_details
#       list_signups, count_signups_by_activity, get_signup_stats
# are imported from the services layer and are no longer defined here.

def _get_signup_counters_by_activity():
    def build_counters():
        counters = defaultdict(lambda: defaultdict(int))
        for signup in list_signups():
            activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
            if not activity_id:
                continue
            role = str(signup.get(SIGNUP_COL_ROLE, '')).strip()
            counters[activity_id]['all'] += 1
            if role:
                counters[activity_id][role] += 1
        return {k: dict(v) for k, v in counters.items()}

    return cached_build('signup_counters', PROFILE_CACHE_TTL_SECONDS, build_counters)


def _count_signups_local(activity_id, role=None):
    """Count signups for an activity using precomputed counters."""
    counters = _get_signup_counters_by_activity().get(str(activity_id), {})
    if role is None:
        return int(counters.get('all', 0) or 0)
    return int(counters.get(role, 0) or 0)


def _calculate_expected_attendance(activity_id):
    """Calculate expected attendance: speaker count + observer count + three reviewers."""
    activity = get_activity_by_id(activity_id)
    if not activity:
        return 0

    # Count speakers (split on commas)
    speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
    speakers_count = len([s.strip() for s in speakers_str.split(',') if s.strip()]) if speakers_str else 0

    # Count observers
    listener_count = _count_signups_local(activity_id, '旁听')

    # Reviewer capacity is fixed at three
    reviewer_count = REVIEWER_LIMIT

    return speakers_count + listener_count + reviewer_count


def _get_signup_stats_local(activity_id):
    """Get an activity's signup statistics, including expected attendance."""
    reviewer_count = _count_signups_local(activity_id, '评议员')
    listener_count = _count_signups_local(activity_id, '旁听')
    expected_attendance = _calculate_expected_attendance(activity_id)
    reviewer_full = reviewer_count >= REVIEWER_LIMIT
    reviewer_remaining = max(0, REVIEWER_LIMIT - reviewer_count)

    return {
        'reviewers': reviewer_count,
        'listeners': listener_count,
        'expected_attendance': expected_attendance,
        'reviewer_full': reviewer_full,
        'reviewer_limit': REVIEWER_LIMIT,
        'reviewer_remaining': reviewer_remaining,
    }


# ===== Statistics and alert helpers =====
def _parse_time_range(time_str):
    """Parse a time-range string such as '10:00-11:00'; return (start_minutes, end_minutes) or None."""
    if not time_str:
        return None
    parts = str(time_str).strip().split('-')
    if len(parts) != 2:
        return None
    try:
        def to_minutes(t):
            h, m = t.strip().split(':')
            return int(h) * 60 + int(m)
        return (to_minutes(parts[0]), to_minutes(parts[1]))
    except Exception:
        return None


def _times_overlap(range1, range2):
    """Check whether two time ranges overlap; touching endpoints do not count."""
    if not range1 or not range2:
        return False
    return range1[0] < range2[1] and range2[0] < range1[1]


def _detect_time_conflicts(activities_details):
    """Detect scheduling conflicts between activities and return the conflicts."""
    conflicts = []
    acts = [a for a in activities_details if a.get('date') and a.get('time')]
    for i, act1 in enumerate(acts):
        for act2 in acts[i + 1:]:
            if str(act1.get('date', '')) != str(act2.get('date', '')):
                continue
            range1 = _parse_time_range(act1.get('time'))
            range2 = _parse_time_range(act2.get('time'))
            if _times_overlap(range1, range2):
                conflicts.append({
                    'activity1_id': act1.get('id'),
                    'activity1_topic': act1.get('topic', ''),
                    'activity2_id': act2.get('id'),
                    'activity2_topic': act2.get('topic', ''),
                    'date': act1.get('date'),
                    'time1': act1.get('time'),
                    'time2': act2.get('time'),
                })
    return conflicts


def _check_cac_conflict(date_str, time_str):
    """Check for time conflicts involving a CAC Meetup and return (has_conflict, message)."""
    try:
        date = datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
        if date.weekday() == CAC_FIXED_WEEKDAY:
            cac_range = _parse_time_range(CAC_FIXED_TIME)
            act_range = _parse_time_range(time_str)
            if cac_range and act_range and _times_overlap(act_range, cac_range):
                weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_name = weekday_names[CAC_FIXED_WEEKDAY]
                return True, f"This activity conflicts with the CAC-hosted session on {day_name} at {CAC_FIXED_TIME}. Please choose another time."
    except Exception:
        pass
    return False, None


def _get_time_slot_pairs():
    """Generate time-slot ranges from the TIME_SLOTS configuration."""
    pairs = []
    for i in range(len(TIME_SLOTS) - 1):
        pairs.append(f"{TIME_SLOTS[i]}-{TIME_SLOTS[i + 1]}")
    return pairs


def _detect_inactive_members():
    """Detect inactive interest groups with no activity records."""
    activities = list_activities()
    speakers_set = set()
    for activity in activities:
        speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
        speakers = [s.strip() for s in speakers_str.split(',') if s.strip()]
        speakers_set.update(speakers)
    return {
        'total_active_speakers': len(speakers_set),
        'message': f'{len(speakers_set)} active speakers or interest groups'
    }


def _detect_boundary_violations():
    """Detect members approaching the participation threshold due to possible overparticipation."""
    signups = list_signups()
    member_participation = Counter()
    
    for signup in signups:
        name = str(signup.get(SIGNUP_COL_NAME, '')).strip()
        if name:
            member_participation[name] += 1
    
    # Set the alert threshold to more than 10 signups
    warning_threshold = 10
    violations = {name: count for name, count in member_participation.items() if count > warning_threshold}
    
    return {
        'warning_threshold': warning_threshold,
        'potential_violations': violations,
        'count': len(violations),
    }


# ===== Flask route =====
@app.get("/")
def index():
    """home page"""
    return render_template("index.html", time_slots=TIME_SLOTS)


@app.get("/organizer")
def organizer():
    """Speaker administration page."""
    return render_template("organizer.html", time_slots=TIME_SLOTS, time_slot_pairs=_get_time_slot_pairs())


@app.get("/profile")
def profile_page():
    """profile page（phase two）"""
    return render_template("profile.html")


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True}), 200


@app.get("/api/activities")
def api_activities():
    """Get activity lists and statistics; return only activities that are not closed."""
    activities = list_activities()
    result = []

    for activity in activities:
        # Skip closed activities
        if activity_is_closed(activity):
            continue
        activity_id = activity.get('_id')
        details = get_activity_details(activity)
        stats = _get_signup_stats_local(activity_id)
        result.append({
            **details,
            **stats,
            'review_documents': _get_activity_review_documents(activity_id),
        })
    
    return jsonify({
        "ok": True,
        "activities": result,
    })


@app.get("/api/activities/filter")
def api_activities_filter():
    activity_type = safe_text(request.args.get('activity_type', '')).lower()
    group_id = safe_text(request.args.get('group_id', ''))
    state = safe_text(request.args.get('state', ''))
    keyword = safe_text(request.args.get('keyword', '')).lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get('page_size', str(PROFILE_EXPLORE_DEFAULT_PAGE_SIZE)))
    except Exception:
        page_size = PROFILE_EXPLORE_DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, PROFILE_EXPLORE_MAX_PAGE_SIZE))
    sort_by = safe_text(request.args.get('sort_by', 'date')).lower()
    sort_order = safe_text(request.args.get('sort_order', 'desc')).lower()

    allowed_types = {'', 'normal', 'cac有约'}
    allowed_states = {'', '进行中', '待结项', '已结项'}
    allowed_sort_by = {'date', 'created', 'topic', 'state'}
    allowed_sort_order = {'asc', 'desc'}
    if activity_type not in allowed_types:
        return jsonify({"ok": False, "message": "activity_type must be regular or CAC-hosted"}), 400
    if state not in allowed_states:
        return jsonify({"ok": False, "message": "state must be In progress, Pending closure, or Closed"}), 400
    if sort_by not in allowed_sort_by:
        return jsonify({"ok": False, "message": "sort_by must be date, created, topic, or state"}), 400
    if sort_order not in allowed_sort_order:
        return jsonify({"ok": False, "message": "sort_order must be asc or desc"}), 400

    def build_response():
        result = []
        for activity in list_activities():
            details = get_activity_details(activity)
            stats = _get_signup_stats_local(activity.get('_id'))

            current_type = safe_text(details.get('activity_type', 'normal')).lower()
            current_group_id = safe_text(details.get('group_id', ''))
            current_state = safe_text(details.get('status', ''))
            current_text = f"{safe_text(details.get('topic', ''))} {safe_text(details.get('speakers', ''))}".lower()

            if activity_type and current_type != activity_type:
                continue
            if group_id and current_group_id != group_id:
                continue
            if state and current_state != state:
                continue
            if keyword and keyword not in current_text:
                continue

            result.append({
                **details,
                **stats,
            })

        if sort_by == 'topic':
            result.sort(key=lambda item: (safe_text(item.get('topic', '')).lower(), item.get('date', ''), item.get('time', '')), reverse=(sort_order == 'desc'))
        elif sort_by == 'state':
            state_weight = {'进行中': 0, '待结项': 1, '已结项': 2}
            result.sort(key=lambda item: (state_weight.get(safe_text(item.get('status', '')), 9), item.get('date', ''), item.get('time', '')), reverse=(sort_order == 'desc'))
        else:
            result.sort(key=lambda item: (item.get('date', ''), item.get('time', ''), item.get('topic', '')), reverse=(sort_order == 'desc'))

        total = len(result)
        start = (page - 1) * page_size
        end = start + page_size
        paged = result[start:end]

        return {
            "ok": True,
            "activities": paged,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": end < total,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

    payload = cached_build(
        'activities_filter',
        PROFILE_CACHE_TTL_SECONDS,
        build_response,
        activity_type,
        group_id,
        state,
        keyword,
        page,
        page_size,
        sort_by,
        sort_order,
    )
    return jsonify(payload)


@app.get("/api/admin/dashboard")
def api_admin_dashboard():
    payload = cached_build(
        'admin_dashboard',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: {
            'monthly_report': _build_monthly_report(),
            'group_health': _build_group_health_report(),
            'reviewer_watch': _build_reviewer_watch(),
            'boundary_watch': _build_boundary_stats(),
            'time_conflicts': _build_time_conflict_report(),
        },
    )
    return jsonify({"ok": True, **payload})


@app.get("/api/activity/<activity_id>")
def api_activity_detail(activity_id):
    """Get an activity's details."""
    activity = get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "Activity not found"}), 404
    
    details = get_activity_details(activity)
    stats = _get_signup_stats_local(activity_id)
    
    return jsonify({
        "ok": True,
        "activity": {
            **details,
            **stats,
            'review_documents': _get_activity_review_documents(activity_id, include_pending=True),
        },
    })


@app.post("/api/signup")
def api_signup():
    """Register as a reviewer or observer."""
    data = request.get_json(silent=True) or {}
    
    name = str(data.get("name", "")).strip()
    activity_id = str(data.get("activity_id", "")).strip()
    role = str(data.get("role", "")).strip()  # Expected values are the stored reviewer or observer roles.
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()
    review_content = str(data.get("review_content", "")).strip()  # Review topic or prompt.

    # Validate required fields
    if not name or not activity_id or not role:
        return jsonify({"ok": False, "message": "Provide a name, activity, and role"}), 400

    # Reviewers must provide review content
    if role == '评议员' and not review_content:
        return jsonify({"ok": False, "message": "Reviewers must provide a review topic"}), 400
    
    # Check that the activity exists.
    activity = get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "Activity not found"}), 404
    activity_type = safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal'

    if role not in ['评议员', '旁听']:
        if not (activity_type == 'cac有约' and role == '参与者'):
            return jsonify({"ok": False, "message": "Role must be Reviewer or Observer (or Participant for a CAC-hosted session)"}), 400

    if not get_user_profile(name) and not email:
        return jsonify({"ok": False, "message": "Add an email address before continuing"}), 400
    _upsert_user_profile(name, email=email, role='普通用户')
    
    with submit_lock:
        signups = list_signups()
        
        # Check whether the reviewer limit has been reached
        if role == '评议员' and activity_type != 'cac有约':
            reviewer_count = _count_signups_local(activity_id, '评议员')
            if reviewer_count >= REVIEWER_LIMIT:
                return jsonify({"ok": False, "message": f"Reviewer capacity reached ({REVIEWER_LIMIT}); registration is unavailable"}), 409
        
        # Check whether the name has already signed up for this activity
        for signup in signups:
            if _get_signup_name(signup) == name:
                if str(signup.get(SIGNUP_COL_ACTIVITY_ID, "")) == activity_id:
                    return jsonify({"ok": False, "message": "You are already registered for this activity"}), 409
        
        # Add the signup record.
        row_data = {
            SIGNUP_COL_NAME: name,
            SIGNUP_COL_ACTIVITY_ID: activity_id,
            SIGNUP_COL_ROLE: role,
            SIGNUP_COL_PHONE: phone,
            SIGNUP_COL_EMAIL: email,
            SIGNUP_COL_REVIEW_CONTENT: review_content if role == '评议员' else '',
        }

        try:
            _append_row(SIGNUP_TABLE_NAME, row_data)
        except Exception as e:
            return jsonify({"ok": False, "message": f"Registration failed: {str(e)}"}), 500

    _notify_signup_change(activity, name, role, email, '报名')
    _notify_organizer_signup(activity, name, role, review_content)
    accepted_invites = _auto_accept_invites_after_signup(activity_id, name)
    touch_version()

    message = f"{role}Registration successful"
    if accepted_invites > 0:
        message += f", and automatically accepted {accepted_invites} invitation(s)"

    return jsonify({"ok": True, "message": message, "accepted_invites": accepted_invites})


@app.get("/api/my-signups/<name>")
def api_my_signups(name):
    """List activities a signup participant has joined."""
    name = str(name).strip()
    if not name:
        return jsonify({"ok": False, "message": "Name is required"}), 400

    signups = []
    for signup in list_signups():
        if _get_signup_name(signup) == name:
            signups.append(_serialize_review_task(signup))

    signups.sort(
        key=lambda item: (
            str(item.get('activity', {}).get('date', '')),
            str(item.get('activity', {}).get('time', '')),
            str(item.get('activity', {}).get('topic', '')),
        )
    )

    return jsonify({
        "ok": True,
        "signups": signups,
    })


@app.delete("/api/signup/<signup_id>")
def api_cancel_signup(signup_id):
    """Cancel a signup (participants may cancel only their own registration by name)."""
    signup_id = str(signup_id).strip()
    signup = get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "Registration not found"}), 404

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "message": "Name is required"}), 400

    signup_name = _get_signup_name(signup)
    if signup_name != name:
        return jsonify({"ok": False, "message": "You can only cancel your own registration"}), 403

    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = get_activity_by_id(activity_id)
    role = str(signup.get(SIGNUP_COL_ROLE, '')).strip() or '报名'
    signup_email = _get_signup_email(signup)

    try:
        base.delete_row(SIGNUP_TABLE_NAME, signup_id)
    except Exception as e:
        return jsonify({"ok": False, "message": f"Could not cancel registration: {str(e)}"}), 500

    if activity:
        _notify_signup_change(activity, signup_name, role, signup_email, '取消')
    touch_version()

    return jsonify({"ok": True, "message": "Registration cancelled"})


@app.post("/api/signup/<signup_id>/review-doc")
def api_submit_review_doc(signup_id):
    """Upload a reviewer's Yuque document link."""
    signup = get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "Registration not found"}), 404
    if _get_signup_role(signup) != '评议员':
        return jsonify({"ok": False, "message": "Only reviewers can submit a review document"}), 400

    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    review_doc_url = str(data.get('review_doc_url', '')).strip()
    if not name or not review_doc_url:
        return jsonify({"ok": False, "message": "Provide your name and review document URL"}), 400
    if _get_signup_name(signup) != name:
        return jsonify({"ok": False, "message": "You can only submit your own review document"}), 403

    try:
        _update_row(SIGNUP_TABLE_NAME, signup.get('_id'), {
            SIGNUP_COL_REVIEW_DOC_URL: review_doc_url,
            SIGNUP_COL_REVIEW_SUBMITTED_AT: _now_iso(),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not submit the review document: {exc}"}), 500

    touch_version()

    return jsonify({"ok": True, "message": "Review document submitted"})


@app.post("/api/review-rating")
def api_rate_review():
    """Rate review documents: observers have a weight of 10, all other readers a weight of 1."""
    data = request.get_json(silent=True) or {}
    signup_id = str(data.get('signup_id', '')).strip()
    rater_name = str(data.get('rater_name', '')).strip()
    comment = str(data.get('comment', '')).strip()
    try:
        score = float(data.get('score', 0))
    except Exception:
        score = 0

    if not signup_id or not rater_name or score <= 0:
        return jsonify({"ok": False, "message": "Provide the reviewer, ratee, and score"}), 400
    if score > 10:
        return jsonify({"ok": False, "message": "The score must be between 1 and 10"}), 400

    signup = get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "Review registration not found"}), 404
    reviewer_name = _get_signup_name(signup)
    if reviewer_name == rater_name:
        return jsonify({"ok": False, "message": "You cannot rate your own review"}), 400
    if not get_signup_review_doc_url(signup):
        return jsonify({"ok": False, "message": "The review document has not been submitted yet"}), 409

    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    existing_rating = None
    for rating in list_review_ratings():
        if str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip() == signup_id and str(rating.get(REVIEW_RATING_COL_RATER_NAME, '')).strip() == rater_name:
            existing_rating = rating
            break

    weight = 1
    for listener_signup in get_activity_signups(activity_id, role='旁听'):
        if _get_signup_name(listener_signup) == rater_name:
            weight = 10
            break

    row_data = {
        REVIEW_RATING_COL_SIGNUP_ID: signup_id,
        REVIEW_RATING_COL_ACTIVITY_ID: activity_id,
        REVIEW_RATING_COL_REVIEWER_NAME: reviewer_name,
        REVIEW_RATING_COL_RATER_NAME: rater_name,
        REVIEW_RATING_COL_SCORE: score,
        REVIEW_RATING_COL_WEIGHT: weight,
        REVIEW_RATING_COL_COMMENT: comment,
    }

    try:
        if existing_rating:
            _update_row(REVIEW_RATING_TABLE_NAME, existing_rating.get('_id'), row_data)
        else:
            _append_row(REVIEW_RATING_TABLE_NAME, row_data)
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not submit the rating: {exc}"}), 500

    touch_version()

    return jsonify({"ok": True, "message": "Rating submitted", "weight": weight})


@app.post("/api/admin/init-phase1-schema")
def api_init_phase1_schema():
    result = _ensure_phase1_schema()
    status_code = 200 if result.get("ok") else 500
    return jsonify(result), status_code


@app.get("/api/groups")
def api_groups_list():
    groups = [serialize_interest_group(group) for group in list_interest_groups()]
    groups.sort(key=lambda item: (item.get('status', ''), item.get('name', '')))
    return jsonify({"ok": True, "groups": groups})


@app.get("/api/group/<group_id>")
def api_group_detail(group_id):
    group = get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "Interest group not found"}), 404
    return jsonify({"ok": True, "group": serialize_interest_group(group)})


@app.get("/api/my-groups/<name>")
def api_my_groups(name):
    memberships = _get_memberships_by_name(name)
    group_ids = [str(item.get(GROUP_MEMBER_COL_GROUP_ID, '')) for item in memberships]
    groups = []
    for group_id in group_ids:
        group = get_interest_group_by_id(group_id)
        if group:
            groups.append(serialize_interest_group(group))
    return jsonify({"ok": True, "groups": groups})


@app.post("/api/group")
def api_group_create():
    data = request.get_json(silent=True) or {}
    group_name = safe_text(data.get('name', ''))
    leader_name = safe_text(data.get('leader_name', ''))
    leader_email = safe_text(data.get('leader_email', ''))
    topic_goal = safe_text(data.get('topic_goal', ''))
    time_boundary = safe_text(data.get('time_boundary', ''))
    execution_plan = safe_text(data.get('execution_plan', ''))
    description = safe_text(data.get('description', ''))
    member_names = data.get('member_names', []) or []
    # Accept a members string from the frontend for compatibility
    members_str = safe_text(data.get('members', ''))
    if members_str and not member_names:
        member_names = [m.strip() for m in members_str.replace('，', ',').split(',') if m.strip()]

    if not group_name or not leader_name or not topic_goal or not time_boundary or not execution_plan:
        return jsonify({"ok": False, "message": "Complete the group name, leader, goal, time boundaries, and execution plan"}), 400

    normalized_members = []
    for item in member_names:
        member_name = safe_text(item)
        if member_name:
            normalized_members.append(member_name)
    if leader_name not in normalized_members:
        normalized_members.append(leader_name)
    normalized_members = sorted(set(normalized_members))
    if len(normalized_members) < 2:
        return jsonify({"ok": False, "message": "An interest group must have at least two members, including its leader"}), 400

    _upsert_user_profile(leader_name, email=leader_email, role='普通用户')
    for member in normalized_members:
        _upsert_user_profile(member, role='普通用户')

    row_data = {
        GROUP_COL_NAME: group_name,
        GROUP_COL_LEADER_NAME: leader_name,
        GROUP_COL_TOPIC_GOAL: topic_goal,
        GROUP_COL_TIME_BOUNDARY: time_boundary,
        GROUP_COL_EXECUTION_PLAN: execution_plan,
        GROUP_COL_DESCRIPTION: description,
        GROUP_COL_STATUS: '活跃',
        GROUP_COL_CREATED_AT: _now_iso(),
    }
    try:
        created = _append_row(INTEREST_GROUP_TABLE_NAME, row_data)
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not create the interest group: {exc}"}), 500

    group_id = str(created.get('_id')) if isinstance(created, dict) else ''
    group = get_interest_group_by_id(group_id)
    if not group:
        groups = list_interest_groups()
        if groups:
            group = groups[-1]
            group_id = str(group.get('_id'))
    group_name_saved = safe_text(group.get(GROUP_COL_NAME, group_name)) if group else group_name

    for member_name in normalized_members:
        member_email = get_user_email(member_name)
        role = '组长' if member_name == leader_name else '组员'
        try:
            _append_row(GROUP_MEMBER_TABLE_NAME, {
                GROUP_MEMBER_COL_GROUP_ID: group_id,
                GROUP_MEMBER_COL_GROUP_NAME: group_name_saved,
                GROUP_MEMBER_COL_MEMBER_NAME: member_name,
                GROUP_MEMBER_COL_MEMBER_EMAIL: member_email,
                GROUP_MEMBER_COL_MEMBER_ROLE: role,
                GROUP_MEMBER_COL_JOINED_AT: _now_iso(),
            })
        except Exception as exc:
            return jsonify({"ok": False, "message": f"Could not save the interest group member: {exc}"}), 500

    touch_version()

    return jsonify({"ok": True, "group": serialize_interest_group(group or get_interest_group_by_id(group_id)), "message": "Interest group created"})


@app.post("/api/group/<group_id>/join")
def api_group_join(group_id):
    group = get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "Interest group not found"}), 404
    data = request.get_json(silent=True) or {}
    member_name = safe_text(data.get('name', ''))
    member_email = safe_text(data.get('email', ''))
    if not member_name:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    if not get_user_profile(member_name) and not member_email:
        return jsonify({"ok": False, "message": "Add an email address before using the system for the first time"}), 400

    _upsert_user_profile(member_name, email=member_email, role='普通用户')
    for membership in _get_memberships_by_name(member_name):
        if str(membership.get(GROUP_MEMBER_COL_GROUP_ID, '')) == str(group_id):
            return jsonify({"ok": False, "message": "You have already joined this interest group"}), 409

    try:
        _append_row(GROUP_MEMBER_TABLE_NAME, {
            GROUP_MEMBER_COL_GROUP_ID: str(group.get('_id')),
            GROUP_MEMBER_COL_GROUP_NAME: safe_text(group.get(GROUP_COL_NAME, '')),
            GROUP_MEMBER_COL_MEMBER_NAME: member_name,
            GROUP_MEMBER_COL_MEMBER_EMAIL: get_user_email(member_name),
            GROUP_MEMBER_COL_MEMBER_ROLE: '组员',
            GROUP_MEMBER_COL_JOINED_AT: _now_iso(),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not join the interest group: {exc}"}), 500

    _notify_group_membership_change(group, member_name, get_user_email(member_name), '加入')
    touch_version()
    return jsonify({"ok": True, "message": "Joined the interest group", "group": serialize_interest_group(group)})


@app.post("/api/group/<group_id>/leave")
def api_group_leave(group_id):
    group = get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "Interest group not found"}), 404
    data = request.get_json(silent=True) or {}
    member_name = safe_text(data.get('name', ''))
    if not member_name:
        return jsonify({"ok": False, "message": "Name is required"}), 400

    membership = None
    for item in list_group_members():
        if str(item.get(GROUP_MEMBER_COL_GROUP_ID, '')) == str(group_id) and safe_text(item.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            membership = item
            break
    if not membership:
        return jsonify({"ok": False, "message": "You are not a member of this interest group"}), 404

    if safe_text(membership.get(GROUP_MEMBER_COL_MEMBER_ROLE, '')) == '组长':
        return jsonify({"ok": False, "message": "The group leader cannot leave until leadership has been transferred"}), 409

    try:
        base.delete_row(GROUP_MEMBER_TABLE_NAME, membership.get('_id'))
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not leave the interest group: {exc}"}), 500

    _notify_group_membership_change(group, member_name, get_user_email(member_name), '退出')
    touch_version()
    return jsonify({"ok": True, "message": "Left the interest group", "group": serialize_interest_group(group)})


@app.get("/api/profile-summary/<name>")
def api_profile_summary(name):
    summary = cached_build('profile_summary', PROFILE_CACHE_TTL_SECONDS, lambda: _build_person_profile_summary(name), safe_text(name))
    if not summary:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    return jsonify({"ok": True, "summary": summary})


@app.get("/api/profile-feed/<name>")
def api_profile_feed(name):
    target = safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    try:
        limit = int(request.args.get('limit', str(PROFILE_FEED_DEFAULT_LIMIT)))
    except Exception:
        limit = PROFILE_FEED_DEFAULT_LIMIT
    type_filter = safe_text(request.args.get('type', ''))
    keyword = safe_text(request.args.get('keyword', ''))
    events = cached_build(
        'profile_feed',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: _build_profile_feed(target, limit=limit, type_filter=type_filter, keyword=keyword),
        target,
        limit,
        type_filter,
        keyword,
    )
    return jsonify({"ok": True, "events": events, "limit": max(1, min(limit, 100))})


@app.get("/api/reviewer-submitted-docs")
def api_reviewer_submitted_docs():
    """List review signups with a submitted document that the current rater has not rated yet."""
    rater_name = safe_text(request.args.get('rater', ''))
    if not rater_name:
        return jsonify({"ok": False, "message": "Pass the rater's name with ?rater="}), 400

    rated_signup_ids = {
        str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip()
        for rating in list_review_ratings()
        if safe_text(rating.get(REVIEW_RATING_COL_RATER_NAME, '')) == rater_name
    }

    docs = []
    for signup in list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        doc_url = get_signup_review_doc_url(signup)
        if not doc_url:
            continue
        signup_id = str(signup.get('_id', '')).strip()
        if signup_id in rated_signup_ids:
            continue
        reviewer_name = _get_signup_name(signup)
        if reviewer_name == rater_name:
            continue
        activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
        activity = get_activity_by_id(activity_id)
        if not activity or not activity_is_closed(activity):
            continue
        docs.append({
            'signup_id': signup_id,
            'reviewer_name': reviewer_name,
            'doc_url': doc_url,
            'activity_id': activity_id,
            'activity_topic': safe_text(activity.get(ACTIVITY_COL_TOPIC, '')),
            'activity_date': safe_text(activity.get(ACTIVITY_COL_DATE, '')).split('T')[0],
        })

    docs.sort(key=lambda x: x.get('activity_date', ''), reverse=True)
    return jsonify({"ok": True, "docs": docs})


@app.get("/api/profile-tasks/<name>")
def api_profile_tasks(name):
    target = safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    tasks = cached_build(
        'profile_tasks',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: _build_profile_tasks(target),
        target,
    )
    return jsonify({"ok": True, "tasks": tasks})


@app.get("/api/profile-recommendations/<name>")
def api_profile_recommendations(name):
    target = safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    try:
        limit = int(request.args.get('limit', '6'))
    except Exception:
        limit = 6
    limit = max(1, min(limit, 20))
    recommendations = cached_build(
        'profile_recommendations',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: _build_profile_recommendations(target, limit=limit),
        target,
        limit,
    )
    return jsonify({"ok": True, "recommendations": recommendations, "limit": limit})


@app.post("/api/invite/<invite_id>/status")
def api_update_invite_status(invite_id):
    invite = get_invite_by_id(invite_id)
    if not invite:
        return jsonify({"ok": False, "message": "Invitation not found"}), 404

    data = request.get_json(silent=True) or {}
    operator_name = safe_text(data.get('operator_name', ''))
    status = safe_text(data.get('status', ''))
    if not operator_name or not status:
        return jsonify({"ok": False, "message": "Provide the actor and target status"}), 400
    if status not in {'已发送', '已接受', '已拒绝', '已撤回'}:
        return jsonify({"ok": False, "message": "Status must be Pending, Accepted, Declined, or Withdrawn"}), 400

    old_status = safe_text(invite.get(INVITE_COL_STATUS, ''))
    if old_status == status:
        return jsonify({"ok": True, "message": "No status change", "invite": serialize_review_invite(invite)})

    inviter_name = safe_text(invite.get(INVITE_COL_INVITER_NAME, ''))
    invitee_name = safe_text(invite.get(INVITE_COL_INVITEE_NAME, ''))
    activity_id = safe_text(invite.get(INVITE_COL_ACTIVITY_ID, ''))
    activity = get_activity_by_id(activity_id)
    activity_creator = _get_activity_creator_name_legacy(activity) if activity else ''
    is_cac_operator = is_cac_user(operator_name)
    is_invitee_operator = operator_name == invitee_name
    allowed = is_cac_operator or operator_name == inviter_name or operator_name == activity_creator or is_invitee_operator
    if not allowed:
        return jsonify({"ok": False, "message": "Only the inviter, invitee, activity organizer, or CAC can change the invitation status"}), 403

    if is_invitee_operator and status not in {'已接受', '已拒绝'}:
        return jsonify({"ok": False, "message": "Invitees can only accept or decline an invitation"}), 403

    if not _is_invite_transition_allowed(old_status, status, is_cac_operator=is_cac_operator):
        return jsonify({"ok": False, "message": f"Cannot change the status from {old_status} to {status}. Only CAC can force a reset."}), 409

    try:
        _update_row(REVIEW_INVITE_TABLE_NAME, invite.get('_id'), {
            INVITE_COL_STATUS: status,
            INVITE_COL_UPDATED_AT: _now_iso(),
            INVITE_COL_UPDATED_BY: operator_name,
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not update the invitation status: {exc}"}), 500

    refreshed = get_invite_by_id(invite_id) or invite

    invitee_email = safe_text(refreshed.get(INVITE_COL_INVITEE_EMAIL, ''))
    if invitee_email and status in {'已接受', '已拒绝', '已撤回'}:
        topic = safe_text(refreshed.get(INVITE_COL_ACTIVITY_TOPIC, '')) or 'Untitled activity'
        invitee_name = safe_text(refreshed.get(INVITE_COL_INVITEE_NAME, '')) or 'there'
        subject = f"[CAC Share Sessions] Invitation status update: {topic}"
        body = (
            f"Hello, {invitee_name},\n\n"
            f"Your invitation status for “{topic}” is now {_english_label(status)}.\n"
            f"Updated by: {operator_name}\n"
        )
        _send_email_async(invitee_email, subject, body)

    touch_version()

    return jsonify({"ok": True, "message": "Invitation status updated", "invite": serialize_review_invite(refreshed)})


# ===== Speaker management API =====
@app.get("/api/my-activities/<name>")
def api_my_activities(name):
    """List activities created by a speaker."""
    name = str(name).strip()
    if not name:
        return jsonify({"ok": False, "message": "Name is required"}), 400
    
    activities = list_activities()
    my_activities = []
    
    for activity in activities:
        creator_name = _get_activity_creator_name_legacy(activity)
        if creator_name == name:
            activity_id = activity.get('_id')
            details = get_activity_details(activity)
            stats = _get_signup_stats_local(activity_id)
            # List signups, including review content
            signups = get_activity_signups(activity_id)
            signups_list = [_serialize_review_task(s) for s in signups]
            my_activities.append({
                **details,
                **stats,
                'review_documents': _get_activity_review_documents(activity_id, include_pending=True),
                'signups': signups_list,
            })
    
    return jsonify({
        "ok": True,
        "activities": my_activities,
    })


@app.post("/api/output-record")
def api_create_output_record():
    """Record an external contribution, such as a CAC Meetup."""
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    output_type = str(data.get('output_type', '')).strip()
    output_date = str(data.get('date', '')).strip()
    note = str(data.get('note', '')).strip()
    if not name or not output_type or not output_date:
        return jsonify({"ok": False, "message": "Provide a name, output type, and date"}), 400
    if output_type not in {'分享', '评议', 'CAC有约'}:
        return jsonify({"ok": False, "message": "Output type must be Sharing, Reviewing, or CAC-hosted session"}), 400

    try:
        _append_row(OUTPUT_RECORD_TABLE_NAME, {
            OUTPUT_RECORD_COL_NAME: name,
            OUTPUT_RECORD_COL_TYPE: output_type,
            OUTPUT_RECORD_COL_DATE: output_date,
            OUTPUT_RECORD_COL_NOTE: note,
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not save the output record: {exc}"}), 500

    touch_version()

    return jsonify({"ok": True, "message": "Output record added"})


@app.post("/api/activity")
def api_create_activity():
    """Create an activity as a speaker."""
    data = request.get_json(silent=True) or {}
    
    # Validate required fields.
    date = str(data.get("date", "")).strip()
    time = str(data.get("time", "")).strip()
    speakers = str(data.get("speakers", "")).strip()
    topic = str(data.get("topic", "")).strip()
    creator_name = str(data.get("creator_name", "")).strip()
    creator_email = str(data.get("creator_email", "")).strip()
    activity_type = safe_text(data.get("activity_type", "normal")) or 'normal'
    group_id = safe_text(data.get("group_id", ""))
    classroom = str(data.get("classroom", "")).strip()
    videourl = str(data.get("videourl", "")).strip()
    
    if not date or not time or not speakers or not topic or not creator_name:
        return jsonify({
            "ok": False, 
            "message": "Provide the date, time, speakers, topic, and name"
        }), 400

    if activity_type not in {'normal', 'cac有约'}:
        return jsonify({"ok": False, "message": "Activity type must be regular or CAC-hosted"}), 400

    # Validate CAC-hosted session time constraints
    if activity_type == 'cac有约':
        from datetime import datetime
        try:
            dt = datetime.strptime(date, '%Y-%m-%d')
        except:
            return jsonify({"ok": False, "message": "Invalid date format"}), 400
        if dt.weekday() != 6:  # 0 = Monday, 6 = Sunday
            return jsonify({"ok": False, "message": "CAC-hosted sessions can only be held on Sundays"}), 400
        allowed_slots = ['14:00-14:30', '14:30-15:00', '15:00-15:30', '15:30-16:00',
                         '16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00']
        if time not in allowed_slots:
            return jsonify({"ok": False, "message": "CAC-hosted sessions must run on Sundays from 14:00 to 18:00 in 30-minute increments"}), 400

    if not get_user_profile(creator_name) and not creator_email:
        return jsonify({"ok": False, "message": "Add an email address before creating an activity for the first time"}), 400
    _upsert_user_profile(creator_name, email=creator_email, role='普通用户')

    creator_memberships = _get_memberships_by_name(creator_name)
    selected_group = None
    if activity_type == 'normal':
        if len(creator_memberships) > 1 and not group_id:
            return jsonify({"ok": False, "message": "You belong to multiple interest groups. Select a group when creating the activity."}), 400
        if group_id:
            selected_group = get_interest_group_by_id(group_id)
            if not selected_group:
                return jsonify({"ok": False, "message": "Selected interest group not found"}), 404
            member_group_ids = set(_get_group_ids_for_member(creator_name))
            if group_id not in member_group_ids:
                return jsonify({"ok": False, "message": "You can only select a group you have joined"}), 403
        elif len(creator_memberships) == 1:
            selected_group = get_interest_group_by_id(creator_memberships[0].get(GROUP_MEMBER_COL_GROUP_ID, ''))

    # Check for scheduling conflicts.
    warnings = []
    classroom_conflict = False
    classroom_conflict_msg = ""
    existing_activities = list_activities()
    new_range = _parse_time_range(time)

    if new_range:
        for act in existing_activities:
            existing_date = str(act.get(ACTIVITY_COL_DATE, '')).strip()
            existing_type = str(act.get(ACTIVITY_COL_TYPE, '')).strip() or 'normal'
            existing_classroom = str(act.get(ACTIVITY_COL_CLASSROOM, '')).strip()

            # Activities on different dates cannot conflict
            if existing_date != date:
                continue

            existing_range = _parse_time_range(act.get(ACTIVITY_COL_TIME, ''))
            if not (existing_range and _times_overlap(new_range, existing_range)):
                continue

            existing_topic = str(act.get(ACTIVITY_COL_TOPIC, '')).strip()

            # Check room conflicts separately for CAC-hosted sessions and regular activities
            if classroom and existing_classroom == classroom:
                # Block room conflicts between activities of the same type
                if activity_type == existing_type:
                    classroom_conflict = True
                    classroom_conflict_msg = f"Room “{classroom}” is already reserved for a same-type activity (“{existing_topic}”). Choose another room or time."
                # Warn about room conflicts between different activity types
                else:
                    type_label = 'CAC-hosted session' if existing_type == 'cac有约' else 'regular activity'
                    warnings.append(f"Room “{classroom}” is already reserved during this time by {type_label} “{existing_topic}”. Continue anyway?")

            # Check time conflicts that do not involve a room
            # Rule 1: Overlapping regular activities trigger a warning only.
            if activity_type != 'cac有约' and existing_type != 'cac有约' and not classroom:
                warnings.append(f"Overlaps with the existing activity “{existing_topic}” (regular activity). Continue?")

            # Rule 2: warn when a regular activity overlaps a CAC-hosted session; types remain independent
            elif activity_type != 'cac有约' and existing_type == 'cac有约' and not classroom:
                warnings.append(f"Conflicts with the CAC-hosted session “{existing_topic}”. Rescheduling is strongly recommended.")

            # Rule 3: warn when a CAC-hosted session overlaps a regular activity; types remain independent
            elif activity_type == 'cac有约' and existing_type != 'cac有约' and not classroom:
                warnings.append(f"Conflicts with existing regular activity “{existing_topic}”; rescheduling is strongly recommended.")

    # Room conflicts prevent submission.
    if classroom_conflict:
        return jsonify({"ok": False, "message": classroom_conflict_msg}), 409

    # Create the activity record.
    row_data = {
        ACTIVITY_COL_DATE: date,
        ACTIVITY_COL_TIME: time,
        ACTIVITY_COL_SPEAKERS: speakers,
        ACTIVITY_COL_TOPIC: topic,
        ACTIVITY_COL_TYPE: activity_type,
        ACTIVITY_COL_GROUP_ID: str(selected_group.get('_id')) if selected_group else None,
        ACTIVITY_COL_GROUP_NAME: safe_text(selected_group.get(GROUP_COL_NAME, '')) if selected_group else None,
        ACTIVITY_COL_CREATOR_NAME: creator_name,
        LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID: creator_name,
        ACTIVITY_COL_CREATOR_EMAIL: creator_email,
        ACTIVITY_COL_CLASSROOM: classroom if classroom else None,
        ACTIVITY_COL_VIDEOURL: videourl if videourl else None,
    }
    
    try:
        _append_row(ACTIVITY_TABLE_NAME, row_data)
        response = {"ok": True, "message": "Activity created"}
        if warnings:
            response["warnings"] = warnings
        _notify_activity_change(
            creator_email,
            creator_name,
            topic,
            '创建',
            [f"Activity time: {date} {time}"],
        )
        _notify_cac_activity_created(activity_type, topic, creator_name)
        touch_version()
        return jsonify(response), 201
    except Exception as e:
        return jsonify({"ok": False, "message": f"Could not create activity: {str(e)}"}), 500


@app.put("/api/activity/<activity_id>")
def api_update_activity(activity_id):
    """Edit an activity (organizers only)."""
    activity_id = str(activity_id).strip()
    activity = get_activity_by_id(activity_id)
    
    if not activity:
        return jsonify({"ok": False, "message": "Activity not found"}), 404
    
    data = request.get_json(silent=True) or {}
    creator_name = str(data.get("creator_name", "")).strip()
    
    # Verify the user's identity.
    actual_creator = _get_activity_creator_name_legacy(activity)
    if actual_creator != creator_name:
        return jsonify({
            "ok": False, 
            "message": "Only the activity organizer can edit this activity"
        }), 403
    
    # Prepare the update data
    update_data = {}
    if "date" in data:
        update_data[ACTIVITY_COL_DATE] = str(data["date"]).strip()
    if "time" in data:
        update_data[ACTIVITY_COL_TIME] = str(data["time"]).strip()
    if "speakers" in data:
        update_data[ACTIVITY_COL_SPEAKERS] = str(data["speakers"]).strip()
    if "topic" in data:
        update_data[ACTIVITY_COL_TOPIC] = str(data["topic"]).strip()
    if "classroom" in data:
        update_data[ACTIVITY_COL_CLASSROOM] = str(data["classroom"]).strip() or None
    if "videourl" in data:
        update_data[ACTIVITY_COL_VIDEOURL] = str(data["videourl"]).strip() or None
    if "creator_email" in data:
        update_data[ACTIVITY_COL_CREATOR_EMAIL] = str(data["creator_email"]).strip() or None
    if "activity_type" in data:
        new_type = safe_text(data.get("activity_type", ""))
        if new_type and new_type not in {'normal', 'cac有约'}:
            return jsonify({"ok": False, "message": "Activity type must be regular or CAC-hosted"}), 400
        update_data[ACTIVITY_COL_TYPE] = new_type or None
    if "group_id" in data:
        new_group_id = safe_text(data.get("group_id", ""))
        if new_group_id:
            group = get_interest_group_by_id(new_group_id)
            if not group:
                return jsonify({"ok": False, "message": "Selected interest group not found"}), 404
            update_data[ACTIVITY_COL_GROUP_ID] = str(group.get('_id'))
            update_data[ACTIVITY_COL_GROUP_NAME] = safe_text(group.get(GROUP_COL_NAME, ''))
        else:
            update_data[ACTIVITY_COL_GROUP_ID] = None
            update_data[ACTIVITY_COL_GROUP_NAME] = None
    
    if not update_data:
        return jsonify({
            "ok": False, 
            "message": "There are no changes to save"
        }), 400
    
    try:
        _update_row(ACTIVITY_TABLE_NAME, activity.get('_id'), update_data)
        creator_email = str(data.get("creator_email", "")).strip() or get_activity_creator_email(activity)
        _notify_activity_change(
            creator_email,
            creator_name,
            str(update_data.get(ACTIVITY_COL_TOPIC) or activity.get(ACTIVITY_COL_TOPIC, '')).strip(),
            '更新',
            [
                f"Activity date: {str(update_data.get(ACTIVITY_COL_DATE) or activity.get(ACTIVITY_COL_DATE, '')).strip()}",
                f"Activity time: {str(update_data.get(ACTIVITY_COL_TIME) or activity.get(ACTIVITY_COL_TIME, '')).strip()}",
            ],
        )
        touch_version()
        return jsonify({"ok": True, "message": "Activity updated"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Update failed: {str(e)}"}), 500


@app.post("/api/activity/<activity_id>/close")
def api_close_activity(activity_id):
    """Close an activity, calculate on-time closure rates, and send review reminders."""
    activity_id = str(activity_id).strip()
    activity = get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "Activity not found"}), 404
    data = request.get_json(silent=True) or {}
    creator_name = str(data.get('creator_name', '')).strip()
    if _get_activity_creator_name_legacy(activity) != creator_name:
        return jsonify({"ok": False, "message": "Only the activity organizer can close this activity"}), 403
    if activity_is_closed(activity):
        return jsonify({"ok": False, "message": "This activity has already been closed"}), 409

    closed_at = _now()
    on_time = _compute_activity_on_time(activity, closed_at=closed_at)
    try:
        _update_row(ACTIVITY_TABLE_NAME, activity.get('_id'), {
            ACTIVITY_COL_STATUS: '已结项',
            ACTIVITY_COL_CLOSED_AT: closed_at.strftime('%Y-%m-%d %H:%M:%S'),
            ACTIVITY_COL_ON_TIME: 'true' if on_time else 'false',
            ACTIVITY_COL_CLOSER_NAME: creator_name,
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Could not close the activity: {exc}"}), 500

    refreshed_activity = get_activity_by_id(activity_id) or activity
    activity_type = safe_text(refreshed_activity.get(ACTIVITY_COL_TYPE, '')) or 'normal'
    if activity_type != 'cac有约':
        for reviewer_signup in get_activity_signups(activity_id, role='评议员'):
            if get_signup_review_doc_url(reviewer_signup):
                continue
            _notify_review_doc_reminder(reviewer_signup, refreshed_activity)
            try:
                _update_row(SIGNUP_TABLE_NAME, reviewer_signup.get('_id'), {
                    SIGNUP_COL_LAST_REVIEW_REMINDER_AT: _now_iso(),
                })
            except Exception as exc:
                logger.error("Update immediate reminder timestamp failed: %s", exc)

    touch_version()

    return jsonify({
        "ok": True,
        "message": "Activity closed",
        "on_time": on_time,
    })


@app.delete("/api/activity/<activity_id>")
def api_delete_activity(activity_id):
    """Delete an activity (organizers only; notify registered participants)."""
    activity_id = str(activity_id).strip()
    activity = get_activity_by_id(activity_id)

    if not activity:
        return jsonify({"ok": False, "message": "Activity not found"}), 404

    data = request.get_json(silent=True) or {}
    creator_name = str(data.get("creator_name", "")).strip()

    # Verify the user's identity.
    actual_creator = _get_activity_creator_name_legacy(activity)
    if actual_creator != creator_name:
        return jsonify({
            "ok": False,
            "message": "Only the activity organizer can delete this activity"
        }), 403

    # Get the activity details.
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or 'Untitled activity'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or 'Date to be confirmed'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or 'Time to be confirmed'

    # Notify everyone who signed up.
    signups = get_activity_signups(activity_id)
    notified_count = 0
    for signup in signups:
        signup_name = _get_signup_name(signup)
        signup_email = _get_signup_email(signup)
        if signup_email:
            subject = f"[CAC Share Sessions] Activity cancelled: {topic}"
            body = (
                f"Hello {signup_name},\n\n"
                f"We are sorry to inform you that the organizer has cancelled the activity you registered for:\n\n"
                f"Activity: {topic}\n"
                f"Time: {date} {time}\n\n"
                f"If you have questions, contact the activity organizer, {creator_name}.\n\n"
                f"— CAC Share Sessions"
            )
            _send_email_async(signup_email, subject, body)
            notified_count += 1

    # Delete all signup records.
    for signup in signups:
        try:
            base.delete_row(SIGNUP_TABLE_NAME, signup.get('_id'))
        except Exception:
            pass

    # Delete the activity record.
    try:
        base.delete_row(ACTIVITY_TABLE_NAME, activity.get('_id'))
        _notify_activity_change(
            get_activity_creator_email(activity),
            creator_name,
            topic,
            '删除',
        )
        touch_version()
        msg = "Activity deleted"
        if notified_count > 0:
            msg += f". {notified_count} participant(s) notified."
        return jsonify({"ok": True, "message": msg})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Delete failed: {str(e)}"}), 500


# ===== CAC administrator API =====


@app.get("/api/cac-admins")
def apilist_cac_admins():
    """List CAC administrators."""
    return jsonify({"ok": True, "admins": list_cac_admins()})


@app.post("/api/cac-admin")
def api_add_cac_admin():
    """Add a CAC administrator."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    requester_name = str(data.get("requester_name", "")).strip()

    if not name:
        return jsonify({"ok": False, "message": "Name is required"}), 400

    # Check permissions: allow existing administrators or initial setup when the list is empty
    existing_admins = list_cac_admins()
    if existing_admins and not is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "Only an administrator can add another administrator"}), 403

    # Check whether the record already exists.
    if is_cac_admin(name):
        return jsonify({"ok": False, "message": "This user is already an administrator"}), 400

    try:
        _append_row(CAC_ADMINS_TABLE_NAME, {
            CAC_ADMIN_COL_NAME: name,
            CAC_ADMIN_COL_CREATED_AT: _now_iso(),
        })
        return jsonify({"ok": True, "message": f"Added {name} as an administrator"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Add failed: {str(e)}"}), 500


@app.delete("/api/cac-admin/<name>")
def api_delete_cac_admin(name):
    """Remove a CAC administrator."""
    try:
        name = str(name).strip()
        data = request.get_json(silent=True) or {}
        requester_name = str(data.get("requester_name", "")).strip()

        if not requester_name:
            return jsonify({"ok": False, "message": "The requester's name is required"}), 400

        if not is_cac_admin(requester_name):
            return jsonify({"ok": False, "message": "Only an administrator can remove an administrator"}), 403

        rows = _list_rows(CAC_ADMINS_TABLE_NAME)
        for row in rows:
            if str(row.get(CAC_ADMIN_COL_NAME, '')).strip() == name:
                try:
                    base.delete_row(CAC_ADMINS_TABLE_NAME, row.get('_id'))
                    return jsonify({"ok": True, "message": f"Removed administrator access for {name}"})
                except Exception as e:
                    logger.error("Delete CAC admin row failed: %s", e)
                    return jsonify({"ok": False, "message": f"Delete failed: {str(e)}"}), 500

        return jsonify({"ok": False, "message": "This user is not an administrator"}), 404
    except Exception as e:
        logger.error("api_delete_cac_admin unexpected error: %s", e)
        return jsonify({"ok": False, "message": f"Server error: {str(e)}"}), 500


# ===== CAC room-slot API =====

def _list_cac_room_slots_local(date=None, time_slot=None):
    """getCAC room slotlist

    A time_slot may be a single interval such as '14:00-14:30' or a merged interval such as '14:00-15:30'.
    For a merged interval, return rooms that are available for every 30-minute slot in the range.
    """
    rows = _list_rows(CAC_ROOM_SLOTS_TABLE_NAME)

    # Parse the required 30-minute time slots
    required_slots = []
    if time_slot:
        # Parse multiple time ranges separated by commas
        for ts in time_slot.split(','):
            ts = ts.strip()
            if not ts:
                continue
            start, end = ts.split('-')[0], ts.split('-')[1]
            # Generate every 30-minute slot in the range
            start_h, start_m = int(start.split(':')[0]), int(start.split(':')[1])
            end_h, end_m = int(end.split(':')[0]), int(end.split(':')[1])
            current_h, current_m = start_h, start_m
            while current_h * 60 + current_m < end_h * 60 + end_m:
                next_h, next_m = current_h, current_m + 30
                if next_m >= 60:
                    next_h += 1
                    next_m -= 60
                required_slots.append(f"{current_h:02d}:{current_m:02d}-{next_h:02d}:{next_m:02d}")
                current_h, current_m = next_h, next_m

    # Check that each room is available for every required time slot.
    classroom_slots = {}  # {classroom: set of available time_slots}
    for row in rows:
        slot_date = str(row.get(CAC_SLOT_COL_DATE, '')).strip()
        slot_time = str(row.get(CAC_SLOT_COL_TIME_SLOT, '')).strip()
        slot_status = str(row.get(CAC_SLOT_COL_STATUS, 'available')).strip()
        slot_classroom = str(row.get(CAC_SLOT_COL_CLASSROOM, '')).strip()

        if date and slot_date != date:
            continue
        if slot_status != 'available':
            continue

        if slot_classroom not in classroom_slots:
            classroom_slots[slot_classroom] = set()
        classroom_slots[slot_classroom].add(slot_time)

    result = []
    if required_slots:
        # Find rooms available for every required time slot
        required_set = set(required_slots)
        for classroom, available_slots in classroom_slots.items():
            if required_set.issubset(available_slots):
                result.append({
                    'id': f"{classroom}-{date}-{time_slot}",
                    'classroom': classroom,
                    'date': date,
                    'time_slot': time_slot,
                    'status': 'available',
                })
    else:
        # If no time is specified, return all available slots.
        for row in rows:
            slot_date = str(row.get(CAC_SLOT_COL_DATE, '')).strip()
            if date and slot_date != date:
                continue
            slot_status = str(row.get(CAC_SLOT_COL_STATUS, 'available')).strip()
            if slot_status != 'available':
                continue
            result.append({
                'id': row.get('_id'),
                'classroom': str(row.get(CAC_SLOT_COL_CLASSROOM, '')).strip(),
                'date': slot_date,
                'time_slot': str(row.get(CAC_SLOT_COL_TIME_SLOT, '')).strip(),
                'status': slot_status,
            })

    return result


@app.get("/api/cac-room-slots")
def apilist_cac_room_slots():
    """Get available room time slots."""
    date = str(request.args.get("date", "")).strip()
    time_slot = str(request.args.get("time_slot", "")).strip()
    slots = _list_cac_room_slots_local(date=date, time_slot=time_slot)
    return jsonify({"ok": True, "slots": slots})


@app.post("/api/cac-room-slot")
def api_add_cac_room_slot():
    """Add a room time slot as an administrator."""
    data = request.get_json(silent=True) or {}
    classroom = str(data.get("classroom", "")).strip()
    date = str(data.get("date", "")).strip()
    time_slot = str(data.get("time_slot", "")).strip()
    requester_name = str(data.get("requester_name", "")).strip()

    if not is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "Only an administrator can add room slots"}), 403

    if not classroom or not date or not time_slot:
        return jsonify({"ok": False, "message": "Provide a room, date, and time slot"}), 400

    try:
        _append_row(CAC_ROOM_SLOTS_TABLE_NAME, {
            CAC_SLOT_COL_CLASSROOM: classroom,
            CAC_SLOT_COL_DATE: date,
            CAC_SLOT_COL_TIME_SLOT: time_slot,
            CAC_SLOT_COL_STATUS: 'available',
            CAC_SLOT_COL_ACTIVITY_ID: '',
            CAC_SLOT_COL_CREATED_BY: requester_name,
            CAC_SLOT_COL_CREATED_AT: _now_iso(),
        })
        return jsonify({"ok": True, "message": "Room slot added"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Add failed: {str(e)}"}), 500


@app.delete("/api/cac-room-slot/<slot_id>")
def api_delete_cac_room_slot(slot_id):
    """Remove a room time slot as an administrator."""
    data = request.get_json(silent=True) or {}
    requester_name = str(data.get("requester_name", "")).strip()

    if not is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "Only an administrator can delete room slots"}), 403

    rows = _list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if row.get('_id') == slot_id:
            try:
                base.delete_row(CAC_ROOM_SLOTS_TABLE_NAME, slot_id)
                return jsonify({"ok": True, "message": "Room slot deleted"})
            except Exception as e:
                return jsonify({"ok": False, "message": f"Delete failed: {str(e)}"}), 500

    return jsonify({"ok": False, "message": "Room slot not found"}), 404


_maintenance_thread_started = False
_shutdown_event = threading.Event()


def _ensure_background_maintenance_started():
    global _maintenance_thread_started
    if _maintenance_thread_started:
        return
    _maintenance_thread_started = True
    threading.Thread(target=_background_maintenance_loop, daemon=True).start()


def shutdown_background_tasks():
    """Gracefully shut down the background maintenance thread."""
    _shutdown_event.set()


_atexit_registered = False


def _register_shutdown():
    global _atexit_registered
    if not _atexit_registered:
        import atexit
        atexit.register(shutdown_background_tasks)
        _atexit_registered = True


_ensure_background_maintenance_started()
_register_shutdown()


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)


import os
import re
import json
import smtplib
import threading
import time
import platform
import tempfile
import uuid
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from email.message import EmailMessage

# 自定义异常处理
from utils import (
    AppError, DatabaseError, ValidationError, NotFoundError, AuthError, ConflictError,
    success_response, error_response
)

# 路由蓝图
from routes import (
    activity_bp, signup_bp, cac_bp, group_bp,
    profile_bp, invite_bp, stats_bp
)

# fcntl is only available on Unix/Linux
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
try:
    import pymysql
except Exception:
    pymysql = None


load_dotenv()

SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "https://table.nju.edu.cn").rstrip("/")
API_TOKEN = os.getenv("SEATABLE_API_TOKEN", "")
DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().lower()
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "table_signup").strip()
MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "5"))
MYSQL_READ_TIMEOUT = int(os.getenv("MYSQL_READ_TIMEOUT", "30"))
MYSQL_WRITE_TIMEOUT = int(os.getenv("MYSQL_WRITE_TIMEOUT", "30"))
TABLE_ROWS_CACHE_TTL_SECONDS = int(os.getenv("TABLE_ROWS_CACHE_TTL_SECONDS", "120"))

# ===== 表名配置 =====
ACTIVITY_TABLE_NAME = os.getenv("ACTIVITY_TABLE_NAME", "分享会活动")
SIGNUP_TABLE_NAME = os.getenv("SIGNUP_TABLE_NAME", "分享会报名")
REVIEW_RATING_TABLE_NAME = os.getenv("REVIEW_RATING_TABLE_NAME", "评议评分")
OUTPUT_RECORD_TABLE_NAME = os.getenv("OUTPUT_RECORD_TABLE_NAME", "输出活动记录")
USER_PROFILE_TABLE_NAME = os.getenv("USER_PROFILE_TABLE_NAME", "用户档案")
INTEREST_GROUP_TABLE_NAME = os.getenv("INTEREST_GROUP_TABLE_NAME", "兴趣组")
GROUP_MEMBER_TABLE_NAME = os.getenv("GROUP_MEMBER_TABLE_NAME", "兴趣组成员")
REVIEW_INVITE_TABLE_NAME = os.getenv("REVIEW_INVITE_TABLE_NAME", "评议邀请")
CAC_ADMINS_TABLE_NAME = os.getenv("CAC_ADMINS_TABLE_NAME", "CAC管理员")
CAC_ROOM_SLOTS_TABLE_NAME = os.getenv("CAC_ROOM_SLOTS_TABLE_NAME", "CAC教室时间槽")

# ===== 活动表字段 =====
ACTIVITY_COL_DATE = os.getenv("ACTIVITY_COL_DATE", "活动日期")
ACTIVITY_COL_TIME = os.getenv("ACTIVITY_COL_TIME", "活动时间")
ACTIVITY_COL_SPEAKERS = os.getenv("ACTIVITY_COL_SPEAKERS", "分享者")
ACTIVITY_COL_TOPIC = os.getenv("ACTIVITY_COL_TOPIC", "活动主题")
ACTIVITY_COL_CLASSROOM = os.getenv("ACTIVITY_COL_CLASSROOM", "活动教室")
ACTIVITY_COL_VIDEOURL = os.getenv("ACTIVITY_COL_VIDEOURL", "线上视频号")
ACTIVITY_COL_CREATOR_NAME = os.getenv("ACTIVITY_COL_CREATOR_NAME", "组织者姓名")
ACTIVITY_COL_CREATOR_EMAIL = os.getenv("ACTIVITY_COL_CREATOR_EMAIL", "组织者邮箱")
ACTIVITY_COL_STATUS = os.getenv("ACTIVITY_COL_STATUS", "活动状态")
ACTIVITY_COL_CLOSED_AT = os.getenv("ACTIVITY_COL_CLOSED_AT", "结项时间")
ACTIVITY_COL_ON_TIME = os.getenv("ACTIVITY_COL_ON_TIME", "准时结项")
ACTIVITY_COL_CLOSER_NAME = os.getenv("ACTIVITY_COL_CLOSER_NAME", "结项人")
ACTIVITY_COL_TYPE = os.getenv("ACTIVITY_COL_TYPE", "活动类型")
ACTIVITY_COL_GROUP_ID = os.getenv("ACTIVITY_COL_GROUP_ID", "所属兴趣组ID")
ACTIVITY_COL_GROUP_NAME = os.getenv("ACTIVITY_COL_GROUP_NAME", "所属兴趣组")
LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID = os.getenv("ACTIVITY_COL_CREATOR_STUDENT_ID", "组织者学号")

# ===== 报名表字段 =====
SIGNUP_COL_NAME = os.getenv("SIGNUP_COL_NAME", "姓名")
SIGNUP_COL_ACTIVITY_ID = os.getenv("SIGNUP_COL_ACTIVITY_ID", "关联活动")
SIGNUP_COL_ROLE = os.getenv("SIGNUP_COL_ROLE", "角色")
SIGNUP_COL_PHONE = os.getenv("SIGNUP_COL_PHONE", "联系电话")
SIGNUP_COL_EMAIL = os.getenv("SIGNUP_COL_EMAIL", "邮箱")
SIGNUP_COL_REVIEW_DOC_URL = os.getenv("SIGNUP_COL_REVIEW_DOC_URL", "评议语雀链接")
SIGNUP_COL_REVIEW_SUBMITTED_AT = os.getenv("SIGNUP_COL_REVIEW_SUBMITTED_AT", "评议提交时间")
SIGNUP_COL_LAST_REVIEW_REMINDER_AT = os.getenv("SIGNUP_COL_LAST_REVIEW_REMINDER_AT", "上次评议提醒时间")
LEGACY_SIGNUP_COL_STUDENT_ID = os.getenv("SIGNUP_COL_STUDENT_ID", "学号")
SIGNUP_COL_REVIEW_CONTENT = os.getenv("SIGNUP_COL_REVIEW_CONTENT", "评议内容")

# ===== 评议评分表字段 =====
REVIEW_RATING_COL_SIGNUP_ID = os.getenv("REVIEW_RATING_COL_SIGNUP_ID", "评议报名ID")
REVIEW_RATING_COL_ACTIVITY_ID = os.getenv("REVIEW_RATING_COL_ACTIVITY_ID", "活动ID")
REVIEW_RATING_COL_REVIEWER_NAME = os.getenv("REVIEW_RATING_COL_REVIEWER_NAME", "评议者姓名")
REVIEW_RATING_COL_RATER_NAME = os.getenv("REVIEW_RATING_COL_RATER_NAME", "评分人姓名")
REVIEW_RATING_COL_SCORE = os.getenv("REVIEW_RATING_COL_SCORE", "评分")
REVIEW_RATING_COL_WEIGHT = os.getenv("REVIEW_RATING_COL_WEIGHT", "权重")
REVIEW_RATING_COL_COMMENT = os.getenv("REVIEW_RATING_COL_COMMENT", "评分备注")

# ===== 输出活动记录表字段 =====
OUTPUT_RECORD_COL_NAME = os.getenv("OUTPUT_RECORD_COL_NAME", "姓名")
OUTPUT_RECORD_COL_TYPE = os.getenv("OUTPUT_RECORD_COL_TYPE", "输出类型")
OUTPUT_RECORD_COL_DATE = os.getenv("OUTPUT_RECORD_COL_DATE", "输出日期")
OUTPUT_RECORD_COL_NOTE = os.getenv("OUTPUT_RECORD_COL_NOTE", "备注")

# ===== 用户档案字段 =====
USER_COL_NAME = os.getenv("USER_COL_NAME", "姓名")
USER_COL_EMAIL = os.getenv("USER_COL_EMAIL", "邮箱")
USER_COL_ROLE = os.getenv("USER_COL_ROLE", "角色")
USER_COL_FIRST_SEEN_AT = os.getenv("USER_COL_FIRST_SEEN_AT", "首次使用时间")

# ===== 兴趣组字段 =====
GROUP_COL_NAME = os.getenv("GROUP_COL_NAME", "组名")
GROUP_COL_LEADER_NAME = os.getenv("GROUP_COL_LEADER_NAME", "组长")
GROUP_COL_TOPIC_GOAL = os.getenv("GROUP_COL_TOPIC_GOAL", "主题目标")
GROUP_COL_TIME_BOUNDARY = os.getenv("GROUP_COL_TIME_BOUNDARY", "时间边界")
GROUP_COL_EXECUTION_PLAN = os.getenv("GROUP_COL_EXECUTION_PLAN", "执行方案")
GROUP_COL_DESCRIPTION = os.getenv("GROUP_COL_DESCRIPTION", "简介")
GROUP_COL_STATUS = os.getenv("GROUP_COL_STATUS", "状态")
GROUP_COL_CREATED_AT = os.getenv("GROUP_COL_CREATED_AT", "创建时间")

# ===== 兴趣组成员字段 =====
GROUP_MEMBER_COL_GROUP_ID = os.getenv("GROUP_MEMBER_COL_GROUP_ID", "兴趣组ID")
GROUP_MEMBER_COL_GROUP_NAME = os.getenv("GROUP_MEMBER_COL_GROUP_NAME", "兴趣组名")
GROUP_MEMBER_COL_MEMBER_NAME = os.getenv("GROUP_MEMBER_COL_MEMBER_NAME", "成员姓名")
GROUP_MEMBER_COL_MEMBER_EMAIL = os.getenv("GROUP_MEMBER_COL_MEMBER_EMAIL", "成员邮箱")
GROUP_MEMBER_COL_MEMBER_ROLE = os.getenv("GROUP_MEMBER_COL_MEMBER_ROLE", "成员身份")
GROUP_MEMBER_COL_JOINED_AT = os.getenv("GROUP_MEMBER_COL_JOINED_AT", "加入时间")

# ===== 评议邀请字段 =====
INVITE_COL_ACTIVITY_ID = os.getenv("INVITE_COL_ACTIVITY_ID", "活动ID")
INVITE_COL_ACTIVITY_TOPIC = os.getenv("INVITE_COL_ACTIVITY_TOPIC", "活动主题")
INVITE_COL_INVITER_NAME = os.getenv("INVITE_COL_INVITER_NAME", "邀请人")
INVITE_COL_INVITEE_NAME = os.getenv("INVITE_COL_INVITEE_NAME", "被邀请人")
INVITE_COL_INVITEE_EMAIL = os.getenv("INVITE_COL_INVITEE_EMAIL", "被邀请邮箱")
INVITE_COL_SOURCE_TYPE = os.getenv("INVITE_COL_SOURCE_TYPE", "邀请来源")
INVITE_COL_STATUS = os.getenv("INVITE_COL_STATUS", "状态")
INVITE_COL_CREATED_AT = os.getenv("INVITE_COL_CREATED_AT", "邀请时间")
INVITE_COL_UPDATED_AT = os.getenv("INVITE_COL_UPDATED_AT", "状态更新时间")
INVITE_COL_UPDATED_BY = os.getenv("INVITE_COL_UPDATED_BY", "状态更新人")

# ===== CAC管理员字段 =====
CAC_ADMIN_COL_NAME = os.getenv("CAC_ADMIN_COL_NAME", "姓名")
CAC_ADMIN_COL_CREATED_AT = os.getenv("CAC_ADMIN_COL_CREATED_AT", "添加时间")

# ===== CAC教室时间槽字段 =====
CAC_SLOT_COL_CLASSROOM = os.getenv("CAC_SLOT_COL_CLASSROOM", "教室")
CAC_SLOT_COL_DATE = os.getenv("CAC_SLOT_COL_DATE", "日期")
CAC_SLOT_COL_TIME_SLOT = os.getenv("CAC_SLOT_COL_TIME_SLOT", "时间段")
CAC_SLOT_COL_STATUS = os.getenv("CAC_SLOT_COL_STATUS", "状态")
CAC_SLOT_COL_ACTIVITY_ID = os.getenv("CAC_SLOT_COL_ACTIVITY_ID", "关联活动ID")
CAC_SLOT_COL_CREATED_BY = os.getenv("CAC_SLOT_COL_CREATED_BY", "创建者")
CAC_SLOT_COL_CREATED_AT = os.getenv("CAC_SLOT_COL_CREATED_AT", "创建时间")

# ===== 自动注册列配置 =====
# 定义每个表需要的列，启动时自动同步到 app_table_columns
AUTO_REGISTER_COLUMNS = {
    # 活动表
    "分享会活动": [
        "活动日期", "活动时间", "分享者", "活动主题", "活动教室", "线上视频号",
        "组织者姓名", "组织者邮箱", "活动状态", "结项时间", "准时结项", "结项人",
        "活动类型", "所属兴趣组ID", "所属兴趣组", "组织者学号", "预期人数",
    ],
    # 报名表
    "分享会报名": [
        "姓名", "关联活动", "角色", "联系电话", "邮箱", "学号",
        "评议语雀链接", "评议提交时间", "上次评议提醒时间", "评议内容",
    ],
    # 评议评分表
    "评议评分": [
        "评议报名ID", "活动ID", "评议者姓名", "评分人姓名", "评分", "权重", "评分备注",
    ],
    # 输出活动记录表
    "输出活动记录": [
        "姓名", "输出类型", "输出日期", "备注",
    ],
    # 用户档案表
    "用户档案": [
        "姓名", "邮箱", "角色", "首次使用时间",
    ],
    # 兴趣组表
    "兴趣组": [
        "组名", "组长", "主题目标", "时间边界", "执行方案", "简介", "状态", "创建时间",
    ],
    # 兴趣组成员表
    "兴趣组成员": [
        "兴趣组ID", "兴趣组名", "成员姓名", "成员邮箱", "成员身份", "加入时间",
    ],
    # 评议邀请表
    "评议邀请": [
        "活动ID", "活动主题", "邀请人", "被邀请人", "被邀请邮箱",
        "邀请来源", "状态", "邀请时间", "状态更新时间", "状态更新人",
    ],
    # CAC管理员表
    "CAC管理员": [
        "姓名", "添加时间",
    ],
    # CAC教室时间槽表
    "CAC教室时间槽": [
        "教室", "日期", "时间段", "状态", "关联活动ID", "创建者", "创建时间",
    ],
}

# ===== 报名限额配置 =====
REVIEWER_LIMIT = int(os.getenv("REVIEWER_LIMIT", "3"))
LISTENER_UNLIMITED = os.getenv("LISTENER_UNLIMITED", "true").lower() == "true"

# ===== 时间槽配置 =====
# 半小时一档，从09:00到22:00
TIME_SLOTS = [x.strip() for x in os.getenv("TIME_SLOTS", "09:00,09:30,10:00,10:30,11:00,11:30,12:00,12:30,13:00,13:30,14:00,14:30,15:00,15:30,16:00,16:30,17:00,17:30,18:00,18:30,19:00,19:30,20:00,20:30,21:00,21:30,22:00").split(",") if x.strip()]

# ===== CAC有约冲突检测配置 =====
# CAC有约固定在哪一天（0=周一, 1=周二, ..., 4=周五, 6=周日），默认周五
CAC_FIXED_WEEKDAY = int(os.getenv("CAC_FIXED_WEEKDAY", "4"))
# CAC有约固定时间段（格式 HH:MM-HH:MM）
CAC_FIXED_TIME = os.getenv("CAC_FIXED_TIME", "18:00-19:00")

# ===== 邮件提醒配置 =====
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "").strip()
BOUNDARY_REPORT_EMAIL = os.getenv("BOUNDARY_REPORT_EMAIL", "nova@nju.edu.cn").strip()
BOUNDARY_LOOKBACK_DAYS = int(os.getenv("BOUNDARY_LOOKBACK_DAYS", "14"))
BOUNDARY_FIRST_REPORT_AT = os.getenv("BOUNDARY_FIRST_REPORT_AT", "2026-03-22 22:00:00").strip()
BOUNDARY_WEEKLY_REPORT_WEEKDAY = int(os.getenv("BOUNDARY_WEEKLY_REPORT_WEEKDAY", "6"))
BOUNDARY_WEEKLY_REPORT_HOUR = int(os.getenv("BOUNDARY_WEEKLY_REPORT_HOUR", "22"))
BOUNDARY_WEEKLY_REPORT_MINUTE = int(os.getenv("BOUNDARY_WEEKLY_REPORT_MINUTE", "0"))
ACTIVITY_CLOSE_GRACE_MINUTES = int(os.getenv("ACTIVITY_CLOSE_GRACE_MINUTES", "120"))
REVIEW_REMINDER_INTERVAL_HOURS = int(os.getenv("REVIEW_REMINDER_INTERVAL_HOURS", "24"))
BACKGROUND_SCAN_INTERVAL_SECONDS = int(os.getenv("BACKGROUND_SCAN_INTERVAL_SECONDS", "3600"))
ROSTER_FILE_PATH = os.getenv("ROSTER_FILE_PATH", os.path.join(os.path.dirname(__file__), "member_roster.local.txt"))
# Use platform-specific temp directory
_temp_dir = tempfile.gettempdir()
TASK_LOCK_FILE = os.getenv("TASK_LOCK_FILE", os.path.join(_temp_dir, "table_signup_background.lock"))
BOUNDARY_REPORT_STATE_FILE = os.getenv("BOUNDARY_REPORT_STATE_FILE", os.path.join(_temp_dir, "table_signup_boundary_report.state"))
CAC_NAME = os.getenv("CAC_NAME", "cac").strip()
CAC_EMAIL = os.getenv("CAC_EMAIL", "nova@nju.edu.cn").strip()
PROFILE_EXPLORE_DEFAULT_PAGE_SIZE = int(os.getenv("PROFILE_EXPLORE_DEFAULT_PAGE_SIZE", "10"))
PROFILE_EXPLORE_MAX_PAGE_SIZE = int(os.getenv("PROFILE_EXPLORE_MAX_PAGE_SIZE", "100"))
PROFILE_CACHE_TTL_SECONDS = int(os.getenv("PROFILE_CACHE_TTL_SECONDS", "120"))
PROFILE_FEED_DEFAULT_LIMIT = int(os.getenv("PROFILE_FEED_DEFAULT_LIMIT", "30"))

class MySQLBase:
    def __init__(self):
        if pymysql is None:
            raise RuntimeError("缺少 pymysql 依赖。请执行: pip install pymysql")
        if not MYSQL_DATABASE:
            raise RuntimeError("MYSQL_DATABASE 不能为空")
        self._local = threading.local()
        self._bootstrap()

    def _connect(self, database=None):
        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=MYSQL_CONNECT_TIMEOUT,
            read_timeout=MYSQL_READ_TIMEOUT,
            write_timeout=MYSQL_WRITE_TIMEOUT,
        )

    def _get_conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None or not getattr(conn, "open", False):
            conn = self._connect(MYSQL_DATABASE)
            self._local.conn = conn
        else:
            conn.ping(reconnect=True)
        return conn

    def _bootstrap(self):
        server_conn = self._connect(None)
        try:
            with server_conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        finally:
            server_conn.close()

        conn = self._connect(MYSQL_DATABASE)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_rows (
                        table_name VARCHAR(191) NOT NULL,
                        row_id VARCHAR(64) NOT NULL,
                        row_data JSON NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (table_name, row_id),
                        KEY idx_table_updated (table_name, updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_table_columns (
                        table_name VARCHAR(191) NOT NULL,
                        column_name VARCHAR(191) NOT NULL,
                        PRIMARY KEY (table_name, column_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
        finally:
            conn.close()

    def list_rows(self, table_name):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT row_id, row_data FROM app_rows WHERE table_name=%s ORDER BY created_at ASC",
                (table_name,),
            )
            rows = cursor.fetchall() or []
        result = []
        for row in rows:
            payload = row.get("row_data")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            payload["_id"] = row.get("row_id")
            result.append(payload)
        return result

    def _sync_columns(self, table_name, columns):
        clean_columns = [str(item).strip() for item in (columns or []) if str(item).strip()]
        if not clean_columns:
            return
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT IGNORE INTO app_table_columns (table_name, column_name) VALUES (%s, %s)",
                [(table_name, column_name) for column_name in clean_columns],
            )

    def append_row(self, table_name, row_data):
        row_id = uuid.uuid4().hex
        payload = dict(row_data or {})
        payload.pop("_id", None)
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO app_rows (table_name, row_id, row_data) VALUES (%s, %s, %s)",
                (table_name, row_id, json.dumps(payload, ensure_ascii=False)),
            )
        self._sync_columns(table_name, payload.keys())
        return {"_id": row_id, **payload}

    def update_row(self, table_name, row_id, row_data):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT row_data FROM app_rows WHERE table_name=%s AND row_id=%s LIMIT 1",
                (table_name, row_id),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"记录不存在: {table_name}/{row_id}")
            payload = row.get("row_data")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            payload.update(dict(row_data or {}))
            payload.pop("_id", None)
            cursor.execute(
                "UPDATE app_rows SET row_data=%s WHERE table_name=%s AND row_id=%s",
                (json.dumps(payload, ensure_ascii=False), table_name, row_id),
            )
        self._sync_columns(table_name, payload.keys())
        return {"_id": row_id, **payload}

    def delete_row(self, table_name, row_id):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM app_rows WHERE table_name=%s AND row_id=%s",
                (table_name, row_id),
            )

    def list_columns(self, table_name):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM app_table_columns WHERE table_name=%s ORDER BY column_name ASC",
                (table_name,),
            )
            rows = cursor.fetchall() or []
        return [{"name": row.get("column_name")} for row in rows if row.get("column_name")]

    def add_table(self, table_name, *args):
        return {"name": table_name, "ok": True}

    def insert_column(self, table_name, column_name, *args):
        self._sync_columns(table_name, [column_name])
        return {"table": table_name, "column": column_name, "ok": True}


if DB_BACKEND == "mysql":
    base = MySQLBase()
else:
    if Base is None:
        raise RuntimeError("未安装 seatable-api，无法使用 seatable 后端")
    if not API_TOKEN:
        raise RuntimeError("SEATABLE_API_TOKEN is required when DB_BACKEND=seatable")
    base = Base(API_TOKEN, SERVER_URL)
    try:
        base.auth()
    except Exception as exc:
        raise RuntimeError(
            "SeaTable 认证失败。请确认使用的是 Base 的 API Token（不是账号令牌），"
            "并且该 Token 对目标表有读写权限。"
        ) from exc

# 自动注册列到 app_table_columns
def _auto_register_columns():
    """启动时自动同步列定义到数据库"""
    if hasattr(base, '_sync_columns'):
        for table_name, columns in AUTO_REGISTER_COLUMNS.items():
            try:
                base._sync_columns(table_name, columns)
            except Exception as e:
                print(f"[WARN] Auto register columns for {table_name} failed: {e}")
        print("[INFO] Auto register columns completed")

_auto_register_columns()

app = Flask(__name__)

# ===== 注册路由蓝图 =====
app.register_blueprint(activity_bp)
app.register_blueprint(signup_bp)
app.register_blueprint(cac_bp)
app.register_blueprint(group_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(invite_bp)
app.register_blueprint(stats_bp)

# ===== 全局异常处理器 =====
@app.errorhandler(AppError)
def handle_app_error(error):
    """统一处理自定义异常"""
    return jsonify({"ok": False, "message": error.message, "code": error.code}), error.status_code

@app.errorhandler(404)
def handle_404(error):
    return jsonify({"ok": False, "message": "资源不存在", "code": "NOT_FOUND"}), 404

@app.errorhandler(500)
def handle_500(error):
    return jsonify({"ok": False, "message": "服务器内部错误", "code": "INTERNAL_ERROR"}), 500

# Protect check+insert in single-process deployment to reduce race conditions.
submit_lock = threading.Lock()
cache_lock = threading.Lock()
read_cache = {}
data_version = 0


def _get_data_version():
    with cache_lock:
        return data_version


def _touch_data_version():
    global data_version
    with cache_lock:
        data_version += 1


def _build_cache_key(namespace, *parts):
    normalized_parts = [namespace, str(_get_data_version())]
    normalized_parts.extend(str(part) for part in parts)
    return "::".join(normalized_parts)


def _cached_build(namespace, ttl_seconds, build_fn, *parts):
    now_ts = time.time()
    cache_key = _build_cache_key(namespace, *parts)
    with cache_lock:
        cached = read_cache.get(cache_key)
        if cached and cached.get('expires_at', 0) > now_ts:
            return cached.get('value')
    value = build_fn()
    with cache_lock:
        read_cache[cache_key] = {
            'value': value,
            'expires_at': now_ts + max(1, ttl_seconds),
        }
    return value


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


def _safe_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes", "y", "是"}


def _safe_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def _should_track_member_name(name):
    text = _safe_text(name)
    if not text:
        return False
    if re.fullmatch(r"[A-Za-z]{1,4}\d{4,}", text):
        return False
    return True


def _is_cac_user(name):
    text = _safe_text(name).lower()
    return text == _safe_text(CAC_NAME).lower() or text == "cac"


def _list_rows(table_name):
    def load_rows():
        try:
            rows = base.list_rows(table_name)
            return rows or []
        except Exception as exc:
            print(f"Error listing rows from {table_name}: {exc}")
            return []

    return _cached_build(
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
    for activity in _list_activities():
        names.update(_split_names(activity.get(ACTIVITY_COL_SPEAKERS, "")))
        creator_name = _get_activity_creator_name(activity)
        if _should_track_member_name(creator_name):
            names.add(creator_name)
    for signup in _list_signups():
        signup_name = _get_signup_name(signup)
        if _should_track_member_name(signup_name):
            names.add(signup_name)
    for record in _list_output_records():
        name = _safe_text(record.get(OUTPUT_RECORD_COL_NAME, ""))
        if _should_track_member_name(name):
            names.add(name)
    for rating in _list_review_ratings():
        reviewer_name = _safe_text(rating.get(REVIEW_RATING_COL_REVIEWER_NAME, ""))
        rater_name = _safe_text(rating.get(REVIEW_RATING_COL_RATER_NAME, ""))
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


def _get_activity_closed_at(activity):
    return _parse_datetime(activity.get(ACTIVITY_COL_CLOSED_AT, ""))


def _activity_is_closed(activity):
    return _safe_bool(activity.get(ACTIVITY_COL_ON_TIME)) or str(activity.get(ACTIVITY_COL_STATUS, "")).strip() == "已结项" or bool(_get_activity_closed_at(activity))


def _compute_activity_on_time(activity, closed_at=None):
    closed_at = closed_at or _get_activity_closed_at(activity)
    end_at = _get_activity_end_datetime(activity)
    if not closed_at or not end_at:
        return None
    return closed_at <= end_at + timedelta(minutes=ACTIVITY_CLOSE_GRACE_MINUTES)


def _get_activity_state(activity):
    if not activity:
        return "未开始"
    if _activity_is_closed(activity):
        return "已结项"
    end_at = _get_activity_end_datetime(activity)
    if end_at and _now() > end_at:
        return "待结项"
    return "进行中"


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
        print(f"Error listing columns for {table_name}: {exc}")
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
            result["errors"].append(f"创建表失败: {action_or_error}")
            return result
        result["table_action"] = action_or_error
        existing_columns = _get_table_columns(table_name)

    if not existing_columns:
        result["errors"].append("无法读取列信息，请确认 token 对该表有权限")
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
            result["errors"].append(f"补列失败 {column_name}: {action_or_error}")
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
        raise RuntimeError(f"{table_name} 缺少可写入字段，请先检查数据表结构配置")
    return base.append_row(table_name, filtered)


def _update_row(table_name, row_id, row_data):
    filtered = _filter_update_row_data(table_name, row_data)
    if not filtered:
        raise RuntimeError(f"{table_name} 缺少可更新字段，请先检查数据表结构配置")
    return base.update_row(table_name, row_id, filtered)


def _get_activity_creator_name(activity):
    value = _get_first_nonempty(
        activity,
        ACTIVITY_COL_CREATOR_NAME,
        LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID,
    )
    return _safe_text(value)


def _get_activity_creator_email(activity):
    value = _get_first_nonempty(activity, ACTIVITY_COL_CREATOR_EMAIL)
    return _safe_text(value)


def _get_signup_email(signup):
    value = _get_first_nonempty(signup, SIGNUP_COL_EMAIL)
    return _safe_text(value)


def _get_signup_name(signup):
    value = _get_first_nonempty(signup, SIGNUP_COL_NAME, LEGACY_SIGNUP_COL_STUDENT_ID)
    return _safe_text(value)


def _mail_configured():
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USERNAME and SMTP_PASSWORD and EMAIL_FROM)


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
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
    return True


def _send_email_async(recipient, subject, body):
    if not recipient or not _mail_configured():
        return

    def worker():
        try:
            _send_email(recipient, subject, body)
        except Exception as exc:
            print(f"Send email failed to {recipient}: {exc}")

    threading.Thread(target=worker, daemon=True).start()


def _notify_signup_change(activity, signup_name, role, recipient_email, action):
    if not recipient_email:
        return
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or '未命名活动'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or '日期待定'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or '时间待定'
    subject = f"[CAC 分享会] {action}提醒"
    body = (
        f"{signup_name}，您好：\n\n"
        f"您对活动《{topic}》的{role}{action}已处理完成。\n"
        f"活动时间：{date} {time}\n\n"
        "如有变更，请以系统页面最新信息为准。"
    )
    _send_email_async(recipient_email, subject, body)


def _notify_organizer_signup(activity, signup_name, role, review_content=''):
    organizer_email = _get_activity_creator_email(activity)
    if not organizer_email:
        return
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or '未命名活动'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or '日期待定'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or '时间待定'
    subject = f"[CAC 分享会] 有新的{role}报名"
    body = (
        f"您好，您创建的活动《{topic}》有新的报名。\n\n"
        f"报名人：{signup_name}\n"
        f"角色：{role}\n"
        f"活动时间：{date} {time}\n"
    )
    if review_content:
        body += f"评议内容：{review_content}\n"
    _send_email_async(organizer_email, subject, body)


def _notify_activity_change(activity_email, creator_name, topic, action, extra_lines=None):
    if not activity_email:
        return
    extra_text = "\n".join(extra_lines or [])
    if extra_text:
        extra_text = f"\n{extra_text}"
    subject = f"[CAC 分享会] 活动{action}提醒"
    body = (
        f"{creator_name}，您好：\n\n"
        f"您发起的活动《{topic or '未命名活动'}》已{action}。"
        f"{extra_text}\n\n"
        "如需继续调整，请返回管理页面操作。"
    )
    _send_email_async(activity_email, subject, body)


def _notify_review_doc_reminder(signup, activity):
    recipient_email = _get_signup_email(signup)
    if not recipient_email:
        return
    signup_name = _get_signup_name(signup)
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or '未命名活动'
    subject = f"[CAC 分享会] 请提交评议文档：《{topic}》"
    body = (
        f"{signup_name}，您好：\n\n"
        f"活动《{topic}》已结项，请尽快上传评议语雀链接。\n"
        "如果已经上传，请忽略此提醒；否则系统会继续每日提醒。"
    )
    _send_email_async(recipient_email, subject, body)


def _notify_boundary_report(non_compliant_names, stats):
    if not _mail_configured() or not non_compliant_names:
        return
    summary_recipient = BOUNDARY_REPORT_EMAIL or CAC_EMAIL
    subject = f"[CAC 分享会] 两周输出活动边界预警（{len(non_compliant_names)}人）"
    body = (
        f"以下成员在最近 {BOUNDARY_LOOKBACK_DAYS} 天内未达到至少一次输出型活动的底线要求：\n\n"
        + "\n".join(non_compliant_names)
        + f"\n\n当前统计覆盖成员总数：{stats.get('tracked_member_count', 0)}"
    )
    if summary_recipient:
        _send_email_async(summary_recipient, subject, body)

    member_email_map = _build_member_email_map()
    for member_name in non_compliant_names:
        recipient_email = member_email_map.get(member_name)
        if not recipient_email:
            continue
        member_body = (
            f"{member_name}，您好：\n\n"
            f"您在最近 {BOUNDARY_LOOKBACK_DAYS} 天内尚未满足“至少参与一次输出型活动（分享/评议/CAC有约）”的底线要求。\n"
            "请尽快安排并完成一次输出活动，避免触发进一步边界处理。"
        )
        _send_email_async(recipient_email, "[CAC 分享会] 个人边界提醒", member_body)


def _build_member_email_map():
    result = {}
    for signup in _list_signups():
        name = _get_signup_name(signup)
        email = _get_signup_email(signup)
        if _should_track_member_name(name) and email:
            result[name] = email
    for activity in _list_activities():
        name = _get_activity_creator_name(activity)
        email = _get_activity_creator_email(activity)
        if _should_track_member_name(name) and email:
            result[name] = email
    if CAC_EMAIL:
        result[_safe_text(CAC_NAME)] = CAC_EMAIL
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


def _list_review_ratings():
    return _list_rows(REVIEW_RATING_TABLE_NAME)


def _list_output_records():
    return _list_rows(OUTPUT_RECORD_TABLE_NAME)


def _list_user_profiles():
    return _list_rows(USER_PROFILE_TABLE_NAME)


def _list_interest_groups():
    return _list_rows(INTEREST_GROUP_TABLE_NAME)


def _list_group_members():
    return _list_rows(GROUP_MEMBER_TABLE_NAME)


def _list_review_invites():
    return _list_rows(REVIEW_INVITE_TABLE_NAME)


def _get_user_profile(name):
    target = _safe_text(name)
    if not target:
        return None
    for profile in _list_user_profiles():
        if _safe_text(profile.get(USER_COL_NAME, '')) == target:
            return profile
    return None


def _upsert_user_profile(name, email=None, role=None):
    name = _safe_text(name)
    if not name:
        return None
    existing = _get_user_profile(name)
    if existing:
        update_data = {}
        current_email = _safe_text(existing.get(USER_COL_EMAIL, ''))
        current_role = _safe_text(existing.get(USER_COL_ROLE, ''))
        if email and email != current_email:
            update_data[USER_COL_EMAIL] = email
        if role and role != current_role:
            update_data[USER_COL_ROLE] = role
        if update_data:
            try:
                _update_row(USER_PROFILE_TABLE_NAME, existing.get('_id'), update_data)
            except Exception as exc:
                print(f"Update user profile failed: {exc}")
        return _get_user_profile(name) or existing

    row_data = {
        USER_COL_NAME: name,
        USER_COL_EMAIL: _safe_text(email),
        USER_COL_ROLE: _safe_text(role) or '普通用户',
        USER_COL_FIRST_SEEN_AT: _now_iso(),
    }
    try:
        _append_row(USER_PROFILE_TABLE_NAME, row_data)
    except Exception as exc:
        print(f"Create user profile failed: {exc}")
    return _get_user_profile(name)


def _get_user_email(name):
    profile = _get_user_profile(name)
    if profile:
        return _safe_text(profile.get(USER_COL_EMAIL, ''))
    return ''


def _get_interest_group_by_id(group_id):
    for group in _list_interest_groups():
        if str(group.get('_id')) == str(group_id):
            return group
    return None


def _serialize_interest_group(group):
    if not group:
        return None
    group_id = str(group.get('_id'))
    members = [m for m in _list_group_members() if str(m.get(GROUP_MEMBER_COL_GROUP_ID, '')) == group_id]
    leader_name = _safe_text(group.get(GROUP_COL_LEADER_NAME, ''))
    return {
        'id': group_id,
        'name': _safe_text(group.get(GROUP_COL_NAME, '')),
        'leader_name': leader_name,
        'topic_goal': _safe_text(group.get(GROUP_COL_TOPIC_GOAL, '')),
        'time_boundary': _safe_text(group.get(GROUP_COL_TIME_BOUNDARY, '')),
        'execution_plan': _safe_text(group.get(GROUP_COL_EXECUTION_PLAN, '')),
        'description': _safe_text(group.get(GROUP_COL_DESCRIPTION, '')),
        'status': _safe_text(group.get(GROUP_COL_STATUS, '')) or '活跃',
        'created_at': _safe_text(group.get(GROUP_COL_CREATED_AT, '')),
        'member_count': len(members),
        'members': [
            {
                'id': str(member.get('_id')),
                'name': _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, '')),
                'email': _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_EMAIL, '')),
                'role': _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_ROLE, '')),
                'joined_at': _safe_text(member.get(GROUP_MEMBER_COL_JOINED_AT, '')),
            }
            for member in members
        ],
    }


def _get_memberships_by_name(name):
    target = _safe_text(name)
    if not target:
        return []
    return [
        member for member in _list_group_members()
        if _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == target
    ]


def _get_group_ids_for_member(name):
    return [str(member.get(GROUP_MEMBER_COL_GROUP_ID, '')) for member in _get_memberships_by_name(name)]


def _notify_group_membership_change(group, member_name, member_email, action):
    group_name = _safe_text(group.get(GROUP_COL_NAME, ''))
    leader_name = _safe_text(group.get(GROUP_COL_LEADER_NAME, ''))
    leader_email = _get_user_email(leader_name)
    subject = f"[CAC 兴趣组] 成员{action}通知"
    body = f"兴趣组《{group_name}》成员变更：{member_name}{action}。"

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
    subject = "[CAC有约] 新活动发起通知"
    body = (
        f"普通成员 {creator_name} 发起了 CAC有约 活动。\n"
        f"主题：{topic}\n"
        "请确认是否有其他安排。系统将默认 CAC 自动参与。"
    )
    _send_email_async(recipient, subject, body)


def _serialize_review_invite(invite):
    return {
        'id': str(invite.get('_id')),
        'activity_id': _safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')),
        'activity_topic': _safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')),
        'inviter_name': _safe_text(invite.get(INVITE_COL_INVITER_NAME, '')),
        'invitee_name': _safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')),
        'invitee_email': _safe_text(invite.get(INVITE_COL_INVITEE_EMAIL, '')),
        'source_type': _safe_text(invite.get(INVITE_COL_SOURCE_TYPE, '')),
        'status': _safe_text(invite.get(INVITE_COL_STATUS, '')),
        'created_at': _safe_text(invite.get(INVITE_COL_CREATED_AT, '')),
        'updated_at': _safe_text(invite.get(INVITE_COL_UPDATED_AT, '')),
        'updated_by': _safe_text(invite.get(INVITE_COL_UPDATED_BY, '')),
    }


def _get_review_invite_by_id(invite_id):
    for invite in _list_review_invites():
        if str(invite.get('_id')) == str(invite_id):
            return invite
    return None


def _list_pending_invites_for_user(activity_id, invitee_name):
    result = []
    target_activity_id = str(activity_id).strip()
    target_name = _safe_text(invitee_name)
    for invite in _list_review_invites():
        if _safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')) != target_activity_id:
            continue
        if _safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target_name:
            continue
        if _safe_text(invite.get(INVITE_COL_STATUS, '')) != '已发送':
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
            print(f"Update invite status failed: {exc}")
    return accepted_count


def _is_invite_transition_allowed(old_status, new_status, is_cac_operator=False):
    old_status = _safe_text(old_status)
    new_status = _safe_text(new_status)
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


def _get_signup_review_doc_url(signup):
    return _safe_text(signup.get(SIGNUP_COL_REVIEW_DOC_URL, ''))


def _get_signup_review_submitted_at(signup):
    return _parse_datetime(signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''))


def _get_signup_last_review_reminder_at(signup):
    return _parse_datetime(signup.get(SIGNUP_COL_LAST_REVIEW_REMINDER_AT, ''))


def _get_signups_grouped_by_activity():
    def build_groups():
        grouped = defaultdict(list)
        for signup in _list_signups():
            activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
            if not activity_id:
                continue
            grouped[activity_id].append(signup)
        return dict(grouped)

    return _cached_build('signups_grouped_activity', PROFILE_CACHE_TTL_SECONDS, build_groups)


def _get_activity_signups(activity_id, role=None):
    matches = list(_get_signups_grouped_by_activity().get(str(activity_id), []))
    if not role:
        return matches
    return [signup for signup in matches if str(signup.get(SIGNUP_COL_ROLE, '')).strip() == role]


def _get_signup_role(signup):
    return str(signup.get(SIGNUP_COL_ROLE, '')).strip()


def _serialize_rating(rating):
    return {
        'id': rating.get('_id'),
        'signup_id': str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip(),
        'activity_id': str(rating.get(REVIEW_RATING_COL_ACTIVITY_ID, '')).strip(),
        'reviewer_name': str(rating.get(REVIEW_RATING_COL_REVIEWER_NAME, '')).strip(),
        'rater_name': str(rating.get(REVIEW_RATING_COL_RATER_NAME, '')).strip(),
        'score': float(rating.get(REVIEW_RATING_COL_SCORE, 0) or 0),
        'weight': float(rating.get(REVIEW_RATING_COL_WEIGHT, 0) or 0),
        'comment': str(rating.get(REVIEW_RATING_COL_COMMENT, '')).strip(),
    }


def _build_review_quality_stats():
    def build_stats():
        per_signup = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'ratings': []})
        per_reviewer = defaultdict(lambda: {'weighted_score': 0.0, 'total_weight': 0.0, 'rating_count': 0, 'review_count': 0})

        for rating in _list_review_ratings():
            item = _serialize_rating(rating)
            signup_id = item['signup_id']
            if not signup_id:
                continue
            per_signup[signup_id]['weighted_score'] += item['score'] * item['weight']
            per_signup[signup_id]['total_weight'] += item['weight']
            per_signup[signup_id]['rating_count'] += 1
            per_signup[signup_id]['ratings'].append(item)

        for signup in _list_signups():
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

    return _cached_build('review_quality_stats', PROFILE_CACHE_TTL_SECONDS, build_stats)


def _serialize_review_task(signup):
    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = _get_activity_by_id(activity_id)
    activity_details = _get_activity_details(activity) if activity else {}
    per_signup_stats, _ = _build_review_quality_stats()
    signup_stats = per_signup_stats.get(str(signup.get('_id')), {})
    average_score = 0
    if signup_stats.get('total_weight', 0) > 0:
        average_score = round(signup_stats['weighted_score'] / signup_stats['total_weight'], 2)
    return {
        **_serialize_signup(signup),
        'review_doc_url': _get_signup_review_doc_url(signup),
        'review_submitted_at': signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''),
        'average_score': average_score,
        'rating_count': signup_stats.get('rating_count', 0),
        'activity_state': _get_activity_state(activity),
        'activity': activity_details,
    }


def _get_activity_review_documents(activity_id, include_pending=False):
    per_signup_stats, _ = _build_review_quality_stats()
    documents = []
    for signup in _get_activity_signups(activity_id, role='评议员'):
        review_doc_url = _get_signup_review_doc_url(signup)
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
    for activity in _list_activities():
        for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
            if _is_cac_user(speaker):
                continue
            counter[speaker] += 1
    ranking = [{'name': name, 'count': count} for name, count in counter.most_common()]
    return ranking


def _build_participation_leaderboard():
    counter = Counter()
    for signup in _list_signups():
        if _get_signup_role(signup) in {'评议员', '旁听'}:
            signup_name = _get_signup_name(signup)
            if _is_cac_user(signup_name):
                continue
            counter[signup_name] += 1
    ranking = [{'name': name, 'count': count} for name, count in counter.most_common()]
    return ranking


def _build_punctuality_leaderboard():
    stats = defaultdict(lambda: {'on_time': 0, 'closed': 0})
    for activity in _list_activities():
        if not _activity_is_closed(activity):
            continue
        creator_name = _get_activity_creator_name(activity)
        if not creator_name:
            continue
        if _is_cac_user(creator_name):
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

    for activity in _list_activities():
        if _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
            for speaker in _split_names(activity.get(ACTIVITY_COL_SPEAKERS, '')):
                output_counter[speaker] += 1

    for signup in _list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        activity = _get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
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
    known_members = {name for name in known_members if not _is_cac_user(name)}
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
    for activity in _list_activities():
        activity_date = _parse_date(activity.get(ACTIVITY_COL_DATE, ''))
        if not activity_date or activity_date.year != year or activity_date.month != month:
            continue
        monthly_activities.append(activity)

    monthly_activity_ids = {str(activity.get('_id')) for activity in monthly_activities}
    monthly_signups = [signup for signup in _list_signups() if str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip() in monthly_activity_ids]
    monthly_outputs = []
    for record in _list_output_records():
        output_date = _parse_date(record.get(OUTPUT_RECORD_COL_DATE, ''))
        if output_date and output_date.year == year and output_date.month == month:
            monthly_outputs.append(record)

    closed_activities = [activity for activity in monthly_activities if _activity_is_closed(activity)]
    on_time_closed = [activity for activity in closed_activities if _compute_activity_on_time(activity)]
    type_counter = Counter((_safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal') for activity in monthly_activities)
    creator_names = {name for name in (_get_activity_creator_name(activity) for activity in monthly_activities) if name}
    participant_names = {name for name in (_get_signup_name(signup) for signup in monthly_signups) if name}

    return {
        'year_month': f"{year:04d}-{month:02d}",
        'activity_count': len(monthly_activities),
        'signup_count': len(monthly_signups),
        'output_record_count': len(monthly_outputs),
        'active_creator_count': len(creator_names),
        'active_participant_count': len(participant_names),
        'closed_count': len(closed_activities),
        'pending_close_count': len([activity for activity in monthly_activities if _get_activity_state(activity) == '待结项']),
        'on_time_close_rate': round((len(on_time_closed) / len(closed_activities)), 4) if closed_activities else 0,
        'activity_type_breakdown': {
            'normal': int(type_counter.get('normal', 0)),
            'cac有约': int(type_counter.get('cac有约', 0)),
        },
    }


def _build_group_health_report(lookback_days=30):
    recent_output_counts = _build_output_counts(lookback_days=lookback_days)
    report = []
    for group in _list_interest_groups():
        group_id = str(group.get('_id'))
        group_name = _safe_text(group.get(GROUP_COL_NAME, ''))
        members = [member for member in _list_group_members() if str(member.get(GROUP_MEMBER_COL_GROUP_ID, '')) == group_id]
        member_names = {_safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) for member in members if _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_NAME, ''))}
        related_activities = []
        for activity in _list_activities():
            if _safe_text(activity.get(ACTIVITY_COL_GROUP_ID, '')) != group_id:
                continue
            if not _within_lookback(activity.get(ACTIVITY_COL_DATE, ''), lookback_days=lookback_days):
                continue
            related_activities.append(activity)

        recent_activity_count = len(related_activities)
        pending_close_count = len([activity for activity in related_activities if _get_activity_state(activity) == '待结项'])
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
            'leader_name': _safe_text(group.get(GROUP_COL_LEADER_NAME, '')),
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
    for signup in _list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        if _get_signup_review_doc_url(signup):
            continue
        activity = _get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if activity and _activity_is_closed(activity):
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
    """检测未结项活动中同日同时段的时间冲突（含 CAC有约 周五 18 点档）"""
    slot_map = defaultdict(list)
    for activity in _list_activities():
        if _activity_is_closed(activity):
            continue
        parsed = _parse_date(activity.get(ACTIVITY_COL_DATE, ''))
        if not parsed:
            continue
        date_str = parsed.strftime('%Y-%m-%d')
        time_slot = _safe_text(activity.get(ACTIVITY_COL_TIME, ''))
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
                    'topic': _safe_text(a.get(ACTIVITY_COL_TOPIC, '')),
                    'speakers': _safe_text(a.get(ACTIVITY_COL_SPEAKERS, '')),
                    'type': _safe_text(a.get(ACTIVITY_COL_TYPE, '')),
                    'status': _get_activity_state(a),
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
    target = _safe_text(name)
    if not target:
        return None
    for index, item in enumerate(items or [], start=1):
        if _safe_text(item.get('name', '')) == target:
            return index
    return None


def _build_person_profile_summary(name):
    target = _safe_text(name)
    if not target:
        return None

    share_ranking = _build_share_leaderboard()
    participation_ranking = _build_participation_leaderboard()
    punctuality_ranking = _build_punctuality_leaderboard()
    _, review_quality_ranking = _build_review_quality_stats()
    boundary_stats = _build_boundary_stats()

    share_count = next((item.get('count', 0) for item in share_ranking if _safe_text(item.get('name', '')) == target), 0)
    participation_count = next((item.get('count', 0) for item in participation_ranking if _safe_text(item.get('name', '')) == target), 0)
    review_quality_item = next((item for item in review_quality_ranking if _safe_text(item.get('name', '')) == target), None)
    punctuality_item = next((item for item in punctuality_ranking if _safe_text(item.get('name', '')) == target), None)

    my_groups = []
    for member in _get_memberships_by_name(target):
        group = _get_interest_group_by_id(member.get(GROUP_MEMBER_COL_GROUP_ID, ''))
        if group:
            my_groups.append({
                'id': str(group.get('_id')),
                'name': _safe_text(group.get(GROUP_COL_NAME, '')),
                'member_role': _safe_text(member.get(GROUP_MEMBER_COL_MEMBER_ROLE, '')),
            })

    my_signups = []
    for signup in _list_signups():
        if _get_signup_name(signup) == target:
            my_signups.append(_serialize_review_task(signup))
    my_signups.sort(key=lambda item: (item.get('activity', {}).get('date', ''), item.get('activity', {}).get('time', '')), reverse=True)

    my_invites = []
    for invite in _list_review_invites():
        if _safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) == target:
            my_invites.append(_serialize_review_invite(invite))
    my_invites.sort(key=lambda item: item.get('created_at', ''), reverse=True)

    output_count_recent = int(boundary_stats.get('output_counts', {}).get(target, 0))
    boundary_ok = output_count_recent >= 1 or _is_cac_user(target)

    return {
        'name': target,
        'is_cac': _is_cac_user(target),
        'profile': {
            'email': _get_user_email(target),
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
    target = _safe_text(name)
    if not target:
        return []

    events = []

    for signup in _list_signups():
        if _get_signup_name(signup) != target:
            continue
        activity = _get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        activity_details = _get_activity_details(activity) if activity else {}
        events.append({
            'type': 'signup',
            'ts': _safe_text(signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, '')) or _safe_text(activity_details.get('date', '')),
            'title': f"报名活动：{_safe_text(activity_details.get('topic', '未命名活动'))}",
            'detail': f"角色：{_safe_text(signup.get(SIGNUP_COL_ROLE, '')) or '-'}",
            'meta': {
                'activity_id': _safe_text(activity_details.get('id', '')),
                'activity_topic': _safe_text(activity_details.get('topic', '')),
                'activity_type': _safe_text(activity_details.get('activity_type', 'normal')),
                'group_name': _safe_text(activity_details.get('group_name', '')),
            },
        })

    for invite in _list_review_invites():
        if _safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target:
            continue
        events.append({
            'type': 'invite',
            'ts': _safe_text(invite.get(INVITE_COL_UPDATED_AT, '')) or _safe_text(invite.get(INVITE_COL_CREATED_AT, '')),
            'title': f"收到邀请：{_safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '未命名活动'))}",
            'detail': f"状态：{_safe_text(invite.get(INVITE_COL_STATUS, '已发送'))} · 来源：{_safe_text(invite.get(INVITE_COL_SOURCE_TYPE, '-'))}",
            'meta': {
                'invite_id': str(invite.get('_id')),
                'activity_id': _safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')),
                'activity_topic': _safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')),
                'invite_status': _safe_text(invite.get(INVITE_COL_STATUS, '已发送')),
            },
        })

    for activity in _list_activities():
        if _get_activity_creator_name(activity) != target:
            continue
        details = _get_activity_details(activity)
        events.append({
            'type': 'created_activity',
            'ts': _safe_text(details.get('date', '')),
            'title': f"创建活动：{_safe_text(details.get('topic', '未命名活动'))}",
            'detail': f"类型：{_safe_text(details.get('activity_type', 'normal'))} · 状态：{_safe_text(details.get('status', '-'))}",
            'meta': {
                'activity_id': _safe_text(details.get('id', '')),
                'group_name': _safe_text(details.get('group_name', '')),
                'activity_topic': _safe_text(details.get('topic', '')),
                'activity_type': _safe_text(details.get('activity_type', 'normal')),
                'state': _safe_text(details.get('status', '')),
            },
        })

    normalized_type_filter = _safe_text(type_filter)
    normalized_keyword = _safe_text(keyword).lower()
    if normalized_type_filter:
        events = [event for event in events if _safe_text(event.get('type', '')) == normalized_type_filter]
    if normalized_keyword:
        events = [
            event for event in events
            if normalized_keyword in _safe_text(event.get('title', '')).lower()
            or normalized_keyword in _safe_text(event.get('detail', '')).lower()
            or normalized_keyword in _safe_text((event.get('meta') or {}).get('activity_topic', '')).lower()
        ]

    events.sort(key=lambda item: (_safe_text(item.get('ts', '')), _safe_text(item.get('title', ''))), reverse=True)
    return events[:max(1, min(limit, 100))]


def _build_profile_tasks(name):
    target = _safe_text(name)
    if not target:
        return []

    tasks = []
    boundary_stats = _build_boundary_stats()
    output_count_recent = int(boundary_stats.get('output_counts', {}).get(target, 0))
    if not _is_cac_user(target) and output_count_recent < 1:
        tasks.append({
            'type': 'boundary_warning',
            'priority': 100,
            'title': '补一条近期输出，避免边界预警',
            'detail': f"最近 {BOUNDARY_LOOKBACK_DAYS} 天内还没有输出型活动记录。",
            'action': 'browse_activities',
            'action_label': '去找活动',
        })

    if not _get_user_email(target):
        tasks.append({
            'type': 'missing_email',
            'priority': 95,
            'title': '补全邮箱，打开提醒能力',
            'detail': '当前个人档案没有邮箱，邀请、报名和边界提醒都无法可靠送达。',
            'action': 'open_account',
            'action_label': '去设置邮箱',
        })

    if not _get_memberships_by_name(target) and not _is_cac_user(target):
        tasks.append({
            'type': 'join_group',
            'priority': 70,
            'title': '加入一个兴趣组',
            'detail': '加入兴趣组后，后续活动归属和推荐会更准确。',
            'action': 'open_groups',
            'action_label': '去看兴趣组',
        })

    for invite in _list_review_invites():
        if _safe_text(invite.get(INVITE_COL_INVITEE_NAME, '')) != target:
            continue
        if _safe_text(invite.get(INVITE_COL_STATUS, '已发送')) != '已发送':
            continue
        tasks.append({
            'type': 'pending_invite',
            'priority': 90,
            'title': f"待处理邀请：{_safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '未命名活动'))}",
            'detail': f"来源：{_safe_text(invite.get(INVITE_COL_SOURCE_TYPE, '-'))} · 邀请人：{_safe_text(invite.get(INVITE_COL_INVITER_NAME, '-'))}",
            'activity_id': _safe_text(invite.get(INVITE_COL_ACTIVITY_ID, '')),
            'activity_topic': _safe_text(invite.get(INVITE_COL_ACTIVITY_TOPIC, '')),
            'invite_id': str(invite.get('_id')),
            'action': 'respond_invite',
            'action_label': '处理邀请',
        })

    for signup in _list_signups():
        if _get_signup_name(signup) != target:
            continue
        if _get_signup_role(signup) != '评议员':
            continue
        if _get_signup_review_doc_url(signup):
            continue
        activity = _get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
        if not activity or not _activity_is_closed(activity):
            continue
        details = _get_activity_details(activity)
        tasks.append({
            'type': 'review_doc',
            'priority': 88,
            'title': f"待提交评议文档：{_safe_text(details.get('topic', '未命名活动'))}",
            'detail': '活动已结项，请尽快补评议语雀链接。',
            'signup_id': str(signup.get('_id')),
            'activity_id': _safe_text(details.get('id', '')),
            'activity_topic': _safe_text(details.get('topic', '')),
            'activity_type': _safe_text(details.get('activity_type', 'normal')),
            'state': _safe_text(details.get('status', '')),
            'action': 'jump_activity',
            'action_label': '查看活动',
        })

    for activity in _list_activities():
        if _get_activity_creator_name(activity) != target:
            continue
        if _get_activity_state(activity) != '待结项':
            continue
        details = _get_activity_details(activity)
        tasks.append({
            'type': 'close_activity',
            'priority': 85,
            'title': f"待结项活动：{_safe_text(details.get('topic', '未命名活动'))}",
            'detail': '活动时间已经过去，请尽快结项并触发后续评议流程。',
            'activity_id': _safe_text(details.get('id', '')),
            'activity_topic': _safe_text(details.get('topic', '')),
            'activity_type': _safe_text(details.get('activity_type', 'normal')),
            'state': _safe_text(details.get('status', '')),
            'action': 'jump_activity',
            'action_label': '去结项',
        })

    tasks.sort(key=lambda item: (-int(item.get('priority', 0)), _safe_text(item.get('title', ''))))
    return tasks[:12]


def _build_profile_recommendations(name, limit=6):
    target = _safe_text(name)
    if not target:
        return []

    joined_group_ids = set(_get_group_ids_for_member(target))
    signed_activity_ids = {
        str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
        for signup in _list_signups()
        if _get_signup_name(signup) == target
    }

    recommendations = []
    for activity in _list_activities():
        details = _get_activity_details(activity)
        activity_id = _safe_text(details.get('id', ''))
        if not activity_id or activity_id in signed_activity_ids:
            continue
        if _get_activity_creator_name(activity) == target:
            continue
        if _safe_text(details.get('status', '')) == '已结项':
            continue

        score = 0
        reasons = []
        group_id = _safe_text(details.get('group_id', ''))
        activity_type = _safe_text(details.get('activity_type', 'normal'))
        state = _safe_text(details.get('status', ''))
        reviewer_remaining = int(_get_signup_stats(activity_id).get('reviewer_remaining', 0) or 0)

        if group_id and group_id in joined_group_ids:
            score += 5
            reasons.append('来自你的兴趣组')
        if state == '进行中':
            score += 3
            reasons.append('正在开放参与')
        elif state == '待结项':
            score += 1
            reasons.append('活动刚结束，可补位旁听/参与记录')
        if activity_type == 'cac有约':
            score += 2
            reasons.append('适合直接参与交流')
        elif reviewer_remaining > 0:
            score += 2
            reasons.append(f'评议员还有 {reviewer_remaining} 个名额')
        else:
            score += 1
            reasons.append('可作为旁听补充近期参与')

        recommended_role = '参与者' if activity_type == 'cac有约' else ('评议员' if reviewer_remaining > 0 else '旁听')
        recommendations.append({
            'activity_id': activity_id,
            'topic': _safe_text(details.get('topic', '未命名活动')),
            'date': _safe_text(details.get('date', '')),
            'time': _safe_text(details.get('time', '')),
            'speakers': _safe_text(details.get('speakers', '')),
            'group_name': _safe_text(details.get('group_name', '')),
            'activity_type': activity_type,
            'state': state,
            'recommended_role': recommended_role,
            'score': score,
            'reasons': reasons[:3],
        })

    recommendations.sort(key=lambda item: (-int(item.get('score', 0)), _safe_text(item.get('date', '')), _safe_text(item.get('topic', ''))), reverse=False)
    return recommendations[:max(1, min(limit, 20))]


def _run_review_reminder_scan():
    with _task_lock():
        reminder_cutoff = _now() - timedelta(hours=REVIEW_REMINDER_INTERVAL_HOURS)
        for signup in _list_signups():
            if _get_signup_role(signup) != '评议员':
                continue
            if _get_signup_review_doc_url(signup):
                continue
            activity = _get_activity_by_id(str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip())
            if not activity or not _activity_is_closed(activity):
                continue
            if (_safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal') == 'cac有约':
                continue
            last_reminder = _get_signup_last_review_reminder_at(signup)
            if last_reminder and last_reminder > reminder_cutoff:
                continue
            _notify_review_doc_reminder(signup, activity)
            try:
                _update_row(SIGNUP_TABLE_NAME, signup.get('_id'), {
                    SIGNUP_COL_LAST_REVIEW_REMINDER_AT: _now_iso(),
                })
            except Exception as exc:
                print(f"Update review reminder timestamp failed: {exc}")


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
    while True:
        try:
            _run_review_reminder_scan()
            _run_boundary_report_scan()
        except Exception as exc:
            print(f"Background maintenance error: {exc}")
        time.sleep(max(300, BACKGROUND_SCAN_INTERVAL_SECONDS))


def _get_signup_by_id(signup_id):
    signups = _list_signups()
    for signup in signups:
        if str(signup.get('_id')) == str(signup_id):
            return signup
    return None


def _serialize_signup(signup):
    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = _get_activity_by_id(activity_id)
    details = _get_activity_details(activity) if activity else {}
    return {
        'id': signup.get('_id'),
        'name': _get_signup_name(signup),
        'activity_id': activity_id,
        'role': str(signup.get(SIGNUP_COL_ROLE, '')).strip(),
        'phone': str(signup.get(SIGNUP_COL_PHONE, '')).strip(),
        'email': _get_signup_email(signup),
        'review_content': str(signup.get(SIGNUP_COL_REVIEW_CONTENT, '')).strip(),
        'review_doc_url': _get_signup_review_doc_url(signup),
        'review_submitted_at': signup.get(SIGNUP_COL_REVIEW_SUBMITTED_AT, ''),
        'activity': details,
    }


# ===== 活动相关函数 =====
def _list_activities():
    """获取所有活动信息"""
    return _list_rows(ACTIVITY_TABLE_NAME)


def _get_activity_index():
    return _cached_build(
        'activity_index',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: {str(activity.get('_id')): activity for activity in _list_activities() if activity.get('_id')},
    )


def _get_activity_by_id(activity_id):
    """根据ID获取活动详情"""
    return _get_activity_index().get(str(activity_id))


def _get_activity_details(activity):
    """提取活动的关键信息"""
    if not activity:
        return None
    return {
        'id': activity.get('_id'),
        'date': activity.get(ACTIVITY_COL_DATE, ''),
        'time': activity.get(ACTIVITY_COL_TIME, ''),
        'speakers': activity.get(ACTIVITY_COL_SPEAKERS, ''),
        'topic': activity.get(ACTIVITY_COL_TOPIC, ''),
        'classroom': activity.get(ACTIVITY_COL_CLASSROOM, ''),
        'videourl': activity.get(ACTIVITY_COL_VIDEOURL, ''),
        'creator_name': _get_activity_creator_name(activity),
        'creator_email': _get_activity_creator_email(activity),
        'activity_type': _safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal',
        'group_id': _safe_text(activity.get(ACTIVITY_COL_GROUP_ID, '')),
        'group_name': _safe_text(activity.get(ACTIVITY_COL_GROUP_NAME, '')),
        'status': _get_activity_state(activity),
        'closed_at': activity.get(ACTIVITY_COL_CLOSED_AT, ''),
        'on_time': _compute_activity_on_time(activity),
        'closer_name': str(activity.get(ACTIVITY_COL_CLOSER_NAME, '')).strip(),
    }


# ===== 报名相关函数 =====
def _list_signups():
    """获取所有报名记录"""
    return _list_rows(SIGNUP_TABLE_NAME)


def _get_signup_counters_by_activity():
    def build_counters():
        counters = defaultdict(lambda: defaultdict(int))
        for signup in _list_signups():
            activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
            if not activity_id:
                continue
            role = str(signup.get(SIGNUP_COL_ROLE, '')).strip()
            counters[activity_id]['all'] += 1
            if role:
                counters[activity_id][role] += 1
        return {k: dict(v) for k, v in counters.items()}

    return _cached_build('signup_counters', PROFILE_CACHE_TTL_SECONDS, build_counters)


def _count_signups_by_activity(activity_id, role=None):
    """统计某个活动的报名人数"""
    counters = _get_signup_counters_by_activity().get(str(activity_id), {})
    if role is None:
        return int(counters.get('all', 0) or 0)
    return int(counters.get(role, 0) or 0)


def _calculate_expected_attendance(activity_id):
    """计算拟参加人数 = 分享者数 + 旁听者数 + 3名评议员"""
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return 0
    
    # 分享者数（按逗号分割）
    speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
    speakers_count = len([s.strip() for s in speakers_str.split(',') if s.strip()]) if speakers_str else 0
    
    # 旁听者数
    listener_count = _count_signups_by_activity(activity_id, '旁听')
    
    # 评议员固定3人
    reviewer_count = REVIEWER_LIMIT
    
    return speakers_count + listener_count + reviewer_count


def _get_signup_stats(activity_id):
    """获取某个活动的报名统计"""
    reviewer_count = _count_signups_by_activity(activity_id, '评议员')
    listener_count = _count_signups_by_activity(activity_id, '旁听')
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


# ===== 统计和预警函数 =====
def _parse_time_range(time_str):
    """解析时间区间字符串（如 '10:00-11:00'），返回 (start_minutes, end_minutes) 或 None"""
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
    """检查两个时间区间是否重叠（不含端点相接）"""
    if not range1 or not range2:
        return False
    return range1[0] < range2[1] and range2[0] < range1[1]


def _detect_time_conflicts(activities_details):
    """检测活动之间的时间冲突，返回冲突列表"""
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
    """检查活动是否与 CAC有约 时间冲突，返回 (has_conflict, message)"""
    try:
        date = datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
        if date.weekday() == CAC_FIXED_WEEKDAY:
            cac_range = _parse_time_range(CAC_FIXED_TIME)
            act_range = _parse_time_range(time_str)
            if cac_range and act_range and _times_overlap(act_range, cac_range):
                weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                day_name = weekday_names[CAC_FIXED_WEEKDAY]
                return True, f"该活动时间与 CAC有约（{day_name} {CAC_FIXED_TIME}）冲突，请注意避开"
    except Exception:
        pass
    return False, None


def _get_time_slot_pairs():
    """根据 TIME_SLOTS 配置生成时间槽区间列表"""
    pairs = []
    for i in range(len(TIME_SLOTS) - 1):
        pairs.append(f"{TIME_SLOTS[i]}-{TIME_SLOTS[i + 1]}")
    return pairs


def _detect_inactive_members():
    """检测消亡的兴趣组（无活动记录）"""
    activities = _list_activities()
    speakers_set = set()
    for activity in activities:
        speakers_str = str(activity.get(ACTIVITY_COL_SPEAKERS, '')).strip()
        speakers = [s.strip() for s in speakers_str.split(',') if s.strip()]
        speakers_set.update(speakers)
    return {
        'total_active_speakers': len(speakers_set),
        'message': f'当前有 {len(speakers_set)} 个活跃的分享者/兴趣组'
    }


def _detect_boundary_violations():
    """检测接近超出边界的社员（过度参与导致可能违规）"""
    signups = _list_signups()
    member_participation = Counter()
    
    for signup in signups:
        name = str(signup.get(SIGNUP_COL_NAME, '')).strip()
        if name:
            member_participation[name] += 1
    
    # 设定阈值：超过10次报名的为预警对象
    warning_threshold = 10
    violations = {name: count for name, count in member_participation.items() if count > warning_threshold}
    
    return {
        'warning_threshold': warning_threshold,
        'potential_violations': violations,
        'count': len(violations),
    }


# ===== Flask 路由 =====
@app.get("/")
def index():
    """主页"""
    return render_template("index.html", time_slots=TIME_SLOTS)


@app.get("/organizer")
def organizer():
    """分享者管理页面"""
    return render_template("organizer.html", time_slots=TIME_SLOTS, time_slot_pairs=_get_time_slot_pairs())


@app.get("/profile")
def profile_page():
    """个人主页（二期）"""
    return render_template("profile.html")


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True}), 200


@app.get("/api/activities")
def api_activities():
    """获取所有活动列表和统计信息（仅返回非已结项的活动）"""
    activities = _list_activities()
    result = []

    for activity in activities:
        # 跳过已结项的活动
        if _activity_is_closed(activity):
            continue
        activity_id = activity.get('_id')
        details = _get_activity_details(activity)
        stats = _get_signup_stats(activity_id)
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
    activity_type = _safe_text(request.args.get('activity_type', '')).lower()
    group_id = _safe_text(request.args.get('group_id', ''))
    state = _safe_text(request.args.get('state', ''))
    keyword = _safe_text(request.args.get('keyword', '')).lower()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get('page_size', str(PROFILE_EXPLORE_DEFAULT_PAGE_SIZE)))
    except Exception:
        page_size = PROFILE_EXPLORE_DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, PROFILE_EXPLORE_MAX_PAGE_SIZE))
    sort_by = _safe_text(request.args.get('sort_by', 'date')).lower()
    sort_order = _safe_text(request.args.get('sort_order', 'desc')).lower()

    allowed_types = {'', 'normal', 'cac有约'}
    allowed_states = {'', '进行中', '待结项', '已结项'}
    allowed_sort_by = {'date', 'created', 'topic', 'state'}
    allowed_sort_order = {'asc', 'desc'}
    if activity_type not in allowed_types:
        return jsonify({"ok": False, "message": "activity_type 仅支持 normal 或 cac有约"}), 400
    if state not in allowed_states:
        return jsonify({"ok": False, "message": "state 仅支持 进行中、待结项、已结项"}), 400
    if sort_by not in allowed_sort_by:
        return jsonify({"ok": False, "message": "sort_by 仅支持 date、created、topic、state"}), 400
    if sort_order not in allowed_sort_order:
        return jsonify({"ok": False, "message": "sort_order 仅支持 asc 或 desc"}), 400

    def build_response():
        result = []
        for activity in _list_activities():
            details = _get_activity_details(activity)
            stats = _get_signup_stats(activity.get('_id'))

            current_type = _safe_text(details.get('activity_type', 'normal')).lower()
            current_group_id = _safe_text(details.get('group_id', ''))
            current_state = _safe_text(details.get('status', ''))
            current_text = f"{_safe_text(details.get('topic', ''))} {_safe_text(details.get('speakers', ''))}".lower()

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
            result.sort(key=lambda item: (_safe_text(item.get('topic', '')).lower(), item.get('date', ''), item.get('time', '')), reverse=(sort_order == 'desc'))
        elif sort_by == 'state':
            state_weight = {'进行中': 0, '待结项': 1, '已结项': 2}
            result.sort(key=lambda item: (state_weight.get(_safe_text(item.get('status', '')), 9), item.get('date', ''), item.get('time', '')), reverse=(sort_order == 'desc'))
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

    payload = _cached_build(
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
    payload = _cached_build(
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
    """获取单个活动的详细信息"""
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    details = _get_activity_details(activity)
    stats = _get_signup_stats(activity_id)
    
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
    """提交评议员或旁听报名"""
    data = request.get_json(silent=True) or {}
    
    name = str(data.get("name", "")).strip()
    activity_id = str(data.get("activity_id", "")).strip()
    role = str(data.get("role", "")).strip()  # '评议员' 或 '旁听'
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()
    review_content = str(data.get("review_content", "")).strip()  # 评议内容

    # 校验基本字段
    if not name or not activity_id or not role:
        return jsonify({"ok": False, "message": "请完整填写姓名、活动和角色"}), 400

    # 校验：评议员必填评议内容
    if role == '评议员' and not review_content:
        return jsonify({"ok": False, "message": "评议员请填写评议内容"}), 400
    
    # 校验活动是否存在
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    activity_type = _safe_text(activity.get(ACTIVITY_COL_TYPE, '')) or 'normal'

    if role not in ['评议员', '旁听']:
        if not (activity_type == 'cac有约' and role == '参与者'):
            return jsonify({"ok": False, "message": "角色必须为'评议员'或'旁听'（CAC有约可选'参与者'）"}), 400

    if not _get_user_profile(name) and not email:
        return jsonify({"ok": False, "message": "首次使用请先填写邮箱"}), 400
    _upsert_user_profile(name, email=email, role='普通用户')
    
    with submit_lock:
        signups = _list_signups()
        
        # 检检查评议员是否已满
        if role == '评议员' and activity_type != 'cac有约':
            reviewer_count = _count_signups_by_activity(activity_id, '评议员')
            if reviewer_count >= REVIEWER_LIMIT:
                return jsonify({"ok": False, "message": f"评议员已满 {REVIEWER_LIMIT} 人，无法报名"}), 409
        
        # 检查姓名是否已报名过该活动
        for signup in signups:
            if _get_signup_name(signup) == name:
                if str(signup.get(SIGNUP_COL_ACTIVITY_ID, "")) == activity_id:
                    return jsonify({"ok": False, "message": "您已经报名过该活动，不能重复提交"}), 409
        
        # 添加新报名记录
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
            return jsonify({"ok": False, "message": f"报名失败: {str(e)}"}), 500

    _notify_signup_change(activity, name, role, email, '报名')
    _notify_organizer_signup(activity, name, role, review_content)
    accepted_invites = _auto_accept_invites_after_signup(activity_id, name)
    _touch_data_version()

    message = f"{role}报名成功"
    if accepted_invites > 0:
        message += f"，并已自动接受 {accepted_invites} 条邀请"

    return jsonify({"ok": True, "message": message, "accepted_invites": accepted_invites})


@app.get("/api/my-signups/<name>")
def api_my_signups(name):
    """查看某个报名者当前已报名的活动"""
    name = str(name).strip()
    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    signups = []
    for signup in _list_signups():
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
    """取消报名（仅允许报名者本人按姓名取消）"""
    signup_id = str(signup_id).strip()
    signup = _get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "报名记录不存在"}), 404

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    signup_name = _get_signup_name(signup)
    if signup_name != name:
        return jsonify({"ok": False, "message": "只能取消您自己的报名记录"}), 403

    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    activity = _get_activity_by_id(activity_id)
    role = str(signup.get(SIGNUP_COL_ROLE, '')).strip() or '报名'
    signup_email = _get_signup_email(signup)

    try:
        base.delete_row(SIGNUP_TABLE_NAME, signup_id)
    except Exception as e:
        return jsonify({"ok": False, "message": f"取消报名失败: {str(e)}"}), 500

    if activity:
        _notify_signup_change(activity, signup_name, role, signup_email, '取消')
    _touch_data_version()

    return jsonify({"ok": True, "message": "报名已取消"})


@app.post("/api/signup/<signup_id>/review-doc")
def api_submit_review_doc(signup_id):
    """评议员上传语雀文档链接"""
    signup = _get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "报名记录不存在"}), 404
    if _get_signup_role(signup) != '评议员':
        return jsonify({"ok": False, "message": "只有评议员可以上传评议文档"}), 400

    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    review_doc_url = str(data.get('review_doc_url', '')).strip()
    if not name or not review_doc_url:
        return jsonify({"ok": False, "message": "请提供姓名和评议语雀链接"}), 400
    if _get_signup_name(signup) != name:
        return jsonify({"ok": False, "message": "只能提交自己的评议文档"}), 403

    try:
        _update_row(SIGNUP_TABLE_NAME, signup.get('_id'), {
            SIGNUP_COL_REVIEW_DOC_URL: review_doc_url,
            SIGNUP_COL_REVIEW_SUBMITTED_AT: _now_iso(),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"评议文档提交失败: {exc}"}), 500

    _touch_data_version()

    return jsonify({"ok": True, "message": "评议文档已提交"})


@app.post("/api/review-rating")
def api_rate_review():
    """为评议文档打分，旁听者权重 10，其余读者权重 1"""
    data = request.get_json(silent=True) or {}
    signup_id = str(data.get('signup_id', '')).strip()
    rater_name = str(data.get('rater_name', '')).strip()
    comment = str(data.get('comment', '')).strip()
    try:
        score = float(data.get('score', 0))
    except Exception:
        score = 0

    if not signup_id or not rater_name or score <= 0:
        return jsonify({"ok": False, "message": "请完整填写评分人、评分对象和分数"}), 400
    if score > 10:
        return jsonify({"ok": False, "message": "评分请控制在 1 到 10 分之间"}), 400

    signup = _get_signup_by_id(signup_id)
    if not signup:
        return jsonify({"ok": False, "message": "评议报名记录不存在"}), 404
    reviewer_name = _get_signup_name(signup)
    if reviewer_name == rater_name:
        return jsonify({"ok": False, "message": "不能给自己的评议打分"}), 400
    if not _get_signup_review_doc_url(signup):
        return jsonify({"ok": False, "message": "该评议文档尚未上传"}), 409

    activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
    existing_rating = None
    for rating in _list_review_ratings():
        if str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip() == signup_id and str(rating.get(REVIEW_RATING_COL_RATER_NAME, '')).strip() == rater_name:
            existing_rating = rating
            break

    weight = 1
    for listener_signup in _get_activity_signups(activity_id, role='旁听'):
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
        return jsonify({"ok": False, "message": f"评分提交失败: {exc}"}), 500

    _touch_data_version()

    return jsonify({"ok": True, "message": "评分已提交", "weight": weight})


@app.post("/api/admin/init-phase1-schema")
def api_init_phase1_schema():
    result = _ensure_phase1_schema()
    status_code = 200 if result.get("ok") else 500
    return jsonify(result), status_code


@app.get("/api/groups")
def api_groups_list():
    groups = [_serialize_interest_group(group) for group in _list_interest_groups()]
    groups.sort(key=lambda item: (item.get('status', ''), item.get('name', '')))
    return jsonify({"ok": True, "groups": groups})


@app.get("/api/group/<group_id>")
def api_group_detail(group_id):
    group = _get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "兴趣组不存在"}), 404
    return jsonify({"ok": True, "group": _serialize_interest_group(group)})


@app.get("/api/my-groups/<name>")
def api_my_groups(name):
    memberships = _get_memberships_by_name(name)
    group_ids = [str(item.get(GROUP_MEMBER_COL_GROUP_ID, '')) for item in memberships]
    groups = []
    for group_id in group_ids:
        group = _get_interest_group_by_id(group_id)
        if group:
            groups.append(_serialize_interest_group(group))
    return jsonify({"ok": True, "groups": groups})


@app.post("/api/group")
def api_group_create():
    data = request.get_json(silent=True) or {}
    group_name = _safe_text(data.get('name', ''))
    leader_name = _safe_text(data.get('leader_name', ''))
    leader_email = _safe_text(data.get('leader_email', ''))
    topic_goal = _safe_text(data.get('topic_goal', ''))
    time_boundary = _safe_text(data.get('time_boundary', ''))
    execution_plan = _safe_text(data.get('execution_plan', ''))
    description = _safe_text(data.get('description', ''))
    member_names = data.get('member_names', []) or []
    # 兼容前端传 members 字符串的情况
    members_str = _safe_text(data.get('members', ''))
    if members_str and not member_names:
        member_names = [m.strip() for m in members_str.replace('，', ',').split(',') if m.strip()]

    if not group_name or not leader_name or not topic_goal or not time_boundary or not execution_plan:
        return jsonify({"ok": False, "message": "请完整填写组名、组长、主题目标、时间边界、执行方案"}), 400

    normalized_members = []
    for item in member_names:
        member_name = _safe_text(item)
        if member_name:
            normalized_members.append(member_name)
    if leader_name not in normalized_members:
        normalized_members.append(leader_name)
    normalized_members = sorted(set(normalized_members))
    if len(normalized_members) < 2:
        return jsonify({"ok": False, "message": "兴趣组创建条件至少 2 人（含组长）"}), 400

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
        return jsonify({"ok": False, "message": f"兴趣组创建失败: {exc}"}), 500

    group_id = str(created.get('_id')) if isinstance(created, dict) else ''
    group = _get_interest_group_by_id(group_id)
    if not group:
        groups = _list_interest_groups()
        if groups:
            group = groups[-1]
            group_id = str(group.get('_id'))
    group_name_saved = _safe_text(group.get(GROUP_COL_NAME, group_name)) if group else group_name

    for member_name in normalized_members:
        member_email = _get_user_email(member_name)
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
            return jsonify({"ok": False, "message": f"兴趣组成员写入失败: {exc}"}), 500

    _touch_data_version()

    return jsonify({"ok": True, "group": _serialize_interest_group(group or _get_interest_group_by_id(group_id)), "message": "兴趣组创建成功"})


@app.post("/api/group/<group_id>/join")
def api_group_join(group_id):
    group = _get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "兴趣组不存在"}), 404
    data = request.get_json(silent=True) or {}
    member_name = _safe_text(data.get('name', ''))
    member_email = _safe_text(data.get('email', ''))
    if not member_name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    if not _get_user_profile(member_name) and not member_email:
        return jsonify({"ok": False, "message": "首次使用请填写邮箱"}), 400

    _upsert_user_profile(member_name, email=member_email, role='普通用户')
    for membership in _get_memberships_by_name(member_name):
        if str(membership.get(GROUP_MEMBER_COL_GROUP_ID, '')) == str(group_id):
            return jsonify({"ok": False, "message": "您已加入该兴趣组"}), 409

    try:
        _append_row(GROUP_MEMBER_TABLE_NAME, {
            GROUP_MEMBER_COL_GROUP_ID: str(group.get('_id')),
            GROUP_MEMBER_COL_GROUP_NAME: _safe_text(group.get(GROUP_COL_NAME, '')),
            GROUP_MEMBER_COL_MEMBER_NAME: member_name,
            GROUP_MEMBER_COL_MEMBER_EMAIL: _get_user_email(member_name),
            GROUP_MEMBER_COL_MEMBER_ROLE: '组员',
            GROUP_MEMBER_COL_JOINED_AT: _now_iso(),
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"加入兴趣组失败: {exc}"}), 500

    _notify_group_membership_change(group, member_name, _get_user_email(member_name), '加入')
    _touch_data_version()
    return jsonify({"ok": True, "message": "加入兴趣组成功", "group": _serialize_interest_group(group)})


@app.post("/api/group/<group_id>/leave")
def api_group_leave(group_id):
    group = _get_interest_group_by_id(group_id)
    if not group:
        return jsonify({"ok": False, "message": "兴趣组不存在"}), 404
    data = request.get_json(silent=True) or {}
    member_name = _safe_text(data.get('name', ''))
    if not member_name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    membership = None
    for item in _list_group_members():
        if str(item.get(GROUP_MEMBER_COL_GROUP_ID, '')) == str(group_id) and _safe_text(item.get(GROUP_MEMBER_COL_MEMBER_NAME, '')) == member_name:
            membership = item
            break
    if not membership:
        return jsonify({"ok": False, "message": "您不在该兴趣组中"}), 404

    if _safe_text(membership.get(GROUP_MEMBER_COL_MEMBER_ROLE, '')) == '组长':
        return jsonify({"ok": False, "message": "组长不能直接退出，请先移交组长"}), 409

    try:
        base.delete_row(GROUP_MEMBER_TABLE_NAME, membership.get('_id'))
    except Exception as exc:
        return jsonify({"ok": False, "message": f"退出兴趣组失败: {exc}"}), 500

    _notify_group_membership_change(group, member_name, _get_user_email(member_name), '退出')
    _touch_data_version()
    return jsonify({"ok": True, "message": "已退出兴趣组", "group": _serialize_interest_group(group)})


@app.get("/api/profile-summary/<name>")
def api_profile_summary(name):
    summary = _cached_build('profile_summary', PROFILE_CACHE_TTL_SECONDS, lambda: _build_person_profile_summary(name), _safe_text(name))
    if not summary:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    return jsonify({"ok": True, "summary": summary})


@app.get("/api/profile-feed/<name>")
def api_profile_feed(name):
    target = _safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    try:
        limit = int(request.args.get('limit', str(PROFILE_FEED_DEFAULT_LIMIT)))
    except Exception:
        limit = PROFILE_FEED_DEFAULT_LIMIT
    type_filter = _safe_text(request.args.get('type', ''))
    keyword = _safe_text(request.args.get('keyword', ''))
    events = _cached_build(
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
    """返回当前评分人尚未评分、已提交文档的评议报名列表"""
    rater_name = _safe_text(request.args.get('rater', ''))
    if not rater_name:
        return jsonify({"ok": False, "message": "请传入评分人姓名 ?rater="}), 400

    rated_signup_ids = {
        str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip()
        for rating in _list_review_ratings()
        if _safe_text(rating.get(REVIEW_RATING_COL_RATER_NAME, '')) == rater_name
    }

    docs = []
    for signup in _list_signups():
        if _get_signup_role(signup) != '评议员':
            continue
        doc_url = _get_signup_review_doc_url(signup)
        if not doc_url:
            continue
        signup_id = str(signup.get('_id', '')).strip()
        if signup_id in rated_signup_ids:
            continue
        reviewer_name = _get_signup_name(signup)
        if reviewer_name == rater_name:
            continue
        activity_id = str(signup.get(SIGNUP_COL_ACTIVITY_ID, '')).strip()
        activity = _get_activity_by_id(activity_id)
        if not activity or not _activity_is_closed(activity):
            continue
        docs.append({
            'signup_id': signup_id,
            'reviewer_name': reviewer_name,
            'doc_url': doc_url,
            'activity_id': activity_id,
            'activity_topic': _safe_text(activity.get(ACTIVITY_COL_TOPIC, '')),
            'activity_date': _safe_text(activity.get(ACTIVITY_COL_DATE, '')).split('T')[0],
        })

    docs.sort(key=lambda x: x.get('activity_date', ''), reverse=True)
    return jsonify({"ok": True, "docs": docs})


@app.get("/api/profile-tasks/<name>")
def api_profile_tasks(name):
    target = _safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    tasks = _cached_build(
        'profile_tasks',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: _build_profile_tasks(target),
        target,
    )
    return jsonify({"ok": True, "tasks": tasks})


@app.get("/api/profile-recommendations/<name>")
def api_profile_recommendations(name):
    target = _safe_text(name)
    if not target:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    try:
        limit = int(request.args.get('limit', '6'))
    except Exception:
        limit = 6
    limit = max(1, min(limit, 20))
    recommendations = _cached_build(
        'profile_recommendations',
        PROFILE_CACHE_TTL_SECONDS,
        lambda: _build_profile_recommendations(target, limit=limit),
        target,
        limit,
    )
    return jsonify({"ok": True, "recommendations": recommendations, "limit": limit})


@app.post("/api/invite/<invite_id>/status")
def api_update_invite_status(invite_id):
    invite = _get_review_invite_by_id(invite_id)
    if not invite:
        return jsonify({"ok": False, "message": "邀请记录不存在"}), 404

    data = request.get_json(silent=True) or {}
    operator_name = _safe_text(data.get('operator_name', ''))
    status = _safe_text(data.get('status', ''))
    if not operator_name or not status:
        return jsonify({"ok": False, "message": "请提供操作人和目标状态"}), 400
    if status not in {'已发送', '已接受', '已拒绝', '已撤回'}:
        return jsonify({"ok": False, "message": "状态必须为 已发送、已接受、已拒绝 或 已撤回"}), 400

    old_status = _safe_text(invite.get(INVITE_COL_STATUS, ''))
    if old_status == status:
        return jsonify({"ok": True, "message": "状态未变化", "invite": _serialize_review_invite(invite)})

    inviter_name = _safe_text(invite.get(INVITE_COL_INVITER_NAME, ''))
    invitee_name = _safe_text(invite.get(INVITE_COL_INVITEE_NAME, ''))
    activity_id = _safe_text(invite.get(INVITE_COL_ACTIVITY_ID, ''))
    activity = _get_activity_by_id(activity_id)
    activity_creator = _get_activity_creator_name(activity) if activity else ''
    is_cac_operator = _is_cac_user(operator_name)
    is_invitee_operator = operator_name == invitee_name
    allowed = is_cac_operator or operator_name == inviter_name or operator_name == activity_creator or is_invitee_operator
    if not allowed:
        return jsonify({"ok": False, "message": "仅邀请人、被邀请人、活动创建者或CAC可修改邀请状态"}), 403

    if is_invitee_operator and status not in {'已接受', '已拒绝'}:
        return jsonify({"ok": False, "message": "被邀请人仅可操作为 已接受 或 已拒绝"}), 403

    if not _is_invite_transition_allowed(old_status, status, is_cac_operator=is_cac_operator):
        return jsonify({"ok": False, "message": f"不允许从 {old_status} 变更为 {status}（仅 CAC 可强制重置）"}), 409

    try:
        _update_row(REVIEW_INVITE_TABLE_NAME, invite.get('_id'), {
            INVITE_COL_STATUS: status,
            INVITE_COL_UPDATED_AT: _now_iso(),
            INVITE_COL_UPDATED_BY: operator_name,
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"更新邀请状态失败: {exc}"}), 500

    refreshed = _get_review_invite_by_id(invite_id) or invite

    invitee_email = _safe_text(refreshed.get(INVITE_COL_INVITEE_EMAIL, ''))
    if invitee_email and status in {'已接受', '已拒绝', '已撤回'}:
        topic = _safe_text(refreshed.get(INVITE_COL_ACTIVITY_TOPIC, '')) or '未命名活动'
        invitee_name = _safe_text(refreshed.get(INVITE_COL_INVITEE_NAME, '')) or '同学'
        subject = f"[CAC 分享会] 邀请状态更新：{topic}"
        body = (
            f"{invitee_name}，您好：\n\n"
            f"您在活动《{topic}》中的邀请状态已更新为：{status}。\n"
            f"操作人：{operator_name}\n"
        )
        _send_email_async(invitee_email, subject, body)

    _touch_data_version()

    return jsonify({"ok": True, "message": "邀请状态已更新", "invite": _serialize_review_invite(refreshed)})


# ===== 分享者管理 API =====
@app.get("/api/my-activities/<name>")
def api_my_activities(name):
    """获取某个分享者的活动列表"""
    name = str(name).strip()
    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400
    
    activities = _list_activities()
    my_activities = []
    
    for activity in activities:
        creator_name = _get_activity_creator_name(activity)
        if creator_name == name:
            activity_id = activity.get('_id')
            details = _get_activity_details(activity)
            stats = _get_signup_stats(activity_id)
            # 获取报名者列表（包含评议内容）
            signups = _get_activity_signups(activity_id)
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
    """登记站外输出活动，如 CAC有约"""
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    output_type = str(data.get('output_type', '')).strip()
    output_date = str(data.get('date', '')).strip()
    note = str(data.get('note', '')).strip()
    if not name or not output_type or not output_date:
        return jsonify({"ok": False, "message": "请完整填写姓名、输出类型和日期"}), 400
    if output_type not in {'分享', '评议', 'CAC有约'}:
        return jsonify({"ok": False, "message": "输出类型必须为 分享、评议 或 CAC有约"}), 400

    try:
        _append_row(OUTPUT_RECORD_TABLE_NAME, {
            OUTPUT_RECORD_COL_NAME: name,
            OUTPUT_RECORD_COL_TYPE: output_type,
            OUTPUT_RECORD_COL_DATE: output_date,
            OUTPUT_RECORD_COL_NOTE: note,
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": f"输出记录保存失败: {exc}"}), 500

    _touch_data_version()

    return jsonify({"ok": True, "message": "输出记录已登记"})


@app.post("/api/activity")
def api_create_activity():
    """创建新活动（分享者）"""
    data = request.get_json(silent=True) or {}
    
    # 验证必填字段
    date = str(data.get("date", "")).strip()
    time = str(data.get("time", "")).strip()
    speakers = str(data.get("speakers", "")).strip()
    topic = str(data.get("topic", "")).strip()
    creator_name = str(data.get("creator_name", "")).strip()
    creator_email = str(data.get("creator_email", "")).strip()
    activity_type = _safe_text(data.get("activity_type", "normal")) or 'normal'
    group_id = _safe_text(data.get("group_id", ""))
    classroom = str(data.get("classroom", "")).strip()
    videourl = str(data.get("videourl", "")).strip()
    
    if not date or not time or not speakers or not topic or not creator_name:
        return jsonify({
            "ok": False, 
            "message": "请完整填写日期、时间、分享者、主题和姓名"
        }), 400

    if activity_type not in {'normal', 'cac有约'}:
        return jsonify({"ok": False, "message": "活动类型必须为 normal 或 cac有约"}), 400

    # cac有约 时间限制验证
    if activity_type == 'cac有约':
        from datetime import datetime
        try:
            dt = datetime.strptime(date, '%Y-%m-%d')
        except:
            return jsonify({"ok": False, "message": "日期格式错误"}), 400
        if dt.weekday() != 6:  # 0=周一, 6=周日
            return jsonify({"ok": False, "message": "CAC有约 只能在周日举办"}), 400
        allowed_slots = ['14:00-14:30', '14:30-15:00', '15:00-15:30', '15:30-16:00',
                         '16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00']
        if time not in allowed_slots:
            return jsonify({"ok": False, "message": "CAC有约 时间段必须为周日 14:00-18:00（半小时一档）"}), 400

    if not _get_user_profile(creator_name) and not creator_email:
        return jsonify({"ok": False, "message": "首次使用请填写邮箱后再创建活动"}), 400
    _upsert_user_profile(creator_name, email=creator_email, role='普通用户')

    creator_memberships = _get_memberships_by_name(creator_name)
    selected_group = None
    if activity_type == 'normal':
        if len(creator_memberships) > 1 and not group_id:
            return jsonify({"ok": False, "message": "您加入了多个兴趣组，请创建活动时选择所属兴趣组"}), 400
        if group_id:
            selected_group = _get_interest_group_by_id(group_id)
            if not selected_group:
                return jsonify({"ok": False, "message": "所选兴趣组不存在"}), 404
            member_group_ids = set(_get_group_ids_for_member(creator_name))
            if group_id not in member_group_ids:
                return jsonify({"ok": False, "message": "只能选择您已加入的兴趣组"}), 403
        elif len(creator_memberships) == 1:
            selected_group = _get_interest_group_by_id(creator_memberships[0].get(GROUP_MEMBER_COL_GROUP_ID, ''))

    # 检测冲突（仅提示，不拦截创建）
    warnings = []
    existing_activities = _list_activities()
    new_range = _parse_time_range(time)
    
    if new_range:
        for act in existing_activities:
            existing_date = str(act.get(ACTIVITY_COL_DATE, '')).strip()
            existing_type = str(act.get(ACTIVITY_COL_TYPE, '')).strip() or 'normal'
            
            # 不同日期的活动无需检测冲突
            if existing_date != date:
                continue
            
            existing_range = _parse_time_range(act.get(ACTIVITY_COL_TIME, ''))
            if not (existing_range and _times_overlap(new_range, existing_range)):
                continue
            
            existing_topic = str(act.get(ACTIVITY_COL_TOPIC, '')).strip()
            
            # 规则1：普通活动与普通活动冲突检测
            if activity_type != 'cac有约' and existing_type != 'cac有约':
                warnings.append(f"与已有活动「{existing_topic}」（普通活动）时间重叠，请确认是否继续")
            
            # 规则2：普通活动与CAC有约冲突检测
            elif activity_type != 'cac有约' and existing_type == 'cac有约':
                warnings.append(f"与 CAC有约「{existing_topic}」时间冲突，强烈建议调整时间！")
            
            # 规则3：CAC有约与普通活动冲突检测
            elif activity_type == 'cac有约' and existing_type != 'cac有约':
                warnings.append(f"与已有活动「{existing_topic}」（普通活动）时间冲突，强烈建议调整时间！")

    # 创建活动记录
    row_data = {
        ACTIVITY_COL_DATE: date,
        ACTIVITY_COL_TIME: time,
        ACTIVITY_COL_SPEAKERS: speakers,
        ACTIVITY_COL_TOPIC: topic,
        ACTIVITY_COL_TYPE: activity_type,
        ACTIVITY_COL_GROUP_ID: str(selected_group.get('_id')) if selected_group else None,
        ACTIVITY_COL_GROUP_NAME: _safe_text(selected_group.get(GROUP_COL_NAME, '')) if selected_group else None,
        ACTIVITY_COL_CREATOR_NAME: creator_name,
        LEGACY_ACTIVITY_COL_CREATOR_STUDENT_ID: creator_name,
        ACTIVITY_COL_CREATOR_EMAIL: creator_email,
        ACTIVITY_COL_CLASSROOM: classroom if classroom else None,
        ACTIVITY_COL_VIDEOURL: videourl if videourl else None,
    }
    
    try:
        _append_row(ACTIVITY_TABLE_NAME, row_data)
        response = {"ok": True, "message": "活动创建成功"}
        if warnings:
            response["warnings"] = warnings
        _notify_activity_change(
            creator_email,
            creator_name,
            topic,
            '创建',
            [f"活动时间：{date} {time}"],
        )
        _notify_cac_activity_created(activity_type, topic, creator_name)
        _touch_data_version()
        return jsonify(response), 201
    except Exception as e:
        return jsonify({"ok": False, "message": f"创建失败: {str(e)}"}), 500


@app.put("/api/activity/<activity_id>")
def api_update_activity(activity_id):
    """编辑活动（仅限创建者）"""
    activity_id = str(activity_id).strip()
    activity = _get_activity_by_id(activity_id)
    
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    
    data = request.get_json(silent=True) or {}
    creator_name = str(data.get("creator_name", "")).strip()
    
    # 验证身份
    actual_creator = _get_activity_creator_name(activity)
    if actual_creator != creator_name:
        return jsonify({
            "ok": False, 
            "message": "只有活动创建者才能编辑此活动"
        }), 403
    
    # 准备更新数据
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
        new_type = _safe_text(data.get("activity_type", ""))
        if new_type and new_type not in {'normal', 'cac有约'}:
            return jsonify({"ok": False, "message": "活动类型必须为 normal 或 cac有约"}), 400
        update_data[ACTIVITY_COL_TYPE] = new_type or None
    if "group_id" in data:
        new_group_id = _safe_text(data.get("group_id", ""))
        if new_group_id:
            group = _get_interest_group_by_id(new_group_id)
            if not group:
                return jsonify({"ok": False, "message": "所选兴趣组不存在"}), 404
            update_data[ACTIVITY_COL_GROUP_ID] = str(group.get('_id'))
            update_data[ACTIVITY_COL_GROUP_NAME] = _safe_text(group.get(GROUP_COL_NAME, ''))
        else:
            update_data[ACTIVITY_COL_GROUP_ID] = None
            update_data[ACTIVITY_COL_GROUP_NAME] = None
    
    if not update_data:
        return jsonify({
            "ok": False, 
            "message": "没有可更新的数据"
        }), 400
    
    try:
        _update_row(ACTIVITY_TABLE_NAME, activity.get('_id'), update_data)
        creator_email = str(data.get("creator_email", "")).strip() or _get_activity_creator_email(activity)
        _notify_activity_change(
            creator_email,
            creator_name,
            str(update_data.get(ACTIVITY_COL_TOPIC) or activity.get(ACTIVITY_COL_TOPIC, '')).strip(),
            '更新',
            [
                f"活动日期：{str(update_data.get(ACTIVITY_COL_DATE) or activity.get(ACTIVITY_COL_DATE, '')).strip()}",
                f"活动时间：{str(update_data.get(ACTIVITY_COL_TIME) or activity.get(ACTIVITY_COL_TIME, '')).strip()}",
            ],
        )
        _touch_data_version()
        return jsonify({"ok": True, "message": "活动更新成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"更新失败: {str(e)}"}), 500


@app.post("/api/activity/<activity_id>/close")
def api_close_activity(activity_id):
    """活动结项，统计准时率并触发评议提醒"""
    activity_id = str(activity_id).strip()
    activity = _get_activity_by_id(activity_id)
    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404
    data = request.get_json(silent=True) or {}
    creator_name = str(data.get('creator_name', '')).strip()
    if _get_activity_creator_name(activity) != creator_name:
        return jsonify({"ok": False, "message": "只有活动创建者才能结项"}), 403
    if _activity_is_closed(activity):
        return jsonify({"ok": False, "message": "活动已经结项"}), 409

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
        return jsonify({"ok": False, "message": f"活动结项失败: {exc}"}), 500

    refreshed_activity = _get_activity_by_id(activity_id) or activity
    activity_type = _safe_text(refreshed_activity.get(ACTIVITY_COL_TYPE, '')) or 'normal'
    if activity_type != 'cac有约':
        for reviewer_signup in _get_activity_signups(activity_id, role='评议员'):
            if _get_signup_review_doc_url(reviewer_signup):
                continue
            _notify_review_doc_reminder(reviewer_signup, refreshed_activity)
            try:
                _update_row(SIGNUP_TABLE_NAME, reviewer_signup.get('_id'), {
                    SIGNUP_COL_LAST_REVIEW_REMINDER_AT: _now_iso(),
                })
            except Exception as exc:
                print(f"Update immediate reminder timestamp failed: {exc}")

    _touch_data_version()

    return jsonify({
        "ok": True,
        "message": "活动已结项",
        "on_time": on_time,
    })


@app.delete("/api/activity/<activity_id>")
def api_delete_activity(activity_id):
    """删除活动（仅限创建者，会通知报名者）"""
    activity_id = str(activity_id).strip()
    activity = _get_activity_by_id(activity_id)

    if not activity:
        return jsonify({"ok": False, "message": "活动不存在"}), 404

    data = request.get_json(silent=True) or {}
    creator_name = str(data.get("creator_name", "")).strip()

    # 验证身份
    actual_creator = _get_activity_creator_name(activity)
    if actual_creator != creator_name:
        return jsonify({
            "ok": False,
            "message": "只有活动创建者才能删除此活动"
        }), 403

    # 获取活动信息
    topic = str(activity.get(ACTIVITY_COL_TOPIC, '')).strip() or '未命名活动'
    date = str(activity.get(ACTIVITY_COL_DATE, '')).strip() or '日期待定'
    time = str(activity.get(ACTIVITY_COL_TIME, '')).strip() or '时间待定'

    # 获取所有报名者并发送通知
    signups = _get_activity_signups(activity_id)
    notified_count = 0
    for signup in signups:
        signup_name = _get_signup_name(signup)
        signup_email = _get_signup_email(signup)
        if signup_email:
            subject = f"[CAC 分享会] 活动取消通知：{topic}"
            body = (
                f"您好 {signup_name}，\n\n"
                f"很抱歉通知您，您报名的活动已被创建者取消：\n\n"
                f"活动：{topic}\n"
                f"时间：{date} {time}\n\n"
                f"如有疑问，请联系活动创建者 {creator_name}。\n\n"
                f"—— CAC 分享会系统"
            )
            _send_email_async(signup_email, subject, body)
            notified_count += 1

    # 删除所有报名记录
    for signup in signups:
        try:
            base.delete_row(SIGNUP_TABLE_NAME, signup.get('_id'))
        except Exception:
            pass

    # 删除活动
    try:
        base.delete_row(ACTIVITY_TABLE_NAME, activity.get('_id'))
        _notify_activity_change(
            _get_activity_creator_email(activity),
            creator_name,
            topic,
            '删除',
        )
        _touch_data_version()
        msg = f"活动已删除"
        if notified_count > 0:
            msg += f"，已通知 {notified_count} 位报名者"
        return jsonify({"ok": True, "message": msg})
    except Exception as e:
        return jsonify({"ok": False, "message": f"删除失败: {str(e)}"}), 500


# ===== CAC管理员相关API =====

def _is_cac_admin(name):
    """检查是否为CAC管理员"""
    if not name:
        return False
    name = str(name).strip()
    rows = _list_rows(CAC_ADMINS_TABLE_NAME)
    for row in rows:
        if str(row.get(CAC_ADMIN_COL_NAME, '')).strip() == name:
            return True
    return False


def _list_cac_admins():
    """获取CAC管理员列表"""
    rows = _list_rows(CAC_ADMINS_TABLE_NAME)
    return [{'name': str(row.get(CAC_ADMIN_COL_NAME, '')).strip()} for row in rows]


@app.get("/api/cac-admins")
def api_list_cac_admins():
    """获取CAC管理员列表"""
    return jsonify({"ok": True, "admins": _list_cac_admins()})


@app.post("/api/cac-admin")
def api_add_cac_admin():
    """添加CAC管理员"""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    requester_name = str(data.get("requester_name", "")).strip()

    if not name:
        return jsonify({"ok": False, "message": "姓名不能为空"}), 400

    # 检查权限：已有管理员或首次初始化（管理员列表为空）
    existing_admins = _list_cac_admins()
    if existing_admins and not _is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "只有管理员才能添加新管理员"}), 403

    # 检查是否已存在
    if _is_cac_admin(name):
        return jsonify({"ok": False, "message": "该用户已是管理员"}), 400

    try:
        _append_row(CAC_ADMINS_TABLE_NAME, {
            CAC_ADMIN_COL_NAME: name,
            CAC_ADMIN_COL_CREATED_AT: _now_iso(),
        })
        return jsonify({"ok": True, "message": f"已添加 {name} 为管理员"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"添加失败: {str(e)}"}), 500


@app.delete("/api/cac-admin/<name>")
def api_delete_cac_admin(name):
    """删除CAC管理员"""
    try:
        name = str(name).strip()
        data = request.get_json(silent=True) or {}
        requester_name = str(data.get("requester_name", "")).strip()

        if not requester_name:
            return jsonify({"ok": False, "message": "缺少请求者姓名"}), 400

        if not _is_cac_admin(requester_name):
            return jsonify({"ok": False, "message": "只有管理员才能删除管理员"}), 403

        rows = _list_rows(CAC_ADMINS_TABLE_NAME)
        for row in rows:
            if str(row.get(CAC_ADMIN_COL_NAME, '')).strip() == name:
                try:
                    base.delete_row(CAC_ADMINS_TABLE_NAME, row.get('_id'))
                    return jsonify({"ok": True, "message": f"已移除 {name} 的管理员权限"})
                except Exception as e:
                    print(f"[ERROR] Delete CAC admin row failed: {e}")
                    return jsonify({"ok": False, "message": f"删除失败: {str(e)}"}), 500

        return jsonify({"ok": False, "message": "该用户不是管理员"}), 404
    except Exception as e:
        print(f"[ERROR] api_delete_cac_admin unexpected error: {e}")
        return jsonify({"ok": False, "message": f"服务器错误: {str(e)}"}), 500


# ===== CAC教室时间槽相关API =====

def _list_cac_room_slots(date=None, time_slot=None):
    """获取CAC教室时间槽列表

    time_slot 可以是单个时间段如 '14:00-14:30' 或合并后的如 '14:00-15:30'
    当是合并后的时间段时，返回在该时间段内所有半小时槽都可用的教室
    """
    rows = _list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    print(f"[DEBUG] _list_cac_room_slots: Found {len(rows)} total slots in database")

    # 解析需要的半小时槽列表
    required_slots = []
    if time_slot:
        # 支持多个时间段，用逗号分隔
        for ts in time_slot.split(','):
            ts = ts.strip()
            if not ts:
                continue
            start, end = ts.split('-')[0], ts.split('-')[1]
            # 生成该范围内的所有半小时槽
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

    print(f"[DEBUG] Required time slots: {required_slots}")

    # 统计每个教室在所有需要的时间槽的可用情况
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
        # 找出在所有需要的时间槽都可用的教室
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
        # 没有特定时间要求，返回所有可用槽
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

    print(f"[DEBUG] _list_cac_room_slots: Returning {len(result)} available slots (date={date}, time_slot={time_slot})")
    return result


@app.get("/api/cac-room-slots")
def api_list_cac_room_slots():
    """获取可用教室时间槽"""
    date = str(request.args.get("date", "")).strip()
    time_slot = str(request.args.get("time_slot", "")).strip()
    slots = _list_cac_room_slots(date=date, time_slot=time_slot)
    return jsonify({"ok": True, "slots": slots})


@app.post("/api/cac-room-slot")
def api_add_cac_room_slot():
    """管理员添加教室时间槽"""
    data = request.get_json(silent=True) or {}
    classroom = str(data.get("classroom", "")).strip()
    date = str(data.get("date", "")).strip()
    time_slot = str(data.get("time_slot", "")).strip()
    requester_name = str(data.get("requester_name", "")).strip()

    if not _is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "只有管理员才能添加教室时间槽"}), 403

    if not classroom or not date or not time_slot:
        return jsonify({"ok": False, "message": "请完整填写教室、日期和时间段"}), 400

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
        return jsonify({"ok": True, "message": "教室时间槽添加成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"添加失败: {str(e)}"}), 500


@app.delete("/api/cac-room-slot/<slot_id>")
def api_delete_cac_room_slot(slot_id):
    """管理员删除教室时间槽"""
    data = request.get_json(silent=True) or {}
    requester_name = str(data.get("requester_name", "")).strip()

    if not _is_cac_admin(requester_name):
        return jsonify({"ok": False, "message": "只有管理员才能删除教室时间槽"}), 403

    rows = _list_rows(CAC_ROOM_SLOTS_TABLE_NAME)
    for row in rows:
        if row.get('_id') == slot_id:
            try:
                base.delete_row(CAC_ROOM_SLOTS_TABLE_NAME, slot_id)
                return jsonify({"ok": True, "message": "教室时间槽已删除"})
            except Exception as e:
                return jsonify({"ok": False, "message": f"删除失败: {str(e)}"}), 500

    return jsonify({"ok": False, "message": "教室时间槽不存在"}), 404


_maintenance_thread_started = False


def _ensure_background_maintenance_started():
    global _maintenance_thread_started
    if _maintenance_thread_started:
        return
    _maintenance_thread_started = True
    threading.Thread(target=_background_maintenance_loop, daemon=True).start()


_ensure_background_maintenance_started()


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)


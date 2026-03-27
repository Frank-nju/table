"""
配置模块

集中管理所有配置常量和环境变量
"""

import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

# ===== 数据库配置 =====
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

# SeaTable 配置
SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "https://table.nju.edu.cn").rstrip("/")
API_TOKEN = os.getenv("SEATABLE_API_TOKEN", "")

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
ACTIVITY_COL_EXPECTED_ATTENDANCE = os.getenv("ACTIVITY_COL_EXPECTED_ATTENDANCE", "预期人数")
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
SIGNUP_COL_REVIEW_CONTENT = os.getenv("SIGNUP_COL_REVIEW_CONTENT", "评议内容")
LEGACY_SIGNUP_COL_STUDENT_ID = os.getenv("SIGNUP_COL_STUDENT_ID", "学号")

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
AUTO_REGISTER_COLUMNS = {
    "分享会活动": [
        "活动日期", "活动时间", "分享者", "活动主题", "活动教室", "线上视频号",
        "组织者姓名", "组织者邮箱", "活动状态", "结项时间", "准时结项", "结项人",
        "活动类型", "所属兴趣组ID", "所属兴趣组", "组织者学号", "预期人数",
    ],
    "分享会报名": [
        "姓名", "关联活动", "角色", "联系电话", "邮箱", "学号",
        "评议语雀链接", "评议提交时间", "上次评议提醒时间", "评议内容",
    ],
    "评议评分": [
        "评议报名ID", "活动ID", "评议者姓名", "评分人姓名", "评分", "权重", "评分备注",
    ],
    "输出活动记录": ["姓名", "输出类型", "输出日期", "备注"],
    "用户档案": ["姓名", "邮箱", "角色", "首次使用时间"],
    "兴趣组": ["组名", "组长", "主题目标", "时间边界", "执行方案", "简介", "状态", "创建时间"],
    "兴趣组成员": ["兴趣组ID", "兴趣组名", "成员姓名", "成员邮箱", "成员身份", "加入时间"],
    "评议邀请": [
        "活动ID", "活动主题", "邀请人", "被邀请人", "被邀请邮箱",
        "邀请来源", "状态", "邀请时间", "状态更新时间", "状态更新人",
    ],
    "CAC管理员": ["姓名", "添加时间"],
    "CAC教室时间槽": ["教室", "日期", "时间段", "状态", "关联活动ID", "创建者", "创建时间"],
}

# ===== 报名限额配置 =====
REVIEWER_LIMIT = int(os.getenv("REVIEWER_LIMIT", "3"))
LISTENER_UNLIMITED = os.getenv("LISTENER_UNLIMITED", "true").lower() == "true"

# ===== 时间槽配置 =====
TIME_SLOTS = [x.strip() for x in os.getenv("TIME_SLOTS", "09:00,09:30,10:00,10:30,11:00,11:30,12:00,12:30,13:00,13:30,14:00,14:30,15:00,15:30,16:00,16:30,17:00,17:30,18:00,18:30,19:00,19:30,20:00,20:30,21:00,21:30,22:00").split(",") if x.strip()]

# ===== CAC有约冲突检测配置 =====
CAC_FIXED_WEEKDAY = int(os.getenv("CAC_FIXED_WEEKDAY", "4"))

# ===== 邮件提醒配置 =====
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)
SENDER_NAME = os.getenv("SENDER_NAME", "CAC分享会")

# ===== 个人主页配置 =====
PROFILE_EXPLORE_DEFAULT_PAGE_SIZE = int(os.getenv("PROFILE_EXPLORE_DEFAULT_PAGE_SIZE", "10"))
PROFILE_EXPLORE_MAX_PAGE_SIZE = int(os.getenv("PROFILE_EXPLORE_MAX_PAGE_SIZE", "100"))
PROFILE_CACHE_TTL_SECONDS = int(os.getenv("PROFILE_CACHE_TTL_SECONDS", "120"))
PROFILE_FEED_DEFAULT_LIMIT = int(os.getenv("PROFILE_FEED_DEFAULT_LIMIT", "30"))

# ===== 其他配置 =====
TASK_LOCK_FILE = os.path.join(tempfile.gettempdir(), "table_signup_task.lock")
ACTIVITY_CLOSE_GRACE_MINUTES = int(os.getenv("ACTIVITY_CLOSE_GRACE_MINUTES", "1440"))  # 24小时
MEMBER_ROSTER_FILE = os.getenv("MEMBER_ROSTER_FILE", "member_roster.txt")
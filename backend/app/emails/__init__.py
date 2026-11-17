"""Plain-text email templates in English and Simplified Chinese."""

from __future__ import annotations

from typing import Any

ROLE_LABELS = {
    "en": {"reviewer": "reviewer", "observer": "observer", "participant": "participant"},
    "zh": {"reviewer": "评议员", "observer": "旁听", "participant": "参与者"},
}

STATUS_LABELS = {
    "en": {"accepted": "accepted", "declined": "declined", "withdrawn": "withdrawn", "pending": "pending"},
    "zh": {"accepted": "已接受", "declined": "已拒绝", "withdrawn": "已撤回", "pending": "待回复"},
}

_SIGN_OFF = {"en": "\n\n— {app}", "zh": "\n\n—— {app}"}

TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "password_reset": {
        "en": (
            "Reset your password",
            "Hi {name},\n\nSomeone (hopefully you) asked to reset your password. Open this link within "
            "{ttl} minutes to choose a new one:\n\n{link}\n\nIf you didn't ask for this, ignore this email.",
        ),
        "zh": (
            "重置密码",
            "{name}，你好：\n\n我们收到了重置密码的请求。请在 {ttl} 分钟内打开以下链接设置新密码：\n\n{link}\n\n"
            "如果这不是你本人的操作，请忽略本邮件。",
        ),
    },
    "account_invite": {
        "en": (
            "Your account is ready",
            "Hi {name},\n\nAn administrator created an account for you. Open this link within {ttl} minutes "
            "to set your password and sign in:\n\n{link}",
        ),
        "zh": (
            "你的账号已创建",
            "{name}，你好：\n\n管理员已为你创建账号。请在 {ttl} 分钟内打开以下链接设置密码并登录：\n\n{link}",
        ),
    },
    "signup_confirmed": {
        "en": (
            "You're signed up: {title}",
            "Hi {name},\n\nYou're signed up as a {role} for “{title}” on {when}.\n\n{link}",
        ),
        "zh": ("报名成功：{title}", "{name}，你好：\n\n你已作为{role}报名「{title}」，时间：{when}。\n\n{link}"),
    },
    "signup_cancelled": {
        "en": ("Signup cancelled: {title}", "Hi {name},\n\nYour signup for “{title}” ({when}) was cancelled."),
        "zh": ("已取消报名：{title}", "{name}，你好：\n\n你对「{title}」（{when}）的报名已取消。"),
    },
    "organizer_new_signup": {
        "en": (
            "New {role}: {title}",
            "Hi {name},\n\n{participant} signed up as a {role} for “{title}” ({when}).{topic}\n\n{link}",
        ),
        "zh": (
            "新的{role}报名：{title}",
            "{name}，你好：\n\n{participant} 以{role}身份报名了「{title}」（{when}）。{topic}\n\n{link}",
        ),
    },
    "activity_cancelled": {
        "en": (
            "Cancelled: {title}",
            "Hi {name},\n\n“{title}”, planned for {when}, has been cancelled by {organizer}. "
            "Your signup has been removed.",
        ),
        "zh": (
            "活动取消：{title}",
            "{name}，你好：\n\n原定于 {when} 的「{title}」已被 {organizer} 取消，你的报名已一并移除。",
        ),
    },
    "activity_rescheduled": {
        "en": (
            "Updated: {title}",
            "Hi {name},\n\nThe details of “{title}” changed. It now takes place on {when}{where}.\n\n{link}",
        ),
        "zh": (
            "活动变更：{title}",
            "{name}，你好：\n\n「{title}」的安排已更新，现在的时间为 {when}{where}。\n\n{link}",
        ),
    },
    "review_reminder": {
        "en": (
            "Please submit your review: {title}",
            "Hi {name},\n\n“{title}” has closed. Please add the link to your review document:\n\n{link}\n\n"
            "You'll get a reminder every {hours} hours until it's submitted.",
        ),
        "zh": (
            "请提交评议：{title}",
            "{name}，你好：\n\n「{title}」已结项，请尽快提交你的评议文档链接：\n\n{link}\n\n提交前系统会每 {hours} 小时提醒一次。",
        ),
    },
    "invite_received": {
        "en": (
            "Review invitation: {title}",
            "Hi {name},\n\n{inviter} invited you to review “{title}” on {when}.{message}\n\nRespond here:\n{link}",
        ),
        "zh": (
            "评议邀请：{title}",
            "{name}，你好：\n\n{inviter} 邀请你评议「{title}」（{when}）。{message}\n\n点此回复：\n{link}",
        ),
    },
    "invite_updated": {
        "en": (
            "Invitation {status}: {title}",
            "Hi {name},\n\nThe review invitation for “{title}” was {status} by {actor}.\n\n{link}",
        ),
        "zh": (
            "邀请{status}：{title}",
            "{name}，你好：\n\n「{title}」的评议邀请已被 {actor} 标记为{status}。\n\n{link}",
        ),
    },
    "group_member_joined": {
        "en": ("{member} joined {group}", "Hi {name},\n\n{member} just joined your interest group “{group}”."),
        "zh": ("{member} 加入了 {group}", "{name}，你好：\n\n{member} 刚刚加入了你的兴趣组「{group}」。"),
    },
    "participation_reminder": {
        "en": (
            "We miss you at share sessions",
            "Hi {name},\n\nWe haven't seen an output from you (sharing, reviewing or a CAC Meetup) in the last "
            "{days} days. Pick an upcoming session here:\n\n{link}",
        ),
        "zh": (
            "最近还没有看到你的输出",
            "{name}，你好：\n\n过去 {days} 天内你还没有输出活动（分享、评议或 CAC 有约）。来看看近期的活动吧：\n\n{link}",
        ),
    },
    "participation_report": {
        "en": (
            "Participation report: {count} inactive member(s)",
            "These members had no output in the last {days} days ({tracked} members tracked):\n\n{names}",
        ),
        "zh": (
            "参与度周报：{count} 位成员未达标",
            "以下成员在过去 {days} 天内没有输出活动（共统计 {tracked} 人）：\n\n{names}",
        ),
    },
    "meetup_proposed": {
        "en": (
            "New CAC Meetup proposed: {title}",
            "{organizer} scheduled a CAC Meetup “{title}” on {when}.\n\n{link}",
        ),
        "zh": ("新的 CAC 有约：{title}", "{organizer} 发起了 CAC 有约「{title}」，时间：{when}。\n\n{link}"),
    },
}


def render(key: str, locale: str, app_name: str, **context: Any) -> tuple[str, str]:
    lang = locale if locale in ("en", "zh") else "en"
    subject_tpl, body_tpl = TEMPLATES[key][lang]
    prefix = f"[{app_name}] "
    subject = prefix + subject_tpl.format(**context)
    body = body_tpl.format(**context) + _SIGN_OFF[lang].format(app=app_name)
    return subject, body


def role_label(role: str, locale: str) -> str:
    return ROLE_LABELS.get(locale, ROLE_LABELS["en"]).get(role, role)


def status_label(status: str, locale: str) -> str:
    return STATUS_LABELS.get(locale, STATUS_LABELS["en"]).get(status, status)

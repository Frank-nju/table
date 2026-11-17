"""Import data from the previous version of the app (v1/v2).

The old app stored every record as a JSON blob in a single `app_rows` table, keyed by Chinese
table and column names, and identified people only by the name they typed. This module maps
those rows onto the relational schema:

* every distinct name becomes a User; users with a known email can claim their account through
  "Forgot password", the rest can be given a set-password link by an administrator;
* free-text classrooms become Rooms, and "HH:MM-HH:MM" strings become proper start/end times;
* the old `CAC管理员` list becomes the admin role.

Run it once against an empty database:

    python -m app.cli import-legacy --source "mysql+pymysql://user:pass@host/table_signup"
    python -m app.cli import-legacy --json legacy-dump.json
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Activity,
    ActivityKind,
    ActivitySpeaker,
    Contribution,
    ContributionKind,
    Group,
    GroupMembership,
    GroupRole,
    GroupStatus,
    Invite,
    InviteSource,
    InviteStatus,
    ReviewRating,
    Room,
    RoomSlot,
    Signup,
    SignupRole,
    User,
    UserRole,
)

log = logging.getLogger(__name__)

T_ACTIVITY = "分享会活动"
T_SIGNUP = "分享会报名"
T_RATING = "评议评分"
T_OUTPUT = "输出活动记录"
T_PROFILE = "用户档案"
T_GROUP = "兴趣组"
T_MEMBER = "兴趣组成员"
T_INVITE = "评议邀请"
T_ADMIN = "CAC管理员"
T_SLOT = "CAC教室时间槽"

SIGNUP_ROLES = {"评议员": SignupRole.REVIEWER, "旁听": SignupRole.OBSERVER, "参与者": SignupRole.PARTICIPANT}
INVITE_STATUSES = {
    "已发送": InviteStatus.PENDING,
    "已接受": InviteStatus.ACCEPTED,
    "已拒绝": InviteStatus.DECLINED,
    "已撤回": InviteStatus.WITHDRAWN,
    "已取消": InviteStatus.WITHDRAWN,
}
OUTPUT_KINDS = {"分享": ContributionKind.SHARING, "评议": ContributionKind.REVIEW, "CAC有约": ContributionKind.MEETUP}
STUDENT_ID = re.compile(r"[A-Za-z]{1,4}\d{4,}")
NAME_SPLIT = re.compile(r"[,，、;；/]+")


@dataclass
class ImportReport:
    created: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        if len(self.warnings) < 200:
            self.warnings.append(message)

    def summary(self) -> str:
        lines = ["Imported:"] + [f"  {k}: {v}" for k, v in sorted(self.created.items())]
        if self.skipped:
            lines += ["Skipped:"] + [f"  {k}: {v}" for k, v in sorted(self.skipped.items())]
        if self.warnings:
            lines += [f"Warnings ({len(self.warnings)} shown):"] + [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


# ----- Loading -----


def load_from_database(url: str) -> dict[str, list[dict[str, Any]]]:
    engine = create_engine(url)
    tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with engine.connect() as conn:
        for table_name, row_id, payload, created_at in conn.execute(
            text("SELECT table_name, row_id, row_data, created_at FROM app_rows ORDER BY created_at")
        ):
            data = json.loads(payload) if isinstance(payload, str | bytes) else dict(payload)
            data["_id"] = row_id
            data.setdefault("_created_at", created_at.isoformat() if created_at else "")
            tables[table_name].append(data)
    return dict(tables)


def load_from_json(path: str) -> dict[str, list[dict[str, Any]]]:
    """Accepts {table: [rows]} or a flat list of {table_name, row_id, row_data} records."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict):
        return {k: list(v) for k, v in raw.items()}
    tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in raw:
        data = rec["row_data"] if isinstance(rec["row_data"], dict) else json.loads(rec["row_data"])
        data["_id"] = rec["row_id"]
        tables[rec["table_name"]].append(data)
    return dict(tables)


# ----- Parsing helpers -----


def _text(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("none", "null") else s


def _date(value: Any) -> date | None:
    s = _text(value)[:10]
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _datetime(value: Any) -> datetime | None:
    """Old timestamps were naive local times like '2026-03-01 18:30:00' (sometimes with a 'T')."""
    s = _text(value).replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            local = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return local.replace(tzinfo=get_settings().tz).astimezone(UTC)
    return None


def _time_range(value: Any) -> tuple[time, time] | None:
    s = _text(value).replace("～", "-").replace("~", "-").replace("–", "-").replace("—", "-")
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None
    try:
        start, end = time.fromisoformat(parts[0].zfill(5)), time.fromisoformat(parts[1].zfill(5))
    except ValueError:
        return None
    return (start, end) if start < end else None


def _bool(value: Any) -> bool | None:
    s = _text(value).lower()
    if not s:
        return None
    return s in ("true", "1", "yes", "y", "是")


def _names(value: Any) -> list[str]:
    return [n.strip() for n in NAME_SPLIT.split(_text(value)) if n.strip()]


# ----- Import -----


class Importer:
    def __init__(self, db: Session, tables: dict[str, list[dict[str, Any]]]):
        self.db = db
        self.tables = tables
        self.report = ImportReport()
        self.users: dict[str, User] = {}
        self.rooms: dict[str, Room] = {}
        self.groups: dict[str, Group] = {}
        self.activities: dict[str, Activity] = {}
        self.signups: dict[str, Signup] = {}

    def rows(self, table: str) -> list[dict[str, Any]]:
        return self.tables.get(table, [])

    def user(self, name: Any, email: Any = "") -> User | None:
        name = _text(name)
        if not name:
            return None
        email = _text(email).lower()
        user = self.users.get(name)
        if user is None:
            user = User(name=name[:64], email=None, participation_tracked=not STUDENT_ID.fullmatch(name))
            self.db.add(user)
            self.users[name] = user
            self.report.created["users"] += 1
        if email and not user.email and "@" in email:
            if any(u.email == email for u in self.users.values()):
                self.report.warn(f"Email {email} is used by several names; kept it on the first one only")
            else:
                user.email = email
        return user

    def room(self, name: Any) -> Room | None:
        name = _text(name)
        if not name:
            return None
        if name not in self.rooms:
            self.rooms[name] = Room(name=name[:80])
            self.db.add(self.rooms[name])
            self.report.created["rooms"] += 1
        return self.rooms[name]

    def run(self) -> ImportReport:
        if self.db.scalar(select(func.count()).select_from(User)):
            raise RuntimeError("The target database already has users. Import into an empty database.")
        self.import_people()
        self.import_groups()
        self.import_activities()
        self.import_signups()
        self.import_ratings()
        self.import_invites()
        self.import_contributions()
        self.import_room_slots()
        self.db.commit()
        return self.report

    def import_people(self) -> None:
        for row in self.rows(T_PROFILE):
            user = self.user(row.get("姓名"), row.get("邮箱"))
            if user is not None and (seen := _datetime(row.get("首次使用时间"))):
                user.created_at = seen
        for row in self.rows(T_ADMIN):
            user = self.user(row.get("姓名"))
            if user is not None:
                user.role = UserRole.ADMIN
        cac_name = "cac"
        if cac_name in self.users:
            self.users[cac_name].participation_tracked = False

    def import_groups(self) -> None:
        for row in self.rows(T_GROUP):
            name = _text(row.get("组名"))
            if not name:
                self.report.skipped["groups (no name)"] += 1
                continue
            if any(g.name == name for g in self.groups.values()):
                name = f"{name} ({row['_id'][:6]})"
                self.report.warn(f"Duplicate group name renamed to {name}")
            group = Group(
                name=name[:80],
                goal=_text(row.get("主题目标")) or "—",
                time_boundary=_text(row.get("时间边界"))[:200] or "—",
                plan=_text(row.get("执行方案")) or "—",
                description=_text(row.get("简介")),
                status=GroupStatus.ACTIVE if _text(row.get("状态")) in ("", "活跃") else GroupStatus.ARCHIVED,
            )
            if created := _datetime(row.get("创建时间")):
                group.created_at = created
            self.db.add(group)
            self.groups[row["_id"]] = group
            self.report.created["groups"] += 1
            leader = self.user(row.get("组长"))
            if leader is not None:
                group.memberships.append(GroupMembership(user=leader, role=GroupRole.LEADER))
        self.db.flush()
        for row in self.rows(T_MEMBER):
            target = self.groups.get(_text(row.get("兴趣组ID")))
            member = self.user(row.get("成员姓名"), row.get("成员邮箱"))
            if target is None or member is None:
                self.report.skipped["group members (unknown group)"] += 1
                continue
            if any(m.user is member for m in target.memberships):
                continue
            role = GroupRole.LEADER if _text(row.get("成员身份")) == "组长" else GroupRole.MEMBER
            if role == GroupRole.LEADER and any(m.role == GroupRole.LEADER for m in target.memberships):
                role = GroupRole.MEMBER
            membership = GroupMembership(user=member, role=role)
            if joined := _datetime(row.get("加入时间")):
                membership.joined_at = joined
            target.memberships.append(membership)
            self.report.created["group memberships"] += 1

    def import_activities(self) -> None:
        for row in self.rows(T_ACTIVITY):
            d = _date(row.get("活动日期"))
            span = _time_range(row.get("活动时间"))
            title = _text(row.get("活动主题"))
            organizer = self.user(row.get("组织者姓名") or row.get("组织者学号"), row.get("组织者邮箱"))
            if d is None or span is None or organizer is None:
                self.report.skipped["activities (missing date, time or organiser)"] += 1
                self.report.warn(f"Skipped activity {title or row['_id']}: {row.get('活动日期')} {row.get('活动时间')}")
                continue
            kind = ActivityKind.MEETUP if _text(row.get("活动类型")).lower() == "cac有约" else ActivityKind.REGULAR
            activity = Activity(
                title=(title or "Untitled")[:200],
                kind=kind,
                date=d,
                start_time=span[0],
                end_time=span[1],
                room=self.room(row.get("活动教室")),
                video_url=_text(row.get("线上视频号"))[:500],
                group=self.groups.get(_text(row.get("所属兴趣组ID"))),
                organizer=organizer,
            )
            closed_at = _datetime(row.get("结项时间"))
            if closed_at or _text(row.get("活动状态")) == "已结项":
                activity.closed_at = closed_at or datetime.combine(d, span[1], tzinfo=get_settings().tz)
                activity.closed_on_time = _bool(row.get("准时结项"))
                # The closer's id is only known after flushing; resolved below.
                activity._legacy_closer = self.user(row.get("结项人"))  # type: ignore[attr-defined]
            speakers = [u for u in (self.user(n) for n in _names(row.get("分享者"))) if u is not None] or [organizer]
            seen: set[int] = set()
            for pos, speaker in enumerate(speakers):
                if id(speaker) in seen:
                    continue
                seen.add(id(speaker))
                activity.speakers.append(ActivitySpeaker(user=speaker, position=pos))
            self.db.add(activity)
            self.activities[row["_id"]] = activity
            self.report.created["activities"] += 1
        self.db.flush()
        for activity in self.activities.values():
            closer = getattr(activity, "_legacy_closer", None)
            if closer is not None:
                activity.closed_by_id = closer.id

    def import_signups(self) -> None:
        seen: set[tuple[int, int]] = set()
        for row in self.rows(T_SIGNUP):
            activity = self.activities.get(_text(row.get("关联活动")))
            user = self.user(row.get("姓名") or row.get("学号"), row.get("邮箱"))
            role = SIGNUP_ROLES.get(_text(row.get("角色")))
            if activity is None or user is None or role is None:
                self.report.skipped["signups (unknown activity, person or role)"] += 1
                continue
            self.db.flush()
            key = (activity.id, user.id)
            if key in seen:
                self.report.skipped["signups (duplicate)"] += 1
                continue
            seen.add(key)
            if phone := _text(row.get("联系电话")):
                user.phone = user.phone or phone[:32]
            signup = Signup(
                activity=activity,
                user=user,
                role=role,
                review_topic=_text(row.get("评议内容")),
                review_doc_url=_text(row.get("评议语雀链接"))[:500],
                review_submitted_at=_datetime(row.get("评议提交时间")),
                last_reminder_at=_datetime(row.get("上次评议提醒时间")),
            )
            self.db.add(signup)
            self.signups[row["_id"]] = signup
            self.report.created["signups"] += 1
        self.db.flush()

    def import_ratings(self) -> None:
        seen: set[tuple[int, int]] = set()
        for row in self.rows(T_RATING):
            signup = self.signups.get(_text(row.get("评议报名ID")))
            rater = self.user(row.get("评分人姓名"))
            try:
                score = round(float(_text(row.get("评分")) or 0))
                weight = int(float(_text(row.get("权重")) or 1))
            except ValueError:
                score, weight = 0, 1
            if signup is None or rater is None or not 1 <= score <= 10:
                self.report.skipped["ratings (unknown review or invalid score)"] += 1
                continue
            self.db.flush()
            if (signup.id, rater.id) in seen or rater.id == signup.user_id:
                self.report.skipped["ratings (duplicate or self)"] += 1
                continue
            seen.add((signup.id, rater.id))
            self.db.add(
                ReviewRating(
                    signup=signup, rater=rater, score=score, weight=max(1, weight), comment=_text(row.get("评分备注"))
                )
            )
            self.report.created["ratings"] += 1

    def import_invites(self) -> None:
        for row in self.rows(T_INVITE):
            activity = self.activities.get(_text(row.get("活动ID")))
            invitee = self.user(row.get("被邀请人"), row.get("被邀请邮箱"))
            if activity is None or invitee is None:
                self.report.skipped["invites (unknown activity or person)"] += 1
                continue
            invite = Invite(
                activity=activity,
                inviter=self.user(row.get("邀请人")),
                invitee=invitee,
                source=InviteSource.CAC if _text(row.get("邀请来源")) == "CAC特邀" else InviteSource.ORGANIZER,
                status=INVITE_STATUSES.get(_text(row.get("状态")), InviteStatus.PENDING),
            )
            if created := _datetime(row.get("邀请时间")):
                invite.created_at = created
            if updated := _datetime(row.get("状态更新时间")):
                invite.updated_at = updated
            self.db.add(invite)
            self.report.created["invites"] += 1

    def import_contributions(self) -> None:
        for row in self.rows(T_OUTPUT):
            user = self.user(row.get("姓名"))
            kind = OUTPUT_KINDS.get(_text(row.get("输出类型")))
            d = _date(row.get("输出日期"))
            if user is None or kind is None or d is None:
                self.report.skipped["contributions (incomplete)"] += 1
                continue
            self.db.add(Contribution(user=user, kind=kind, date=d, note=_text(row.get("备注"))[:500]))
            self.report.created["contributions"] += 1

    def import_room_slots(self) -> None:
        merged: dict[tuple[str, date], list[tuple[time, time]]] = defaultdict(list)
        for row in self.rows(T_SLOT):
            d = _date(row.get("日期"))
            span = _time_range(row.get("时间段"))
            room_name = _text(row.get("教室"))
            if d is None or span is None or not room_name:
                self.report.skipped["room slots (incomplete)"] += 1
                continue
            merged[(room_name, d)].append(span)
        for (room_name, d), spans in merged.items():
            room = self.room(room_name)
            # The old app stored one row per 30 minutes; join adjacent rows into one window.
            spans.sort()
            windows: list[list[time]] = []
            for start, end in spans:
                if windows and start <= windows[-1][1]:
                    windows[-1][1] = max(windows[-1][1], end)
                else:
                    windows.append([start, end])
            for start, end in windows:
                self.db.add(RoomSlot(room=room, date=d, start_time=start, end_time=end))
                self.report.created["room slots"] += 1


def run_import(db: Session, tables: dict[str, list[dict[str, Any]]]) -> ImportReport:
    return Importer(db, tables).run()

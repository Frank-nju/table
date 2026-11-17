"""Relational data model."""

from __future__ import annotations

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime, utcnow


def _enum(cls: type[enum.Enum]) -> Enum:
    return Enum(
        cls,
        native_enum=False,
        length=20,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


class UserRole(enum.StrEnum):
    MEMBER = "member"
    ADMIN = "admin"


class ActivityKind(enum.StrEnum):
    REGULAR = "regular"  # a share session organised by members
    MEETUP = "meetup"  # a CAC Meetup (CAC有约), held in a fixed weekly window


class SignupRole(enum.StrEnum):
    REVIEWER = "reviewer"
    OBSERVER = "observer"
    PARTICIPANT = "participant"  # CAC Meetups only


class InviteStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class InviteSource(enum.StrEnum):
    ORGANIZER = "organizer"
    CAC = "cac"


class GroupStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class GroupRole(enum.StrEnum):
    LEADER = "leader"
    MEMBER = "member"


class ContributionKind(enum.StrEnum):
    SHARING = "sharing"
    REVIEW = "review"
    MEETUP = "meetup"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # NULL = account not claimed yet
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.MEMBER)
    locale: Mapped[str] = mapped_column(String(8), default="en")
    phone: Mapped[str | None] = mapped_column(String(32))
    bio: Mapped[str | None] = mapped_column(String(280))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    participation_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_claimed(self) -> bool:
        return self.password_hash is not None


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    goal: Mapped[str] = mapped_column(Text)
    time_boundary: Mapped[str] = mapped_column(String(200))
    plan: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[GroupStatus] = mapped_column(_enum(GroupStatus), default=GroupStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    memberships: Mapped[list[GroupMembership]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="GroupMembership.joined_at"
    )


class GroupMembership(Base):
    __tablename__ = "group_memberships"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[GroupRole] = mapped_column(_enum(GroupRole), default=GroupRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    group: Mapped[Group] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(lazy="joined")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    capacity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RoomSlot(Base):
    """A window during which a room may be booked."""

    __tablename__ = "room_slots"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_room_slot_order"),
        Index("ix_room_slots_room_date", "room_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    room: Mapped[Room] = relationship(lazy="joined")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_activity_time_order"),
        Index("ix_activities_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[ActivityKind] = mapped_column(_enum(ActivityKind), default=ActivityKind.REGULAR)
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"), index=True)
    location: Mapped[str] = mapped_column(String(200), default="")
    video_url: Mapped[str] = mapped_column(String(500), default="")
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="SET NULL"), index=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_on_time: Mapped[bool | None] = mapped_column(Boolean)
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    room: Mapped[Room | None] = relationship(lazy="joined")
    group: Mapped[Group | None] = relationship(lazy="joined")
    organizer: Mapped[User] = relationship(foreign_keys=[organizer_id], lazy="joined")
    speakers: Mapped[list[ActivitySpeaker]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="ActivitySpeaker.position"
    )
    signups: Mapped[list[Signup]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="Signup.created_at"
    )
    invites: Mapped[list[Invite]] = relationship(back_populates="activity", cascade="all, delete-orphan")

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None


class ActivitySpeaker(Base):
    __tablename__ = "activity_speakers"

    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    activity: Mapped[Activity] = relationship(back_populates="speakers")
    user: Mapped[User] = relationship(lazy="joined")


class Signup(Base):
    __tablename__ = "signups"
    __table_args__ = (UniqueConstraint("activity_id", "user_id", name="uq_signup_activity_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[SignupRole] = mapped_column(_enum(SignupRole))
    review_topic: Mapped[str] = mapped_column(Text, default="")
    review_doc_url: Mapped[str] = mapped_column(String(500), default="")
    review_submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_reminder_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    activity: Mapped[Activity] = relationship(back_populates="signups")
    user: Mapped[User] = relationship(lazy="joined")
    ratings: Mapped[list[ReviewRating]] = relationship(back_populates="signup", cascade="all, delete-orphan")


class ReviewRating(Base):
    __tablename__ = "review_ratings"
    __table_args__ = (
        UniqueConstraint("signup_id", "rater_id", name="uq_rating_signup_rater"),
        CheckConstraint("score >= 1 AND score <= 10", name="ck_rating_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    signup_id: Mapped[int] = mapped_column(ForeignKey("signups.id", ondelete="CASCADE"), index=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    signup: Mapped[Signup] = relationship(back_populates="ratings")
    rater: Mapped[User] = relationship(lazy="joined")


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    inviter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[InviteSource] = mapped_column(_enum(InviteSource), default=InviteSource.ORGANIZER)
    status: Mapped[InviteStatus] = mapped_column(_enum(InviteStatus), default=InviteStatus.PENDING)
    message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    activity: Mapped[Activity] = relationship(back_populates="invites")
    inviter: Mapped[User | None] = relationship(foreign_keys=[inviter_id], lazy="joined")
    invitee: Mapped[User] = relationship(foreign_keys=[invitee_id], lazy="joined")


class Contribution(Base):
    """An output recorded manually by an admin (e.g. a talk given outside the platform)."""

    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[ContributionKind] = mapped_column(_enum(ContributionKind))
    date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")


class OutboxEmail(Base):
    """Emails are queued here and delivered by the worker, so a slow SMTP server never blocks a request."""

    __tablename__ = "outbox_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    to_address: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")


class JobRun(Base):
    """Records periodic jobs that must run at most once per period (e.g. the weekly report)."""

    __tablename__ = "job_runs"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    ran_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

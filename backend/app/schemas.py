"""Request and response models for the HTTP API."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from datetime import time as Time
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

from app.models import (
    ActivityKind,
    ContributionKind,
    GroupRole,
    GroupStatus,
    InviteSource,
    InviteStatus,
    SignupRole,
    UserRole,
)
from app.scheduling import ActivityState

HHMM = Annotated[Time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str)]


def _strip(value: str) -> str:
    return value.strip()


def _http_url(value: str) -> str:
    value = value.strip()
    if value and not value.lower().startswith(("http://", "https://")):
        raise ValueError("must start with http:// or https://")
    return value


Name = Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=64)]
Url = Annotated[str, AfterValidator(_http_url), Field(max_length=500)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
Locale = Literal["en", "zh"]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----- Users & auth -----


class UserBrief(Schema):
    id: int
    name: str


class Me(Schema):
    id: int
    name: str
    email: str | None
    role: UserRole
    locale: str
    phone: str | None
    bio: str | None
    created_at: datetime


class RegisterIn(BaseModel):
    name: Name
    email: EmailStr
    password: Password
    locale: Locale = "en"


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: Password


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: Password


class MeUpdate(BaseModel):
    name: Name | None = None
    locale: Locale | None = None
    phone: Annotated[str, AfterValidator(_strip), Field(max_length=32)] | None = None
    bio: Annotated[str, AfterValidator(_strip), Field(max_length=280)] | None = None


class AdminUserOut(Schema):
    id: int
    name: str
    email: str | None
    role: UserRole
    is_active: bool
    is_claimed: bool
    participation_tracked: bool
    created_at: datetime
    last_login_at: datetime | None


class AdminUserCreate(BaseModel):
    name: Name
    email: EmailStr | None = None


class AdminUserUpdate(BaseModel):
    name: Name | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    participation_tracked: bool | None = None


# ----- Rooms -----


class RoomOut(Schema):
    id: int
    name: str
    capacity: int | None
    notes: str
    is_active: bool


class RoomIn(BaseModel):
    name: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=80)]
    capacity: int | None = Field(default=None, ge=1, le=10000)
    notes: Annotated[str, AfterValidator(_strip), Field(max_length=200)] = ""
    is_active: bool = True


class RoomSlotOut(Schema):
    id: int
    room: RoomOut
    date: Date
    start_time: HHMM
    end_time: HHMM


class RoomSlotIn(BaseModel):
    room_id: int
    date: Date
    start_time: Time
    end_time: Time
    repeat_weeks: int = Field(default=1, ge=1, le=26, description="Create the same slot on this many weeks")


class RoomAvailability(BaseModel):
    room: RoomOut
    available: bool
    reason: str | None = None  # "no_slot" | "booked"
    booked_by: UserBrief | None = None
    booked_activity_title: str | None = None


# ----- Groups -----


class GroupMemberOut(BaseModel):
    user: UserBrief
    role: GroupRole
    joined_at: datetime


class GroupOut(BaseModel):
    id: int
    name: str
    goal: str
    time_boundary: str
    plan: str
    description: str
    status: GroupStatus
    created_at: datetime
    leader: UserBrief | None
    member_count: int
    is_member: bool = False


class GroupDetail(GroupOut):
    members: list[GroupMemberOut]
    recent_activities: list[ActivityOut] = []


class GroupIn(BaseModel):
    name: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=80)]
    goal: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=2000)]
    time_boundary: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=200)]
    plan: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=4000)]
    description: Annotated[str, AfterValidator(_strip), Field(max_length=2000)] = ""
    member_ids: list[int] = Field(default_factory=list, max_length=100)


class GroupUpdate(BaseModel):
    name: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=80)] | None = None
    goal: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=2000)] | None = None
    time_boundary: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=200)] | None = None
    plan: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=4000)] | None = None
    description: Annotated[str, AfterValidator(_strip), Field(max_length=2000)] | None = None
    status: GroupStatus | None = None


class TransferLeadershipIn(BaseModel):
    user_id: int


# ----- Activities -----


class SignupCounts(BaseModel):
    reviewers: int
    observers: int
    participants: int
    reviewer_limit: int | None  # None = unlimited (CAC Meetups)
    reviewer_spots_left: int | None


class ViewerContext(BaseModel):
    signup_id: int | None = None
    signup_role: SignupRole | None = None
    can_manage: bool = False
    pending_invite_id: int | None = None


class ActivityOut(BaseModel):
    id: int
    title: str
    description: str
    kind: ActivityKind
    date: Date
    start_time: HHMM
    end_time: HHMM
    state: ActivityState
    room: RoomOut | None
    location: str
    video_url: str
    group: UserBrief | None  # {id, name}
    organizer: UserBrief
    speakers: list[UserBrief]
    counts: SignupCounts
    closed_at: datetime | None
    closed_on_time: bool | None
    created_at: datetime
    viewer: ViewerContext = Field(default_factory=ViewerContext)


class RatingOut(BaseModel):
    id: int
    rater: UserBrief
    score: int
    weight: int
    comment: str
    updated_at: datetime


class SignupOut(BaseModel):
    id: int
    user: UserBrief
    role: SignupRole
    review_topic: str
    review_doc_url: str
    review_submitted_at: datetime | None
    created_at: datetime
    email: str | None = None  # visible to organisers, admins and the person themself
    phone: str | None = None
    average_score: float | None = None
    rating_count: int = 0
    my_score: int | None = None
    ratings: list[RatingOut] | None = None  # visible to the reviewer, organisers and admins


class ActivityDetail(ActivityOut):
    signups: list[SignupOut]


class ActivityPage(BaseModel):
    items: list[ActivityOut]
    total: int
    page: int
    page_size: int


class ActivityIn(BaseModel):
    title: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=200)]
    description: Annotated[str, AfterValidator(_strip), Field(max_length=5000)] = ""
    kind: ActivityKind = ActivityKind.REGULAR
    date: Date
    start_time: Time
    end_time: Time
    room_id: int | None = None
    location: Annotated[str, AfterValidator(_strip), Field(max_length=200)] = ""
    video_url: Url = ""
    group_id: int | None = None
    speaker_ids: list[int] = Field(default_factory=list, max_length=20)
    acknowledge_warnings: bool = False


class ActivityUpdate(BaseModel):
    title: Annotated[str, AfterValidator(_strip), Field(min_length=1, max_length=200)] | None = None
    description: Annotated[str, AfterValidator(_strip), Field(max_length=5000)] | None = None
    kind: ActivityKind | None = None
    date: Date | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    room_id: int | None = None
    location: Annotated[str, AfterValidator(_strip), Field(max_length=200)] | None = None
    video_url: Url | None = None
    group_id: int | None = None
    speaker_ids: list[int] | None = Field(default=None, max_length=20)
    acknowledge_warnings: bool = False


class Issue(BaseModel):
    code: str
    message: str
    activity_id: int | None = None
    activity_title: str | None = None


class ScheduleCheck(BaseModel):
    errors: list[Issue]
    warnings: list[Issue]


class CloseResult(BaseModel):
    activity: ActivityOut
    on_time: bool
    reminders_sent: int


# ----- Signups, reviews, ratings -----


class SignupIn(BaseModel):
    role: SignupRole
    review_topic: Annotated[str, AfterValidator(_strip), Field(max_length=2000)] = ""
    phone: Annotated[str, AfterValidator(_strip), Field(max_length=32)] | None = None


class ReviewDocIn(BaseModel):
    review_doc_url: Annotated[Url, Field(min_length=8)]


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=10)
    comment: Annotated[str, AfterValidator(_strip), Field(max_length=1000)] = ""


class ReviewToRate(BaseModel):
    signup_id: int
    reviewer: UserBrief
    review_doc_url: str
    review_topic: str
    activity: UserBrief  # {id, name=title}
    activity_date: Date
    weight: int


class MySignup(BaseModel):
    id: int
    role: SignupRole
    review_topic: str
    review_doc_url: str
    review_submitted_at: datetime | None
    average_score: float | None
    rating_count: int
    activity: ActivityOut


# ----- Invites -----


class InviteIn(BaseModel):
    invitee_id: int
    source: InviteSource = InviteSource.ORGANIZER
    message: Annotated[str, AfterValidator(_strip), Field(max_length=500)] = ""


class InviteStatusIn(BaseModel):
    status: InviteStatus


class InviteOut(BaseModel):
    id: int
    activity: UserBrief  # {id, name=title}
    activity_date: Date
    activity_start_time: HHMM
    inviter: UserBrief | None
    invitee: UserBrief
    source: InviteSource
    status: InviteStatus
    message: str
    created_at: datetime
    updated_at: datetime


# ----- Contributions -----


class ContributionIn(BaseModel):
    user_id: int
    kind: ContributionKind
    date: Date
    note: Annotated[str, AfterValidator(_strip), Field(max_length=500)] = ""


class ContributionOut(BaseModel):
    id: int
    user: UserBrief
    kind: ContributionKind
    date: Date
    note: str
    created_at: datetime


# ----- Stats -----


class CountEntry(BaseModel):
    user: UserBrief
    count: int


class ReviewQualityEntry(BaseModel):
    user: UserBrief
    score: float
    rating_count: int
    review_count: int


class PunctualityEntry(BaseModel):
    user: UserBrief
    closed_count: int
    on_time_count: int
    on_time_rate: float


class Leaderboards(BaseModel):
    sharing: list[CountEntry]
    participation: list[CountEntry]
    review_quality: list[ReviewQualityEntry]
    punctuality: list[PunctualityEntry]
    since: Date | None


class Overview(BaseModel):
    upcoming_count: int
    activities_this_month: int
    members: int
    groups: int


class ParticipationWatch(BaseModel):
    lookback_days: int
    tracked_count: int
    inactive: list[UserBrief]


class MonthlyReport(BaseModel):
    month: str
    activity_count: int
    regular_count: int
    meetup_count: int
    signup_count: int
    contribution_count: int
    active_organizers: int
    active_participants: int
    closed_count: int
    awaiting_close_count: int
    on_time_close_rate: float | None


class GroupHealth(BaseModel):
    group: UserBrief
    leader: UserBrief | None
    member_count: int
    active_member_count: int
    recent_activity_count: int
    awaiting_close_count: int
    score: int
    status: Literal["healthy", "at_risk", "inactive"]


class ReviewerWatchEntry(BaseModel):
    user: UserBrief
    score: float | None
    rating_count: int
    review_count: int
    missing_docs: int
    status: Literal["missing_docs", "low_score", "needs_feedback", "ok"]


class ConflictGroup(BaseModel):
    date: Date
    activities: list[ActivityOut]


class AdminDashboard(BaseModel):
    monthly: MonthlyReport
    participation: ParticipationWatch
    groups: list[GroupHealth]
    reviewers: list[ReviewerWatchEntry]
    conflicts: list[ConflictGroup]


class Task(BaseModel):
    kind: Literal[
        "inactive", "missing_email", "join_group", "pending_invite", "submit_review", "close_activity", "rate_reviews"
    ]
    priority: int
    activity: UserBrief | None = None
    invite_id: int | None = None
    signup_id: int | None = None
    count: int | None = None


class Recommendation(BaseModel):
    activity: ActivityOut
    suggested_role: SignupRole
    reasons: list[str]


class PersonalMetrics(BaseModel):
    share_count: int
    participation_count: int
    review_score: float | None
    review_rating_count: int
    on_time_rate: float | None
    closed_count: int
    recent_outputs: int
    lookback_days: int
    is_inactive: bool
    ranks: dict[str, int | None]


class MyGroup(BaseModel):
    id: int
    name: str
    role: GroupRole


class MeDashboard(BaseModel):
    metrics: PersonalMetrics
    tasks: list[Task]
    upcoming: list[MySignup]
    organizing: list[ActivityOut]
    groups: list[MyGroup]
    invites: list[InviteOut]
    recommendations: list[Recommendation]


class HistoryEntry(BaseModel):
    kind: Literal["spoke", "organized", "signed_up", "contribution"]
    date: Date
    activity: ActivityOut | None = None
    role: SignupRole | None = None
    contribution: ContributionOut | None = None


class PublicProfile(BaseModel):
    user: UserBrief
    bio: str | None
    joined_at: datetime
    groups: list[MyGroup]
    metrics: PersonalMetrics
    history: list[HistoryEntry]


class PublicConfig(BaseModel):
    app_name: str
    timezone: str
    time_grid: list[str]
    slot_minutes: int
    reviewer_limit: int
    meetup_weekday: int
    meetup_window: tuple[str, str]
    close_grace_minutes: int
    participation_lookback_days: int
    allow_registration: bool
    allowed_email_domains: list[str]
    mail_enabled: bool


GroupDetail.model_rebuild()
